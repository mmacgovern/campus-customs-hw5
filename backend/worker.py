"""A background thread with its own event loop for all MCP and agent work.

Why: on Windows, `uvicorn --reload` runs the app on an event loop that cannot
start subprocesses, and our MCP server is a subprocess (stdio). This thread
always uses a loop that can (Proactor on Windows), so the exact command
`uvicorn main:app --reload --port 8000` works. FastAPI routes hand coroutines
to this loop and await the result.
"""

import asyncio
import sys
import threading
from concurrent.futures import Future
from typing import Any, Coroutine

from fastmcp import Client

from .mcp_client import backend_client, tool_data


class Worker:
    def __init__(self) -> None:
        self.loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._client: Client | None = None
        self._client_lock: asyncio.Lock | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        ready = threading.Event()

        def _run() -> None:
            self.loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self._client_lock = asyncio.Lock()
            ready.set()
            self.loop.run_forever()

        self._thread = threading.Thread(target=_run, name="agent-worker", daemon=True)
        self._thread.start()
        ready.wait()
        self.wait(self._open_client())

    def stop(self) -> None:
        if self.loop is None:
            return
        try:
            self.wait(self._close_client(), timeout=10)
        finally:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self._thread.join(timeout=10)
            self.loop = self._thread = None

    # ---- run coroutines on the worker loop ----
    def submit(self, coro: Coroutine) -> Future:
        """Start a coroutine on the worker loop; returns immediately."""
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def wait(self, coro: Coroutine, timeout: float | None = 60) -> Any:
        return self.submit(coro).result(timeout)

    async def run(self, coro: Coroutine) -> Any:
        """Await a coroutine running on the worker loop from a FastAPI route."""
        return await asyncio.wrap_future(self.submit(coro))

    # ---- long-lived MCP client for the routes ----
    async def _open_client(self) -> None:
        self._client = backend_client()
        await self._client.__aenter__()

    async def _close_client(self) -> None:
        if self._client is not None:
            await self._client.__aexit__(None, None, None)
            self._client = None

    async def _call(self, name: str, args: dict) -> Any:
        async with self._client_lock:  # one request at a time on the shared session
            if self._client is None or not self._client.is_connected():
                await self._open_client()
            result = await self._client.call_tool(name, args, raise_on_error=False)
        return tool_data(result)

    async def call_tool(self, name: str, **args: Any) -> Any:
        """Call one MCP tool (any tool, including backend-only ones)."""
        return await self.run(self._call(name, args))


worker = Worker()
