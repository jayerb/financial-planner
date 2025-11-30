"""Tests for the interactive shell functionality."""

import pytest
import sys
import os
import shutil
import tempfile
from io import StringIO

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from shell import FinancialPlanShell, get_yearly_fields, load_plan
from render.renderers import RENDERER_REGISTRY
from model.field_metadata import FIELD_METADATA, get_short_name, get_description, wrap_header


# Path to test fixtures
FIXTURES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'mcp_server_tests', 'fixtures'))

# Path to the project root (for reference files)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture(scope="module")
def test_base_path():
    """Create a temporary directory structure for testing.
    
    This creates a temp directory with the required structure:
    - input-parameters/testprogram/spec.json (from fixtures)
    - reference/*.json (symlinked from project)
    - src/ (symlinked from project for load_plan to work)
    """
    temp_dir = tempfile.mkdtemp()
    
    # Copy the test program from fixtures
    input_params_dir = os.path.join(temp_dir, 'input-parameters')
    os.makedirs(input_params_dir)
    shutil.copytree(
        os.path.join(FIXTURES_PATH, 'testprogram'),
        os.path.join(input_params_dir, 'testprogram')
    )
    
    # Symlink the reference directory from the project root
    os.symlink(
        os.path.join(PROJECT_ROOT, 'reference'),
        os.path.join(temp_dir, 'reference')
    )
    
    # Symlink the src directory from the project root
    os.symlink(
        os.path.join(PROJECT_ROOT, 'src'),
        os.path.join(temp_dir, 'src')
    )
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


def load_test_plan(test_base_path: str, program_name: str = 'testprogram'):
    """Load a test plan from the test fixture directory."""
    import json
    from tax.FederalDetails import FederalDetails
    from tax.StateDetails import StateDetails
    from tax.ESPPDetails import ESPPDetails
    from tax.SocialSecurityDetails import SocialSecurityDetails
    from tax.MedicareDetails import MedicareDetails
    from calc.rsu_calculator import RSUCalculator
    from calc.plan_calculator import PlanCalculator
    
    spec_path = os.path.join(test_base_path, 'input-parameters', program_name, 'spec.json')
    with open(spec_path, 'r') as f:
        spec = json.load(f)
    
    tax_year = spec.get('firstYear', 2026)
    inflation_rate = spec.get('federalBracketInflation')
    final_year = spec.get('lastPlanningYear')
    
    fed = FederalDetails(inflation_rate, final_year)
    state = StateDetails(inflation_rate, final_year)
    
    fed_ref_path = os.path.join(test_base_path, 'reference', 'federal-details.json')
    with open(fed_ref_path, 'r') as f:
        fed_ref = json.load(f)
    max_espp = fed_ref.get('maxESPPValue', 0)
    espp = ESPPDetails(max_espp)
    
    social_security = SocialSecurityDetails(inflation_rate, final_year)
    
    medicare_ref_path = os.path.join(test_base_path, 'reference', 'flat-tax-details.json')
    with open(medicare_ref_path, 'r') as f:
        medicare_ref = json.load(f)
    medicare = MedicareDetails(
        medicare_rate=medicare_ref.get('medicare', 0),
        surcharge_threshold=medicare_ref.get('surchargeThreshold', 0),
        surcharge_rate=medicare_ref.get('surchargeRate', 0)
    )
    
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
    
    calculator = PlanCalculator(fed, state, espp, social_security, medicare, rsu_calculator)
    return calculator.calculate(spec)


class TestFieldsCommand:
    """Test the fields command displays correct categories."""
    
    def test_hsa_withdrawal_in_expenses_category(self):
        """Test that hsa_withdrawal is listed in the Expenses category."""
        shell = FinancialPlanShell()
        
        # Capture output
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            shell.do_fields('')
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # The Expenses section should contain hsa_withdrawal
        assert 'hsa_withdrawal' in result
        
        # Verify it appears after "Expenses:" heading
        expenses_idx = result.find('Expenses:')
        hsa_withdrawal_idx = result.find('hsa_withdrawal')
        assert expenses_idx != -1
        assert hsa_withdrawal_idx != -1
        assert hsa_withdrawal_idx > expenses_idx
    
    def test_medical_premium_fields_in_expenses_category(self):
        """Test that medical_premium and medical_premium_expense are in Expenses."""
        shell = FinancialPlanShell()
        
        # Capture output
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            shell.do_fields('')
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Both medical premium fields should be in output
        assert 'medical_premium' in result
        assert 'medical_premium_expense' in result
    
    def test_all_yearly_fields_are_listed(self):
        """Test that all YearlyData fields appear in the fields output."""
        shell = FinancialPlanShell()
        available_fields = get_yearly_fields()
        
        # Capture output
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            shell.do_fields('')
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Every field in YearlyData should appear in the output
        missing_fields = []
        for field in available_fields:
            if field not in result:
                missing_fields.append(field)
        
        assert not missing_fields, f"Fields not listed in 'fields' command: {missing_fields}"


