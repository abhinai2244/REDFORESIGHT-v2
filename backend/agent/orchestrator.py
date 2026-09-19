import logging
import asyncio
from typing import Dict, Any, List, TypedDict, Optional
from langgraph.graph import StateGraph, END
from backend.schemas import ObservedSignal, SplunkContext, DefenderBrief, PredictedMove
from backend.agent.game_tree import TacticClassifier, GameTreeEngine
from backend.memory.agent_memory import AgentMemory
from backend.splunk.mcp_client import SplunkMCPClient

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    signal: ObservedSignal
    splunk_context: Optional[SplunkContext]
    classified_tactic: Optional[str]
    candidate_moves: List[Dict[str, Any]]
    final_brief: Optional[DefenderBrief]

class RedForesightOrchestrator:
    def __init__(self, memory: AgentMemory, mcp_client: SplunkMCPClient, llm_client: Any = None):
        self.memory = memory
        self.mcp_client = mcp_client
        self.llm_client = llm_client
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)

        workflow.add_node("ingest_signal", self.node_ingest_signal)
        workflow.add_node("pull_splunk_context", self.node_pull_splunk_context)
        workflow.add_node("classify_tactic", self.node_classify_tactic)
        workflow.add_node("expand_game_tree", self.node_expand_game_tree)
        workflow.add_node("score_and_prune", self.node_score_and_prune)
        workflow.add_node("generate_brief", self.node_generate_brief)

        workflow.set_entry_point("ingest_signal")
        workflow.add_edge("ingest_signal", "pull_splunk_context")
        workflow.add_edge("pull_splunk_context", "classify_tactic")
        workflow.add_edge("classify_tactic", "expand_game_tree")
        workflow.add_edge("expand_game_tree", "score_and_prune")
        workflow.add_edge("score_and_prune", "generate_brief")
        workflow.add_edge("generate_brief", END)

        return workflow.compile()

    async def node_ingest_signal(self, state: AgentState) -> Dict[str, Any]:
        logger.info(f"Ingesting signal: {state['signal'].signal_id}")
        return {"signal": state["signal"]}

    async def node_pull_splunk_context(self, state: AgentState) -> Dict[str, Any]:
        host = state["signal"].host
        context = await self.mcp_client.pull_host_context(host)
        return {"splunk_context": context}

    async def node_classify_tactic(self, state: AgentState) -> Dict[str, Any]:
        proc = state['signal'].process_name or ""
        cmd = state['signal'].command_line or ""

        # Check direct technique ID lookup first
        tech = self.memory.semantic_brain.get_technique(proc)
        if tech:
            return {"classified_tactic": tech.tactic}

        query = f"{proc} {cmd}".strip()
        semantic_hits = self.memory.semantic_brain.search(query, top_k=5)
        tactic = TacticClassifier.classify_tactic(semantic_hits)
        return {"classified_tactic": tactic}

    async def node_expand_game_tree(self, state: AgentState) -> Dict[str, Any]:
        tactic = state.get("classified_tactic") or "Execution"
        all_techs = self.memory.semantic_brain.techniques_map
        moves = GameTreeEngine.expand_and_score(tactic, all_techs, top_limit=5)
        return {"candidate_moves": moves}

    async def node_score_and_prune(self, state: AgentState) -> Dict[str, Any]:
        moves = state.get("candidate_moves", [])
        if self.llm_client and moves:
            try:
                moves = await self.llm_client.rescore_moves(moves, state["signal"], state.get("splunk_context"))
            except Exception as e:
                logger.warning(f"LLM rescoring failed: {e}")
        return {"candidate_moves": moves}

    async def node_generate_brief(self, state: AgentState) -> Dict[str, Any]:
        moves = [PredictedMove(**m) for m in state.get("candidate_moves", [])]
        brief = DefenderBrief(
            brief_id=f"brief_{state['signal'].signal_id}",
            episode_id=state['signal'].signal_id,
            host=state['signal'].host,
            observed_technique=state['signal'].process_name,
            observed_tactic=state.get("classified_tactic"),
            predicted_moves=moves,
            splunk_context_summary=f"Process events: {len(state['splunk_context'].process_events) if state.get('splunk_context') else 0}",
            recommended_mitigations=["Isolate host if confidence > 0.75", "Rotate local admin credentials"],
            llm_adversarial_narrative="Adversary likely preparing lateral movement or credential access."
        )
        return {"final_brief": brief}

    async def run(self, signal: ObservedSignal) -> DefenderBrief:
        initial_state = {
            "signal": signal,
            "splunk_context": None,
            "classified_tactic": None,
            "candidate_moves": [],
            "final_brief": None
        }
        res = await self.graph.ainvoke(initial_state)
        return res["final_brief"]
