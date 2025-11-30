"""Tests for renderer year range functionality."""

import pytest
import sys
import os
import shutil
import tempfile
from io import StringIO

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from render.renderers import (
    BalancesRenderer,
    AnnualSummaryRenderer,
    ContributionsRenderer,
    MoneyMovementRenderer,
    CashFlowRenderer,
    parse_year_range,
    RENDERER_REGISTRY,
)
from model.PlanData import PlanData, YearlyData


# Path to test fixtures
FIXTURES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'mcp_server_tests', 'fixtures'))

# Path to the project root (for reference files)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


@pytest.fixture(scope="module")
def test_base_path():
    """Create a temporary directory structure for testing."""
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


@pytest.fixture(scope="module")
def plan_data(test_base_path):
    """Load test plan data once for the module."""
    return load_test_plan(test_base_path, 'testprogram')


class TestParseYearRange:
    """Test the parse_year_range helper function."""
    
    @pytest.fixture
    def mock_plan_data(self):
        """Create a minimal mock PlanData for testing."""
        plan = PlanData(
            first_year=2025,
            last_working_year=2035,
            last_planning_year=2065
        )
        return plan
    
    def test_parse_single_year(self, mock_plan_data):
        """Test parsing a single year (no range)."""
        start, end = parse_year_range("2030", mock_plan_data)
        assert start == 2030
        assert end == 2030
    
    def test_parse_full_range(self, mock_plan_data):
        """Test parsing a complete year range."""
        start, end = parse_year_range("2028-2032", mock_plan_data)
        assert start == 2028
        assert end == 2032
    
    def test_parse_open_start_range(self, mock_plan_data):
        """Test parsing a range with open start (uses first_year)."""
        start, end = parse_year_range("-2030", mock_plan_data)
        assert start == 2025  # first_year
        assert end == 2030
    
    def test_parse_open_end_range(self, mock_plan_data):
        """Test parsing a range with open end (uses last_planning_year)."""
        start, end = parse_year_range("2030-", mock_plan_data)
        assert start == 2030
        assert end == 2065  # last_planning_year
    
    def test_parse_full_open_range(self, mock_plan_data):
        """Test parsing a fully open range (uses defaults for both)."""
        start, end = parse_year_range("-", mock_plan_data)
        assert start == 2025  # first_year
        assert end == 2065  # last_planning_year


class TestBalancesRendererYearRange:
    """Test BalancesRenderer with year ranges."""
    
    def test_renderer_no_year_range(self, plan_data):
        """Test that renderer without year range shows all years."""
        renderer = BalancesRenderer()
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Should show first and last years
        assert str(plan_data.first_year) in result
        assert str(plan_data.last_planning_year) in result
    
    def test_renderer_with_year_range(self, plan_data):
        """Test that renderer with year range only shows specified years."""
        # Use years within the plan range
        start_year = plan_data.first_year + 2  # 2027
        end_year = plan_data.first_year + 5    # 2030
        
        renderer = BalancesRenderer(start_year=start_year, end_year=end_year)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Should show years in range
        assert str(start_year) in result
        assert str(end_year) in result
        
        # Should NOT show years outside range
        assert str(plan_data.first_year) not in result or str(plan_data.first_year) == str(start_year)
        
        # Check that a year clearly outside the range is not shown
        outside_year = end_year + 5
        # Count occurrences - might appear in header but not in data rows
        lines = result.split('\n')
        data_lines = [l for l in lines if l.strip().startswith(str(outside_year))]
        assert len(data_lines) == 0
    
    def test_renderer_start_year_only(self, plan_data):
        """Test renderer with only start year specified."""
        start_year = plan_data.first_year + 5  # 2030
        
        renderer = BalancesRenderer(start_year=start_year)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Should show start year and years after
        assert str(start_year) in result
        assert str(plan_data.last_planning_year) in result
        
        # Should NOT show years before start
        year_before = start_year - 1
        lines = result.split('\n')
        data_lines = [l for l in lines if l.strip().startswith(str(year_before))]
        assert len(data_lines) == 0
    
    def test_renderer_end_year_only(self, plan_data):
        """Test renderer with only end year specified."""
        end_year = plan_data.first_year + 5  # 2030
        
        renderer = BalancesRenderer(end_year=end_year)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Should show first year and end year
        assert str(plan_data.first_year) in result
        assert str(end_year) in result
        
        # Should NOT show years after end
        year_after = end_year + 1
        lines = result.split('\n')
        data_lines = [l for l in lines if l.strip().startswith(str(year_after))]
        assert len(data_lines) == 0