class TestGetYearlyFields:
    """Test the get_yearly_fields helper function."""
    
    def test_returns_list_of_strings(self):
        """Test that get_yearly_fields returns a list of field name strings."""
        fields = get_yearly_fields()
        
        assert isinstance(fields, list)
        assert len(fields) > 0
        assert all(isinstance(f, str) for f in fields)
    
    def test_includes_expected_fields(self):
        """Test that expected fields are present."""
        fields = get_yearly_fields()
        
        expected_fields = [
            'year', 'is_working_year', 'base_salary', 'gross_income',
            'federal_tax', 'take_home_pay', 'hsa_withdrawal',
            'medical_premium', 'medical_premium_expense'
        ]
        
        for expected in expected_fields:
            assert expected in fields, f"Expected field '{expected}' not in YearlyData"


class TestFieldMetadata:
    """Test field metadata dictionary and helper functions."""
    
    def test_all_yearly_fields_have_metadata(self):
        """Test that all YearlyData fields have metadata defined."""
        fields = get_yearly_fields()
        missing = [f for f in fields if f not in FIELD_METADATA]
        assert not missing, f"Fields missing metadata: {missing}"
    
    def test_short_names_are_unique(self):
        """Test that all short names are unique."""
        short_names = [info.short_name for info in FIELD_METADATA.values()]
        duplicates = [name for name in short_names if short_names.count(name) > 1]
        assert not duplicates, f"Duplicate short names: {set(duplicates)}"
    
    def test_get_short_name_returns_correct_value(self):
        """Test get_short_name returns the correct short name."""
        assert get_short_name('gross_income') == 'Gross Income'
        assert get_short_name('take_home_pay') == 'Take Home'
        assert get_short_name('balance_ira') == 'IRA Balance'
    
    def test_get_short_name_returns_field_name_for_unknown(self):
        """Test get_short_name returns field name when not found."""
        assert get_short_name('unknown_field') == 'unknown_field'
    
    def test_get_description_returns_correct_value(self):
        """Test get_description returns the correct description."""
        assert 'taxable income' in get_description('gross_income').lower()
        assert 'after' in get_description('take_home_pay').lower()
    
    def test_get_description_returns_empty_for_unknown(self):
        """Test get_description returns empty string when not found."""
        assert get_description('unknown_field') == ''
    
    def test_wrap_header_short_text(self):
        """Test wrap_header returns single line for short text."""
        result = wrap_header("Short", 14)
        assert result == ["Short"]
    
    def test_wrap_header_exact_width(self):
        """Test wrap_header returns single line when text exactly fits."""
        result = wrap_header("Exactly 14 ch", 14)
        assert result == ["Exactly 14 ch"]
    
    def test_wrap_header_wraps_long_text(self):
        """Test wrap_header wraps long text across multiple lines."""
        result = wrap_header("Short-Term Capital Gains", 14)
        assert len(result) >= 2
        assert all(len(line) <= 14 for line in result)
    
    def test_wrap_header_preserves_words(self):
        """Test wrap_header doesn't break words."""
        result = wrap_header("Federal Tax", 8)
        # Should wrap to ["Federal", "Tax"] not break "Federal"
        assert result == ["Federal", "Tax"]
    
    def test_wrap_header_multiple_words(self):
        """Test wrap_header handles multiple words."""
        result = wrap_header("Long-Term CG Tax", 12)
        # Words should be kept together as much as possible
        for line in result:
            assert len(line) <= 12

    def test_fields_command_shows_short_names_and_descriptions(self):
        """Test that fields command displays short names and descriptions."""
        shell = FinancialPlanShell()
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            shell.do_fields('')
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Check that short names and descriptions appear
        assert 'Gross Inc' in result
        assert 'Take Home' in result
        assert 'taxable income' in result.lower() or 'gross income' in result.lower()
    
    def test_fields_command_with_specific_field(self):
        """Test that fields command shows detailed info for a specific field."""
        shell = FinancialPlanShell()
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            shell.do_fields('gross_income')
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        assert 'gross_income' in result
        assert 'Gross Inc' in result
        assert 'Description' in result


