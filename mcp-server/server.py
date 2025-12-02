#!/usr/bin/env python3
"""MCP Server for Financial Planner.

This server exposes financial planning calculations as MCP tools,
allowing AI assistants to answer questions about a user's financial plan.
"""

import os
import sys
import json
import asyncio
from typing import Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from tools import MultiProgramTools


# Create the MCP server
server = Server("financial-planner")

# Global tools instance (initialized on startup)
tools: MultiProgramTools | None = None


def get_tools() -> MultiProgramTools:
    """Get or initialize the tools instance."""
    global tools
    if tools is None:
        # Default program can be set via FINANCIAL_PLANNER_PROGRAM env var
        default_program = os.environ.get('FINANCIAL_PLANNER_PROGRAM')
        base_path = os.path.join(os.path.dirname(__file__), '..')
        tools = MultiProgramTools(base_path, default_program)
    return tools


# Common program parameter schema
PROGRAM_PARAM = {
    "type": "string",
    "description": "The program name (folder in input-parameters). If not specified, uses the default program. Use list_programs to see available programs."
}


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available financial planning tools."""
    return [
        Tool(
            name="list_programs",
            description="List all available financial planning programs. Use this to see which programs are available and their basic info.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="reload_programs",
            description="Reload all financial planning programs from disk. Use this after adding, modifying, or removing program spec.json files to refresh the cache without restarting the server.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_program_overview",
            description="Get an overview of the financial plan including key dates, income sources, and plan parameters. Use this first to understand the scope of the plan.",
            inputSchema={
                "type": "object",
                "properties": {
                    "program": PROGRAM_PARAM
                },
                "required": []
            }
        ),
        Tool(
            name="list_available_years",
            description="List all years covered by the financial plan, indicating which are working years vs retirement years.",
            inputSchema={
                "type": "object",
                "properties": {
                    "program": PROGRAM_PARAM
                },
                "required": []
            }
        ),
        Tool(
            name="get_annual_summary",
            description="Get income and tax summary for a specific year. Includes gross income, all tax categories, effective tax rate, and take-home pay.",
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {
                        "type": "integer",
                        "description": "The tax year to get summary for"
                    },
                    "program": PROGRAM_PARAM
                },
                "required": ["year"]
            }
        ),
        Tool(
            name="get_tax_details",
            description="Get detailed tax breakdown for a specific year including federal brackets, FICA components, state taxes, deductions, and deferrals.",
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {
                        "type": "integer",
                        "description": "The tax year to get details for"
                    },
                    "program": PROGRAM_PARAM
                },
                "required": ["year"]
            }
        ),
        Tool(
            name="get_income_breakdown",
            description="Get detailed income breakdown for a specific year including salary, bonus, RSUs, ESPP, capital gains, and deferred comp disbursements.",
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {
                        "type": "integer",
                        "description": "The tax year to get income breakdown for"
                    },
                    "program": PROGRAM_PARAM
                },
                "required": ["year"]
            }
        ),
        Tool(
            name="get_deferred_comp_info",
            description="Get deferred compensation plan information for a specific year including contributions, balance, and disbursements.",
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {
                        "type": "integer",
                        "description": "The year to get deferred comp info for"
                    },
                    "program": PROGRAM_PARAM
                },
                "required": ["year"]
            }
        ),
        Tool(
            name="get_retirement_balances",
            description="Get 401(k) and deferred compensation balances for a specific year or all years.",
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {
                        "type": "integer",
                        "description": "Optional: specific year to get balances for. If omitted, returns all years."
                    },
                    "program": PROGRAM_PARAM
                },
                "required": []
            }
        ),
        Tool(
            name="get_investment_balances",
            description="Get investment account balances (taxable brokerage, tax-deferred 401k/IRA, HSA) for a specific year or all years. Shows how accounts grow with appreciation over the planning horizon.",
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {
                        "type": "integer",
                        "description": "Optional: specific year to get balances for. If omitted, returns summary with initial, retirement, and final balances."
                    },
                    "program": PROGRAM_PARAM
                },
                "required": []
            }
        ),
        Tool(
            name="compare_years",
            description="Compare financial metrics between two years.",
            inputSchema={
                "type": "object",
                "properties": {
                    "year1": {
                        "type": "integer",
                        "description": "First year to compare"
                    },
                    "year2": {
                        "type": "integer",
                        "description": "Second year to compare"
                    },
                    "program": PROGRAM_PARAM
                },
                "required": ["year1", "year2"]
            }
        ),
        Tool(
            name="get_lifetime_totals",
            description="Get lifetime totals for income, taxes, and take-home pay across the entire planning horizon.",
            inputSchema={
                "type": "object",
                "properties": {
                    "program": PROGRAM_PARAM
                },
                "required": []
            }
        ),
        Tool(
            name="search_financial_data",
            description="Search for specific financial metrics. Use this when looking for specific values like 'ESPP income in 2029' or 'Medicare tax in 2035'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query about financial data, e.g., 'ESPP income', 'federal tax', 'take home pay'"
                    },
                    "year": {
                        "type": "integer",
                        "description": "Optional: specific year to search in"
                    },
                    "program": PROGRAM_PARAM
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="compare_programs",
            description="Compare two financial planning programs and get analysis of which is better. Compares lifetime income, taxes, take-home pay, tax efficiency, and retirement assets. Returns a recommendation on which program is better overall with specific insights.",
            inputSchema={
                "type": "object",
                "properties": {
                    "program1": {
                        "type": "string",
                        "description": "First program name to compare"
                    },
                    "program2": {
                        "type": "string",
                        "description": "Second program name to compare"
                    },
                    "metrics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional: specific metrics to compare. Options: 'lifetime_income', 'lifetime_taxes', 'take_home', 'tax_efficiency', 'retirement_assets', 'working_income', 'working_take_home', 'retirement_income', 'retirement_take_home', 'assets_at_retirement'. If not specified, compares all metrics."
                    }
                },
                "required": ["program1", "program2"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    try:
        fp_tools = get_tools()
        program = arguments.get("program")
        
        if name == "list_programs":
            result = fp_tools.list_programs()
        elif name == "reload_programs":
            result = fp_tools.reload_programs()
        elif name == "get_program_overview":
            result = fp_tools.get_program_overview(program)
        elif name == "list_available_years":
            result = fp_tools.list_available_years(program)
        elif name == "get_annual_summary":
            result = fp_tools.get_annual_summary(arguments["year"], program)
        elif name == "get_tax_details":
            result = fp_tools.get_tax_details(arguments["year"], program)
        elif name == "get_income_breakdown":
            result = fp_tools.get_income_breakdown(arguments["year"], program)
        elif name == "get_deferred_comp_info":
            result = fp_tools.get_deferred_comp_info(arguments["year"], program)
        elif name == "get_retirement_balances":
            result = fp_tools.get_retirement_balances(arguments.get("year"), program)
        elif name == "get_investment_balances":
            result = fp_tools.get_investment_balances(arguments.get("year"), program)
        elif name == "compare_years":
            result = fp_tools.compare_years(arguments["year1"], arguments["year2"], program)
        elif name == "get_lifetime_totals":
            result = fp_tools.get_lifetime_totals(program)
        elif name == "search_financial_data":
            result = fp_tools.search_financial_data(
                arguments["query"],
                arguments.get("year"),
                program
            )
        elif name == "compare_programs":
            result = fp_tools.compare_programs(
                arguments["program1"],
                arguments["program2"],
                arguments.get("metrics")
            )
        else:
            result = {"error": f"Unknown tool: {name}"}
        
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2, default=str)
        )]
    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({"error": str(e)}, indent=2)
        )]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
