"""Manages MCP server lifecycle for benchmark runs."""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client


# MCP server configurations per service
MCP_SERVERS: dict[str, dict] = {
    "github": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env_map": {"GITHUB_PERSONAL_ACCESS_TOKEN": "GITHUB_TOKEN"},
    },
    # Future services:
    # "postgres": { ... },
    # "google": { ... },
}


@asynccontextmanager
async def mcp_session(service: str) -> AsyncGenerator[ClientSession, None]:
    """Start an MCP server for a service and yield an initialized session.

    Usage:
        async with mcp_session("github") as session:
            tools = await session.list_tools()
            result = await session.call_tool("get_file_contents", {...})
    """
    server_config = MCP_SERVERS.get(service)
    if server_config is None:
        raise ValueError(f"No MCP server configured for service: {service}")

    # Build environment: map env vars (e.g., GITHUB_TOKEN -> GITHUB_PERSONAL_ACCESS_TOKEN)
    env = {"PATH": os.environ.get("PATH", "")}
    for server_key, local_key in server_config.get("env_map", {}).items():
        value = os.environ.get(local_key, "")
        if not value:
            raise ValueError(
                f"MCP server for {service} requires {local_key} to be set in environment"
            )
        env[server_key] = value

    server_params = StdioServerParameters(
        command=server_config["command"],
        args=server_config["args"],
        env=env,
    )

    devnull = open(os.devnull, "w")
    async with stdio_client(server_params, errlog=devnull) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


@asynccontextmanager
async def gateway_session(service: str) -> AsyncGenerator[ClientSession, None]:
    """Connect to MCP Gateway for a service and yield an initialized session.

    Uses streamable HTTP transport with Bearer token auth.  The Gateway URL
    and API key are read from environment variables GATEWAY_MCP_URL and
    GATEWAY_API_KEY respectively.

    Usage:
        async with gateway_session("github") as session:
            tools = await session.list_tools()
            result = await session.call_tool("get_file_contents", {...})
    """
    gateway_url = os.environ.get("GATEWAY_MCP_URL", "")
    gateway_api_key = os.environ.get("GATEWAY_API_KEY", "")
    if not gateway_url:
        raise ValueError("GATEWAY_MCP_URL must be set in environment")
    if not gateway_api_key:
        raise ValueError("GATEWAY_API_KEY must be set in environment")

    headers = {"Authorization": f"Bearer {gateway_api_key}"}

    async with streamablehttp_client(url=gateway_url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session