class TestRenderCommand:
    """Test the render command functionality."""
    
    @pytest.fixture
    def shell_with_plan(self, test_base_path):
        """Create a shell with a loaded plan."""
        plan_data = load_test_plan(test_base_path, 'testprogram')
        return FinancialPlanShell(plan_data, 'testprogram')
    
    @pytest.fixture
    def shell_without_plan(self):
        """Create a shell without a loaded plan."""
        return FinancialPlanShell()
    
    def test_render_without_plan_shows_error(self, shell_without_plan):
        """Test that render command requires a loaded plan."""
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            shell_without_plan.do_render('')
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert "No plan loaded" in result
    
    def test_render_no_args_lists_modes(self, shell_with_plan):
        """Test that render with no arguments lists available modes."""
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            shell_with_plan.do_render('')
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert "Available render modes" in result
        
        # Check that all registered modes are listed
        for mode in RENDERER_REGISTRY.keys():
            assert mode in result
    
    def test_render_invalid_mode_shows_error(self, shell_with_plan):
        """Test that invalid render mode shows error message."""
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            shell_with_plan.do_render('InvalidMode')
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert "Unknown render mode" in result
        assert "InvalidMode" in result
    
    def test_render_balances_produces_output(self, shell_with_plan):
        """Test that render Balances produces table output."""
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            shell_with_plan.do_render('Balances')
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        # Should contain year data
        assert str(shell_with_plan.plan_data.first_year) in result
    
    def test_render_tax_details_requires_year(self, shell_with_plan):
        """Test that TaxDetails mode requires a year argument."""
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            shell_with_plan.do_render('TaxDetails')
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert "requires a year argument" in result
    
    def test_render_tax_details_with_year(self, shell_with_plan):
        """Test that TaxDetails renders correctly with a year argument."""
        first_year = shell_with_plan.plan_data.first_year
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            shell_with_plan.do_render(f'TaxDetails {first_year}')
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        # Should contain tax-related information
        assert str(first_year) in result
    
    def test_render_tax_details_invalid_year(self, shell_with_plan):
        """Test that TaxDetails with invalid year shows error."""
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            shell_with_plan.do_render('TaxDetails notayear')
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert "Invalid year" in result
    
    def test_render_tax_details_out_of_range_year(self, shell_with_plan):
        """Test that TaxDetails with out-of-range year shows error."""
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            shell_with_plan.do_render('TaxDetails 1900')
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert "must be between" in result
    
    def test_complete_render_returns_modes(self, shell_with_plan):
        """Test that tab completion returns available render modes."""
        completions = shell_with_plan.complete_render('', 'render ', 7, 7)
        
        for mode in RENDERER_REGISTRY.keys():
            assert mode in completions
    
    def test_complete_render_filters_by_prefix(self, shell_with_plan):
        """Test that tab completion filters by prefix."""
        completions = shell_with_plan.complete_render('Tax', 'render Tax', 7, 10)
        
        assert 'TaxDetails' in completions
        assert 'Balances' not in completions


