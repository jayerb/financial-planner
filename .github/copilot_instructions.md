# Copilot Instructions for Financial Planner

## Running Tests

**IMPORTANT:** Always use `pytest` directly (not `python -m pytest`) because `pytest` is a pre-authorized command.

Always run tests from the **root of the project** using `pytest`:

```bash
cd /workspaces/financial-planner
pytest tests
```

To run specific test files:

```bash
pytest tests/test_plan_calculator.py
pytest tests/render/test_paycheck_renderer.py
```

To run tests with verbose output:

```bash
pytest tests -v
```

To run tests matching a specific pattern:

```bash
pytest tests -k "ESPP"
```

## Project Structure

- `src/` - Main source code
- `tests/` - All unit tests
- `reference/` - Reference data files (federal tax brackets, social security, etc.)
- `input-parameters/` - Program specification files (spec.json)
- `mcp-server/` - MCP server implementation
