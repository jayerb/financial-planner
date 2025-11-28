![Unit Tests](https://github.com/jayerb/financial-planner/actions/workflows/unit-tests.yml/badge.svg)

# Financial Planner

A retirement planning application that estimates tax burden and financial projections using AI-powered natural language queries. Create your financial plan, start the MCP server, and ask questions like "What's my take-home pay in 2030?" directly in your AI assistant.

> **Note**: Tax calculations are approximations and should not be used for tax filing purposes.

## Quick Start

### Step 1: Create Your Financial Plan

First, create a configuration file with your financial details:

**Option A: Interactive Wizard (Recommended)**
```bash
python src/Program.py --generate
```
Answer the prompts to enter your income, deductions, retirement plans, RSUs, ESPP, and other financial details. Your configuration will be saved to `input-parameters/<your-plan-name>/spec.json`.

**Option B: Manual Configuration**
Copy an existing example and modify it:
```bash
cp -r input-parameters/myprogram input-parameters/myplan
# Edit input-parameters/myplan/spec.json with your details
```

### Step 2: Start the MCP Server

The MCP (Model Context Protocol) server enables AI assistants to answer questions about your financial plan.

**Install dependencies:**
```bash
pip install mcp
# Or: pip install -r mcp-server/requirements.txt
```

**Configure your AI assistant:**

<details>
<summary><strong>VS Code with GitHub Copilot</strong></summary>

Create `.vscode/mcp.json` in your workspace:

```json
{
  "servers": {
    "financial-planner": {
      "type": "stdio",
      "command": "/path/to/.venv/bin/python",
      "args": ["mcp-server/server.py"]
    }
  }
}
```
Replace the Python path with your interpreter. Restart VS Code to activate.
</details>

<details>
<summary><strong>Claude Desktop</strong></summary>

Edit your config file:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "financial-planner": {
      "command": "python",
      "args": ["/path/to/financial-planner/mcp-server/server.py"]
    }
  }
}
```
</details>

<details>
<summary><strong>Other MCP Clients</strong></summary>

The server uses stdio transport. Run directly:
```bash
python mcp-server/server.py
```
</details>

### Step 3: Ask Questions!

Once configured, ask your AI assistant questions like:

- "What programs are available?"
- "What's my take-home pay in 2030 for myprogram?"
- "How much federal tax will I pay in 2027 for quickexample?"
- "Compare my income between 2025 and 2040 for myprogram"
- "What's my effective tax rate for myprogram?"
- "When do my deferred comp disbursements start for myprogram?"
- "What's my total lifetime tax burden for myprogram?"

The MCP server automatically discovers **all programs** in `input-parameters/` at startup. When multiple programs exist, you must specify which program to query by including the program name in your question.

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `list_programs` | List all available programs and their basic info |
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

All tools accept an optional `program` parameter to specify which plan to query.

## Command-Line Interface

You can also run the financial planner directly from the command line:

```bash
# Run with default output (tax details for first year)
python src/Program.py myprogram

# Show accumulated balances (401k, deferred comp)
python src/Program.py myprogram --mode Balances

# Show annual summary table
python src/Program.py myprogram --mode AnnualSummary
```

## Project Structure

```
financial-planner/
├── src/                    # Main source code
│   ├── Program.py          # CLI entry point
│   ├── spec_generator.py   # Interactive configuration wizard
│   ├── calc/               # Calculators (take-home, RSU, balances)
│   ├── tax/                # Tax computation (federal, state, FICA)
│   ├── model/              # Data models
│   └── render/             # Output renderers
├── mcp-server/             # MCP server for AI assistant integration
│   ├── server.py           # MCP server entry point
│   └── tools.py            # Tool implementations
├── input-parameters/       # Your financial plan configurations
│   └── myprogram/          # Example plan
├── reference/              # Tax brackets and statutory parameters
└── tests/                  # Unit tests
```

## Technical Details

### State Tax Support

The project supports a simple state tax model driven by `reference/flat-tax-details.json`.

State taxable income is computed as:
```
gross_income - (inflated 401k + inflated HSA) - medical/dental/vision - inflated state standard deduction
```

The state tax calculation intentionally excludes the federal standard deduction but includes retirement and HSA contributions.

### ESPP (Employee Stock Purchase Plan) Support

ESPP taxable benefit is treated as part of gross income and flows into AGI for both federal and state calculations. The taxable benefit is calculated as:

```
espp_taxable = maxESPPValue × esppDiscount
```

For example, with a `maxESPPValue` of $25,000 and an `esppDiscount` of 15%, the taxable benefit is $3,750.

### Statutory Parameters

The following parameters are configured in `reference/`:
- 2026 Tax Brackets with estimated annual growth
- Max 401k and HSA contributions
- Max ESPP contribution value ($25k)
- Federal and state standard deductions
- Social Security wage base and rate
- Medicare rate and surcharge threshold

### Input Variables

Your `spec.json` can include:

**Income**
- Base salary and bonus percentage
- Annual salary growth estimate
- RSU grants and vesting schedules
- ESPP discount and contribution
- Short-term and long-term capital gains

**Deductions**
- Deferred compensation plan percentages
- Medical/dental/vision premiums

## Running Unit Tests

```bash
pip install pytest
pytest tests
```
