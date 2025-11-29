![Unit Tests](https://github.com/jayerb/financial-planner/actions/workflows/unit-tests.yml/badge.svg)

# Financial Planner

A retirement planning application that estimates tax burden and financial projections over a multi-decade planning horizon. Create your financial plan, then query any data you want using the interactive shell.

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

### Step 2: Query Your Data with the Interactive Shell

The interactive shell loads your complete financial plan and lets you query any data fields across any year range:

```bash
python src/shell.py myprogram
```

Once loaded, you'll see an interactive prompt:

```
Financial Plan Interactive Shell
=================================
Program: myprogram
Years: 2025 - 2076
Working years: 2025 - 2031

Type 'help' for available commands.
Type 'fields' to see available data fields.
Type 'exit' or 'quit' to exit.

>
```

### Shell Commands

| Command | Description |
|---------|-------------|
| `get <fields> [year_range]` | Query one or more fields from yearly data |
| `fields` | List all available field names (50+ fields) |
| `years` | Show available year range and categorization |
| `summary` | Show lifetime summary totals |
| `help` | Show help message |
| `exit` / `quit` | Exit the shell |

### Query Examples

**Single field, all years:**
```
> get gross_income
```

**Multiple fields (comma-separated):**
```
> get gross_income, federal_tax, state_tax
```

**Specific year range:**
```
> get take_home_pay 2026-2030
```

**Complex query:**
```
> get base_salary, bonus, rsu_vested_value, total_taxes 2026-2035
```

**Sample output:**
```
  Year  take_home_pay  federal_tax  state_tax
---------------------------------------------
  2026    $218,295.63   $59,295.26  $19,124.08
  2027    $220,655.20   $58,007.56  $18,545.74
  2028    $216,109.88   $52,138.63  $15,917.37
  2029    $211,583.07   $47,851.06  $14,161.21
  2030    $218,043.36   $49,629.00  $14,629.32
---------------------------------------------
 Total  $1,084,687.13  $266,921.51  $82,377.72
```

### Available Data Fields

The shell can query 50+ fields organized by category:

| Category | Example Fields |
|----------|----------------|
| **Income** | `base_salary`, `bonus`, `rsu_vested_value`, `espp_income`, `gross_income` |
| **Taxes** | `federal_tax`, `state_tax`, `total_fica`, `total_taxes`, `effective_tax_rate` |
| **Deductions** | `standard_deduction`, `itemized_deduction`, `max_401k`, `max_hsa` |
| **Take Home** | `take_home_pay`, `adjusted_gross_income` |
| **Contributions** | `employee_401k_contribution`, `employer_401k_match`, `hsa_contribution` |
| **Balances** | `balance_401k`, `balance_deferred_comp`, `balance_hsa`, `balance_taxable`, `total_assets` |
| **Expenses** | `annual_expenses`, `special_expenses`, `income_expense_difference` |

Use the `fields` command in the shell to see the complete list.

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
│   ├── shell.py            # Interactive query shell
│   ├── spec_generator.py   # Interactive configuration wizard
│   ├── calc/               # Calculators (take-home, RSU, balances)
│   ├── tax/                # Tax computation (federal, state, FICA)
│   ├── model/              # Data models
│   └── render/             # Output renderers
├── mcp-server/             # MCP server for AI assistant integration (alternative)
│   ├── server.py           # MCP server entry point
│   └── tools.py            # Tool implementations
├── input-parameters/       # Your financial plan configurations
│   └── myprogram/          # Example plan
├── reference/              # Tax brackets and statutory parameters
└── tests/                  # Unit tests
```

## MCP Server (Alternative)

For AI assistant integration, an MCP (Model Context Protocol) server is also available. See `mcp-server/README.md` for setup instructions.

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

**Investments**
- Investment account balances (taxable, tax-deferred, HSA)
- Expected appreciation rates
- HSA employer contribution (automatically inflated; only employee portion is tax-deductible)

## Running Unit Tests

```bash
pip install pytest
pytest tests
```
