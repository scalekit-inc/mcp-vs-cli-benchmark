"""Manages MCP server lifecycle for benchmark runs."""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


# Streamable-HTTP MCP server configurations per service
MCP_REMOTE_SERVERS: dict[str, dict] = {
    "github": {
        "url": "https://api.githubcopilot.com/mcp/",
        "auth_env": "GITHUB_TOKEN",  # GitHub PAT used as Bearer token
    },
    # Future services:
    # "google": { "url": "...", "auth_env": "GOOGLE_TOKEN" },
}


@asynccontextmanager
async def mcp_session(service: str) -> AsyncGenerator[ClientSession, None]:
    """Connect to an MCP server for a service and yield an initialized session.

    Uses the official remote streamable-HTTP MCP server (e.g. GitHub Copilot MCP).

    Usage:
        async with mcp_session("github") as session:
            tools = await session.list_tools()
            result = await session.call_tool("get_file_contents", {...})
    """
    server_config = MCP_REMOTE_SERVERS.get(service)
    if server_config is None:
        raise ValueError(f"No MCP server configured for service: {service}")

    token = os.environ.get(server_config["auth_env"], "")
    if not token:
        raise ValueError(
            f"MCP server for {service} requires {server_config['auth_env']} "
            "to be set in environment"
        )

    url = server_config["url"]
    headers = {"Authorization": f"Bearer {token}"}

    async with streamablehttp_client(
        url=url,
        headers=headers,
        timeout=60,
        sse_read_timeout=300,
    ) as (read, write, _):
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
