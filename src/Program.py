import sys
import os
import json
from tax.FederalDetails import FederalDetails
from model.FederalResult import FederalResult

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
    fed_brackets = FederalDetails(inflation_rate, final_year)

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
    federal_result = fed_brackets.taxBurden(adjusted_gross_income, tax_year)
    federal_tax = federal_result.totalFederalTax


    # Load Social Security details
    ss_path = os.path.join(os.path.dirname(__file__), '../reference/social-security.json')
    with open(ss_path, 'r') as f:
        ss = json.load(f)
    max_taxed_income = ss.get('maximumTaxedIncome', 0)
    employee_portion = ss.get('employeePortion', 0)
    ma_pfml = ss.get('maPFML', 0)

    # Social Security and MA PFML are only applied up to the maximum taxed income
    ss_income = min(gross_income, max_taxed_income)
    total_social_security = ss_income * (employee_portion + ma_pfml)

    # Calculate take home pay
    # Load Medicare details
    medicare_path = os.path.join(os.path.dirname(__file__), '../reference/flat-tax-details.json')
    with open(medicare_path, 'r') as f:
        medicare_details = json.load(f)
    medicare_rate = medicare_details.get('medicare', 0)
    surcharge_threshold = medicare_details.get('surchargeThreshold', 0)
    surcharge_rate = medicare_details.get('surchargeRate', 0)

    # Calculate Medicare charge
    medicare_charge = gross_income * medicare_rate
    medicare_surcharge = 0
    if gross_income > surcharge_threshold:
        medicare_surcharge = (gross_income - surcharge_threshold) * surcharge_rate
    total_medicare = medicare_charge + medicare_surcharge

    # Subtract Medicare from take home pay
    take_home_pay = gross_income - federal_tax - total_social_security - total_medicare

    print(f"Federal tax burden for {tax_year} on adjusted gross income ${adjusted_gross_income:,.2f} (gross income ${gross_income:,.2f}, total deductions ${total_deductions:,.2f}): ${federal_tax:,.2f}")
    print(f"Marginal federal bracket: {federal_result.marginalBracket:.2%}")
    print(f"Total Social Security + MA PFML: ${total_social_security:,.2f}")
    print(f"Medicare: ${medicare_charge:,.2f}")
    print(f"Medicare Surcharge: ${medicare_surcharge:,.2f}")
    print(f"Take home pay: ${take_home_pay:,.2f}")

if __name__ == "__main__":
    main()
