import asyncio
import logging
from typing import Callable, Optional
from backend.splunk.mcp_client import SplunkMCPClient
from backend.schemas import ObservedSignal

logger = logging.getLogger(__name__)

class SplunkWatcher:
    def __init__(self, mcp_client: SplunkMCPClient, callback: Callable, poll_interval: int = 5, index: str = "redforesight_range"):
        self.mcp_client = mcp_client
        self.callback = callback
        self.poll_interval = poll_interval
        self.index = index
        self.running = False
        self.seen_events = set()

    async def start(self):
        self.running = True
        logger.info(f"Started SplunkWatcher polling index='{self.index}' every {self.poll_interval}s...")
        while self.running:
            try:
                query = f"index={self.index} | table _time, host, sourcetype, Image, CommandLine, User, EventCode | sort - _time | head 10"
                events = await self.mcp_client.search(query)
                for ev in events:
                    event_id = f"{ev.get('_time')}_{ev.get('host')}_{ev.get('Image')}"
                    if event_id not in self.seen_events:
                        self.seen_events.add(event_id)
                        signal = ObservedSignal(
                            signal_id=f"sig_{len(self.seen_events)}",
                            source_index=self.index,
                            sourcetype=ev.get("sourcetype", "WinEventLog:Sysmon"),
                            host=ev.get("host", "UNKNOWN-HOST"),
                            user=ev.get("User"),
                            process_name=ev.get("Image"),
                            command_line=ev.get("CommandLine"),
                            raw_event=ev
                        )
                        asyncio.create_task(self.callback(signal))
            except Exception as e:
                logger.warning(f"Error in SplunkWatcher: {e}")
            await asyncio.sleep(self.poll_interval)

    def stop(self):
        self.running = False