class TestAnnualSummaryRendererYearRange:
    """Test AnnualSummaryRenderer with year ranges."""
    
    def test_renderer_no_year_range(self, plan_data):
        """Test that renderer without year range shows all years."""
        renderer = AnnualSummaryRenderer()
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Should show first and last years
        assert str(plan_data.first_year) in result
        assert str(plan_data.last_planning_year) in result
    
    def test_renderer_with_year_range(self, plan_data):
        """Test that renderer with year range only shows specified years."""
        start_year = plan_data.first_year + 2  # 2027
        end_year = plan_data.first_year + 5    # 2030
        
        renderer = AnnualSummaryRenderer(start_year=start_year, end_year=end_year)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Should show years in range
        assert str(start_year) in result
        assert str(end_year) in result
        
        # Check that a year clearly outside the range is not shown in data
        outside_year = end_year + 5
        lines = result.split('\n')
        data_lines = [l for l in lines if l.strip().startswith(str(outside_year))]
        assert len(data_lines) == 0
    
    def test_totals_reflect_filtered_range(self, plan_data):
        """Test that totals are calculated for the filtered range only."""
        # Get a small range
        start_year = plan_data.first_year
        end_year = plan_data.first_year + 2  # Only 3 years
        
        renderer = AnnualSummaryRenderer(start_year=start_year, end_year=end_year)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Calculate expected totals for the range
        expected_gross = 0
        for year in range(start_year, end_year + 1):
            yd = plan_data.get_year(year)
            if yd:
                expected_gross += yd.gross_income
        
        # The totals row should be in the output
        assert "TOTAL" in result


class TestContributionsRendererYearRange:
    """Test ContributionsRenderer with year ranges."""
    
    def test_renderer_no_year_range(self, plan_data):
        """Test that renderer without year range shows working years."""
        renderer = ContributionsRenderer()
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Should show first year
        assert str(plan_data.first_year) in result
    
    def test_renderer_with_year_range(self, plan_data):
        """Test that renderer with year range only shows specified years."""
        start_year = plan_data.first_year + 2  # 2027
        end_year = plan_data.first_year + 5    # 2030 (within working years)
        
        renderer = ContributionsRenderer(start_year=start_year, end_year=end_year)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Should show years in range
        assert str(start_year) in result
        
        # Should NOT show years before range
        year_before = start_year - 1
        lines = result.split('\n')
        data_lines = [l for l in lines if l.strip().startswith(str(year_before))]
        assert len(data_lines) == 0


class TestMoneyMovementRendererYearRange:
    """Test MoneyMovementRenderer with year ranges."""
    
    def test_renderer_no_year_range(self, plan_data):
        """Test that renderer without year range shows all years."""
        renderer = MoneyMovementRenderer()
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Should show first and last years
        assert str(plan_data.first_year) in result
        assert str(plan_data.last_planning_year) in result
    
    def test_renderer_with_year_range(self, plan_data):
        """Test that renderer with year range only shows specified years."""
        start_year = plan_data.first_year + 2  # 2027
        end_year = plan_data.first_year + 5    # 2030
        
        renderer = MoneyMovementRenderer(start_year=start_year, end_year=end_year)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Should show years in range
        assert str(start_year) in result
        assert str(end_year) in result
        
        # Check that a year clearly outside the range is not shown
        outside_year = end_year + 5
        lines = result.split('\n')
        data_lines = [l for l in lines if l.strip().startswith(str(outside_year))]
        assert len(data_lines) == 0


class TestCashFlowRendererYearRange:
    """Test CashFlowRenderer with year ranges."""
    
    def test_renderer_no_year_range(self, plan_data):
        """Test that renderer without year range shows all years."""
        renderer = CashFlowRenderer()
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Should show first and last years
        assert str(plan_data.first_year) in result
        assert str(plan_data.last_planning_year) in result
    
    def test_renderer_with_year_range(self, plan_data):
        """Test that renderer with year range only shows specified years."""
        start_year = plan_data.first_year + 2  # 2027
        end_year = plan_data.first_year + 5    # 2030
        
        renderer = CashFlowRenderer(start_year=start_year, end_year=end_year)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Should show years in range
        assert str(start_year) in result
        assert str(end_year) in result
        
        # Check that a year clearly outside the range is not shown
        outside_year = end_year + 5
        lines = result.split('\n')
        data_lines = [l for l in lines if l.strip().startswith(str(outside_year))]
        assert len(data_lines) == 0
    
    def test_final_balances_use_range_end(self, plan_data):
        """Test that final balances section uses the end of the range."""
        start_year = plan_data.first_year
        end_year = plan_data.first_year + 5  # 2030
        
        renderer = CashFlowRenderer(start_year=start_year, end_year=end_year)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # The output should contain "Final Account Balances" section
        assert "Final Account Balances" in result


