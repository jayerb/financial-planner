#!/usr/bin/env python3
"""Interactive command shell for querying financial plan data.

This module provides an interactive shell that loads a financial plan
at startup and allows querying any field(s) from the yearly data
across a specified date range.

Usage:
    python src/shell.py [program_name]
    
Commands:
    get <fields> [year_or_range]  - Query fields from yearly data
    fields                        - List all available fields
    years                         - Show available year range
    load <program_name>           - Load a financial plan
    generate                      - Create or update a financial plan
    help                          - Show help message
    exit/quit                     - Exit the shell
    
Examples:
    > get gross_income
    > get gross_income, federal_tax
    > get take_home_pay 2026
    > get take_home_pay 2026-2030
    > get base_salary, bonus 2028-
    > load myprogram
"""

import sys
import os
import json
import cmd
import readline
from dataclasses import fields as dataclass_fields

# Configure readline for tab completion
# This must be done before the cmd.Cmd class is used
try:
    # For Unix/Linux/macOS - use libedit or GNU readline
    if 'libedit' in readline.__doc__:
        # macOS uses libedit which has different syntax
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        # GNU readline (Linux)
        readline.parse_and_bind("tab: complete")
except (AttributeError, TypeError):
    pass  # readline might not be fully available

# Add src directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from tax.FederalDetails import FederalDetails
from tax.StateDetails import StateDetails
from tax.ESPPDetails import ESPPDetails
from tax.SocialSecurityDetails import SocialSecurityDetails
from tax.MedicareDetails import MedicareDetails
from calc.rsu_calculator import RSUCalculator
from calc.plan_calculator import PlanCalculator
from model.PlanData import PlanData, YearlyData
from model.field_metadata import FIELD_METADATA, get_short_name, get_description
from spec_generator import run_generator
from render.renderers import (
    RENDERER_REGISTRY, 
    TaxDetailsRenderer,
    list_user_configs,
    get_user_config,
    save_user_config,
    delete_user_config,
    reload_renderer_registry,
    USER_CONFIG_DIR,
)


def load_plan(program_name: str) -> PlanData:
    """Load and calculate plan data for the given program.
    
    Args:
        program_name: Name of the program folder in input-parameters
        
    Returns:
        Calculated PlanData object
    """
    # Build path to spec.json
    spec_path = os.path.join(os.path.dirname(__file__), '../input-parameters', program_name, 'spec.json')
    if not os.path.exists(spec_path):
        raise FileNotFoundError(f"Spec file not found: {spec_path}")
    
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
    return calculator.calculate(spec)


def get_yearly_fields() -> list:
    """Get list of all field names from YearlyData dataclass."""
    return [f.name for f in dataclass_fields(YearlyData)]


def format_value(value) -> str:
    """Format a value for display."""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    elif isinstance(value, float):
        if abs(value) >= 1000:
            return f"${value:,.2f}"
        elif value == 0:
            return "$0.00"
        elif abs(value) < 1:
            return f"{value:.4f}"
        else:
            return f"${value:,.2f}"
    elif isinstance(value, int):
        return str(value)
    else:
        return str(value)


