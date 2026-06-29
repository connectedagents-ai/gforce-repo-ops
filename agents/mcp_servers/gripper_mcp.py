"""
Gripper MCP Server for G Force
--------------------------------
Bridges OpenClaw/Hermes to the physical OpenClaw gripper
running on a Raspberry Pi via FastAPI.

Tools:
  - gripper_open: Fully open the gripper
  - gripper_close: Close the gripper
  - gripper_set_force: Set force limit
  - gripper_move: Move to position (0-100%)
  - gripper_status: Get current state

Safety: All commands are validated against PI_MAX_FORCE limit.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
import structlog
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

log = structlog.get_logger()

server = Server("gforce-gripper-mcp")


def _get_pi_base_url() -> str:
    host = os.environ.get("PI_HOST", "localhost")
    port = os.environ.get("PI_GRIPPER_PORT", "8080")
    return f"http://{host}:{port}"


def _get_max_force() -> int:
    return int(os.environ.get("PI_MAX_FORCE", "80"))


def _get_api_key() -> str | None:
    return os.environ.get("PI_GRIPPER_API_KEY") or None


def _headers() -> dict[str, str]:
    key = _get_api_key()
    if key:
        return {"X-API-Key": key}
    return {}


TOOLS: list[Tool] = [
    Tool(
        name="gripper_open",
        description="Fully open the OpenClaw gripper",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="gripper_close",
        description="Close the OpenClaw gripper at current force setting",
        inputSchema={
            "type": "object",
            "properties": {
                "force": {
                    "type": "integer",
                    "description": "Force percentage 1-100 (default: 50). Safety max enforced server-side.",
                    "default": 50,
                }
            },
        },
    ),
    Tool(
        name="gripper_set_force",
        description="Set the gripper force limit",
        inputSchema={
            "type": "object",
            "required": ["force"],
            "properties": {
                "force": {"type": "integer", "minimum": 1, "maximum": 100}
            },
        },
    ),
    Tool(
        name="gripper_move",
        description="Move gripper to a specific position (0=closed, 100=fully open)",
        inputSchema={
            "type": "object",
            "required": ["position"],
            "properties": {
                "position": {"type": "integer", "minimum": 0, "maximum": 100}
            },
        },
    ),
    Tool(
        name="gripper_status",
        description="Get current gripper position, force, and state",
        inputSchema={"type": "object", "properties": {}},
    ),
]


@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    base_url = _get_pi_base_url()
    max_force = _get_max_force()

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            if name == "gripper_open":
                resp = await client.post(f"{base_url}/open", headers=_headers())
                resp.raise_for_status()
                data = resp.json()
                return [TextContent(type="text", text=f"✅ Gripper opened. State: {data}")]

            elif name == "gripper_close":
                force = min(arguments.get("force", 50), max_force)
                resp = await client.post(
                    f"{base_url}/close",
                    json={"force": force},
                    headers=_headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                return [TextContent(type="text", text=f"✅ Gripper closed at {force}% force. State: {data}")]

            elif name == "gripper_set_force":
                force = arguments["force"]
                if force > max_force:
                    return [TextContent(
                        type="text",
                        text=f"⚠️ Safety limit: Force {force}% exceeds max {max_force}%. "
                             f"Clamped to {max_force}%.",
                    )]
                resp = await client.post(
                    f"{base_url}/set_force/{force}",
                    headers=_headers(),
                )
                resp.raise_for_status()
                return [TextContent(type="text", text=f"✅ Force limit set to {force}%")]

            elif name == "gripper_move":
                pos = arguments["position"]
                resp = await client.post(
                    f"{base_url}/move/{pos}",
                    headers=_headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                return [TextContent(type="text", text=f"✅ Gripper moved to {pos}%. State: {data}")]

            elif name == "gripper_status":
                resp = await client.get(f"{base_url}/status", headers=_headers())
                resp.raise_for_status()
                data = resp.json()
                text = (
                    f"Gripper Status:\n"
                    f"  State: {data.get('state', 'unknown')}\n"
                    f"  Position: {data.get('position', 0)}%\n"
                    f"  Force: {data.get('force', 0)}%\n"
                    f"  Temperature: {data.get('temperature_c', 'N/A')}°C"
                )
                return [TextContent(type="text", text=text)]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except httpx.ConnectError:
            return [TextContent(
                type="text",
                text=f"❌ Cannot reach gripper bridge at {base_url}. "
                     "Check PI_HOST env var and ensure the Pi is powered on.",
            )]
        except httpx.HTTPStatusError as e:
            return [TextContent(type="text", text=f"❌ Gripper API error {e.response.status_code}: {e.response.text}")]
        except Exception as e:
            log.error("gripper_mcp_error", tool=name, error=str(e))
            return [TextContent(type="text", text=f"❌ Error: {e}")]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
