# Financial Planner MCP Server

This is an MCP (Model Context Protocol) server that exposes the financial planning calculations to AI assistants. Users can ask natural language questions about their financial plan and get accurate answers.

## Features

- **Multi-program support**: Query any program in `input-parameters/` by name
- **Automatic discovery**: All programs are loaded and cached at startup
- **Natural language queries**: Ask questions like "What's my take-home pay in 2030 for quickexample?"

## Installation

1. Install the MCP package:
   ```bash
   pip install mcp
   ```

2. Or install all dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### For Claude Desktop

Add the following to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "financial-planner": {
      "command": "python",
      "args": ["/path/to/financial-planner/mcp-server/server.py"],
      "env": {
        "FINANCIAL_PLANNER_PROGRAM": "myprogram"
      }
    }
  }
}
```

Replace `/path/to/financial-planner` with the actual path to your financial-planner directory.

Set `FINANCIAL_PLANNER_PROGRAM` to set the default program (optional - if not set, the first discovered program will be used).

### For VS Code with GitHub Copilot

Add to `.vscode/mcp.json` in your workspace:

```json
{
  "servers": {
    "financial-planner": {
      "type": "stdio",
      "command": "/path/to/.venv/bin/python",
      "args": ["mcp-server/server.py"],
      "env": {
        "FINANCIAL_PLANNER_PROGRAM": "myprogram"
      }
    }
  }
}
```

## Available Tools

The MCP server provides the following tools. All tools accept an optional `program` parameter to specify which program to query:

| Tool | Description |
|------|-------------|
| `list_programs` | List all available programs with their basic info |
| `get_program_overview` | Overview of the financial plan including dates and income sources |
| `list_available_years` | List all years in the plan (working vs retirement) |
| `get_annual_summary` | Income and tax summary for a specific year |
| `get_tax_details` | Detailed tax breakdown for a specific year |
| `get_income_breakdown` | Detailed income sources for a specific year |
| `get_deferred_comp_info` | Deferred compensation info for a specific year |
| `get_retirement_balances` | 401(k) and deferred comp balances |
| `compare_years` | Compare financial metrics between two years |
| `get_lifetime_totals` | Lifetime totals across the planning horizon |
| `search_financial_data` | Search for specific metrics (e.g., "ESPP income in 2029") |

## Example Questions

Once configured, you can ask your AI assistant questions like:

- "What programs are available?"
- "How much is my ESPP income for 2029?"
- "What's my take-home pay in 2030 for the quickexample program?"
- "What's my effective tax rate in 2031?"
- "Compare my take-home pay between 2025 and 2035 for myprogram"
- "When do my deferred comp disbursements start and end?"
- "What's my total lifetime tax burden?"
- "How much will I have in my 401(k) by 2050?"
- "What's my RSU vested value in 2027?"
- "Show me my federal tax breakdown for 2030"

### Specifying a Program

You can specify which program to query in your questions:
- "What's my take-home pay in 2030 for **quickexample**?"
- "Compare gross income for **program1** in 2026 vs 2030"

If you don't specify a program, the default program will be used.

## Creating Your Own Program

1. Create a new folder in `input-parameters/` (e.g., `input-parameters/myplan/`)
2. Create a `spec.json` file with your financial details
3. Update the `FINANCIAL_PLANNER_PROGRAM` environment variable to match your folder name

See `input-parameters/myprogram/spec.json` for an example of the spec format.

## Running Manually (for testing)

You can test the server manually:

```bash
cd /path/to/financial-planner
FINANCIAL_PLANNER_PROGRAM=myprogram python mcp-server/server.py
```

The server communicates via stdio, so you'll need an MCP client to interact with it properly.
