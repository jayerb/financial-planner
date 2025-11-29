import sys
import os
import json
import argparse
from tax.FederalDetails import FederalDetails
from tax.StateDetails import StateDetails
from tax.ESPPDetails import ESPPDetails
from tax.SocialSecurityDetails import SocialSecurityDetails
from tax.MedicareDetails import MedicareDetails
from calc.rsu_calculator import RSUCalculator
from calc.plan_calculator import PlanCalculator
from render.renderers import TaxDetailsRenderer, BalancesRenderer, AnnualSummaryRenderer, ContributionsRenderer, MoneyMovementRenderer, RENDERER_REGISTRY
from spec_generator import run_generator


def main():
    parser = argparse.ArgumentParser(
        description='Financial planning calculator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  TaxDetails     Print detailed tax breakdown for the first year (default)
  Balances       Print accumulated balances for 401(k) and deferred compensation plans
  AnnualSummary  Print summary table of income and tax burden for each working year
  Contributions  Print yearly contributions to each account type

Examples:
  python src/Program.py myprogram
  python src/Program.py myprogram --mode TaxDetails
  python src/Program.py myprogram --mode Balances
  python src/Program.py myprogram --mode AnnualSummary
  python src/Program.py myprogram --mode Contributions
  python src/Program.py --generate
        """
    )
    parser.add_argument('program_name', nargs='?', help='Name of the program (folder in input-parameters)')
    parser.add_argument('--mode', '-m', 
                        choices=list(RENDERER_REGISTRY.keys()), 
                        default='TaxDetails',
                        help='Output mode: TaxDetails (default) or Balances')
    parser.add_argument('--generate', '-g',
                        action='store_true',
                        help='Launch interactive wizard to create a new spec.json configuration')
    
    args = parser.parse_args()
    
    # If --generate flag is set, run the interactive generator
    if args.generate:
        program_name = run_generator()
        if program_name is None:
            sys.exit(0)
        # Ask if user wants to run the plan
        run_plan = input("Would you like to run the plan now? [Y/n]: ").strip().lower()
        if run_plan in ('', 'y', 'yes'):
            args.program_name = program_name
        else:
            sys.exit(0)
    
    # Require program_name if not generating
    if not args.program_name:
        parser.error("program_name is required (or use --generate to create a new configuration)")
    
    program_name = args.program_name
    # Build path to spec.json
    spec_path = os.path.join(os.path.dirname(__file__), '../input-parameters', program_name, 'spec.json')
    if not os.path.exists(spec_path):
        print(f"Spec file not found: {spec_path}")
        sys.exit(1)
    with open(spec_path, 'r') as f:
        spec = json.load(f)
    
    # Build detail instances
    tax_year = spec.get('firstYear', 2026)
    inflation_rate = spec.get('federalBracketInflation')
    final_year = spec.get('lastPlanningYear')
    
    fed = FederalDetails(inflation_rate, final_year)
    state = StateDetails(inflation_rate, final_year)
    
    # Read max ESPP cap from reference
    fed_ref_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '../reference', 'federal-details.json'))
    with open(fed_ref_path, 'r') as f:
        fed_ref = json.load(f)
    max_espp = fed_ref.get('maxESPPValue', 0)
    espp = ESPPDetails(max_espp)

    # Create Social Security details
    social_security = SocialSecurityDetails(inflation_rate, final_year)

    # Read Medicare details from reference
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

    # Create the unified plan calculator
    calculator = PlanCalculator(fed, state, espp, social_security, medicare, rsu_calculator)
    
    # Calculate all data in a single pass
    plan_data = calculator.calculate(spec)

    # Render based on mode
    if args.mode == 'TaxDetails':
        renderer = TaxDetailsRenderer(tax_year)
        renderer.render(plan_data)
    elif args.mode == 'Balances':
        renderer = BalancesRenderer()
        renderer.render(plan_data)
    elif args.mode == 'AnnualSummary':
        renderer = AnnualSummaryRenderer()
        renderer.render(plan_data)
    elif args.mode == 'Contributions':
        renderer = ContributionsRenderer()
        renderer.render(plan_data)
    elif args.mode == 'MoneyMovement':
        renderer = MoneyMovementRenderer()
        renderer.render(plan_data)


if __name__ == "__main__":
    main()
