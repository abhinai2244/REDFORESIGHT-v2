import asyncio
from typing import Dict, Any, List
from backend.memory.vector_store import VectorStore
from backend.memory.semantic import SemanticBrain
from backend.memory.episodic import EpisodicMemory

class AgentMemory:
    def __init__(self, persist_dir: str = "./chroma_db"):
        self.vector_store = VectorStore(persist_dir=persist_dir)
        self.semantic_brain = SemanticBrain(self.vector_store)
        self.episodic_memory = EpisodicMemory(self.vector_store)

    def initialize(self):
        self.semantic_brain.initialize()

    async def search_all(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        semantic_fut = loop.run_in_executor(None, self.semantic_brain.search, query, top_k)
        episodic_fut = loop.run_in_executor(None, self.episodic_memory.search_similar_episodes, query, top_k)
        semantic_res, episodic_res = await asyncio.gather(semantic_fut, episodic_fut)
        return {
            "semantic_techniques": semantic_res,
            "similar_episodes": episodic_res
        }
