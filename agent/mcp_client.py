"""Connects to REAL MCP servers over stdio and exposes their tools as a ToolRegistry.
The MCP SDK is async, the agent is sync, so one background thread owns the event loop.
All connections live in ONE long-running task (anyio requires enter and exit in the same task)."""
import asyncio
import sys
import threading
from pathlib import Path
from agent.tools import Tool, ToolRegistry

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SERVERS = {
    "calc": "mcp_servers.calc_server.server",
    "docs": "mcp_servers.docs_server.server",
}


class MCPToolRegistry(ToolRegistry):
    def __init__(self, servers: dict[str, str] | None = None, startup_timeout: float = 30,
                 call_timeout: float = 30):
        super().__init__()
        self.servers = servers or DEFAULT_SERVERS
        self.call_timeout = call_timeout
        self._sessions: dict[str, object] = {}
        self._ready, self._error, self._stop = threading.Event(), None, None
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._main_future = asyncio.run_coroutine_threadsafe(self._main(), self._loop)
        if not self._ready.wait(startup_timeout):
            self.close()
            raise TimeoutError("MCP servers did not start in time")
        if self._error:
            self.close()
            raise RuntimeError(f"MCP startup failed: {self._error}")

    async def _main(self):
        from contextlib import AsyncExitStack
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        self._stop = asyncio.Event()
        try:
            async with AsyncExitStack() as stack:
                for name, module in self.servers.items():
                    params = StdioServerParameters(command=sys.executable, args=["-m", module],
                                                   cwd=str(PROJECT_ROOT))
                    read, write = await stack.enter_async_context(stdio_client(params))
                    session = await stack.enter_async_context(ClientSession(read, write))
                    await session.initialize()
                    self._sessions[name] = session
                    for t in (await session.list_tools()).tools:
                        props = (t.inputSchema or {}).get("properties", {})
                        required = set((t.inputSchema or {}).get("required", []))
                        params_desc = {k: (v.get("description") or v.get("type", "value")) for k, v in props.items()}
                        self.register(Tool(t.name, (t.description or "").strip().splitlines()[0] if t.description else "",
                                           params_desc, self._make_fn(name, t.name),
                                           optional=set(props) - required))
                self._ready.set()
                await self._stop.wait()
        except Exception as e:  # startup errors are reported to the constructor
            self._error = e
            self._ready.set()

    def _make_fn(self, server: str, tool: str):
        def call(**kwargs) -> str:
            fut = asyncio.run_coroutine_threadsafe(self._sessions[server].call_tool(tool, kwargs), self._loop)
            result = fut.result(timeout=self.call_timeout)
            text = "\n".join(c.text for c in result.content if getattr(c, "type", "") == "text")
            if result.isError:
                raise RuntimeError(text or "tool failed")
            return text
        return call

    def close(self):
        if self._stop is not None:
            self._loop.call_soon_threadsafe(self._stop.set)
            try:
                self._main_future.result(timeout=10)
            except Exception:
                pass
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()
