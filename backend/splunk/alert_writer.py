import logging
import json
import httpx
from typing import Dict, Any, Optional
from backend.schemas import DefenderBrief

logger = logging.getLogger(__name__)

class SplunkAlertWriter:
    def __init__(self, hec_url: str = "https://127.0.0.1:8088/services/collector/event", token: Optional[str] = None):
        self.hec_url = hec_url
        self.token = token

    async def write_brief(self, brief: DefenderBrief) -> bool:
        if not self.token:
            logger.info(f"Splunk Alert Writer (local fallback): Brief {brief.brief_id} generated for host {brief.host}")
            return True

        headers = {
            "Authorization": f"Splunk {self.token}",
            "Content-Type": "application/json"
        }
        payload = {
            "index": "redforesight_range",
            "sourcetype": "redforesight:brief",
            "event": brief.model_dump()
        }

        try:
            async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
                res = await client.post(self.hec_url, json=payload, headers=headers)
                if res.status_code == 200:
                    logger.info(f"Successfully posted brief {brief.brief_id} to Splunk HEC")
                    return True
        except Exception as e:
            logger.warning(f"Failed to post brief to Splunk HEC: {e}")

        return False
