"""Interactive spec.json generator for financial planning.

This module provides an interactive command-line interface to generate
a spec.json configuration file by prompting users for their financial
planning parameters.
"""

import os
import json
from datetime import datetime
from typing import Any, Optional


def prompt_int(prompt: str, default: Optional[int] = None, min_val: Optional[int] = None, max_val: Optional[int] = None) -> int:
    """Prompt for an integer value with optional default and validation."""
    while True:
        default_str = f" [{default}]" if default is not None else ""
        try:
            value = input(f"{prompt}{default_str}: ").strip()
            if value == "" and default is not None:
                return default
            result = int(value)
            if min_val is not None and result < min_val:
                print(f"  Value must be at least {min_val}")
                continue
            if max_val is not None and result > max_val:
                print(f"  Value must be at most {max_val}")
                continue
            return result
        except ValueError:
            print("  Please enter a valid integer")


def prompt_float(prompt: str, default: Optional[float] = None, min_val: Optional[float] = None, max_val: Optional[float] = None) -> float:
    """Prompt for a float value with optional default and validation."""
    while True:
        default_str = f" [{default}]" if default is not None else ""
        try:
            value = input(f"{prompt}{default_str}: ").strip()
            if value == "" and default is not None:
                return default
            result = float(value)
            if min_val is not None and result < min_val:
                print(f"  Value must be at least {min_val}")
                continue
            if max_val is not None and result > max_val:
                print(f"  Value must be at most {max_val}")
                continue
            return result
        except ValueError:
            print("  Please enter a valid number")


def prompt_percent(prompt: str, default: Optional[float] = None, max_val: float = 100.0) -> float:
    """Prompt for a percentage and return as a fraction (0-1)."""
    while True:
        default_display = f" [{default * 100:.1f}%]" if default is not None else ""
        try:
            value = input(f"{prompt} (%){default_display}: ").strip().rstrip('%')
            if value == "" and default is not None:
                return default
            result = float(value)
            if result < 0:
                print("  Percentage cannot be negative")
                continue
            if result > max_val:
                print(f"  Percentage cannot exceed {max_val}%")
                continue
            return result / 100.0
        except ValueError:
            print("  Please enter a valid percentage (e.g., 15 for 15%)")


def prompt_currency(prompt: str, default: Optional[float] = None, min_val: float = 0) -> float:
    """Prompt for a currency value."""
    while True:
        default_str = f" [${default:,.2f}]" if default is not None else ""
        try:
            value = input(f"{prompt} ($){default_str}: ").strip().lstrip('$').replace(',', '')
            if value == "" and default is not None:
                return default
            result = float(value)
            if result < min_val:
                print(f"  Value must be at least ${min_val:,.2f}")
                continue
            return result
        except ValueError:
            print("  Please enter a valid dollar amount (e.g., 50000 or 50,000)")


def prompt_yes_no(prompt: str, default: bool = False) -> bool:
    """Prompt for a yes/no answer."""
    default_str = "Y/n" if default else "y/N"
    while True:
        value = input(f"{prompt} [{default_str}]: ").strip().lower()
        if value == "":
            return default
        if value in ('y', 'yes'):
            return True
        if value in ('n', 'no'):
            return False
        print("  Please enter 'y' or 'n'")


def prompt_string(prompt: str, default: Optional[str] = None) -> str:
    """Prompt for a string value."""
    default_str = f" [{default}]" if default else ""
    value = input(f"{prompt}{default_str}: ").strip()
    if value == "" and default:
        return default
    return value


def prompt_choice(prompt: str, choices: list[str], default: Optional[str] = None) -> str:
    """Prompt for a choice from a list of options."""
    choices_str = "/".join(choices)
    default_str = f" [{default}]" if default else ""
    while True:
        value = input(f"{prompt} ({choices_str}){default_str}: ").strip()
        if value == "" and default:
            return default
        # Case-insensitive match
        for choice in choices:
            if value.lower() == choice.lower():
                return choice
        print(f"  Please enter one of: {choices_str}")


def prompt_date(prompt: str, default: Optional[str] = None) -> str:
    """Prompt for a date in YYYY-MM-DD format."""
    default_str = f" [{default}]" if default else ""
    while True:
        value = input(f"{prompt} (YYYY-MM-DD){default_str}: ").strip()
        if value == "" and default:
            return default
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return value
        except ValueError:
            print("  Please enter a valid date in YYYY-MM-DD format (e.g., 2026-01-09)")


