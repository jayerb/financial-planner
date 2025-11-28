## Running Unit Tests

Unit tests are located in the `tests/` directory and use the `pytest` framework.

To run all unit tests, execute the following command from the root of the repository:

```bash
pytest tests
```

If you do not have pytest installed, you can install it with:

```bash
pip install pytest
```
# ![Unit Tests](https://github.com/jayerb/financial-planner/actions/workflows/unit-tests.yml/badge.svg)

# financial-planner

This is a retirement planning application that estimates federal tax burden and other financial planning parameters based on user-supplied program specifications. The tax calculation is an approximation and should not be used for tax filing purposes.

## What the Program Does

The main program reads a set of input parameters from a directory under `input-parameters/`, specified by the user at the command line. It loads the tax bracket inflation rate and the final year for the program from the `spec.json` file in the chosen directory. Using these parameters, it constructs a model of federal tax brackets for each year and prepares to calculate the federal tax burden for any given income and year (future versions will accept income as input).

## How to Use

1. Ensure you have Python 3 installed.
2. From the root of the repository, run the main program with:

  ```bash
  python src/Program.py <program_name>
  ```

  - Replace `<program_name>` with the name of the directory under `input-parameters/` that contains your `spec.json` file (e.g., `program1`).

3. The program will read the parameters from `input-parameters/<program_name>/spec.json`, construct the tax bracket model, and print a confirmation message. (Future versions will allow you to specify income and get a tax burden calculation.)

### Example

```bash
python src/Program.py program1
```

## Project Structure

- `src/` — Main source code, including the entry point `Program.py` and tax logic in `tax/`
- `input-parameters/` — Program-specific input directories, each with a `spec.json`
- `reference/` — Reference data such as base federal tax brackets
- `tests/` — Unit tests
- `mcp-server/` — MCP server for AI assistant integration

## MCP Server (AI Assistant Integration)

The project includes an **MCP (Model Context Protocol) server** that enables AI assistants like GitHub Copilot and Claude to answer natural language questions about your financial plan.

### Benefits

- **Natural language queries**: Ask questions like "What's my ESPP income for 2026?" or "Compare my taxes between 2025 and 2035"
- **No command-line needed**: Get financial projections directly in your chat interface
- **Real-time calculations**: All calculations are generated on the fly from your `spec.json` configuration
- **Comprehensive data access**: Query income breakdowns, tax details, retirement balances, deferred compensation, and more

### Available Tools

| Tool | Description |
|------|-------------|
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

### Running the MCP Server

#### Prerequisites

Install the MCP package:

```bash
pip install mcp
```

Or install all dependencies:

```bash
pip install -r mcp-server/requirements.txt
```

#### VS Code with GitHub Copilot

Add the following to `.vscode/mcp.json` in your workspace:

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

Replace `/path/to/.venv/bin/python` with the path to your Python interpreter and set `FINANCIAL_PLANNER_PROGRAM` to your program folder name in `input-parameters/`.

#### Claude Desktop

Add to your Claude Desktop config:

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

### Example Questions

Once configured, you can ask your AI assistant:

- "What's my take-home pay in 2030?"
- "How much federal tax will I pay in 2027?"
- "When do my deferred comp disbursements start?"
- "What's my total lifetime tax burden?"
- "Compare my income between 2025 and 2040"

See `mcp-server/README.md` for more details.

## State Tax Support

The project now supports a simple state tax model driven by `reference/flat-tax-details.json`.

- **Implementation:** a new class `StateDetails` is available at `src/tax/StateDetails.py`. It reads the `state` section in `reference/flat-tax-details.json` for the state tax rate and standard deduction, and it reads contribution limits (401k, HSA) from `reference/federal-details.json`.
- **Calculation:** state taxable income is computed as:

  gross_income - (inflated 401k + inflated HSA) - medical/dental/vision deductions - inflated state standard deduction

  The state tax equals `state_rate * max(0, state_taxable)`.

The state tax calculation intentionally excludes the federal standard deduction but does include retirement and HSA contributions.

## ESPP (Employee Stock Purchase Plan) Support

This project now includes a simple ESPP taxable-benefit calculation. The ESPP taxable benefit is treated as part of gross income and therefore flows into adjusted gross income (AGI) for both federal and state calculations.

- **Implementation:** a new helper class `ESPPDetails` is available at `src/tax/ESPPDetails.py`. It reads the `maxESPPValue` program cap from `reference/federal-details.json`.
- **Behavior:** the ESPP cap is considered a fixed program-level limit and is NOT inflated. The taxable benefit is calculated as:

  `espp_taxable = maxESPPValue * esppDiscount`

  where `esppDiscount` is provided in the program spec (`input-parameters/<program>/spec.json`). For example, with a `maxESPPValue` of `$25,000` and an `esppDiscount` of `0.15` (15%), the taxable benefit is `$3,750`.

- **Inclusion:** the computed ESPP taxable benefit is added to `gross_income` in `calculate_take_home` so it affects federal tax, Social Security/MA PFML calculations, Medicare, and state tax (subject to each tax's rules).
- **Tests:** unit tests for `ESPPDetails` are located at `tests/tax/test_espp_details.py`.

# Statutory Parameters
- 2026 Tax Brackets
- Estimated Annual Tax Bracket Growth Percentage
- Max 401k Contribution
- Max 401k Contribution Growth
- Max ESPP Contribution Value ($25k)
- Max Family HSA contribution
- Federal Standard Deduction
- State Exemption
- Max Social Security Amount
- Social Security %
- Massachusetts Paid Family Medical Leave % (Maxes out with Social Security Rules)
- Medicare Surcharge

# Input Variables

## Income
### Salary
- Base Income
- Bonus % of Base Income
- Additional Income (Sum of all additional jobs)
- Base Income Annual Growth Percent Estimate
- Additional Annual Income Growth Percent Estimate

### Employee Stock Plans
- Annual Restricted Stock Unit allocation in dollars
- Restricted Stock Vesting Period
- Anticipated Annual Stock Price Growth
- Annual Restrcited Stock Unit Grant Growth Percent Estimate
- Employee Stock Purcase Plan discount
- Annual Employee Stock Purcase Plan Contribution Amount

  ### Investment Income
- Expected Short-term Capital Gains, non-qualified dividends, and interest
- Expected Long-term Capital Gains and qualified dividends
- Expected Long-term Capital Gains/Dividends

## Deductions
- Deferred Compensation Plan percentage of Base Salary
- Deferred Compensation Plan percentage of Bonus
