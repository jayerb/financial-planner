import sys
import os
import json
import argparse
from tax.FederalDetails import FederalDetails
from tax.StateDetails import StateDetails
from tax.ESPPDetails import ESPPDetails
from tax.SocialSecurityDetails import SocialSecurityDetails
from tax.MedicareDetails import MedicareDetails
from calc.take_home import TakeHomeCalculator
from calc.rsu_calculator import RSUCalculator
from calc.balance_calculator import BalanceCalculator
from calc.deferred_comp_calculator import DeferredCompCalculator
from render.renderers import TaxDetailsRenderer, BalancesRenderer, AnnualSummaryRenderer, RENDERER_REGISTRY


def calculate_yearly_deferrals(calculator: TakeHomeCalculator, spec: dict) -> dict:
    """Calculate yearly deferrals for working years only.
    
    This is needed to initialize the DeferredCompCalculator before 
    calculating post-working year results that include disbursements.
    
    Args:
        calculator: TakeHomeCalculator instance (without deferred comp calculator set)
        spec: The program specification dictionary
        
    Returns:
        Dictionary mapping year to total deferral amount
    """
    first_year = spec.get('firstYear', 2026)
    last_working_year = spec.get('lastWorkingYear', first_year + 10)
    
    yearly_deferrals = {}
    for year in range(first_year, last_working_year + 1):
        results = calculator.calculate(spec, year)
        yearly_deferrals[year] = results.get('total_deferral', 0)
    
    return yearly_deferrals


def main():
    parser = argparse.ArgumentParser(
        description='Financial planning calculator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  TaxDetails     Print detailed tax breakdown for the first year (default)
  Balances       Print accumulated balances for 401(k) and deferred compensation plans
  AnnualSummary  Print summary table of income and tax burden for each working year

Examples:
  python src/Program.py myprogram
  python src/Program.py myprogram --mode TaxDetails
  python src/Program.py myprogram --mode Balances
  python src/Program.py myprogram --mode AnnualSummary
        """
    )
    parser.add_argument('program_name', help='Name of the program (folder in input-parameters)')
    parser.add_argument('--mode', '-m', 
                        choices=list(RENDERER_REGISTRY.keys()), 
                        default='TaxDetails',
                        help='Output mode: TaxDetails (default) or Balances')
    
    args = parser.parse_args()
    
    program_name = args.program_name
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

    # Calculate yearly deferrals and create deferred comp calculator
    yearly_deferrals = calculate_yearly_deferrals(calculator, spec)
    deferred_comp_calculator = DeferredCompCalculator(spec, yearly_deferrals)
    calculator.set_deferred_comp_calculator(deferred_comp_calculator)

    # Calculate and render based on mode
    if args.mode == 'TaxDetails':
        results = calculator.calculate(spec, tax_year)
        renderer = TaxDetailsRenderer(tax_year)
        renderer.render(results)
    elif args.mode == 'Balances':
        balance_calculator = BalanceCalculator(calculator, fed)
        balance_result = balance_calculator.calculate(spec)
        renderer = BalancesRenderer()
        renderer.render(balance_result)
    elif args.mode == 'AnnualSummary':
        last_planning_year = spec.get('lastPlanningYear', tax_year + 30)
        yearly_results = {}
        for year in range(tax_year, last_planning_year + 1):
            yearly_results[year] = calculator.calculate(spec, year)
        renderer = AnnualSummaryRenderer()
        renderer.render(yearly_results)

if __name__ == "__main__":
    main()
