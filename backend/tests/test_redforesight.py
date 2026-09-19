import unittest
import asyncio
from backend.schemas import ObservedSignal, MitreTechnique, PredictedMove
from backend.agent.game_tree import TacticClassifier, GameTreeEngine
from backend.memory.vector_store import VectorStore

class TestRedForesight(unittest.TestCase):
    def test_tactic_classifier(self):
        hits = [
            {"metadata": {"tactic": "Credential Access"}},
            {"metadata": {"tactic": "Credential Access"}},
            {"metadata": {"tactic": "Execution"}}
        ]
        tactic = TacticClassifier.classify_tactic(hits)
        self.assertEqual(tactic, "Credential Access")

    def test_game_tree_engine(self):
        techs = {
            "T1003.001": MitreTechnique(
                technique_id="T1003.001",
                name="LSASS Memory",
                tactic="Credential Access",
                description="Dumping memory",
                platforms=["Windows"]
            )
        }
        moves = GameTreeEngine.expand_and_score("Execution", techs)
        self.assertTrue(len(moves) > 0)
        self.assertEqual(moves[0]["technique_id"], "T1003.001")

if __name__ == "__main__":
    unittest.main()
