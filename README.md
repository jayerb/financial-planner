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

## State Tax Support

The project now supports a simple state tax model driven by `reference/flat-tax-details.json`.

- **Implementation:** a new class `StateDetails` is available at `src/tax/StateDetails.py`. It reads the `state` section in `reference/flat-tax-details.json` for the state tax rate and standard deduction, and it reads contribution limits (401k, HSA) from `reference/federal-details.json`.
- **Calculation:** state taxable income is computed as:

  gross_income - (inflated 401k + inflated HSA) - medical/dental/vision deductions - inflated state standard deduction

  The state tax equals `state_rate * max(0, state_taxable)`.

The state tax calculation intentionally excludes the federal standard deduction but does include retirement and HSA contributions.

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