class FinancialPlanShell(cmd.Cmd):
    """Interactive shell for querying financial plan data."""
    
    intro = """
Financial Plan Interactive Shell
=================================
Type 'help' for available commands.
Type 'fields' to see available data fields.
Type 'exit' or 'quit' to exit.
"""
    prompt = '> '
    
    def __init__(self, plan_data: PlanData = None, program_name: str = None):
        super().__init__()
        self.plan_data = plan_data
        self.program_name = program_name
        self.available_fields = get_yearly_fields()
        self._update_intro()
    
    def preloop(self):
        """Set up readline before entering the command loop."""
        try:
            # Set completer delimiters - space and comma separate arguments
            readline.set_completer_delims(' \t\n,')
            # Ensure tab completion is bound
            if 'libedit' in (readline.__doc__ or ''):
                readline.parse_and_bind("bind ^I rl_complete")
            else:
                readline.parse_and_bind("tab: complete")
        except (AttributeError, TypeError):
            pass  # readline might not be fully available
    
    def _get_available_programs(self) -> list:
        """Get list of available program names from input-parameters directory."""
        input_params_dir = os.path.join(os.path.dirname(__file__), '../input-parameters')
        programs = []
        if os.path.exists(input_params_dir):
            for item in sorted(os.listdir(input_params_dir)):
                if os.path.isdir(os.path.join(input_params_dir, item)):
                    programs.append(item)
        return programs
    
    def _update_intro(self):
        """Update the intro message based on current state."""
        if self.plan_data and self.program_name:
            self.intro = f"""
Financial Plan Interactive Shell
=================================
Program: {self.program_name}
Years: {self.plan_data.first_year} - {self.plan_data.last_planning_year}
Working years: {self.plan_data.first_year} - {self.plan_data.last_working_year}

Type 'help' for available commands.
Type 'fields' to see available data fields.
Type 'exit' or 'quit' to exit.
"""
        else:
            self.intro = """
Financial Plan Interactive Shell
=================================
No plan loaded. Use 'load <program_name>' or 'generate' to get started.

Type 'help' for available commands.
Type 'exit' or 'quit' to exit.
"""
    
    def _require_plan(self) -> bool:
        """Check if a plan is loaded. Returns True if loaded, False otherwise."""
        if self.plan_data is None:
            print("No plan loaded. Use 'load <program_name>' or 'generate' first.")
            return False
        return True
    
    def do_get(self, arg: str):
        """Query field(s) from yearly data.
        
        Usage: get <fields> [year_or_range]
        
        Arguments:
            fields        - Comma-separated list of field names
            year_or_range - Optional: single year (2026) or range (2026-2030)
                            If range end is omitted (2026-), runs to last planning year
        
        Examples:
            get gross_income
            get gross_income, federal_tax
            get take_home_pay 2026
            get take_home_pay 2026-2030
            get base_salary, bonus 2028-
        """
        if not self._require_plan():
            return
        
        if not arg.strip():
            print("Error: Please specify at least one field to query.")
            print("Usage: get <fields> [year_or_range]")
            print("Example: get gross_income 2026-2030")
            return
        
        # Parse the argument to extract fields and optional year range
        parts = arg.strip().split()
        
        # Check if the last part looks like a year or year range
        year_range = None
        field_parts = parts
        
        if parts:
            potential_range = parts[-1]
            # Check for year range (contains dash)
            if '-' in potential_range:
                try:
                    range_parts = potential_range.split('-')
                    if len(range_parts) == 2:
                        first_year = int(range_parts[0])
                        # End year is optional - if empty, use last planning year
                        if range_parts[1]:
                            last_year = int(range_parts[1])
                        else:
                            last_year = self.plan_data.last_planning_year
                        year_range = (first_year, last_year)
                        field_parts = parts[:-1]
                except ValueError:
                    pass  # Not a valid year range, treat as field name
            else:
                # Check for single year (no dash)
                try:
                    single_year = int(potential_range)
                    # Looks like a year (4 digits, reasonable range)
                    if 1900 <= single_year <= 2200:
                        year_range = (single_year, single_year)
                        field_parts = parts[:-1]
                except ValueError:
                    pass  # Not a valid year, treat as field name
        
        # Join remaining parts and split by comma to get field names
        fields_str = ' '.join(field_parts)
        field_names = [f.strip() for f in fields_str.split(',') if f.strip()]
        
        if not field_names:
            print("Error: No valid field names provided.")
            return
        
        # Validate field names
        invalid_fields = [f for f in field_names if f not in self.available_fields]
        if invalid_fields:
            print(f"Error: Unknown field(s): {', '.join(invalid_fields)}")
            print("Use 'fields' command to see available field names.")
            return
        
        # Determine year range
        if year_range:
            first_year, last_year = year_range
        else:
            first_year = self.plan_data.first_year
            last_year = self.plan_data.last_planning_year
        
        # Validate year range
        if first_year > last_year:
            print(f"Error: First year ({first_year}) cannot be greater than last year ({last_year})")
            return
        
        if first_year < self.plan_data.first_year or last_year > self.plan_data.last_planning_year:
            print(f"Warning: Requested range extends beyond plan data ({self.plan_data.first_year}-{self.plan_data.last_planning_year})")
        
        # Build header using short names from field metadata
        header = ["Year"] + [get_short_name(f) for f in field_names]
        
        # Calculate column widths
        col_widths = [max(len(str(header[i])), 6) for i in range(len(header))]
        
        # Collect rows first to determine proper column widths
        rows = []
        for year in range(first_year, last_year + 1):
            yearly_data = self.plan_data.get_year(year)
            if yearly_data is None:
                continue
            
            row = [str(year)]
            for field_name in field_names:
                value = getattr(yearly_data, field_name, None)
                formatted = format_value(value)
                row.append(formatted)
            rows.append(row)
            
            # Update column widths
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(cell))
        
        if not rows:
            print(f"No data available for years {first_year}-{last_year}")
            return
        
        # Print header
        header_line = "  ".join(h.rjust(col_widths[i]) for i, h in enumerate(header))
        print()
        print(header_line)
        print("-" * len(header_line))
        
        # Print data rows
        for row in rows:
            print("  ".join(cell.rjust(col_widths[i]) for i, cell in enumerate(row)))
        
        # Print totals if multiple years and numeric fields
        if len(rows) > 1:
            print("-" * len(header_line))
            total_row = ["Total"]
            for field_name in field_names:
                # Sum numeric values
                total = 0.0
                can_sum = True
                for year in range(first_year, last_year + 1):
                    yearly_data = self.plan_data.get_year(year)
                    if yearly_data:
                        value = getattr(yearly_data, field_name, None)
                        if isinstance(value, (int, float)) and field_name not in ('year', 'is_working_year', 'marginal_bracket', 'effective_tax_rate'):
                            total += value
                        elif field_name in ('marginal_bracket', 'effective_tax_rate'):
                            can_sum = False
                        elif isinstance(value, bool):
                            can_sum = False
                
                if can_sum and field_name not in ('year', 'is_working_year'):
                    total_row.append(format_value(total))
                else:
                    total_row.append("-")
            
            print("  ".join(cell.rjust(col_widths[i]) for i, cell in enumerate(total_row)))
        
        print()
    
    def do_fields(self, arg: str):
        """List all available fields that can be queried.
        
        Usage: fields [field_name]
        
        If a field name is provided, shows detailed info for that field.
        Otherwise, shows all fields grouped by category.
        """
        # If a specific field is requested, show detailed info
        if arg.strip():
            field_name = arg.strip()
            if field_name not in self.available_fields:
                print(f"Error: Unknown field '{field_name}'")
                print("Use 'fields' without arguments to see all available fields.")
                return
            
            info = FIELD_METADATA.get(field_name)
            print(f"\n{field_name}:")
            if info:
                print(f"  Short name: {info.short_name}")
                print(f"  Description: {info.description}")
            else:
                print("  No metadata available")
            print()
            return
        
        print("\nAvailable fields in YearlyData:")
        print("=" * 70)
        
        # Group fields by category
        categories = {
            "Year Info": ["year", "is_working_year"],
            "Income": ["base_salary", "bonus", "other_income", "espp_income", "rsu_vested_value",
                      "short_term_capital_gains", "long_term_capital_gains", "deferred_comp_disbursement",
                      "gross_income", "earned_income_for_fica"],
            "Deductions": ["standard_deduction", "itemized_deduction", "max_401k", "max_hsa",
                          "employee_hsa", "employer_hsa", "medical_dental_vision", "total_deductions"],
            "Deferrals": ["base_deferral", "bonus_deferral", "total_deferral"],
            "Adjusted Income": ["adjusted_gross_income"],
            "Federal Taxes": ["ordinary_income_tax", "long_term_capital_gains_tax", "federal_tax", "marginal_bracket"],
            "FICA Taxes": ["social_security_tax", "medicare_tax", "medicare_surcharge", "total_fica"],
            "State Taxes": ["state_income_tax", "state_short_term_capital_gains_tax", "state_tax"],
            "Local Taxes": ["local_tax"],
            "Tax Summary": ["total_taxes", "effective_tax_rate", "take_home_pay"],
            "Contributions": ["employee_401k_contribution", "employer_401k_match", "total_401k_contribution",
                             "hsa_contribution", "deferred_comp_contribution", "taxable_contribution", "total_contributions"],
            "Expenses": ["annual_expenses", "special_expenses", "travel_expenses", "medical_premium", "medical_premium_expense",
                        "total_expenses", "income_expense_difference", "hsa_withdrawal", "ira_withdrawal",
                        "taxable_account_adjustment"],
            "Appreciation": ["appreciation_ira", "appreciation_deferred_comp", "appreciation_hsa", 
                            "appreciation_taxable", "total_appreciation"],
            "Balances": ["balance_ira", "balance_deferred_comp", "balance_hsa", "balance_taxable", "total_assets"]
        }
        
        for category, fields in categories.items():
            print(f"\n{category}:")
            for field in fields:
                if field in self.available_fields:
                    short_name = get_short_name(field)
                    description = get_description(field)
                    print(f"  {field:<32} [{short_name:<12}] {description}")
        print()
    
    def complete_fields(self, text, line, begidx, endidx):
        """Tab completion for the fields command.
        
        Matches field names containing the text anywhere (case-insensitive substring match).
        """
        if not text:
            return self.available_fields
        text_lower = text.lower()
        return [f for f in self.available_fields if text_lower in f.lower()]
        print()
    
    def do_years(self, arg: str):
        """Show the available year range and categorization."""
        if not self._require_plan():
            return
        
        print(f"\nPlan Year Range:")
        print(f"  First year: {self.plan_data.first_year}")
        print(f"  Last working year: {self.plan_data.last_working_year}")
        print(f"  Last planning year: {self.plan_data.last_planning_year}")
        print(f"\nWorking years ({self.plan_data.first_year}-{self.plan_data.last_working_year}):")
        working = list(self.plan_data.working_years().keys())
        print(f"  {min(working)} - {max(working)} ({len(working)} years)")
        print(f"\nRetirement years ({self.plan_data.last_working_year + 1}-{self.plan_data.last_planning_year}):")
        retirement = list(self.plan_data.retirement_years().keys())
        if retirement:
            print(f"  {min(retirement)} - {max(retirement)} ({len(retirement)} years)")
        else:
            print("  None")
        print()
    
    def do_summary(self, arg: str):
        """Show lifetime summary totals from the plan."""
        if not self._require_plan():
            return
        
        print(f"\nLifetime Summary for '{self.program_name}':")
        print("=" * 40)
        print(f"Total Gross Income:    {format_value(self.plan_data.total_gross_income)}")
        print(f"Total Federal Tax:     {format_value(self.plan_data.total_federal_tax)}")
        print(f"Total FICA:            {format_value(self.plan_data.total_fica)}")
        print(f"Total State Tax:       {format_value(self.plan_data.total_state_tax)}")
        print(f"Total Taxes:           {format_value(self.plan_data.total_taxes)}")
        print(f"Total Take Home:       {format_value(self.plan_data.total_take_home)}")
        print()
        print("Final Balances:")
        print(f"  401(k)/IRA:          {format_value(self.plan_data.final_401k_balance)}")
        print(f"  Deferred Comp:       {format_value(self.plan_data.final_deferred_comp_balance)}")
        print(f"  HSA:                 {format_value(self.plan_data.final_hsa_balance)}")
        print(f"  Taxable:             {format_value(self.plan_data.final_taxable_balance)}")
        print(f"  Total Assets:        {format_value(self.plan_data.total_retirement_assets)}")
        print()
    
    def do_render(self, arg: str):
        """Render financial data using different output formats.
        
        Usage: render [mode] [year_or_range]
        
        If no mode is specified, shows available render modes.
        
        Available modes:
            TaxDetails     - Detailed tax breakdown (requires year)
            Balances       - Account balances over time
            AnnualSummary  - Year-by-year summary
            Contributions  - Retirement contributions breakdown
            MoneyMovement  - Cash flow and account movements
            CashFlow       - Income, expenses, and net cash flow
        
        Year range format (for multi-year modes):
            2026-2030    - From 2026 to 2030 inclusive
            2026-        - From 2026 to end of plan
            -2030        - From start of plan to 2030
        
        Examples:
            render                       - List available modes
            render Balances              - Show all account balances
            render Balances 2026-2030    - Show balances for 2026-2030
            render TaxDetails 2026       - Show tax details for 2026
        """
        if not self._require_plan():
            return
        
        parts = arg.strip().split()
        
        if not parts:
            # List available render modes
            print("\nAvailable render modes:")
            print("=" * 40)
            for mode in RENDERER_REGISTRY.keys():
                print(f"  - {mode}")
            print("\nUsage: render <mode> [year_or_range]")
            print("Note: TaxDetails requires a single year.")
            print("      Other modes accept year ranges like 2026-2030")
            print()
            return
        
        mode = parts[0]
        
        # Case-insensitive lookup for render mode
        mode_lower = mode.lower()
        matched_mode = None
        for registry_mode in RENDERER_REGISTRY.keys():
            if registry_mode.lower() == mode_lower:
                matched_mode = registry_mode
                break
        
        if matched_mode is None:
            print(f"Error: Unknown render mode '{mode}'")
            print(f"Available modes: {', '.join(RENDERER_REGISTRY.keys())}")
            return
        
        renderer_class = RENDERER_REGISTRY[matched_mode]
        
        # TaxDetails requires a single year argument
        if matched_mode == 'TaxDetails':
            if len(parts) < 2:
                print("Error: TaxDetails requires a year argument.")
                print(f"Usage: render TaxDetails <year>")
                print(f"Example: render TaxDetails {self.plan_data.first_year}")
                return
            try:
                tax_year = int(parts[1])
                if tax_year < self.plan_data.first_year or tax_year > self.plan_data.last_planning_year:
                    print(f"Error: Year must be between {self.plan_data.first_year} and {self.plan_data.last_planning_year}")
                    return
                renderer = TaxDetailsRenderer(tax_year)
            except ValueError:
                print(f"Error: Invalid year '{parts[1]}'")
                return
        else:
            # Multi-year renderers accept optional year range
            start_year = None
            end_year = None
            
            if len(parts) >= 2:
                year_arg = parts[1]
                try:
                    if '-' in year_arg:
                        # Parse year range
                        range_parts = year_arg.split('-')
                        if range_parts[0]:
                            start_year = int(range_parts[0])
                        else:
                            start_year = self.plan_data.first_year
                        if len(range_parts) > 1 and range_parts[1]:
                            end_year = int(range_parts[1])
                        else:
                            end_year = self.plan_data.last_planning_year
                    else:
                        # Single year - show just that year
                        single_year = int(year_arg)
                        start_year = single_year
                        end_year = single_year
                    
                    # Validate year range
                    if start_year < self.plan_data.first_year or end_year > self.plan_data.last_planning_year:
                        print(f"Warning: Year range extends beyond plan data ({self.plan_data.first_year}-{self.plan_data.last_planning_year})")
                    if start_year > end_year:
                        print(f"Error: Start year ({start_year}) cannot be greater than end year ({end_year})")
                        return
                except ValueError:
                    print(f"Error: Invalid year or range '{year_arg}'")
                    return
            
            renderer = renderer_class(start_year=start_year, end_year=end_year)
        
        # Render the output
        print()
        output = renderer.render(self.plan_data)
        print(output)
    
    def complete_render(self, text, line, begidx, endidx):
        """Tab completion for the render command.
        
        Matches render mode names containing the text anywhere (case-insensitive substring match).
        """
        parts = line.split()
        if len(parts) <= 2:
            # Complete render mode names - case-insensitive substring match
            if not text:
                return list(RENDERER_REGISTRY.keys())
            text_lower = text.lower()
            return [mode for mode in RENDERER_REGISTRY.keys() if text_lower in mode.lower()]
        return []
    
    def do_config(self, arg: str):
        """Manage custom renderer configurations.
        
        Usage: config <subcommand> [arguments]
        
        Subcommands:
            list              - List all custom renderer configurations
            show <name>       - Show details of a specific configuration
            create <name>     - Interactively create a new configuration
            delete <name>     - Delete a configuration
            reload            - Reload configurations from disk
        
        Custom configurations are stored in the report-config directory.
        
        Examples:
            config list
            config show IncomeSummary
            config create MyReport
            config delete MyReport
            config reload
        """
        parts = arg.strip().split(maxsplit=1)
        
        if not parts:
            print("\nCustom Renderer Configuration Management")
            print("=" * 45)
            print("\nSubcommands:")
            print("  list              - List all custom configurations")
            print("  show <name>       - Show details of a configuration")
            print("  create <name>     - Create a new configuration")
            print("  delete <name>     - Delete a configuration")
            print("  reload            - Reload configurations from disk")
            print(f"\nConfigurations are stored in: {USER_CONFIG_DIR}")
            print()
            return
        
        subcommand = parts[0].lower()
        subarg = parts[1] if len(parts) > 1 else ''
        
        if subcommand == 'list':
            self._config_list()
        elif subcommand == 'show':
            self._config_show(subarg)
        elif subcommand == 'create':
            self._config_create(subarg)
        elif subcommand == 'delete':
            self._config_delete(subarg)
        elif subcommand == 'reload':
            self._config_reload()
        else:
            print(f"Unknown subcommand: {subcommand}")
            print("Use 'config' without arguments for help.")
    
    def _config_list(self):
        """List all custom renderer configurations."""
        configs = list_user_configs()
        
        if not configs:
            print("\nNo custom renderer configurations found.")
            print(f"Create one with 'config create <name>' or add JSON files to: {USER_CONFIG_DIR}")
            print()
            return
        
        print("\nCustom Renderer Configurations:")
        print("=" * 70)
        print(f"  {'Name':<20} {'Title':<30} {'Source File':<20}")
        print(f"  {'-' * 20} {'-' * 30} {'-' * 20}")
        
        for cfg in configs:
            print(f"  {cfg['name']:<20} {cfg['title'][:28]:<30} {cfg['source_file']:<20}")
        
        print(f"\nTotal: {len(configs)} configuration(s)")
        print()
    
    def _config_show(self, name: str):
        """Show details of a specific configuration."""
        if not name:
            print("Error: Please specify a configuration name.")
            print("Usage: config show <name>")
            return
        
        config = get_user_config(name)
        if config is None:
            print(f"Error: Configuration '{name}' not found.")
            print("Use 'config list' to see available configurations.")
            return
        
        print(f"\nConfiguration: {name}")
        print("=" * 50)
        print(f"  Title:       {config.get('title', name)}")
        print(f"  Show Totals: {'Yes' if config.get('show_totals', True) else 'No'}")
        print(f"  Source File: {config.get('_source_file', 'unknown')}")
        print()
        print("  Fields:")
        for field in config.get('fields', []):
            short_name = get_short_name(field)
            print(f"    - {field} [{short_name}]")
        print()
    
    def _config_create(self, name: str):
        """Interactively create a new configuration."""
        if not name:
            print("Error: Please specify a configuration name.")
            print("Usage: config create <name>")
            return
        
        # Check if name already exists
        existing = get_user_config(name)
        if existing:
            overwrite = input(f"Configuration '{name}' already exists. Overwrite? [y/N]: ").strip().lower()
            if overwrite not in ('y', 'yes'):
                print("Cancelled.")
                return
        
        print(f"\nCreating configuration: {name}")
        print("=" * 50)
        
        # Get title
        title = input(f"Title [{name}]: ").strip()
        if not title:
            title = name
        
        # Get fields with tab completion support
        print("\nEnter field names one per line (empty line to finish):")
        print("Tip: Use TAB to search/complete field names.")
        print()
        
        fields = []
        
        # Set up custom completer for field names
        def field_completer(text, state):
            """Completer function for field names."""
            text_lower = text.lower()
            if not text:
                matches = self.available_fields[:]
            else:
                # Case-insensitive substring match
                matches = [f for f in self.available_fields if text_lower in f.lower()]
            
            try:
                return matches[state]
            except IndexError:
                return None
        
        # Save original completer and delims
        old_completer = readline.get_completer()
        old_delims = readline.get_completer_delims()
        
        try:
            # Set custom completer for field input
            readline.set_completer(field_completer)
            readline.set_completer_delims(' \t\n')
            
            while True:
                try:
                    field = input("  Field: ").strip()
                except EOFError:
                    print()
                    break
                    
                if not field:
                    break
                
                if field not in self.available_fields:
                    print(f"    Warning: '{field}' is not a recognized field name.")
                    add_anyway = input("    Add anyway? [y/N]: ").strip().lower()
                    if add_anyway not in ('y', 'yes'):
                        continue
                
                fields.append(field)
                print(f"    Added: {field}")
        finally:
            # Restore original completer
            readline.set_completer(old_completer)
            readline.set_completer_delims(old_delims)
        
        if not fields:
            print("\nError: At least one field is required.")
            return
        
        # Get show_totals
        show_totals_input = input("\nShow totals row? [Y/n]: ").strip().lower()
        show_totals = show_totals_input not in ('n', 'no')
        
        # Get filename
        filename = input("\nSave to file [custom.json]: ").strip()
        if not filename:
            filename = 'custom.json'
        if not filename.endswith('.json'):
            filename += '.json'
        
        # Create config
        config = {
            'title': title,
            'fields': fields,
            'show_totals': show_totals
        }
        
        # Save config
        if save_user_config(name, config, filename):
            print(f"\nConfiguration '{name}' saved to {filename}")
            reload_renderer_registry()
            print("Renderer registry updated. You can now use 'render {name}'.")
        else:
            print("\nFailed to save configuration.")
        print()
    
    def _config_delete(self, name: str):
        """Delete a configuration."""
        if not name:
            print("Error: Please specify a configuration name.")
            print("Usage: config delete <name>")
            return
        
        config = get_user_config(name)
        if config is None:
            print(f"Error: Configuration '{name}' not found.")
            print("Use 'config list' to see available configurations.")
            return
        
        # Confirm deletion
        confirm = input(f"Delete configuration '{name}'? [y/N]: ").strip().lower()
        if confirm not in ('y', 'yes'):
            print("Cancelled.")
            return
        
        if delete_user_config(name):
            print(f"Configuration '{name}' deleted.")
            reload_renderer_registry()
            print("Renderer registry updated.")
        else:
            print("Failed to delete configuration.")
        print()
    
    def _config_reload(self):
        """Reload configurations from disk."""
        reload_renderer_registry()
        configs = list_user_configs()
        print(f"\nReloaded configurations. {len(configs)} custom renderer(s) available.")
        print()
    
    def complete_config(self, text, line, begidx, endidx):
        """Tab completion for the config command."""
        parts = line.split()
        
        if len(parts) <= 2:
            # Complete subcommands
            subcommands = ['list', 'show', 'create', 'delete', 'reload']
            if not text:
                return subcommands
            return [s for s in subcommands if s.startswith(text.lower())]
        elif len(parts) == 3 or (len(parts) == 2 and text):
            # Complete configuration names for show/delete
            subcommand = parts[1].lower()
            if subcommand in ('show', 'delete'):
                configs = list_user_configs()
                config_names = [c['name'] for c in configs]
                if not text:
                    return config_names
                return [n for n in config_names if n.lower().startswith(text.lower())]
        return []

    def do_generate(self, arg: str):
        """Launch the interactive wizard to create or update a financial plan.
        
        Usage: generate
        
        This runs the spec generator wizard. After generating a plan,
        you will be prompted to load it.
        """
        print()
        program_name = run_generator()
        if program_name:
            print()
            reload_choice = input(f"Would you like to load '{program_name}' now? [Y/n]: ").strip().lower()
            if reload_choice in ('', 'y', 'yes'):
                self.do_load(program_name)
    
    def do_load(self, arg: str):
        """Load a financial plan.
        
        Usage: load <program_name>
        
        If no program name is given and a plan is already loaded, reloads it.
        """
        program_name = arg.strip() if arg.strip() else self.program_name
        
        if not program_name:
            print("Please specify a program name.")
            print("Available programs:")
            input_params_dir = os.path.join(os.path.dirname(__file__), '../input-parameters')
            if os.path.exists(input_params_dir):
                for item in sorted(os.listdir(input_params_dir)):
                    if os.path.isdir(os.path.join(input_params_dir, item)):
                        print(f"  - {item}")
            return
        
        try:
            print(f"Loading financial plan '{program_name}'...")
            self.plan_data = load_plan(program_name)
            self.program_name = program_name
            print(f"Plan loaded successfully!")
            print(f"Years: {self.plan_data.first_year} - {self.plan_data.last_planning_year}")
            print(f"Working years: {self.plan_data.first_year} - {self.plan_data.last_working_year}")
        except FileNotFoundError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"Error loading plan: {e}")
    
    def do_help(self, arg: str):
        """Show help for available commands."""
        if arg:
            # Show help for specific command
            super().do_help(arg)
        else:
            print("""
Available Commands:
==================

  get <fields> [year_or_range]
      Query one or more fields from yearly data.
      Fields should be comma-separated.
      Year specifier is optional:
        - Single year: 2026
        - Range: 2026-2030 (inclusive)
        - Open-ended: 2026- (from 2026 to last planning year)
      
      Examples:
        get gross_income
        get gross_income, federal_tax
        get take_home_pay 2026
        get take_home_pay 2026-2030
        get base_salary, bonus 2028-

  fields
      List all available field names that can be queried.

  years
      Show the plan's year range and categorization.

  summary
      Show lifetime summary totals.

  render [mode] [year_or_range]
      Render financial data using different output formats.
      Modes: TaxDetails, Balances, AnnualSummary, Contributions,
             MoneyMovement, CashFlow, plus any custom renderers.
      Note: TaxDetails requires a single year argument.
            Other modes accept year ranges like 2026-2030
      
      Examples:
        render                       - List available modes
        render Balances              - Show all account balances
        render Balances 2026-2030    - Show balances for 2026-2030
        render AnnualSummary 2028-   - Show summary from 2028 to end
        render TaxDetails 2026       - Show tax details for 2026

  config <subcommand> [arguments]
      Manage custom renderer configurations stored in report-config/.
      
      Subcommands:
        list              - List all custom configurations
        show <name>       - Show details of a configuration
        create <name>     - Interactively create a new configuration
        delete <name>     - Delete a configuration
        reload            - Reload configurations from disk
      
      Examples:
        config list
        config show IncomeSummary
        config create MyReport
        config delete MyReport

  generate
      Launch the interactive wizard to create or update a financial plan.

  load [program_name]
      Load a financial plan. Shows available programs if none specified.

  help [command]
      Show this help message or help for a specific command.

  exit, quit
      Exit the shell.
""")
    
    def do_exit(self, arg: str):
        """Exit the shell."""
        print("Goodbye!")
        return True
    
    def do_quit(self, arg: str):
        """Exit the shell."""
        return self.do_exit(arg)
    
    def do_EOF(self, arg: str):
        """Handle Ctrl+D to exit."""
        print()  # Print newline for clean exit
        return self.do_exit(arg)
    
    def emptyline(self):
        """Do nothing on empty line."""
        pass
    
    def default(self, line: str):
        """Handle unknown commands."""
        print(f"Unknown command: {line}")
        print("Type 'help' for available commands.")
    
    def completedefault(self, text, line, begidx, endidx):
        """Provide tab completion for field names.
        
        Matches field names containing the text anywhere (case-insensitive substring match).
        """
        if line.startswith('get '):
            # Complete field names - case-insensitive substring match
            if not text:
                return self.available_fields
            text_lower = text.lower()
            return [f for f in self.available_fields if text_lower in f.lower()]
        return []
    
    def complete_get(self, text, line, begidx, endidx):
        """Tab completion for the get command.
        
        Matches field names containing the text anywhere (case-insensitive substring match).
        """
        if not text:
            return self.available_fields
        text_lower = text.lower()
        return [f for f in self.available_fields if text_lower in f.lower()]
    
    def complete_load(self, text, line, begidx, endidx):
        """Tab completion for the load command."""
        programs = self._get_available_programs()
        return [p for p in programs if p.startswith(text)]
    
    def complete_help(self, text, line, begidx, endidx):
        """Tab completion for the help command."""
        commands = ['get', 'fields', 'years', 'summary', 'render', 'generate', 'load', 'exit', 'quit']
        return [c for c in commands if c.startswith(text)]


def main():
    program_name = sys.argv[1] if len(sys.argv) > 1 else None
    
    if program_name:
        try:
            print(f"Loading financial plan '{program_name}'...")
            plan_data = load_plan(program_name)
            print("Plan loaded successfully!")
            
            shell = FinancialPlanShell(plan_data, program_name)
            shell.cmdloop()
            
        except FileNotFoundError as e:
            print(f"Error: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Error loading plan: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        # Start shell without a loaded plan
        shell = FinancialPlanShell()
        shell.cmdloop()


if __name__ == "__main__":
    main()