class TestTabCompletion:
    """Test tab completion for all commands."""
    
    @pytest.fixture
    def shell(self):
        """Create a shell without a loaded plan."""
        return FinancialPlanShell()
    
    def test_complete_get_returns_fields(self, shell):
        """Test that get command completion returns field names."""
        completions = shell.complete_get('', 'get ', 4, 4)
        
        assert 'gross_income' in completions
        assert 'take_home_pay' in completions
        assert 'federal_tax' in completions
    
    def test_complete_get_filters_by_prefix(self, shell):
        """Test that get completion filters by prefix."""
        completions = shell.complete_get('gross', 'get gross', 4, 9)
        
        assert 'gross_income' in completions
        assert 'take_home_pay' not in completions
    
    def test_complete_fields_returns_field_names(self, shell):
        """Test that fields command completion returns field names."""
        completions = shell.complete_fields('', 'fields ', 7, 7)
        
        assert 'gross_income' in completions
        assert 'balance_ira' in completions
    
    def test_complete_fields_filters_by_prefix(self, shell):
        """Test that fields completion filters by prefix."""
        completions = shell.complete_fields('balance', 'fields balance', 7, 14)
        
        assert 'balance_ira' in completions
        assert 'balance_hsa' in completions
        assert 'gross_income' not in completions
    
    def test_complete_load_returns_programs(self, shell):
        """Test that load command completion returns available programs."""
        completions = shell.complete_load('', 'load ', 5, 5)
        
        # Should return a list (may be empty if no programs exist)
        assert isinstance(completions, list)
    
    def test_complete_load_filters_by_prefix(self, shell):
        """Test that load completion filters by prefix."""
        # Get available programs first
        programs = shell._get_available_programs()
        if not programs:
            pytest.skip("No programs available")
        
        # Use the first program's first two characters as a prefix
        first_program = programs[0]
        prefix = first_program[:2]
        
        completions = shell.complete_load(prefix, f'load {prefix}', 5, 5 + len(prefix))
        
        # The first program should be in completions
        assert first_program in completions
        # Programs not starting with prefix shouldn't be included
        for prog in programs:
            if not prog.startswith(prefix):
                assert prog not in completions
    
    def test_complete_help_returns_commands(self, shell):
        """Test that help command completion returns available commands."""
        completions = shell.complete_help('', 'help ', 5, 5)
        
        assert 'get' in completions
        assert 'fields' in completions
        assert 'render' in completions
        assert 'load' in completions
        assert 'summary' in completions
    
    def test_complete_help_filters_by_prefix(self, shell):
        """Test that help completion filters by prefix."""
        completions = shell.complete_help('ge', 'help ge', 5, 7)
        
        assert 'get' in completions
        assert 'generate' in completions
        assert 'fields' not in completions
    
    def test_get_available_programs(self, shell):
        """Test the helper method to get available programs."""
        programs = shell._get_available_programs()
        
        # Should return a list (may be empty if no programs exist)
        assert isinstance(programs, list)


class TestCaseInsensitiveTabCompletion:
    """Test case-insensitive substring matching for tab completion."""
    
    @pytest.fixture
    def shell(self):
        """Create a shell without a loaded plan."""
        return FinancialPlanShell()
    
    def test_complete_get_case_insensitive_lowercase(self, shell):
        """Test that get completion is case-insensitive with lowercase input."""
        completions = shell.complete_get('tax', 'get tax', 4, 7)
        
        # Should match fields containing 'tax' anywhere
        assert 'federal_tax' in completions
        assert 'state_tax' in completions
        assert 'total_taxes' in completions
        assert 'medicare_tax' in completions
    
    def test_complete_get_case_insensitive_uppercase(self, shell):
        """Test that get completion is case-insensitive with uppercase input."""
        completions = shell.complete_get('TAX', 'get TAX', 4, 7)
        
        # Should match fields containing 'tax' anywhere (case-insensitive)
        assert 'federal_tax' in completions
        assert 'state_tax' in completions
        assert 'total_taxes' in completions
    
    def test_complete_get_case_insensitive_mixed_case(self, shell):
        """Test that get completion is case-insensitive with mixed case input."""
        completions = shell.complete_get('TaX', 'get TaX', 4, 7)
        
        # Should match fields containing 'tax' anywhere (case-insensitive)
        assert 'federal_tax' in completions
        assert 'state_tax' in completions
    
    def test_complete_get_substring_match(self, shell):
        """Test that get completion matches substrings, not just prefixes."""
        completions = shell.complete_get('income', 'get income', 4, 10)
        
        # Should match fields containing 'income' anywhere
        assert 'gross_income' in completions
        assert 'adjusted_gross_income' in completions
        assert 'other_income' in completions
        # Should not include fields without 'income'
        assert 'federal_tax' not in completions
    
    def test_complete_fields_case_insensitive(self, shell):
        """Test that fields completion is case-insensitive."""
        completions = shell.complete_fields('BALANCE', 'fields BALANCE', 7, 14)
        
        # Should match fields containing 'balance' (case-insensitive)
        assert 'balance_ira' in completions
        assert 'balance_hsa' in completions
        assert 'balance_taxable' in completions
        assert 'balance_deferred_comp' in completions
    
    def test_complete_fields_substring_match(self, shell):
        """Test that fields completion matches substrings."""
        completions = shell.complete_fields('ira', 'fields ira', 7, 10)
        
        # Should match fields containing 'ira' anywhere
        assert 'balance_ira' in completions
        assert 'appreciation_ira' in completions
        assert 'ira_withdrawal' in completions
    
    def test_completedefault_case_insensitive(self, shell):
        """Test that default completion is case-insensitive for get command."""
        completions = shell.completedefault('SALARY', 'get SALARY', 4, 10)
        
        # Should match fields containing 'salary' (case-insensitive)
        assert 'base_salary' in completions
    
    def test_completedefault_substring_match(self, shell):
        """Test that default completion matches substrings for get command."""
        completions = shell.completedefault('contribution', 'get contribution', 4, 16)
        
        # Should match fields containing 'contribution' anywhere
        assert 'employee_401k_contribution' in completions
        assert 'total_401k_contribution' in completions
        assert 'hsa_contribution' in completions
        assert 'deferred_comp_contribution' in completions
        assert 'taxable_contribution' in completions
        assert 'total_contributions' in completions
    
    def test_complete_get_empty_returns_all_fields(self, shell):
        """Test that empty text returns all fields."""
        completions = shell.complete_get('', 'get ', 4, 4)
        
        assert len(completions) == len(shell.available_fields)
    
    def test_complete_fields_empty_returns_all_fields(self, shell):
        """Test that empty text returns all fields for fields command."""
        completions = shell.complete_fields('', 'fields ', 7, 7)
        
        assert len(completions) == len(shell.available_fields)


