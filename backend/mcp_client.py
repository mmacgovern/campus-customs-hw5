"""Connects the agents to our MCP server (mcp_server/server.py) over stdio.

This is the only path from the backend to shop data. There is no second data
layer: agents (and later the approval route) go through these MCP tools.
"""

import json
import sys
from functools import lru_cache
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.toolsets import AbstractToolset

from .config import BACKEND_ONLY_TOOLS, MCP_SERVER_SCRIPT, PROJECT_ROOT


def _transport() -> StdioTransport:
    """Launch mcp_server/server.py with this project's Python."""
    return StdioTransport(
        command=sys.executable,
        args=[str(MCP_SERVER_SCRIPT)],
        cwd=str(PROJECT_ROOT),
        keep_alive=False,  # fresh server per connection; nothing tied to an old event loop
    )


@lru_cache(maxsize=1)
def get_mcp_toolset() -> MCPToolset:
    """One shared MCP connection for the agents."""
    # 'failed' shows tool errors to the model instead of crashing the run.
    return MCPToolset(Client(_transport()), id="campus-customs", tool_error_behavior="failed")


def backend_client() -> Client:
    """A plain MCP client for the API routes (they may call backend-only tools)."""
    return Client(_transport())


def tool_data(result: Any) -> Any:
    """Turn a FastMCP CallToolResult into the dict the tool returned."""
    data = result.structured_content
    if data is None:
        text = "".join(getattr(c, "text", "") for c in result.content)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"message": text}
    if isinstance(data, dict) and set(data) == {"result"}:
        return data["result"]
    return data


def agent_toolset(allowed_tools: frozenset[str]) -> AbstractToolset:
    """A filtered view of the MCP tools for one agent.

    Only tools on the agent's allow-list are visible, and backend-only tools
    (the pay tool, reject, table setup) are always hidden, whatever the allow-list says.
    """
    return get_mcp_toolset().filtered(
        lambda ctx, tool_def: tool_def.name in allowed_tools
        and tool_def.name not in BACKEND_ONLY_TOOLS
    )
