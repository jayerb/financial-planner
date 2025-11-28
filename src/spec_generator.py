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


def print_section(title: str) -> None:
    """Print a section header."""
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)
    print()


def generate_spec() -> dict:
    """Interactive wizard to generate a spec.json configuration."""
    current_year = datetime.now().year
    
    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║      Financial Planner - Configuration Generator          ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()
    print("This wizard will guide you through creating your financial plan.")
    print("Press Enter to accept default values shown in [brackets].")
    print()

    spec: dict[str, Any] = {}

    # =========================================================================
    # PLANNING HORIZON
    # =========================================================================
    print_section("Planning Horizon")
    
    spec['firstYear'] = prompt_int(
        "First year of your plan",
        default=current_year,
        min_val=current_year - 5,
        max_val=current_year + 5
    )
    
    spec['lastWorkingYear'] = prompt_int(
        "Last year you plan to work (retirement year)",
        default=spec['firstYear'] + 10,
        min_val=spec['firstYear']
    )
    
    spec['lastPlanningYear'] = prompt_int(
        "Last year of your financial plan",
        default=spec['lastWorkingYear'] + 30,
        min_val=spec['lastWorkingYear']
    )
    
    spec['federalBracketInflation'] = prompt_percent(
        "Expected annual inflation rate for tax brackets",
        default=0.03
    )

    # =========================================================================
    # INCOME
    # =========================================================================
    print_section("Income")
    
    income: dict[str, Any] = {}
    
    income['baseSalary'] = prompt_currency(
        "Annual base salary",
        min_val=0
    )
    
    income['bonusFraction'] = prompt_percent(
        "Annual bonus as percentage of base salary",
        default=0.0
    )
    
    income['annualBaseIncreaseFraction'] = prompt_percent(
        "Expected annual salary increase",
        default=0.03
    )
    
    income['otherIncome'] = prompt_currency(
        "Other annual income (side jobs, etc.)",
        default=0.0
    )

    # Investment Income
    print()
    print("--- Investment Income ---")
    
    income['shortTermCapitalGains'] = prompt_currency(
        "Expected annual short-term capital gains",
        default=0.0
    )
    
    income['longTermCapitalGains'] = prompt_currency(
        "Expected annual long-term capital gains",
        default=0.0
    )

    spec['income'] = income

    # =========================================================================
    # DEFERRED COMPENSATION
    # =========================================================================
    print_section("Deferred Compensation")
    
    has_deferred = prompt_yes_no("Do you have a deferred compensation plan?", default=False)
    
    if has_deferred:
        spec['income']['baseDeferralFraction'] = prompt_percent(
            "Percentage of base salary to defer",
            default=0.0,
            max_val=75.0
        )
        
        spec['income']['bonusDeferralFraction'] = prompt_percent(
            "Percentage of bonus to defer",
            default=0.0,
            max_val=75.0
        )
        
        deferred_plan: dict[str, Any] = {}
        deferred_plan['maxDeferralFraction'] = prompt_percent(
            "Maximum allowed deferral fraction",
            default=0.75,
            max_val=100.0
        )
        
        deferred_plan['dispursementYears'] = prompt_int(
            "Number of years for disbursements after retirement",
            default=10,
            min_val=1,
            max_val=30
        )
        
        deferred_plan['annualGrowthFraction'] = prompt_percent(
            "Expected annual growth rate on deferred balance",
            default=0.05
        )
        
        spec['deferredCompensationPlan'] = deferred_plan

    # =========================================================================
    # EMPLOYEE STOCK PURCHASE PLAN (ESPP)
    # =========================================================================
    print_section("Employee Stock Purchase Plan (ESPP)")
    
    has_espp = prompt_yes_no("Do you participate in an ESPP?", default=False)
    
    if has_espp:
        spec['esppDiscount'] = prompt_percent(
            "ESPP discount percentage",
            default=0.15
        )
        
        spec['income']['esppIncome'] = prompt_currency(
            "Annual ESPP taxable income (discount benefit)",
            default=0.0
        )

    # =========================================================================
    # RESTRICTED STOCK UNITS (RSUs)
    # =========================================================================
    print_section("Restricted Stock Units (RSUs)")
    
    has_rsu = prompt_yes_no("Do you have RSU grants?", default=False)
    
    if has_rsu:
        rsu: dict[str, Any] = {}
        
        rsu['currentStockPrice'] = prompt_currency(
            "Current stock price",
            min_val=0.01
        )
        
        rsu['expectedSharePriceGrowthFraction'] = prompt_percent(
            "Expected annual stock price growth",
            default=0.07
        )
        
        rsu['vestingPeriodYears'] = prompt_int(
            "Vesting period (years)",
            default=4,
            min_val=1,
            max_val=10
        )
        
        rsu['initialAnnualGrantValue'] = prompt_currency(
            "Expected annual RSU grant value (in dollars)",
            default=0.0
        )
        
        rsu['annualGrantIncreaseFraction'] = prompt_percent(
            "Expected annual increase in grant value",
            default=0.05
        )
        
        # Previous grants
        print()
        has_previous = prompt_yes_no("Do you have unvested grants from previous years?", default=False)
        
        previous_grants = []
        if has_previous:
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
    
    deductions: dict[str, Any] = {}
    
    deductions['medicalDentalVision'] = prompt_currency(
        "Annual medical/dental/vision premiums (pre-tax)",
        default=0.0
    )
    
    if deductions['medicalDentalVision'] > 0 or prompt_yes_no("Add any deductions?", default=False):
        spec['deductions'] = deductions

    # =========================================================================
    # COMPANY BENEFITS
    # =========================================================================
    print_section("Company Benefits")
    
    has_life_insurance = prompt_yes_no("Does your company provide taxable life insurance?", default=False)
    
    if has_life_insurance:
        spec['companyProvidedLifeInsurance'] = {
            'annualPremium': prompt_currency(
                "Annual taxable life insurance premium",
                default=0.0
            )
        }

    # =========================================================================
    # INVESTMENT ACCOUNTS
    # =========================================================================
    print_section("Investment Accounts")
    
    investments: dict[str, Any] = {}
    
    # Taxable brokerage accounts
    print("--- Taxable Accounts ---")
    investments['taxableBalance'] = prompt_currency(
        "Current taxable brokerage account balance",
        default=0.0
    )
    
    if investments['taxableBalance'] > 0:
        investments['taxableAppreciationRate'] = prompt_percent(
            "Expected annual appreciation rate for taxable accounts",
            default=0.07
        )
    
    # Tax-deferred accounts (401k, Traditional IRA)
    print()
    print("--- Tax-Deferred Accounts (401k, Traditional IRA) ---")
    investments['taxDeferredBalance'] = prompt_currency(
        "Current 401(k) and Traditional IRA balance",
        default=0.0
    )
    
    if investments['taxDeferredBalance'] > 0:
        investments['taxDeferredAppreciationRate'] = prompt_percent(
            "Expected annual appreciation rate for tax-deferred accounts",
            default=0.07
        )
    
    # HSA
    print()
    print("--- Health Savings Account (HSA) ---")
    investments['hsaBalance'] = prompt_currency(
        "Current HSA balance",
        default=0.0
    )
    
    if investments['hsaBalance'] > 0:
        investments['hsaAppreciationRate'] = prompt_percent(
            "Expected annual appreciation rate for HSA",
            default=0.07
        )
    
    # Only add investments section if any accounts have balances
    if investments['taxableBalance'] > 0 or investments['taxDeferredBalance'] > 0 or investments['hsaBalance'] > 0:
        spec['investments'] = investments

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


def run_generator() -> Optional[str]:
    """Run the interactive generator and return the program name if successful."""
    try:
        spec = generate_spec()
        
        print_section("Save Configuration")
        
        # Get program name
        program_name = prompt_string(
            "Enter a name for this plan (used as folder name)",
            default="myplan"
        )
        
        # Clean up the name (remove spaces, special chars)
        program_name = "".join(c if c.isalnum() or c in '-_' else '_' for c in program_name)
        
        # Determine base path
        base_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
        
        # Check if it already exists
        program_dir = os.path.join(base_path, 'input-parameters', program_name)
        if os.path.exists(program_dir):
            overwrite = prompt_yes_no(
                f"'{program_name}' already exists. Overwrite?",
                default=False
            )
            if not overwrite:
                print("Cancelled. No changes made.")
                return None
        
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
