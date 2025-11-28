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

    print(f"\n=== Tax Summary for {tax_year} ===")
    print(f"\nGross Income: ${results['gross_income']:,.2f}")
    print(f"RSU Vested: ${results['rsu_vested_value']:,.2f}")
    
    print(f"\n--- Deductions ---")
    deductions = results['deductions']
    print(f"  Standard Deduction: ${deductions['standardDeduction']:,.2f}")
    print(f"  401(k) Contribution: ${deductions['max401k']:,.2f}")
    print(f"  HSA Contribution: ${deductions['maxHSA']:,.2f}")
    print(f"  Medical/Dental/Vision: ${deductions['medicalDentalVision']:,.2f}")
    print(f"  Total Deductions: ${results['total_deductions']:,.2f}")
    
    print(f"\nAdjusted Gross Income: ${results['adjusted_gross_income']:,.2f}")
    
    print(f"\n--- Federal Taxes ---")
    print(f"  Ordinary Income Tax: ${results['ordinary_income_tax']:,.2f}")
    print(f"  Long-Term Capital Gains Tax: ${results['long_term_capital_gains_tax']:,.2f}")
    print(f"  Total Federal Tax: ${results['federal_tax']:,.2f}")
    print(f"  Marginal Bracket: {results['marginal_bracket']:.2%}")
    
    print(f"\n--- Other Taxes ---")
    print(f"  Social Security + MA PFML: ${results['total_social_security']:,.2f}")
    print(f"  Medicare: ${results['medicare_charge']:,.2f}")
    print(f"  Medicare Surcharge: ${results['medicare_surcharge']:,.2f}")
    
    print(f"\n--- State Taxes ---")
    print(f"  State Income Tax: ${results.get('state_income_tax', 0):,.2f}")
    print(f"  State Short-Term Capital Gains Tax: ${results.get('state_short_term_capital_gains_tax', 0):,.2f}")
    print(f"  Total State Tax: ${results.get('state_tax', 0):,.2f}")
    
    print(f"\n=== Take Home Pay: ${results['take_home_pay']:,.2f} ===")

    # calculation moved to `src/calc/take_home.py`

if __name__ == "__main__":
    main()
