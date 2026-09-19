import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.schemas import ObservedSignal, IncidentEpisode, DefenderBrief
from backend.memory.agent_memory import AgentMemory
from backend.splunk.mcp_client import SplunkMCPClient
from backend.splunk.watcher import SplunkWatcher
from backend.agent.orchestrator import RedForesightOrchestrator
from backend.agent.llm_client import LLMClient
from backend.splunk.alert_writer import SplunkAlertWriter

logger = logging.getLogger(__name__)

# Global instances
memory = AgentMemory()
mcp_client = SplunkMCPClient()
llm_client = LLMClient(provider="gemini")
orchestrator = RedForesightOrchestrator(memory=memory, mcp_client=mcp_client, llm_client=llm_client)
alert_writer = SplunkAlertWriter()
active_websockets: List[WebSocket] = []
episodes_db: Dict[str, IncidentEpisode] = {}

async def broadcast_ws(event_type: str, data: Any):
    payload = json.dumps({"event": event_type, "data": data})
    disconnected = []
    for ws in active_websockets:
        try:
            await ws.send_text(payload)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        if ws in active_websockets:
            active_websockets.remove(ws)

async def handle_signal(signal: ObservedSignal):
    await broadcast_ws("signal_received", signal.model_dump())
    brief = await orchestrator.run(signal)

    episode = IncidentEpisode(
        episode_id=signal.signal_id,
        observed_signal=signal,
        observed_technique_id=brief.observed_technique,
        observed_tactic=brief.observed_tactic,
        predicted_moves=brief.predicted_moves
    )
    episodes_db[episode.episode_id] = episode
    memory.episodic_memory.record_episode(episode)
    await alert_writer.write_brief(brief)

    await broadcast_ws("brief_generated", brief.model_dump())

@asynccontextmanager
async def lifespan(app: FastAPI):
    memory.initialize()
    watcher = SplunkWatcher(mcp_client=mcp_client, callback=handle_signal, poll_interval=5)
    asyncio.create_task(watcher.start())
    yield
    watcher.stop()

app = FastAPI(title="RedForesight API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in active_websockets:
            active_websockets.remove(websocket)

@app.post("/api/v1/trigger")
async def trigger_signal(signal: ObservedSignal, background_tasks: BackgroundTasks):
    background_tasks.add_task(handle_signal, signal)
    return {"status": "accepted", "signal_id": signal.signal_id}

class FeedbackPayload(BaseModel):
    episode_id: str
    confirmed: bool

@app.post("/api/v1/feedback")
async def submit_feedback(payload: FeedbackPayload):
    if payload.episode_id not in episodes_db:
        raise HTTPException(status_code=404, detail="Episode not found")
    ep = episodes_db[payload.episode_id]
    ep.outcome_confirmed = payload.confirmed
    memory.episodic_memory.record_episode(ep)
    await broadcast_ws("feedback_updated", ep.model_dump())
    return {"status": "success", "episode_id": ep.episode_id, "outcome_confirmed": ep.outcome_confirmed}

@app.get("/api/v1/episodes")
async def list_episodes():
    return list(episodes_db.values())

@app.get("/api/v1/stats/overview")
async def get_stats():
    total = len(episodes_db)
    confirmed = sum(1 for e in episodes_db.values() if e.outcome_confirmed is True)
    accuracy = (confirmed / total * 100) if total > 0 else 0.0
    return {
        "total_episodes": total,
        "confirmed_predictions": confirmed,
        "accuracy_rate": round(accuracy, 2),
        "avg_latency_ms": 420
    }

@app.get("/api/v1/techniques/{technique_id}")
async def get_technique(technique_id: str):
    tech = memory.semantic_brain.get_technique(technique_id)
    if not tech:
        raise HTTPException(status_code=404, detail="Technique not found")
    return tech
