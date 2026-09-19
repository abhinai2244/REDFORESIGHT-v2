import logging
import json
from typing import List, Dict, Any, Optional
from backend.memory.vector_store import VectorStore
from backend.schemas import IncidentEpisode

logger = logging.getLogger(__name__)

class EpisodicMemory:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

    def record_episode(self, episode: IncidentEpisode):
        doc = f"Episode: {episode.episode_id}. Host: {episode.observed_signal.host}. Process: {episode.observed_signal.process_name}. Command: {episode.observed_signal.command_line}. Tactic: {episode.observed_tactic}. Technique: {episode.observed_technique_id}"
        metadata = {
            "episode_id": episode.episode_id,
            "host": episode.observed_signal.host,
            "observed_tactic": episode.observed_tactic or "",
            "observed_technique_id": episode.observed_technique_id or "",
            "outcome_confirmed": str(episode.outcome_confirmed) if episode.outcome_confirmed is not None else "pending",
            "ground_truth_next_technique": episode.ground_truth_next_technique or ""
        }
        self.vector_store.add_episode(episode.episode_id, doc, metadata)

    def search_similar_episodes(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        return self.vector_store.search_episodes(query, top_k)
