"""
Server-Sent Events (SSE) Event Broker
Streams real-time step execution with timings to the "Under the Hood" UI drawer.
"""
import asyncio
import json
import time
from typing import Dict, List, AsyncGenerator
from collections import defaultdict

class EventBroker:
    """Manages real-time event streaming per session for pipeline observability."""

    def __init__(self):
        self.listeners: Dict[str, List[asyncio.Queue]] = defaultdict(list)

    def publish(self, session_id: str, data: Dict[str, Any]):
        """Synchronously broadcasts an execution step event to active session listeners."""
        if not isinstance(data, dict):
            return
        event_str = f"data: {json.dumps(data)}\n\n"
        if session_id in self.listeners:
            for queue in self.listeners[session_id]:
                try:
                    queue.put_nowait(event_str)
                except Exception:
                    pass

    async def emit_step(
        self,
        session_id: str,
        step_name: str,
        detail: str,
        elapsed_ms: float,
        status: str = "success"
    ):
        """Broadcasts an execution step event to all active session listeners."""
        payload = {
            "timestamp": time.time(),
            "step_name": step_name,
            "detail": detail,
            "elapsed_ms": round(elapsed_ms, 2),
            "status": status
        }
        event_str = f"data: {json.dumps(payload)}\n\n"

        if session_id in self.listeners:
            for queue in self.listeners[session_id]:
                await queue.put(event_str)

    async def subscribe(self, session_id: str) -> AsyncGenerator[str, None]:
        """Subscribes an HTTP SSE connection to session events."""
        queue: asyncio.Queue = asyncio.Queue()
        self.listeners[session_id].append(queue)
        try:
            # Send initial connected handshake
            init_event = json.dumps({
                "timestamp": time.time(),
                "step_name": "connected",
                "detail": "Observability stream active",
                "elapsed_ms": 0.0,
                "status": "connected"
            })
            yield f"data: {init_event}\n\n"

            while True:
                msg = await queue.get()
                yield msg
        finally:
            self.listeners[session_id].remove(queue)
            if not self.listeners[session_id]:
                del self.listeners[session_id]

event_broker = EventBroker()
