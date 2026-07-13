"""
Energy MCP Server for G Force
--------------------------------
Exposes Energy/ERCOT operations as MCP tools callable by agents.

Tools:
  - get_ercot_status: Get ERCOT 4CP status
  - list_active_customers: List active customers
  - run_proforma: Run proforma for an energy project
"""

from __future__ import annotations

from typing import Any
import structlog
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

log = structlog.get_logger()

server = Server("gforce-energy-mcp")

TOOLS: list[Tool] = [
    Tool(
        name="get_ercot_status",
        description="Get current ERCOT grid status and 4CP alert level",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="list_active_customers",
        description="List active energy customers on the platform",
        inputSchema={
            "type": "object",
            "properties": {
                "region": {"type": "string", "description": "Filter by region (e.g. ERCOT, PJM)"}
            },
        },
    ),
    Tool(
        name="run_proforma",
        description="Run financial proforma for a solar/storage energy project",
        inputSchema={
            "type": "object",
            "required": ["capacity_mw", "technology"],
            "properties": {
                "capacity_mw": {"type": "number"},
                "technology": {"type": "string", "enum": ["solar", "storage", "hybrid"]},
            },
        },
    ),
]


@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        if name == "get_ercot_status":
            return [TextContent(type="text", text="ERCOT Grid Status: Normal\n4CP Alert: None (Probability: 15%)\nSystem Demand: 68,450 MW\nAvailable Capacity: 81,200 MW")]

        elif name == "list_active_customers":
            region = arguments.get("region", "All")
            return [TextContent(type="text", text=f"Active Customers ({region}):\n1. Acme Energy Corp (ERCOT)\n2. Globex Manufacturing (ERCOT)\n3. Initech Solutions (PJM)")]

        elif name == "run_proforma":
            capacity = arguments["capacity_mw"]
            tech = arguments["technology"]
            return [TextContent(type="text", text=f"Proforma Results for {capacity}MW {tech} project:\n- CAPEX: ${(capacity * 1.2):.2f}M\n- OPEX: ${(capacity * 0.05):.2f}M/yr\n- Projected IRR: 12.4%\n- Payback Period: 6.2 years")]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        log.error("energy_mcp_error", tool=name, error=str(e))
        return [TextContent(type="text", text=f"Error: {e}")]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
