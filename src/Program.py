import sys
import os
import json
from tax.FederalBrackets import FederalBrackets

def main():
    if len(sys.argv) < 2:
        print("Usage: python src/Program.py <program_name>")
        sys.exit(1)
    program_name = sys.argv[1]
    # Build path to spec.json
    spec_path = os.path.join(os.path.dirname(__file__), '../input-parameters', program_name, 'spec.json')
    if not os.path.exists(spec_path):
        print(f"Spec file not found: {spec_path}")
        sys.exit(1)
    with open(spec_path, 'r') as f:
        spec = json.load(f)
    # Extract required parameters
    final_year = spec.get('lastYear')
    inflation_rate = spec.get('federalBracketInflation')
    if final_year is None or inflation_rate is None:
        print("spec.json must contain 'lastYear' and 'federalBracketInflation' fields.")
        sys.exit(1)
    # Construct FederalBrackets instance
    fed_brackets = FederalBrackets(inflation_rate, final_year)

    # Calculate gross income for 2026
    income_details = spec.get('income', {})
    base_salary = income_details.get('baseSalary', 0)
    bonus_fraction = income_details.get('bonusFraction', 0)
    other_income = income_details.get('otherIncome', 0)
    gross_income = base_salary + (base_salary * bonus_fraction) + other_income

    # Get total deductions for 2026
    tax_year = 2026
    total_deductions = fed_brackets.totalDeductions(tax_year)
    adjusted_gross_income = gross_income - total_deductions

    # Calculate federal tax burden for 2026 using adjusted gross income
    federal_tax = fed_brackets.taxBurden(adjusted_gross_income, tax_year)

    print(f"Federal tax burden for {tax_year} on adjusted gross income ${adjusted_gross_income:,.2f} (gross income ${gross_income:,.2f}, total deductions ${total_deductions:,.2f}): ${federal_tax:,.2f}")

if __name__ == "__main__":
    main()
