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
from render.renderers import TaxDetailsRenderer, BalancesRenderer, AnnualSummaryRenderer, ContributionsRenderer, RENDERER_REGISTRY
from calc.investment_calculator import InvestmentCalculator
from spec_generator import run_generator


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

    # Calculate taxable balances for capital gains percentage calculation
    def calculate_taxable_balances(spec: dict) -> dict:
        investments = spec.get('investments', {})
        initial_balance = investments.get('taxableBalance', 0.0)
        appreciation_rate = investments.get('taxableAppreciationRate', 0.07)
        first_yr = spec.get('firstYear', 2026)
        last_yr = spec.get('lastPlanningYear', first_yr + 30)
        
        balances = {}
        balance = initial_balance
        for year in range(first_yr, last_yr + 1):
            balances[year] = balance
            balance = balance * (1 + appreciation_rate)
        return balances
    
    taxable_balances = calculate_taxable_balances(spec)
    calculator.set_taxable_balances(taxable_balances)

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
    elif args.mode == 'Contributions':
        last_working_year = spec.get('lastWorkingYear', tax_year + 10)
        last_planning_year = spec.get('lastPlanningYear', tax_year + 30)
        
        # Calculate yearly results for working years
        yearly_results = {}
        yearly_contributions = {}
        for year in range(tax_year, last_working_year + 1):
            results = calculator.calculate(spec, year)
            yearly_results[year] = results
            
            # Build contribution data for InvestmentCalculator
            deductions = results.get('deductions', {})
            employee_401k = deductions.get('max401k', 0)
            employee_hsa = deductions.get('employeeHSA', deductions.get('maxHSA', 0))
            
            # Calculate employer 401k match
            investments = spec.get('investments', {})
            match_percent = investments.get('employer401kMatchPercent', 0)
            match_max_salary_percent = investments.get('employer401kMatchMaxSalaryPercent', 0)
            
            # Calculate base salary and bonus for this year (with inflation)
            income = spec.get('income', {})
            base_salary = income.get('baseSalary', 0)
            bonus_fraction = income.get('bonusFraction', 0)
            annual_increase = income.get('annualBaseIncreaseFraction', 0)
            years_from_first = year - tax_year
            if years_from_first > 0:
                base_salary = base_salary * ((1 + annual_increase) ** years_from_first)
            bonus = base_salary * bonus_fraction
            
            # Deduct deferred compensation from salary + bonus for match calculation
            total_deferral = results.get('total_deferral', 0)
            matchable_compensation = base_salary + bonus - total_deferral
            
            # Employer match: match_percent of employee contribution up to match_max_salary_percent of compensation
            max_matchable = matchable_compensation * match_max_salary_percent
            matchable_contribution = min(employee_401k, max_matchable)
            employer_match = matchable_contribution * match_percent
            
            yearly_contributions[year] = {
                '401k': employee_401k,
                'hsa': employee_hsa,
                'employer_match': employer_match
            }
        
        # Create investment calculator with contributions
        investment_calc = InvestmentCalculator(
            spec, tax_year, last_planning_year,
            last_working_year=last_working_year,
            yearly_contributions=yearly_contributions
        )
        
        renderer = ContributionsRenderer()
        renderer.render({
            'yearly_results': yearly_results,
            'investment_balances': investment_calc.get_all_balances(),
            'last_working_year': last_working_year
        })

if __name__ == "__main__":
    main()
