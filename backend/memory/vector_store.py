import os
import logging
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, persist_dir: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_dir, settings=Settings(anonymized_telemetry=False))
        self.mitre_collection = self.client.get_or_create_collection(
            name="mitre_techniques",
            metadata={"hnsw:space": "cosine"}
        )
        self.episodic_collection = self.client.get_or_create_collection(
            name="incident_episodes",
            metadata={"hnsw:space": "cosine"}
        )

    def add_techniques(self, ids: List[str], documents: List[str], metadatas: List[Dict[str, Any]]):
        if ids:
            self.mitre_collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )

    def search_techniques(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        results = self.mitre_collection.query(
            query_texts=[query],
            n_results=top_k
        )
        hits = []
        if results and results.get("ids") and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                hits.append({
                    "technique_id": results["ids"][0][i],
                    "document": results["documents"][0][i] if results.get("documents") else "",
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "distance": results["distances"][0][i] if results.get("distances") else 0.0
                })
        return hits

    def add_episode(self, episode_id: str, document: str, metadata: Dict[str, Any]):
        self.episodic_collection.upsert(
            ids=[episode_id],
            documents=[document],
            metadatas=metadata
        )

    def search_episodes(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        results = self.episodic_collection.query(
            query_texts=[query],
            n_results=top_k
        )
        hits = []
        if results and results.get("ids") and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                hits.append({
                    "episode_id": results["ids"][0][i],
                    "document": results["documents"][0][i] if results.get("documents") else "",
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "distance": results["distances"][0][i] if results.get("distances") else 0.0
                })
        return hits
