from typing import List, Dict, Any
from backend.schemas import MitreTechnique

KILL_CHAIN_NEXT: Dict[str, List[str]] = {
    "Reconnaissance": ["Resource Development", "Initial Access"],
    "Resource Development": ["Initial Access"],
    "Initial Access": ["Execution", "Persistence", "Defense Evasion"],
    "Execution": ["Persistence", "Privilege Escalation", "Discovery", "Credential Access"],
    "Persistence": ["Privilege Escalation", "Defense Evasion"],
    "Privilege Escalation": ["Defense Evasion", "Credential Access", "Discovery"],
    "Defense Evasion": ["Credential Access", "Discovery", "Execution"],
    "Credential Access": ["Lateral Movement", "Discovery", "Collection"],
    "Discovery": ["Lateral Movement", "Collection", "Credential Access"],
    "Lateral Movement": ["Execution", "Collection", "Command And Control"],
    "Collection": ["Exfiltration", "Command And Control"],
    "Command And Control": ["Exfiltration", "Impact"],
    "Exfiltration": ["Impact"],
    "Impact": []
}

class TacticClassifier:
    @staticmethod
    def classify_tactic(semantic_hits: List[Dict[str, Any]]) -> str:
        if not semantic_hits:
            return "Initial Access"
        tactic_counts = {}
        for hit in semantic_hits:
            meta = hit.get("metadata", {})
            tactic = meta.get("tactic", "Initial Access")
            tactic_counts[tactic] = tactic_counts.get(tactic, 0) + 1
        sorted_tactics = sorted(tactic_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_tactics[0][0]

class GameTreeEngine:
    @staticmethod
    def expand_and_score(
        current_tactic: str,
        all_techniques: Dict[str, MitreTechnique],
        semantic_hits: List[Dict[str, Any]] = None,
        top_limit: int = 5
    ) -> List[Dict[str, Any]]:
        next_tactics = KILL_CHAIN_NEXT.get(current_tactic, ["Execution", "Discovery"])
        candidate_moves = []

        hit_distances = {}
        if semantic_hits:
            for hit in semantic_hits:
                tid = hit.get("technique_id")
                dist = hit.get("distance", 0.5)
                hit_distances[tid] = dist

        for tech_id, tech in all_techniques.items():
            if tech.tactic in next_tactics or tech.tactic == current_tactic:
                dist = hit_distances.get(tech.technique_id, 0.5)
                # Convert distance to similarity score (0.0 to 1.0)
                sim_boost = max(0.0, 1.0 - dist)
                p_semantic = 0.7 + (0.25 * sim_boost) if tech.tactic in next_tactics else 0.4
                p_platform = 0.9 if "Windows" in tech.platforms else 0.4
                p_severity = 0.85
                raw_prob = p_semantic * p_platform * p_severity
                candidate_moves.append({
                    "technique_id": tech.technique_id,
                    "technique_name": tech.name,
                    "tactic": tech.tactic,
                    "raw_probability": round(raw_prob, 3),
                    "llm_adjusted_probability": round(raw_prob, 3),
                    "reasoning": f"Game-tree transition from {current_tactic} to {tech.tactic} (sim score: {sim_boost:.2f})"
                })

        candidate_moves.sort(key=lambda x: x["raw_probability"], reverse=True)
        pruned_moves = candidate_moves[:top_limit]

        total = sum(m["raw_probability"] for m in pruned_moves) or 1.0
        for m in pruned_moves:
            norm = round(m["raw_probability"] / total, 3)
            m["raw_probability"] = norm
            m["llm_adjusted_probability"] = norm

        return pruned_moves
