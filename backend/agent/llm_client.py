import os
import json
import logging
import httpx
from typing import List, Dict, Any, Optional
from backend.schemas import ObservedSignal, SplunkContext

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self, provider: str = "gemini", api_key: Optional[str] = None):
        self.provider = provider.lower()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")

    async def rescore_moves(
        self,
        candidate_moves: List[Dict[str, Any]],
        signal: ObservedSignal,
        splunk_context: Optional[SplunkContext]
    ) -> List[Dict[str, Any]]:
        prompt = self._build_prompt(candidate_moves, signal, splunk_context)

        if self.provider == "gemini" and self.api_key:
            return await self._call_gemini(prompt, candidate_moves)
        elif self.provider == "anthropic" and self.api_key:
            return await self._call_anthropic(prompt, candidate_moves)
        elif self.provider == "ollama":
            return await self._call_ollama(prompt, candidate_moves)

        logger.info("Using heuristic/fallback LLM scoring.")
        return candidate_moves

    def _build_prompt(self, candidate_moves: List[Dict[str, Any]], signal: ObservedSignal, splunk_context: Optional[SplunkContext]) -> str:
        moves_str = json.dumps(candidate_moves, indent=2)
        cmd = signal.command_line or signal.process_name or "Unknown"
        host = signal.host
        return f"""
You are an expert Red Team Operator analyzing a active cyber incident.
Observed Activity: Host={host}, Command/Process={cmd}

Candidate Next Moves from Game Tree:
{moves_str}

Evaluate the candidate moves against real attacker behavior. Re-assign realistic probabilities (0.0 to 1.0) and provide concise reasoning for each move.
Return ONLY valid JSON in this format:
[
  {{
    "technique_id": "T1003.001",
    "llm_adjusted_probability": 0.85,
    "reasoning": "Reasoning here..."
  }}
]
"""

    async def _call_gemini(self, prompt: str, candidate_moves: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                    return self._parse_llm_json(text, candidate_moves)
        except Exception as e:
            logger.warning(f"Gemini API call failed: {e}")
        return candidate_moves

    async def _call_anthropic(self, prompt: str, candidate_moves: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}]
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    text = res.json()["content"][0]["text"]
                    return self._parse_llm_json(text, candidate_moves)
        except Exception as e:
            logger.warning(f"Anthropic API call failed: {e}")
        return candidate_moves

    async def _call_ollama(self, prompt: str, candidate_moves: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    text = res.json()["response"]
                    return self._parse_llm_json(text, candidate_moves)
        except Exception as e:
            logger.warning(f"Ollama call failed: {e}")
        return candidate_moves

    def _parse_llm_json(self, text: str, candidate_moves: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        try:
            start = text.find("[")
            end = text.rfind("]") + 1
            if start != -1 and end != 0:
                json_str = text[start:end]
                parsed = json.loads(json_str)
                prob_map = {item["technique_id"]: item for item in parsed if "technique_id" in item}
                for move in candidate_moves:
                    tid = move["technique_id"]
                    if tid in prob_map:
                        move["llm_adjusted_probability"] = prob_map[tid].get("llm_adjusted_probability", move["raw_probability"])
                        move["reasoning"] = prob_map[tid].get("reasoning", move["reasoning"])
        except Exception as e:
            logger.warning(f"Error parsing LLM JSON: {e}")
        return candidate_moves
