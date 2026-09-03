"""
ARIA MCP Client Manager
Connects to multiple MCP servers (stdio subprocess transport).
Exposes their tools as callable Python functions for Gemini's tool-use loop.

Usage:
    manager = MCPManager(servers_config)
    manager.start()                         # connect to all servers
    tools = manager.get_tool_functions()    # list of Python functions
    result = manager.call_tool("add_note", {"content": "buy milk"})
    manager.stop()
"""

import asyncio
import threading
import subprocess
import sys
import os
from typing import Any
from contextlib import AsyncExitStack

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("[MCPManager] ⚠ mcp package not installed — MCP tools disabled")


# ── Default built-in servers (always enabled, no config needed) ──────────────
def _python(script: str) -> dict:
    """Helper to define a Python-based MCP server entry."""
    return {
        "name": os.path.splitext(os.path.basename(script))[0],
        "command": sys.executable,
        "args": [os.path.join(os.path.dirname(__file__), '..', 'mcp_servers', script)],
        "enabled": True,
    }

BUILTIN_SERVERS = [
    _python("notes_server.py"),
    _python("file_browser_server.py"),
    _python("system_info_server.py"),
]


class MCPManager:
    """
    Manages MCP client connections to multiple servers.
    Runs an asyncio event loop in a background thread.
    All public methods are synchronous (blocking until result ready).
    """

    def __init__(self, extra_servers: list[dict] | None = None):
        self._servers_config = BUILTIN_SERVERS + (extra_servers or [])
        self._sessions: dict[str, ClientSession]  = {}   # name → session
        self._tool_map: dict[str, tuple[str, Any]] = {}  # tool_name → (server_name, tool_schema)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._stack  = AsyncExitStack()
        self._ready  = threading.Event()
        self._tools_cache: list[dict] = []

    # ── Public API ─────────────────────────────────────────────────────────────

    def start(self):
        """Start background event loop and connect to all enabled servers."""
        if not MCP_AVAILABLE:
            return
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="ARIA-MCP")
        self._thread.start()
        self._ready.wait(timeout=20)   # wait up to 20s for connections
        print(f"[MCPManager] Ready — {len(self._tool_map)} tools from {len(self._sessions)} servers")

    def stop(self):
        """Disconnect from all servers and stop the background loop."""
        if self._loop and self._loop.is_running():
            try:
                future = asyncio.run_coroutine_threadsafe(self._cleanup(), self._loop)
                future.result(timeout=2)
            except Exception:
                pass
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except Exception:
                pass

    def get_tool_schemas(self) -> list[dict]:
        """Return a list of {name, description, inputSchema} dicts for all MCP tools."""
        return list(self._tools_cache)

    def call_tool(self, tool_name: str, arguments: dict) -> str:
        """Call an MCP tool synchronously. Returns the result as a string."""
        if not MCP_AVAILABLE or not self._loop:
            return f"MCP not available."
        if tool_name not in self._tool_map:
            return f"Unknown MCP tool: {tool_name}"
        future = asyncio.run_coroutine_threadsafe(
            self._async_call_tool(tool_name, arguments), self._loop
        )
        try:
            return future.result(timeout=15)
        except Exception as e:
            return f"Tool error: {e}"

    def has_tool(self, tool_name: str) -> bool:
        return tool_name in self._tool_map

    # ── Internal async machinery ───────────────────────────────────────────────

    def _run_loop(self):
        """Background thread: runs the asyncio event loop forever."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect_all())

    async def _connect_all(self):
        """Connect to every enabled server and collect their tools."""
        await self._stack.__aenter__()
        for srv in self._servers_config:
            if not srv.get("enabled", True):
                continue
            await self._connect_server(srv)
        self._ready.set()
        # Keep the loop alive until shutdown
        try:
            await asyncio.Event().wait()
        except (asyncio.CancelledError, GeneratorExit):
            pass

    async def _connect_server(self, srv: dict):
        """Connect to a single MCP server via stdio."""
        name = srv["name"]
        cmd  = srv["command"]
        args = srv.get("args", [])
        env  = {**os.environ, **srv.get("env", {})}

        try:
            params = StdioServerParameters(command=cmd, args=args, env=env)
            read, write = await self._stack.enter_async_context(stdio_client(params))
            session     = await self._stack.enter_async_context(ClientSession(read, write))
            await session.initialize()

            # List tools from this server
            result = await session.list_tools()
            self._sessions[name] = session

            for tool in result.tools:
                self._tool_map[tool.name] = (name, tool)
                self._tools_cache.append({
                    "name":        tool.name,
                    "description": tool.description or "",
                    "inputSchema": tool.inputSchema if hasattr(tool, 'inputSchema') else {},
                })
            print(f"[MCPManager] [OK] '{name}' - {len(result.tools)} tools: "
                  f"{[t.name for t in result.tools]}")

        except Exception as e:
            print(f"[MCPManager] [FAIL] Failed to connect '{name}': {e}")

    async def _async_call_tool(self, tool_name: str, arguments: dict) -> str:
        """Actually call the tool on the right session."""
        server_name, _schema = self._tool_map[tool_name]
        session = self._sessions.get(server_name)
        if not session:
            return f"Server '{server_name}' not connected."

        result = await session.call_tool(tool_name, arguments=arguments)

        # Extract text from result content
        parts = []
        for c in result.content:
            if hasattr(c, 'text'):
                parts.append(c.text)
            else:
                parts.append(str(c))
        return "\n".join(parts) if parts else "(no output)"

    async def _cleanup(self):
        try:
            await self._stack.aclose()
        except Exception:
            pass