def print_section(title: str) -> None:
    """Print a section header."""
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)
    print()


def load_existing_spec(program_name: str, base_path: str) -> Optional[dict]:
    """Load an existing spec.json if it exists.
    
    Args:
        program_name: Name of the program folder
        base_path: Base path to the financial-planner directory
        
    Returns:
        The spec dictionary if it exists, None otherwise
    """
    spec_path = os.path.join(base_path, 'input-parameters', program_name, 'spec.json')
    if os.path.exists(spec_path):
        try:
            with open(spec_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    return None


def get_nested(d: dict, *keys, default=None):
    """Safely get a nested dictionary value.
    
    Args:
        d: The dictionary to search
        *keys: The sequence of keys to traverse
        default: Default value if path doesn't exist
        
    Returns:
        The value at the nested path, or default
    """
    for key in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(key, default)
        if d is None:
            return default
    return d


def generate_spec(existing_spec: Optional[dict] = None) -> dict:
    """Interactive wizard to generate a spec.json configuration.
    
    Args:
        existing_spec: Optional existing spec to use for default values
    """
    current_year = datetime.now().year
    ex = existing_spec or {}

    spec: dict[str, Any] = {}

    # =========================================================================
    # PLANNING HORIZON
    # =========================================================================
    print_section("Planning Horizon")
    
    spec['birthYear'] = prompt_int(
        "Your birth year (for Medicare eligibility at age 65)",
        default=ex.get('birthYear', current_year - 50),
        min_val=1900,
        max_val=current_year
    )
    
    spec['firstYear'] = prompt_int(
        "First year of your plan",
        default=ex.get('firstYear', current_year),
        min_val=current_year - 5,
        max_val=current_year + 5
    )
    
    spec['lastWorkingYear'] = prompt_int(
        "Last year you plan to work (retirement year)",
        default=ex.get('lastWorkingYear', spec['firstYear'] + 10),
        min_val=spec['firstYear']
    )
    
    spec['lastPlanningYear'] = prompt_int(
        "Last year of your financial plan",
        default=ex.get('lastPlanningYear', spec['lastWorkingYear'] + 30),
        min_val=spec['lastWorkingYear']
    )
    
    spec['federalBracketInflation'] = prompt_percent(
        "Expected annual inflation rate for tax brackets",
        default=ex.get('federalBracketInflation', 0.03)
    )

    # =========================================================================
    # INCOME
    # =========================================================================
    print_section("Income")
    
    income: dict[str, Any] = {}
    ex_income = ex.get('income', {})
    
    income['baseSalary'] = prompt_currency(
        "Annual base salary",
        default=ex_income.get('baseSalary'),
        min_val=0
    )
    
    income['bonusFraction'] = prompt_percent(
        "Annual bonus as percentage of base salary",
        default=ex_income.get('bonusFraction', 0.0)
    )
    
    income['annualBaseIncreaseFraction'] = prompt_percent(
        "Expected annual salary increase",
        default=ex_income.get('annualBaseIncreaseFraction', 0.03)
    )
    
    income['otherIncome'] = prompt_currency(
        "Other annual income (side jobs, etc.)",
        default=ex_income.get('otherIncome', 0.0)
    )

    # Investment Income - as percentages of taxable account balance
    print()
    print("--- Investment Income (as % of taxable account balance) ---")
    print("Note: Realized capital gains are calculated as a percentage of your taxable account balance.")
    print("These represent gains you actually realize (sell) each year, creating taxable income.")
    print("As your balance grows, so will your realized capital gains income.")
    
    income['realizedShortTermCapitalGainsPercent'] = prompt_percent(
        "Annual realized short-term capital gains as % of taxable balance",
        default=ex_income.get('realizedShortTermCapitalGainsPercent', 0.01)
    )
    
    income['realizedLongTermCapitalGainsPercent'] = prompt_percent(
        "Annual realized long-term capital gains as % of taxable balance",
        default=ex_income.get('realizedLongTermCapitalGainsPercent', 0.02)
    )

    spec['income'] = income

    # =========================================================================
    # PAY SCHEDULE
    # =========================================================================
    print_section("Pay Schedule")
    
    ex_pay_schedule = ex.get('paySchedule', {})
    has_existing_pay_schedule = 'paySchedule' in ex
    has_pay_schedule = prompt_yes_no("Do you want to configure pay schedule details?", default=has_existing_pay_schedule)
    
    if has_pay_schedule:
        pay_schedule: dict[str, Any] = {}
        
        # Default first pay date to first Friday of the first year
        default_first_pay_date = ex_pay_schedule.get('firstPayDate', f"{spec['firstYear']}-01-09")
        
        pay_schedule['firstPayDate'] = prompt_date(
            "First pay date of the year",
            default=default_first_pay_date
        )
        
        pay_schedule['schedule'] = prompt_choice(
            "Pay schedule",
            choices=['BiWeekly', 'BiMonthly'],
            default=ex_pay_schedule.get('schedule', 'BiWeekly')
        )
        
        pay_schedule['bonusPayPeriod'] = prompt_int(
            "Pay period number after which bonus is paid (e.g., 17)",
            default=ex_pay_schedule.get('bonusPayPeriod', 17),
            min_val=1,
            max_val=26
        )
        
        pay_schedule['rsuVestingPayPeriod'] = prompt_int(
            "Pay period number after which RSUs vest (e.g., 21)",
            default=ex_pay_schedule.get('rsuVestingPayPeriod', 21),
            min_val=1,
            max_val=26
        )
        
        spec['paySchedule'] = pay_schedule

    # =========================================================================
    # DEFERRED COMPENSATION
    # =========================================================================
    print_section("Deferred Compensation")
    
    # Check if existing spec has deferred compensation
    has_existing_deferred = 'deferredCompensationPlan' in ex or ex_income.get('baseDeferralFraction', 0) > 0
    has_deferred = prompt_yes_no("Do you have a deferred compensation plan?", default=has_existing_deferred)
    
    ex_deferred = ex.get('deferredCompensationPlan', {})
    
    if has_deferred:
        spec['income']['baseDeferralFraction'] = prompt_percent(
            "Percentage of base salary to defer",
            default=ex_income.get('baseDeferralFraction', 0.0),
            max_val=75.0
        )
        
        spec['income']['bonusDeferralFraction'] = prompt_percent(
            "Percentage of bonus to defer",
            default=ex_income.get('bonusDeferralFraction', 0.0),
            max_val=75.0
        )
        
        deferred_plan: dict[str, Any] = {}
        deferred_plan['maxDeferralFraction'] = prompt_percent(
            "Maximum allowed deferral fraction",
            default=ex_deferred.get('maxDeferralFraction', 0.75),
            max_val=100.0
        )
        
        deferred_plan['disbursementYears'] = prompt_int(
            "Number of years for disbursements after retirement",
            default=ex_deferred.get('disbursementYears', 10),
            min_val=1,
            max_val=30
        )
        
        deferred_plan['annualGrowthFraction'] = prompt_percent(
            "Expected annual growth rate on deferred balance",
            default=ex_deferred.get('annualGrowthFraction', 0.05)
        )
        
        spec['deferredCompensationPlan'] = deferred_plan

    # =========================================================================
    # EMPLOYEE STOCK PURCHASE PLAN (ESPP)
    # =========================================================================
    print_section("Employee Stock Purchase Plan (ESPP)")
    
    has_existing_espp = ex.get('esppDiscount', 0) > 0 or ex_income.get('esppIncome', 0) > 0
    has_espp = prompt_yes_no("Do you participate in an ESPP?", default=has_existing_espp)
    
    if has_espp:
        spec['esppDiscount'] = prompt_percent(
            "ESPP discount percentage",
            default=ex.get('esppDiscount', 0.15)
        )
        
        spec['income']['esppIncome'] = prompt_currency(
            "Annual ESPP taxable income (discount benefit)",
            default=ex_income.get('esppIncome', 0.0)
        )

    # =========================================================================
    # RESTRICTED STOCK UNITS (RSUs)
    # =========================================================================
    print_section("Restricted Stock Units (RSUs)")
    
    has_existing_rsu = 'restrictedStockUnits' in ex
    has_rsu = prompt_yes_no("Do you have RSU grants?", default=has_existing_rsu)
    
    ex_rsu = ex.get('restrictedStockUnits', {})
    
    if has_rsu:
        rsu: dict[str, Any] = {}
        
        rsu['currentStockPrice'] = prompt_currency(
            "Current stock price",
            default=ex_rsu.get('currentStockPrice'),
            min_val=0.01
        )
        
        rsu['expectedSharePriceGrowthFraction'] = prompt_percent(
            "Expected annual stock price growth",
            default=ex_rsu.get('expectedSharePriceGrowthFraction', 0.07)
        )
        
        rsu['vestingPeriodYears'] = prompt_int(
            "Vesting period (years)",
            default=ex_rsu.get('vestingPeriodYears', 4),
            min_val=1,
            max_val=10
        )
        
        rsu['initialAnnualGrantValue'] = prompt_currency(
            "Expected annual RSU grant value (in dollars)",
            default=ex_rsu.get('initialAnnualGrantValue', 0.0)
        )
        
        rsu['annualGrantIncreaseFraction'] = prompt_percent(
            "Expected annual increase in grant value",
            default=ex_rsu.get('annualGrantIncreaseFraction', 0.05)
        )
        
        # Previous grants
        print()
        ex_previous_grants = ex_rsu.get('previousGrants', [])
        has_existing_previous = len(ex_previous_grants) > 0
        if has_existing_previous:
            print(f"Existing previous grants: {len(ex_previous_grants)} grant(s)")
            for grant in ex_previous_grants:
                print(f"  - Year {grant.get('year')}: {grant.get('grantShares')} shares, "
                      f"{grant.get('vestingPeriodYears')}-year vesting")
            keep_existing = prompt_yes_no("Keep existing previous grants?", default=True)
            if keep_existing:
                previous_grants = ex_previous_grants.copy()
                add_more = prompt_yes_no("Add more grants?", default=False)
            else:
                previous_grants = []
                add_more = prompt_yes_no("Do you have unvested grants from previous years?", default=False)
        else:
            previous_grants = []
            add_more = prompt_yes_no("Do you have unvested grants from previous years?", default=False)
        
        if add_more:
            print()
            print("Enter previous grants (press Enter with no year to finish):")
            while True:
                year_str = input("  Grant year (or Enter to finish): ").strip()
                if year_str == "":
                    break
                try:
                    year = int(year_str)
                    shares = prompt_int("    Number of shares granted", min_val=1)
                    vest_years = prompt_int("    Vesting period for this grant", default=rsu['vestingPeriodYears'], min_val=1)
                    previous_grants.append({
                        "year": year,
                        "grantShares": shares,
                        "vestingPeriodYears": vest_years
                    })
                except ValueError:
                    print("    Please enter a valid year")
        
        rsu['previousGrants'] = previous_grants
        spec['restrictedStockUnits'] = rsu

    # =========================================================================
    # DEDUCTIONS
    # =========================================================================
    print_section("Deductions")
    
    ex_deductions = ex.get('deductions', {})
    deductions: dict[str, Any] = {}
    
    deductions['medicalDentalVision'] = prompt_currency(
        "Annual medical/dental/vision premiums (pre-tax)",
        default=ex_deductions.get('medicalDentalVision', 0.0)
    )
    
    if deductions['medicalDentalVision'] > 0:
        deductions['medicalInflationRate'] = prompt_percent(
            "Expected annual medical cost inflation rate",
            default=ex_deductions.get('medicalInflationRate', 0.05)
        )
    
    has_existing_deductions = len(ex_deductions) > 0
    if deductions['medicalDentalVision'] > 0 or prompt_yes_no("Add any deductions?", default=has_existing_deductions):
        spec['deductions'] = deductions

    # =========================================================================
    # INSURANCE (for retirement)
    # =========================================================================
    print_section("Insurance (Post-Retirement)")
    
    print("Note: These values represent your insurance costs as of your plan start year.")
    print("Pre-Medicare costs are used after retirement until age 65 (e.g., COBRA or private insurance).")
    print("Medicare costs are used starting at age 65.")
    print("All costs will be inflated from the plan start year to when you actually need them.")
    print()
    
    ex_insurance = ex.get('insurance', {})
    has_existing_insurance = 'insurance' in ex
    has_insurance = prompt_yes_no("Do you want to plan for post-retirement insurance costs?", default=has_existing_insurance)
    
    if has_insurance:
        insurance: dict[str, Any] = {}
        
        insurance['fullInsurancePremiums'] = prompt_currency(
            "Annual pre-Medicare insurance premiums (as of plan start year)",
            default=ex_insurance.get('fullInsurancePremiums', 0.0)
        )
        
        insurance['medicarePremiums'] = prompt_currency(
            "Annual Medicare premiums (as of plan start year, used at age 65+)",
            default=ex_insurance.get('medicarePremiums', 0.0)
        )
        
        if insurance['fullInsurancePremiums'] > 0 or insurance['medicarePremiums'] > 0:
            insurance['premiumInflationRate'] = prompt_percent(
                "Expected annual insurance premium inflation rate",
                default=ex_insurance.get('premiumInflationRate', 0.05)
            )
        
        if insurance['fullInsurancePremiums'] > 0 or insurance['medicarePremiums'] > 0:
            spec['insurance'] = insurance

    # =========================================================================
    # LOCAL TAXES
    # =========================================================================
    print_section("Local Taxes")
    
    ex_local_tax = ex.get('localTax', {})
    has_existing_local_tax = 'localTax' in ex
    has_local_tax = prompt_yes_no("Do you have local taxes (e.g., property/real estate tax)?", default=has_existing_local_tax)
    
    if has_local_tax:
        local_tax: dict[str, Any] = {}
        
        local_tax['realEstate'] = prompt_currency(
            "Annual real estate/property tax",
            default=ex_local_tax.get('realEstate', 0.0)
        )
        
        local_tax['inflationRate'] = prompt_percent(
            "Expected annual property tax inflation rate",
            default=ex_local_tax.get('inflationRate', 0.03)
        )
        
        spec['localTax'] = local_tax

    # =========================================================================
    # COMPANY BENEFITS
    # =========================================================================
    print_section("Company Benefits")
    
    ex_life_insurance = ex.get('companyProvidedLifeInsurance', {})
    has_existing_life = 'companyProvidedLifeInsurance' in ex
    has_life_insurance = prompt_yes_no("Does your company provide taxable life insurance?", default=has_existing_life)
    
    if has_life_insurance:
        spec['companyProvidedLifeInsurance'] = {
            'annualPremium': prompt_currency(
                "Annual taxable life insurance premium",
                default=ex_life_insurance.get('annualPremium', 0.0)
            )
        }

    # =========================================================================
    # INVESTMENT ACCOUNTS
    # =========================================================================
    print_section("Investment Accounts")
    
    ex_investments = ex.get('investments', {})
    investments: dict[str, Any] = {}
    
    # Taxable brokerage accounts
    print("--- Taxable Accounts ---")
    investments['taxableBalance'] = prompt_currency(
        "Current taxable brokerage account balance",
        default=ex_investments.get('taxableBalance', 0.0)
    )
    
    if investments['taxableBalance'] > 0:
        investments['taxableAppreciationRate'] = prompt_percent(
            "Expected annual appreciation rate for taxable accounts",
            default=ex_investments.get('taxableAppreciationRate', 0.07)
        )
    
    # Tax-deferred accounts (401k, Traditional IRA)
    print()
    print("--- Tax-Deferred Accounts (401k, Traditional IRA) ---")
    investments['taxDeferredBalance'] = prompt_currency(
        "Current 401(k) and Traditional IRA balance",
        default=ex_investments.get('taxDeferredBalance', 0.0)
    )
    
    if investments['taxDeferredBalance'] > 0:
        investments['taxDeferredAppreciationRate'] = prompt_percent(
            "Expected annual appreciation rate for tax-deferred accounts",
            default=ex_investments.get('taxDeferredAppreciationRate', 0.07)
        )
    
    # Employer 401k match
    print()
    print("--- Employer 401(k) Match ---")
    print("Note: The match is calculated on salary AFTER any deferred compensation contributions.")
    has_existing_match = ex_investments.get('employer401kMatchPercent', 0) > 0
    has_employer_match = prompt_yes_no("Does your employer offer a 401(k) match?", default=has_existing_match)
    
    if has_employer_match:
        investments['employer401kMatchPercent'] = prompt_percent(
            "Employer match percentage (e.g., 50% means employer matches 50 cents per dollar)",
            default=ex_investments.get('employer401kMatchPercent', 0.50)
        )
        investments['employer401kMatchMaxSalaryPercent'] = prompt_percent(
            "Maximum salary percentage eligible for match (e.g., 6% means match on up to 6% of salary)",
            default=ex_investments.get('employer401kMatchMaxSalaryPercent', 0.06)
        )
    
    # HSA
    print()
    print("--- Health Savings Account (HSA) ---")
    investments['hsaBalance'] = prompt_currency(
        "Current HSA balance",
        default=ex_investments.get('hsaBalance', 0.0)
    )
    
    if investments['hsaBalance'] > 0:
        investments['hsaAppreciationRate'] = prompt_percent(
            "Expected annual appreciation rate for HSA",
            default=ex_investments.get('hsaAppreciationRate', 0.07)
        )
    
    # Always ask about HSA employer contribution if working and has HSA balance or participating in HSA
    # The HSA max contribution is split between employer and employee
    print()
    print("Note: The statutory HSA maximum is the combined employer + employee contribution.")
    print("Only the employee contribution is tax-deferred from your income.")
    investments['hsaEmployerContribution'] = prompt_currency(
        "Annual HSA employer contribution (will grow with inflation)",
        default=ex_investments.get('hsaEmployerContribution', 0.0)
    )
    
    # HSA withdrawals
    print()
    print("--- HSA Withdrawals ---")
    print("Note: HSA withdrawals for qualified medical expenses are tax-free.")
    print("These withdrawals reduce your HSA balance but don't add to taxable income.")
    investments['hsaAnnualWithdrawal'] = prompt_currency(
        "Annual HSA withdrawal for medical expenses (as of plan start year)",
        default=ex_investments.get('hsaAnnualWithdrawal', 0.0)
    )
    
    if investments['hsaAnnualWithdrawal'] > 0:
        investments['hsaWithdrawalInflationRate'] = prompt_percent(
            "Expected annual HSA withdrawal inflation rate",
            default=ex_investments.get('hsaWithdrawalInflationRate', 0.04)
        )
    
    # Only add investments section if any accounts have balances
    if investments['taxableBalance'] > 0 or investments['taxDeferredBalance'] > 0 or investments['hsaBalance'] > 0:
        spec['investments'] = investments

    # =========================================================================
    # EXPENSES
    # =========================================================================
    print_section("Expenses")
    
    ex_expenses = ex.get('expenses', {})
    has_existing_expenses = 'expenses' in ex
    has_expenses = prompt_yes_no("Do you want to track annual expenses?", default=has_existing_expenses)
    
    if has_expenses:
        expenses: dict[str, Any] = {}
        
        expenses['annualAmount'] = prompt_currency(
            "Annual expense amount (as of plan start year)",
            default=ex_expenses.get('annualAmount', 0.0)
        )
        
        if expenses['annualAmount'] > 0:
            expenses['inflationRate'] = prompt_percent(
                "Expected annual expense inflation rate",
                default=ex_expenses.get('inflationRate', 0.03)
            )
        
        # Special case expenses
        print()
        ex_special_expenses = ex_expenses.get('specialExpenses', [])
        has_existing_special = len(ex_special_expenses) > 0
        if has_existing_special:
            print(f"Existing special expenses: {len(ex_special_expenses)} item(s)")
            for exp in ex_special_expenses:
                print(f"  - Year {exp.get('year')}: ${exp.get('amount'):,.2f} - {exp.get('description', 'No description')}")
            keep_existing = prompt_yes_no("Keep existing special expenses?", default=True)
            if keep_existing:
                special_expenses = [dict(e) for e in ex_special_expenses]  # Deep copy
                add_more = prompt_yes_no("Add more special expenses?", default=False)
            else:
                special_expenses = []
                add_more = prompt_yes_no("Do you have any special one-time expenses in future years?", default=False)
        else:
            special_expenses = []
            add_more = prompt_yes_no("Do you have any special one-time expenses in future years?", default=False)
        
        if add_more:
            print()
            print("Enter special expenses (press Enter with no year to finish):")
            print("Examples: college tuition, home renovation, car purchase, wedding, etc.")
            while True:
                year_str = input("  Year of expense (or Enter to finish): ").strip()
                if year_str == "":
                    break
                try:
                    year = int(year_str)
                    if year < spec['firstYear'] or year > spec['lastPlanningYear']:
                        print(f"    Year must be between {spec['firstYear']} and {spec['lastPlanningYear']}")
                        continue
                    amount = prompt_currency("    Expense amount", min_val=0.01)
                    description = prompt_string("    Description (optional)", default="")
                    expense_entry: dict[str, Any] = {
                        "year": year,
                        "amount": amount
                    }
                    if description:
                        expense_entry["description"] = description
                    special_expenses.append(expense_entry)
                except ValueError:
                    print("    Please enter a valid year")
        
        if special_expenses:
            expenses['specialExpenses'] = special_expenses
        
        # Travel expenses
        print()
        has_existing_travel = 'travelAmount' in ex_expenses
        has_travel = prompt_yes_no("Do you want to track travel expenses separately?", default=has_existing_travel)
        
        if has_travel:
            expenses['travelAmount'] = prompt_currency(
                "Annual travel expense amount (as of plan start year)",
                default=ex_expenses.get('travelAmount', 0.0)
            )
            
            if expenses['travelAmount'] > 0:
                expenses['travelRetirementMultiplier'] = prompt_float(
                    "Retirement year travel multiplier (e.g., 1.5 = 50% increase in retirement)",
                    default=ex_expenses.get('travelRetirementMultiplier', 1.0),
                    min_val=0.0
                )
                
                expenses['travelInflationRate'] = prompt_percent(
                    "Expected annual travel expense inflation rate",
                    default=ex_expenses.get('travelInflationRate', ex_expenses.get('inflationRate', 0.03))
                )
        
        if expenses['annualAmount'] > 0 or special_expenses or expenses.get('travelAmount', 0) > 0:
            spec['expenses'] = expenses

    return spec


def save_spec(spec: dict, program_name: str, base_path: str) -> str:
    """Save the spec to a JSON file.
    
    Args:
        spec: The specification dictionary
        program_name: Name for the program folder
        base_path: Base path to the financial-planner directory
        
    Returns:
        Path to the saved file
    """
    # Create the directory
    program_dir = os.path.join(base_path, 'input-parameters', program_name)
    os.makedirs(program_dir, exist_ok=True)
    
    # Save the spec
    spec_path = os.path.join(program_dir, 'spec.json')
    with open(spec_path, 'w') as f:
        json.dump(spec, f, indent=4)
    
    return spec_path


def list_existing_programs(base_path: str) -> list[str]:
    """List all existing programs in the input-parameters directory.
    
    Args:
        base_path: Base path to the financial-planner directory
        
    Returns:
        List of program names
    """
    input_params_path = os.path.join(base_path, 'input-parameters')
    if not os.path.exists(input_params_path):
        return []
    
    programs = []
    for name in os.listdir(input_params_path):
        program_dir = os.path.join(input_params_path, name)
        spec_path = os.path.join(program_dir, 'spec.json')
        if os.path.isdir(program_dir) and os.path.exists(spec_path):
            programs.append(name)
    
    return sorted(programs)


def run_generator() -> Optional[str]:
    """Run the interactive generator and return the program name if successful."""
    try:
        # Determine base path
        base_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
        
        print()
        print("╔════════════════════════════════════════════════════════════╗")
        print("║      Financial Planner - Configuration Generator          ║")
        print("╚════════════════════════════════════════════════════════════╝")
        print()
        
        # List existing programs
        existing_programs = list_existing_programs(base_path)
        if existing_programs:
            print("Existing plans:")
            for prog in existing_programs:
                print(f"  - {prog}")
            print()
            print("Enter an existing plan name to update it, or a new name to create.")
        else:
            print("No existing plans found. Enter a name for your new plan.")
        print()
        
        # Get program name first
        program_name = prompt_string(
            "Plan name",
            default="myplan"
        )
        
        # Clean up the name (remove spaces, special chars)
        program_name = "".join(c if c.isalnum() or c in '-_' else '_' for c in program_name)
        
        # Check if program exists and load it
        existing_spec = load_existing_spec(program_name, base_path)
        if existing_spec:
            print()
            print(f"Found existing plan '{program_name}'. Values will be used as defaults.")
        else:
            print()
            print(f"Creating new plan '{program_name}'.")
        
        # Generate spec with existing values as defaults
        spec = generate_spec(existing_spec)
        
        # Save
        spec_path = save_spec(spec, program_name, base_path)
        
        print()
        print("╔════════════════════════════════════════════════════════════╗")
        print("║                    Configuration Saved!                    ║")
        print("╚════════════════════════════════════════════════════════════╝")
        print()
        print(f"  Saved to: {spec_path}")
        print()
        print("  To run your financial plan:")
        print(f"    python src/Program.py {program_name}")
        print()
        print("  Available modes:")
        print(f"    python src/Program.py {program_name} --mode TaxDetails")
        print(f"    python src/Program.py {program_name} --mode Balances")
        print(f"    python src/Program.py {program_name} --mode AnnualSummary")
        print()
        
        return program_name
        
    except KeyboardInterrupt:
        print("\n\nCancelled. No changes made.")
        return None


if __name__ == "__main__":
    run_generator()