class TestCaseInsensitiveRendererSearch:
    """Test case-insensitive matching for render command and tab completion."""
    
    @pytest.fixture
    def shell_with_plan(self, test_base_path):
        """Create a shell with a loaded plan."""
        plan_data = load_test_plan(test_base_path, 'testprogram')
        return FinancialPlanShell(plan_data, 'testprogram')
    
    def test_render_mode_case_insensitive_lowercase(self, shell_with_plan):
        """Test that render mode lookup is case-insensitive with lowercase input."""
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            shell_with_plan.do_render('balances')
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        # Should successfully render, not show error
        assert "Unknown render mode" not in result
        assert str(shell_with_plan.plan_data.first_year) in result
    
    def test_render_mode_case_insensitive_uppercase(self, shell_with_plan):
        """Test that render mode lookup is case-insensitive with uppercase input."""
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            shell_with_plan.do_render('BALANCES')
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        # Should successfully render, not show error
        assert "Unknown render mode" not in result
        assert str(shell_with_plan.plan_data.first_year) in result
    
    def test_render_mode_case_insensitive_mixed_case(self, shell_with_plan):
        """Test that render mode lookup is case-insensitive with mixed case input."""
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            shell_with_plan.do_render('BaLaNcEs')
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        # Should successfully render, not show error
        assert "Unknown render mode" not in result
        assert str(shell_with_plan.plan_data.first_year) in result
    
    def test_render_taxdetails_case_insensitive(self, shell_with_plan):
        """Test that TaxDetails mode is case-insensitive."""
        first_year = shell_with_plan.plan_data.first_year
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            shell_with_plan.do_render(f'taxdetails {first_year}')
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        # Should successfully render, not show error
        assert "Unknown render mode" not in result
        assert str(first_year) in result
    
    def test_complete_render_case_insensitive_lowercase(self, shell_with_plan):
        """Test that render tab completion is case-insensitive with lowercase input."""
        completions = shell_with_plan.complete_render('tax', 'render tax', 7, 10)
        
        # Should match TaxDetails (case-insensitive)
        assert 'TaxDetails' in completions
    
    def test_complete_render_case_insensitive_uppercase(self, shell_with_plan):
        """Test that render tab completion is case-insensitive with uppercase input."""
        completions = shell_with_plan.complete_render('TAX', 'render TAX', 7, 10)
        
        # Should match TaxDetails (case-insensitive)
        assert 'TaxDetails' in completions
    
    def test_complete_render_substring_match(self, shell_with_plan):
        """Test that render tab completion matches substrings."""
        completions = shell_with_plan.complete_render('flow', 'render flow', 7, 11)
        
        # Should match CashFlow (substring match)
        assert 'CashFlow' in completions
        # Should not match modes without 'flow'
        assert 'Balances' not in completions
    
    def test_complete_render_substring_case_insensitive(self, shell_with_plan):
        """Test that render tab completion does case-insensitive substring match."""
        completions = shell_with_plan.complete_render('SUMMARY', 'render SUMMARY', 7, 14)
        
        # Should match AnnualSummary (case-insensitive substring)
        assert 'AnnualSummary' in completions
    
    def test_complete_render_empty_returns_all_modes(self, shell_with_plan):
        """Test that empty text returns all render modes."""
        completions = shell_with_plan.complete_render('', 'render ', 7, 7)
        
        assert len(completions) == len(RENDERER_REGISTRY)