class TestShellRenderWithYearRange:
    """Test shell render command with year range argument."""
    
    @pytest.fixture
    def shell_with_plan(self, test_base_path):
        """Create a shell with a loaded plan."""
        from shell import FinancialPlanShell
        plan_data = load_test_plan(test_base_path, 'testprogram')
        return FinancialPlanShell(plan_data, 'testprogram')
    
    def test_render_balances_with_year_range(self, shell_with_plan):
        """Test render Balances with year range argument."""
        first_year = shell_with_plan.plan_data.first_year
        end_year = first_year + 3
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            shell_with_plan.do_render(f'Balances {first_year}-{end_year}')
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Should show years in range
        assert str(first_year) in result
        assert str(end_year) in result
        
        # Should NOT show years well outside range
        outside_year = end_year + 5
        lines = result.split('\n')
        data_lines = [l for l in lines if l.strip().startswith(str(outside_year))]
        assert len(data_lines) == 0
    
    def test_render_annual_summary_with_year_range(self, shell_with_plan):
        """Test render AnnualSummary with year range argument."""
        first_year = shell_with_plan.plan_data.first_year
        end_year = first_year + 3
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            shell_with_plan.do_render(f'AnnualSummary {first_year}-{end_year}')
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Should show years in range
        assert str(first_year) in result
        assert str(end_year) in result
    
    def test_render_contributions_with_year_range(self, shell_with_plan):
        """Test render Contributions with year range argument."""
        first_year = shell_with_plan.plan_data.first_year
        end_year = first_year + 3
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            shell_with_plan.do_render(f'Contributions {first_year}-{end_year}')
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Should show first year
        assert str(first_year) in result
    
    def test_render_money_movement_with_year_range(self, shell_with_plan):
        """Test render MoneyMovement with year range argument."""
        first_year = shell_with_plan.plan_data.first_year
        end_year = first_year + 3
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            shell_with_plan.do_render(f'MoneyMovement {first_year}-{end_year}')
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Should show years in range
        assert str(first_year) in result
        assert str(end_year) in result
    
    def test_render_cash_flow_with_year_range(self, shell_with_plan):
        """Test render CashFlow with year range argument."""
        first_year = shell_with_plan.plan_data.first_year
        end_year = first_year + 3
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            shell_with_plan.do_render(f'CashFlow {first_year}-{end_year}')
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Should show years in range
        assert str(first_year) in result
        assert str(end_year) in result
    
    def test_render_with_open_end_range(self, shell_with_plan):
        """Test render with open-ended range (startYear-)."""
        start_year = shell_with_plan.plan_data.first_year + 5
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            shell_with_plan.do_render(f'Balances {start_year}-')
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Should show start year and last planning year
        assert str(start_year) in result
        assert str(shell_with_plan.plan_data.last_planning_year) in result
        
        # Should NOT show years before start
        year_before = start_year - 1
        lines = result.split('\n')
        data_lines = [l for l in lines if l.strip().startswith(str(year_before))]
        assert len(data_lines) == 0
    
    def test_render_with_open_start_range(self, shell_with_plan):
        """Test render with open-start range (-endYear)."""
        end_year = shell_with_plan.plan_data.first_year + 5
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            shell_with_plan.do_render(f'Balances -{end_year}')
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Should show first year and end year
        assert str(shell_with_plan.plan_data.first_year) in result
        assert str(end_year) in result
        
        # Should NOT show years after end
        year_after = end_year + 1
        lines = result.split('\n')
        data_lines = [l for l in lines if l.strip().startswith(str(year_after))]
        assert len(data_lines) == 0
    
    def test_render_with_invalid_year_range(self, shell_with_plan):
        """Test render with invalid year range shows error."""
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            shell_with_plan.do_render('Balances notayear-alsowrong')
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Should show an error
        assert "Invalid" in result or "Error" in result or "error" in result.lower()
    
    def test_render_tax_details_ignores_year_range(self, shell_with_plan):
        """Test that TaxDetails still uses single year argument."""
        first_year = shell_with_plan.plan_data.first_year
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            shell_with_plan.do_render(f'TaxDetails {first_year}')
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Should successfully render for the year
        assert str(first_year) in result
        assert "TAX SUMMARY" in result
