import asyncio
import logging
from typing import List, Dict, Any
from backend.agent.mitre_loader import load_mitre_techniques
from backend.memory.vector_store import VectorStore
from backend.schemas import MitreTechnique

logger = logging.getLogger(__name__)

class SemanticBrain:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.techniques_map: Dict[str, MitreTechnique] = {}

    def initialize(self):
        techniques = load_mitre_techniques()
        ids = []
        documents = []
        metadatas = []

        for tech in techniques:
            self.techniques_map[tech.technique_id] = tech
            ids.append(tech.technique_id)
            doc = f"Technique ID: {tech.technique_id}. Name: {tech.name}. Tactic: {tech.tactic}. Description: {tech.description}"
            documents.append(doc)
            metadatas.append({
                "technique_id": tech.technique_id,
                "name": tech.name,
                "tactic": tech.tactic,
                "platforms": ",".join(tech.platforms)
            })

        # Batch upsert in groups of 50
        batch_size = 50
        for i in range(0, len(ids), batch_size):
            self.vector_store.add_techniques(
                ids=ids[i:i+batch_size],
                documents=documents[i:i+batch_size],
                metadatas=metadatas[i:i+batch_size]
            )
        logger.info(f"Initialized SemanticBrain with {len(ids)} MITRE ATT&CK techniques.")

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        return self.vector_store.search_techniques(query=query, top_k=top_k)

    def get_technique(self, technique_id: str) -> MitreTechnique:
        return self.techniques_map.get(technique_id)
