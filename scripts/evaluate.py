#!/usr/bin/env python3
"""
Evaluation Harness for RedForesight v2.
Runs real attack chains against the agent pipeline and evaluates Precision@1, Precision@3, and MRR.
"""

import asyncio
import json
import logging
from pathlib import Path
from backend.schemas import ObservedSignal, IncidentEpisode
from backend.agent.orchestrator import RedForesightOrchestrator
from backend.memory.agent_memory import AgentMemory
from backend.splunk.mcp_client import SplunkMCPClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_evaluation():
    memory = AgentMemory()
    memory.initialize()
    mcp_client = SplunkMCPClient()
    orchestrator = RedForesightOrchestrator(memory=memory, mcp_client=mcp_client)

    ground_truth_file = Path("fixtures/ground_truth_chain_a.json")
    if not ground_truth_file.exists():
        logger.error(f"Ground truth file not found: {ground_truth_file}")
        return

    with open(ground_truth_file, "r") as f:
        gt_data = json.load(f)

    steps = gt_data.get("steps", [])
    logger.info(f"Evaluating attack chain '{gt_data.get('chain_id')}' with {len(steps)} steps...")

    hits_top1 = 0
    hits_top3 = 0
    mrr_sum = 0.0
    total_evals = 0

    for i in range(len(steps) - 1):
        current_step = steps[i]
        next_step = steps[i + 1]

        signal = ObservedSignal(
            signal_id=f"eval_{i}",
            source_index="redforesight_range",
            sourcetype="WinEventLog:Sysmon",
            host=current_step.get("host", "VICTIM-01"),
            process_name=current_step.get("technique_id"),
            command_line=f"Executed {current_step.get('technique_id')}"
        )

        brief = await orchestrator.run(signal)
        predicted_ids = [m.technique_id for m in brief.predicted_moves]
        actual_next = next_step.get("technique_id")

        total_evals += 1
        rank = 0
        actual_base = actual_next.split('.')[0]
        pred_bases = [p.split('.')[0] for p in predicted_ids]

        if actual_next in predicted_ids:
            rank = predicted_ids.index(actual_next) + 1
        elif actual_base in pred_bases:
            rank = pred_bases.index(actual_base) + 1

        if rank == 1:
            hits_top1 += 1
        if 1 <= rank <= 3:
            hits_top3 += 1
        if rank > 0:
            mrr_sum += 1.0 / rank

        logger.info(f"Step {i+1}: Observed={current_step.get('technique_id')}, Actual Next={actual_next}, Predictions={predicted_ids[:3]}, Rank={rank}")

    p1 = (hits_top1 / total_evals * 100) if total_evals > 0 else 0.0
    p3 = (hits_top3 / total_evals * 100) if total_evals > 0 else 0.0
    mrr = (mrr_sum / total_evals) if total_evals > 0 else 0.0

    print("\n" + "="*50)
    print("REDFORESIGHT EVALUATION REPORT")
    print("="*50)
    print(f"Total Evaluations: {total_evals}")
    print(f"Precision@1:       {p1:.2f}%")
    print(f"Precision@3:       {p3:.2f}%")
    print(f"MRR:               {mrr:.3f}")
    print("="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(run_evaluation())
