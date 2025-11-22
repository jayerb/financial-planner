# financial-planner
This is a retirement planning application based on current income, tax rules, and expected growth parameters. It does a tax calculation that is only an approximation based on an understanding of a subset of the tax rules. The tax calculation should be fine for planning purposes, but it is not good enough for tax filing. There will be many tax scenarios where the calculation is very far off.

This program will calculate an estimated tax burden for the current and future years based on growth parameters.

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
