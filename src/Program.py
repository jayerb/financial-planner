import sys
import os
import json
from tax.FederalDetails import FederalDetails
from tax.StateDetails import StateDetails
from tax.ESPPDetails import ESPPDetails
from tax.SocialSecurityDetails import SocialSecurityDetails
from tax.MedicareDetails import MedicareDetails
from calc.take_home import TakeHomeCalculator
from calc.rsu_calculator import RSUCalculator

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
    # Build detail instances and inject into the calculator
    tax_year = spec.get('firstYear', 2026)
    inflation_rate = spec.get('federalBracketInflation')
    final_year = spec.get('lastPlanningYear')
    fed = FederalDetails(inflation_rate, final_year)
    state = StateDetails(inflation_rate, final_year)
    # read max ESPP cap from reference and pass into ESPPDetails
    fed_ref_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '../reference', 'federal-details.json'))
    with open(fed_ref_path, 'r') as f:
        fed_ref = json.load(f)
    max_espp = fed_ref.get('maxESPPValue', 0)
    espp = ESPPDetails(max_espp)

    # Create Social Security details with inflation rate and final year
    social_security = SocialSecurityDetails(inflation_rate, final_year)

    # read Medicare details from reference
    medicare_ref_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '../reference', 'flat-tax-details.json'))
    with open(medicare_ref_path, 'r') as f:
        medicare_ref = json.load(f)
    medicare = MedicareDetails(
        medicare_rate=medicare_ref.get('medicare', 0),
        surcharge_threshold=medicare_ref.get('surchargeThreshold', 0),
        surcharge_rate=medicare_ref.get('surchargeRate', 0)
    )

    # Create RSU calculator from spec
    rsu_config = spec.get('restrictedStockUnits', {})
    rsu_calculator = RSUCalculator(
        previous_grants=rsu_config.get('previousGrants', []),
        first_year=tax_year,
        last_year=spec.get('lastWorkingYear', tax_year + 20),
        first_year_stock_price=rsu_config.get('currentStockPrice', 0),
        first_year_grant_value=rsu_config.get('initialAnnualGrantValue', 0),
        annual_grant_increase=rsu_config.get('annualGrantIncreaseFraction', 0),
        expected_share_price_growth_fraction=rsu_config.get('expectedSharePriceGrowthFraction', 0)
    )

    calculator = TakeHomeCalculator(fed, state, espp, social_security, medicare, rsu_calculator)
    results = calculator.calculate(spec, tax_year)

    # Calculate total taxes for summary
    total_federal = results['federal_tax']
    total_fica = results['total_social_security'] + results['medicare_charge'] + results['medicare_surcharge']
    total_state = results.get('state_tax', 0)
    total_taxes = total_federal + total_fica + total_state

    print()
    print("=" * 60)
    print(f"{'TAX SUMMARY FOR ' + str(tax_year):^60}")
    print("=" * 60)
    
    print()
    print("-" * 60)
    print("INCOME")
    print("-" * 60)
    print(f"  {'Gross Income:':<40} ${results['gross_income']:>14,.2f}")
    print(f"  {'RSU Vested:':<40} ${results['rsu_vested_value']:>14,.2f}")
    
    print()
    print("-" * 60)
    print("DEDUCTIONS")
    print("-" * 60)
    deductions = results['deductions']
    print(f"  {'Standard Deduction:':<40} ${deductions['standardDeduction']:>14,.2f}")
    print(f"  {'401(k) Contribution:':<40} ${deductions['max401k']:>14,.2f}")
    print(f"  {'HSA Contribution:':<40} ${deductions['maxHSA']:>14,.2f}")
    print(f"  {'Medical/Dental/Vision:':<40} ${deductions['medicalDentalVision']:>14,.2f}")
    print(f"  {'-' * 40}")
    print(f"  {'Total Deductions:':<40} ${results['total_deductions']:>14,.2f}")
    
    print()
    print(f"  {'Adjusted Gross Income:':<40} ${results['adjusted_gross_income']:>14,.2f}")
    
    print()
    print("-" * 60)
    print("FEDERAL TAXES")
    print("-" * 60)
    print(f"  {'Ordinary Income Tax:':<40} ${results['ordinary_income_tax']:>14,.2f}")
    print(f"  {'Long-Term Capital Gains Tax:':<40} ${results['long_term_capital_gains_tax']:>14,.2f}")
    print(f"  {'-' * 40}")
    print(f"  {'Total Federal Tax:':<40} ${results['federal_tax']:>14,.2f}")
    print(f"  {'Marginal Bracket:':<40} {results['marginal_bracket']:>14.2%}")
    
    print()
    print("-" * 60)
    print("FICA TAXES")
    print("-" * 60)
    print(f"  {'Social Security + MA PFML:':<40} ${results['total_social_security']:>14,.2f}")
    print(f"  {'Medicare:':<40} ${results['medicare_charge']:>14,.2f}")
    print(f"  {'Medicare Surcharge:':<40} ${results['medicare_surcharge']:>14,.2f}")
    print(f"  {'-' * 40}")
    print(f"  {'Total FICA:':<40} ${total_fica:>14,.2f}")
    
    print()
    print("-" * 60)
    print("STATE TAXES")
    print("-" * 60)
    print(f"  {'State Income Tax:':<40} ${results.get('state_income_tax', 0):>14,.2f}")
    print(f"  {'State Short-Term Capital Gains Tax:':<40} ${results.get('state_short_term_capital_gains_tax', 0):>14,.2f}")
    print(f"  {'-' * 40}")
    print(f"  {'Total State Tax:':<40} ${total_state:>14,.2f}")
    
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  {'Gross Income:':<40} ${results['gross_income']:>14,.2f}")
    print(f"  {'Total Deductions:':<40} ${results['total_deductions']:>14,.2f}")
    print(f"  {'Total Federal Tax:':<40} ${total_federal:>14,.2f}")
    print(f"  {'Total FICA:':<40} ${total_fica:>14,.2f}")
    print(f"  {'Total State Tax:':<40} ${total_state:>14,.2f}")
    print(f"  {'-' * 40}")
    print(f"  {'TOTAL TAXES PAID:':<40} ${total_taxes:>14,.2f}")
    print()
    print("=" * 60)
    print(f"{'TAKE HOME PAY:':^44} ${results['take_home_pay']:>14,.2f}")
    print("=" * 60)
    print()

    # calculation moved to `src/calc/take_home.py`

if __name__ == "__main__":
    main()
