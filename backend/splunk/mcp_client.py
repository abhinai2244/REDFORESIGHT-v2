import asyncio
import logging
import json
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Dict, Any, List, Optional
from backend.schemas import SplunkContext
from backend.splunk import spl_templates

logger = logging.getLogger(__name__)

class SplunkMCPClient:
    def __init__(self, mcp_url: str = "https://127.0.0.1:8089/services/mcp", token: Optional[str] = None):
        self.mcp_url = mcp_url
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}" if token else "",
            "Content-Type": "application/json"
        }

    async def _call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        try:
            async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
                res = await client.post(self.mcp_url, json=payload, headers=self.headers)
                if res.status_code == 200:
                    data = res.json()
                    if "error" in data:
                        return {"success": False, "error": data["error"]}
                    return {"success": True, "result": data.get("result", {})}
                return {"success": False, "error": f"HTTP {res.status_code}: {res.text}"}
        except Exception as e:
            logger.warning(f"MCP tool call failed: {e}")
            return {"success": False, "error": str(e)}

    async def health_check(self) -> bool:
        res = await self._call_mcp_tool("splunk_get_info", {})
        return res.get("success", False)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), retry=retry_if_exception_type(Exception))
    async def search(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        res = await self._call_mcp_tool("splunk_run_query", {"query": query, "count": limit})
        if res.get("success"):
            result_data = res.get("result", {})
            if isinstance(result_data, dict) and "results" in result_data:
                return result_data["results"]
            elif isinstance(result_data, list):
                return result_data
        return []

    async def pull_host_context(self, host: str) -> SplunkContext:
        proc_spl = spl_templates.PROCESS_CREATION_EVENTS.format(host=host, limit=10)
        auth_spl = spl_templates.AUTH_EVENTS_IN_WINDOW.format(host=host, limit=10)
        net_spl = spl_templates.NETWORK_CONNECTIONS_FROM_HOST.format(host=host, limit=10)
        reg_spl = spl_templates.REGISTRY_MODIFICATION_EVENTS.format(host=host, limit=10)

        results = await asyncio.gather(
            self.search(proc_spl),
            self.search(auth_spl),
            self.search(net_spl),
            self.search(reg_spl),
            return_exceptions=True
        )

        proc_res = results[0] if isinstance(results[0], list) else []
        auth_res = results[1] if isinstance(results[1], list) else []
        net_res = results[2] if isinstance(results[2], list) else []
        reg_res = results[3] if isinstance(results[3], list) else []

        return SplunkContext(
            host=host,
            process_events=proc_res,
            auth_events=auth_res,
            net_events=net_res,
            registry_events=reg_res
        )
