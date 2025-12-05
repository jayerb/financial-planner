"""Tests for PaycheckRenderer."""

import pytest
import sys
import os
import shutil
import tempfile
from io import StringIO

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from render.renderers import (
    PaycheckRenderer,
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


class TestPaycheckRendererRegistry:
    """Test that PaycheckRenderer is properly registered."""
    
    def test_renderer_in_registry(self):
        """Test that PaycheckRenderer is in the RENDERER_REGISTRY."""
        assert 'Paycheck' in RENDERER_REGISTRY
    
    def test_registry_returns_correct_class(self):
        """Test that the registry returns the PaycheckRenderer class."""
        assert RENDERER_REGISTRY['Paycheck'] == PaycheckRenderer


class TestPaycheckRendererBasic:
    """Test basic PaycheckRenderer functionality."""
    
    def test_renderer_initializes_with_defaults(self):
        """Test that renderer initializes with default values."""
        renderer = PaycheckRenderer()
        assert renderer.tax_year is None
        assert renderer.program_name is None
    
    def test_renderer_initializes_with_start_year(self):
        """Test that renderer accepts start_year parameter."""
        renderer = PaycheckRenderer(start_year=2028)
        assert renderer.tax_year == 2028
    
    def test_renderer_initializes_with_program_name(self):
        """Test that renderer accepts program_name parameter."""
        renderer = PaycheckRenderer(program_name='myprogram')
        assert renderer.program_name == 'myprogram'
    
    def test_renderer_ignores_end_year(self):
        """Test that renderer accepts but ignores end_year parameter."""
        renderer = PaycheckRenderer(start_year=2028, end_year=2035)
        # Should only use start_year
        assert renderer.tax_year == 2028


class TestPaycheckRendererOutput:
    """Test PaycheckRenderer output formatting."""
    
    def test_renderer_produces_output(self, plan_data):
        """Test that renderer produces output for a valid year."""
        renderer = PaycheckRenderer(start_year=plan_data.first_year)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert len(result) > 0
    
    def test_renderer_shows_year_in_header(self, plan_data):
        """Test that renderer shows the year in the header."""
        year = plan_data.first_year
        renderer = PaycheckRenderer(start_year=year)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert f'PAYCHECK - {year}' in result
    
    def test_renderer_shows_program_name(self, plan_data):
        """Test that renderer shows program name when provided."""
        renderer = PaycheckRenderer(start_year=plan_data.first_year, program_name='testprogram')
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert 'testprogram' in result
    
    def test_renderer_shows_gross_pay_section(self, plan_data):
        """Test that renderer shows gross pay section."""
        renderer = PaycheckRenderer(start_year=plan_data.first_year)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert 'GROSS PAY' in result
        assert 'Gross Pay:' in result
    
    def test_renderer_shows_tax_withholdings_section(self, plan_data):
        """Test that renderer shows tax withholdings section."""
        renderer = PaycheckRenderer(start_year=plan_data.first_year)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert 'TAX WITHHOLDINGS' in result
        assert 'Federal Income Tax:' in result
        assert 'State Income Tax:' in result
        assert 'Social Security:' in result
        assert 'Medicare:' in result
        assert 'Total Tax Withholdings:' in result
    
    def test_renderer_shows_pretax_deductions_section(self, plan_data):
        """Test that renderer shows pre-tax deductions section."""
        renderer = PaycheckRenderer(start_year=plan_data.first_year)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert 'PRE-TAX DEDUCTIONS' in result
    
    def test_renderer_shows_net_pay_section(self, plan_data):
        """Test that renderer shows net pay section."""
        renderer = PaycheckRenderer(start_year=plan_data.first_year)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert 'NET PAY' in result
        assert 'Net Pay (Take-Home):' in result
    
    def test_renderer_shows_annual_projections(self, plan_data):
        """Test that renderer shows annual projections section."""
        renderer = PaycheckRenderer(start_year=plan_data.first_year)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert 'ANNUAL PROJECTIONS' in result
        assert 'Pay Schedule:' in result
        assert 'Annual Base Salary:' in result
        assert 'Annual Net Pay:' in result


class TestPaycheckRendererDefaultYear:
    """Test PaycheckRenderer default year behavior."""
    
    def test_renderer_defaults_to_first_year(self, plan_data):
        """Test that renderer defaults to plan's first year when no year specified."""
        renderer = PaycheckRenderer()
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert f'PAYCHECK - {plan_data.first_year}' in result


class TestPaycheckRendererNonWorkingYear:
    """Test PaycheckRenderer behavior for non-working years."""
    
    def test_renderer_handles_non_working_year(self, plan_data):
        """Test that renderer shows appropriate message for non-working year."""
        # Use a year after the last working year
        non_working_year = plan_data.last_working_year + 5
        renderer = PaycheckRenderer(start_year=non_working_year)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert 'not a working year' in result


class TestPaycheckRendererInvalidYear:
    """Test PaycheckRenderer behavior for invalid years."""
    
    def test_renderer_handles_year_not_in_plan(self, plan_data):
        """Test that renderer handles year not in plan data."""
        # Use a year way before the plan starts
        invalid_year = plan_data.first_year - 100
        renderer = PaycheckRenderer(start_year=invalid_year)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert 'No data available' in result


class TestPaycheckRendererMockData:
    """Test PaycheckRenderer with mock data for precise value testing."""
    
    @pytest.fixture
    def mock_plan_data(self):
        """Create mock PlanData with known paycheck values."""
        plan = PlanData(
            first_year=2026,
            last_working_year=2030,
            last_planning_year=2050
        )
        
        # Create a working year with known paycheck values
        yd = YearlyData(year=2026, is_working_year=True)
        yd.earned_income_for_fica = 260000  # Results in $10,000/paycheck for 26 periods
        yd.paycheck_gross = 10000.00
        yd.paycheck_federal_tax = 2500.00
        yd.paycheck_state_tax = 500.00
        yd.paycheck_social_security = 620.00
        yd.paycheck_medicare = 145.00
        yd.paycheck_401k = 884.62
        yd.paycheck_hsa = 150.00
        yd.paycheck_deferred_comp = 1000.00
        yd.paycheck_medical_dental = 200.00
        yd.paycheck_net = 5000.38
        yd.pay_period_ss_limit_reached = 10
        yd.pay_period_medicare_surcharge_starts = 15
        yd.paycheck_take_home_after_ss_limit = 5620.38
        yd.paycheck_take_home_after_medicare_surcharge = 5520.38
        
        plan.yearly_data[2026] = yd
        return plan
    
    def test_renderer_shows_correct_gross_pay(self, mock_plan_data):
        """Test that renderer shows correct gross pay value."""
        renderer = PaycheckRenderer(start_year=2026)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(mock_plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert '10,000.00' in result
    
    def test_renderer_shows_correct_net_pay(self, mock_plan_data):
        """Test that renderer shows correct net pay value."""
        renderer = PaycheckRenderer(start_year=2026)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(mock_plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert '5,000.38' in result
    
    def test_renderer_shows_ss_limit_reached_period(self, mock_plan_data):
        """Test that renderer shows when SS limit is reached."""
        renderer = PaycheckRenderer(start_year=2026)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(mock_plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert 'SS wage base reached' in result
        assert '10' in result  # Pay period 10
    
    def test_renderer_shows_medicare_surcharge_period(self, mock_plan_data):
        """Test that renderer shows when Medicare surcharge starts."""
        renderer = PaycheckRenderer(start_year=2026)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(mock_plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert 'Medicare surcharge' in result
        assert '15' in result  # Pay period 15
    
    def test_renderer_shows_401k_contribution(self, mock_plan_data):
        """Test that renderer shows 401(k) contribution."""
        renderer = PaycheckRenderer(start_year=2026)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(mock_plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert '401(k) Contribution:' in result
        assert '884.62' in result
    
    def test_renderer_shows_hsa_contribution(self, mock_plan_data):
        """Test that renderer shows HSA contribution."""
        renderer = PaycheckRenderer(start_year=2026)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(mock_plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert 'HSA Contribution:' in result
        assert '150.00' in result
    
    def test_renderer_shows_deferred_comp(self, mock_plan_data):
        """Test that renderer shows deferred compensation."""
        renderer = PaycheckRenderer(start_year=2026)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(mock_plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert 'Deferred Compensation:' in result
        assert '1,000.00' in result


class TestPaycheckRendererNoPretaxDeductions:
    """Test PaycheckRenderer when there are no pre-tax deductions."""
    
    @pytest.fixture
    def mock_plan_no_deductions(self):
        """Create mock PlanData with no pre-tax deductions."""
        plan = PlanData(
            first_year=2026,
            last_working_year=2030,
            last_planning_year=2050
        )
        
        yd = YearlyData(year=2026, is_working_year=True)
        yd.earned_income_for_fica = 260000
        yd.paycheck_gross = 10000.00
        yd.paycheck_federal_tax = 2500.00
        yd.paycheck_state_tax = 500.00
        yd.paycheck_social_security = 620.00
        yd.paycheck_medicare = 145.00
        # No pre-tax deductions
        yd.paycheck_401k = 0
        yd.paycheck_hsa = 0
        yd.paycheck_deferred_comp = 0
        yd.paycheck_medical_dental = 0
        yd.paycheck_net = 6235.00
        yd.pay_period_ss_limit_reached = 0
        yd.pay_period_medicare_surcharge_starts = 0
        yd.paycheck_take_home_after_ss_limit = 0
        yd.paycheck_take_home_after_medicare_surcharge = 0
        
        plan.yearly_data[2026] = yd
        return plan
    
    def test_renderer_shows_none_for_no_deductions(self, mock_plan_no_deductions):
        """Test that renderer shows (None) when no pre-tax deductions."""
        renderer = PaycheckRenderer(start_year=2026)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(mock_plan_no_deductions)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert '(None)' in result
    
    def test_renderer_hides_paycheck_changes_section(self, mock_plan_no_deductions):
        """Test that renderer hides paycheck changes section when no thresholds."""
        renderer = PaycheckRenderer(start_year=2026)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(mock_plan_no_deductions)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert 'PAYCHECK CHANGES DURING YEAR' not in result


class TestBonusPaycheckRendering:
    """Test bonus paycheck section rendering."""
    
    @pytest.fixture
    def mock_plan_with_bonus(self):
        """Create a mock plan with bonus paycheck data."""
        plan = PlanData(
            first_year=2026,
            last_working_year=2030,
            last_planning_year=2050
        )
        
        yd = YearlyData(year=2026, is_working_year=True)
        yd.base_salary = 260000
        yd.bonus = 52000
        yd.gross_income = 312000
        yd.earned_income_for_fica = 312000
        
        # Regular paycheck data
        yd.paycheck_gross = 10000.00
        yd.paycheck_federal_tax = 2500.00
        yd.paycheck_state_tax = 500.00
        yd.paycheck_social_security = 620.00
        yd.paycheck_medicare = 145.00
        yd.paycheck_401k = 750.00
        yd.paycheck_hsa = 150.00
        yd.paycheck_deferred_comp = 0
        yd.paycheck_medical_dental = 200.00
        yd.paycheck_net = 5235.00
        
        # Bonus paycheck data
        yd.bonus_paycheck_gross = 52000.00
        yd.bonus_paycheck_federal_tax = 11440.00  # 22% supplemental rate
        yd.bonus_paycheck_state_tax = 2600.00
        yd.bonus_paycheck_social_security = 3224.00
        yd.bonus_paycheck_medicare = 754.00
        yd.bonus_paycheck_deferred_comp = 0
        yd.bonus_paycheck_net = 33982.00
        
        plan.yearly_data[2026] = yd
        return plan
    
    @pytest.fixture
    def mock_plan_with_bonus_deferral(self):
        """Create a mock plan with bonus and deferred compensation."""
        plan = PlanData(
            first_year=2026,
            last_working_year=2030,
            last_planning_year=2050
        )
        
        yd = YearlyData(year=2026, is_working_year=True)
        yd.base_salary = 260000
        yd.bonus = 52000
        yd.gross_income = 312000
        yd.earned_income_for_fica = 312000
        
        # Regular paycheck data
        yd.paycheck_gross = 10000.00
        yd.paycheck_federal_tax = 2500.00
        yd.paycheck_state_tax = 500.00
        yd.paycheck_social_security = 620.00
        yd.paycheck_medicare = 145.00
        yd.paycheck_401k = 750.00
        yd.paycheck_hsa = 150.00
        yd.paycheck_deferred_comp = 2000.00
        yd.paycheck_medical_dental = 200.00
        yd.paycheck_net = 3235.00
        
        # Bonus paycheck data with deferral
        yd.bonus_paycheck_gross = 52000.00
        yd.bonus_paycheck_federal_tax = 11440.00
        yd.bonus_paycheck_state_tax = 2600.00
        yd.bonus_paycheck_social_security = 3224.00
        yd.bonus_paycheck_medicare = 754.00
        yd.bonus_paycheck_deferred_comp = 39000.00  # 75% deferred
        yd.bonus_paycheck_net = -5018.00  # Negative due to high deferral
        
        plan.yearly_data[2026] = yd
        return plan
    
    @pytest.fixture
    def mock_plan_no_bonus(self):
        """Create a mock plan without bonus."""
        plan = PlanData(
            first_year=2026,
            last_working_year=2030,
            last_planning_year=2050
        )
        
        yd = YearlyData(year=2026, is_working_year=True)
        yd.base_salary = 260000
        yd.bonus = 0
        yd.gross_income = 260000
        yd.earned_income_for_fica = 260000
        
        # Regular paycheck data
        yd.paycheck_gross = 10000.00
        yd.paycheck_federal_tax = 2500.00
        yd.paycheck_state_tax = 500.00
        yd.paycheck_social_security = 620.00
        yd.paycheck_medicare = 145.00
        yd.paycheck_401k = 750.00
        yd.paycheck_hsa = 150.00
        yd.paycheck_deferred_comp = 0
        yd.paycheck_medical_dental = 200.00
        yd.paycheck_net = 5235.00
        
        # No bonus paycheck data
        yd.bonus_paycheck_gross = 0
        yd.bonus_paycheck_federal_tax = 0
        yd.bonus_paycheck_state_tax = 0
        yd.bonus_paycheck_social_security = 0
        yd.bonus_paycheck_medicare = 0
        yd.bonus_paycheck_deferred_comp = 0
        yd.bonus_paycheck_net = 0
        
        plan.yearly_data[2026] = yd
        return plan
    
    def test_renderer_shows_bonus_paycheck_section(self, mock_plan_with_bonus):
        """Test that renderer shows bonus paycheck section when bonus > 0."""
        renderer = PaycheckRenderer(start_year=2026)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(mock_plan_with_bonus)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert 'BONUS PAYCHECK' in result
    
    def test_renderer_shows_bonus_gross(self, mock_plan_with_bonus):
        """Test that renderer shows gross bonus amount."""
        renderer = PaycheckRenderer(start_year=2026)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(mock_plan_with_bonus)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert 'Gross Bonus:' in result
        assert '52,000.00' in result
    
    def test_renderer_shows_bonus_federal_tax(self, mock_plan_with_bonus):
        """Test that renderer shows federal tax on bonus with supplemental rate."""
        renderer = PaycheckRenderer(start_year=2026)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(mock_plan_with_bonus)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert 'Federal (22% supplemental rate):' in result
        assert '11,440.00' in result
    
    def test_renderer_shows_bonus_state_tax(self, mock_plan_with_bonus):
        """Test that renderer shows state tax on bonus."""
        renderer = PaycheckRenderer(start_year=2026)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(mock_plan_with_bonus)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert 'State Income Tax:' in result
    
    def test_renderer_shows_bonus_fica_taxes(self, mock_plan_with_bonus):
        """Test that renderer shows FICA taxes on bonus."""
        renderer = PaycheckRenderer(start_year=2026)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(mock_plan_with_bonus)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        # Check for bonus-specific FICA taxes (appears under Tax Withholdings in bonus section)
        assert '3,224.00' in result  # Social Security
        assert '754.00' in result    # Medicare
    
    def test_renderer_shows_bonus_net(self, mock_plan_with_bonus):
        """Test that renderer shows net bonus amount."""
        renderer = PaycheckRenderer(start_year=2026)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(mock_plan_with_bonus)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert 'Net Bonus (Take-Home):' in result
        assert '33,982.00' in result
    
    def test_renderer_shows_bonus_deferred_comp(self, mock_plan_with_bonus_deferral):
        """Test that renderer shows deferred compensation on bonus."""
        renderer = PaycheckRenderer(start_year=2026)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(mock_plan_with_bonus_deferral)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert 'Deferred Compensation:' in result
        assert '39,000.00' in result
    
    def test_renderer_handles_negative_bonus_net(self, mock_plan_with_bonus_deferral):
        """Test that renderer handles negative net bonus (when deferral > net)."""
        renderer = PaycheckRenderer(start_year=2026)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(mock_plan_with_bonus_deferral)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert 'Net Bonus (Take-Home):' in result
        # Should show negative amount
        assert '-5,018.00' in result or '-$5,018.00' in result or '($5,018.00)' in result or '$     -5,018.00' in result
    
    def test_renderer_hides_bonus_section_when_no_bonus(self, mock_plan_no_bonus):
        """Test that renderer hides bonus section when bonus is 0."""
        renderer = PaycheckRenderer(start_year=2026)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(mock_plan_no_bonus)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        assert 'BONUS PAYCHECK' not in result
    
    def test_renderer_hides_bonus_deferred_when_zero(self, mock_plan_with_bonus):
        """Test that renderer hides deferred comp line when bonus deferral is 0."""
        renderer = PaycheckRenderer(start_year=2026)
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(mock_plan_with_bonus)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        # The bonus paycheck should appear
        assert 'BONUS PAYCHECK' in result
        # But Pre-Tax Deductions section for bonus should not appear when deferral is 0
        # Count occurrences of "Pre-Tax Deductions" - should only appear once (for regular paycheck)
        lines = result.split('\n')
        bonus_section_start = None
        for i, line in enumerate(lines):
            if 'BONUS PAYCHECK' in line:
                bonus_section_start = i
                break
        
        if bonus_section_start:
            bonus_section = '\n'.join(lines[bonus_section_start:])
            # Should not have "Pre-Tax Deductions:" in bonus section since deferral is 0
            assert 'Pre-Tax Deductions:' not in bonus_section


class TestBonusPaycheckCalculation:
    """Test bonus paycheck calculation in plan_calculator."""
    
    def test_bonus_paycheck_calculated_in_plan(self, plan_data):
        """Test that bonus paycheck fields are calculated in the plan."""
        yd = plan_data.get_year(plan_data.first_year)
        
        # If there's a bonus, bonus paycheck should be calculated
        if yd.bonus > 0:
            assert yd.bonus_paycheck_gross > 0
            assert yd.bonus_paycheck_gross == yd.bonus
    
    def test_bonus_federal_at_supplemental_rate(self, plan_data):
        """Test that bonus federal tax uses 22% supplemental rate."""
        yd = plan_data.get_year(plan_data.first_year)
        
        if yd.bonus > 0:
            # Federal tax should be 22% of gross bonus
            expected_federal = yd.bonus * 0.22
            assert abs(yd.bonus_paycheck_federal_tax - expected_federal) < 0.01
    
    def test_bonus_net_calculation(self, plan_data):
        """Test that bonus net is calculated correctly."""
        yd = plan_data.get_year(plan_data.first_year)
        
        if yd.bonus > 0:
            expected_net = (yd.bonus_paycheck_gross - 
                           yd.bonus_paycheck_federal_tax -
                           yd.bonus_paycheck_state_tax -
                           yd.bonus_paycheck_social_security -
                           yd.bonus_paycheck_medicare -
                           yd.bonus_paycheck_deferred_comp)
            assert abs(yd.bonus_paycheck_net - expected_net) < 0.01
    
    def test_bonus_deferred_comp_equals_bonus_deferral(self, plan_data):
        """Test that bonus deferred comp equals bonus_deferral field."""
        yd = plan_data.get_year(plan_data.first_year)
        
        if yd.bonus > 0:
            assert yd.bonus_paycheck_deferred_comp == yd.bonus_deferral

