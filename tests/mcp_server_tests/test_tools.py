"""Tests for the MCP server tools module."""

import os
import sys
import json
import shutil
import tempfile
import pytest
from unittest.mock import patch, MagicMock

# Add src and mcp-server to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../mcp-server')))

from tools import FinancialPlannerTools, MultiProgramTools


# Path to test fixtures (contains reference files needed for calculations)
FIXTURES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'fixtures'))

# Path to the project root (for reference files)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))


@pytest.fixture(scope="module")
def test_base_path():
    """Create a temporary directory structure for testing.
    
    This creates a temp directory with the required structure:
    - input-parameters/testprogram/spec.json (from fixtures)
    - reference/*.json (symlinked from project)
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
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestFinancialPlannerTools:
    """Tests for FinancialPlannerTools class."""
    
    @pytest.fixture
    def tools(self, test_base_path):
        """Create a FinancialPlannerTools instance using testprogram."""
        return FinancialPlannerTools(test_base_path, 'testprogram')
    
    def test_init_loads_spec(self, tools):
        """Test that initialization loads the spec correctly."""
        assert tools.spec is not None
        assert 'firstYear' in tools.spec
        assert 'income' in tools.spec
    
    def test_init_sets_key_dates(self, tools):
        """Test that key dates are extracted from spec."""
        assert tools.first_year == 2025
        assert tools.last_working_year == 2035
        assert tools.last_planning_year == 2065
    
    def test_init_creates_calculators(self, tools):
        """Test that all calculators are initialized."""
        assert tools.fed is not None
        assert tools.state is not None
        assert tools.espp is not None
        assert tools.social_security is not None
        assert tools.medicare is not None
        assert tools.rsu_calculator is not None
        assert tools.plan_calculator is not None
        assert tools.plan_data is not None
    
    def test_init_caches_results(self, tools):
        """Test that results are cached for all years."""
        assert tools.plan_data is not None
        assert tools.plan_data.yearly_data is not None
        expected_years = tools.last_planning_year - tools.first_year + 1
        assert len(tools.plan_data.yearly_data) == expected_years
    
    def test_get_program_overview(self, tools):
        """Test get_program_overview returns expected structure."""
        overview = tools.get_program_overview()
        
        assert 'program_name' in overview
        assert 'planning_horizon' in overview
        assert 'income_sources' in overview
        assert 'deferred_compensation' in overview
        assert 'rsu_info' in overview
        assert 'inflation_assumption' in overview
        
        horizon = overview['planning_horizon']
        assert horizon['first_year'] == 2025
        assert horizon['last_working_year'] == 2035
        assert horizon['last_planning_year'] == 2065
        assert horizon['working_years'] == 11
    
    def test_list_available_years(self, tools):
        """Test list_available_years returns correct year categorization."""
        years = tools.list_available_years()
        
        assert 'working_years' in years
        assert 'retirement_years' in years
        assert 'total_years' in years
        
        assert 2025 in years['working_years']
        assert 2035 in years['working_years']
        assert 2036 in years['retirement_years']
        assert 2065 in years['retirement_years']
    
    def test_get_annual_summary_working_year(self, tools):
        """Test get_annual_summary for a working year."""
        summary = tools.get_annual_summary(2025)
        
        assert 'error' not in summary
        assert summary['year'] == 2025
        assert summary['is_working_year'] is True
        assert 'gross_income' in summary
        assert 'federal_tax' in summary
        assert 'fica_tax' in summary
        assert 'state_tax' in summary
        assert 'total_tax' in summary
        assert 'effective_tax_rate' in summary
        assert 'take_home_pay' in summary
        assert summary['gross_income'] > 0
    
    def test_get_annual_summary_retirement_year(self, tools):
        """Test get_annual_summary for a retirement year."""
        summary = tools.get_annual_summary(2050)
        
        assert 'error' not in summary
        assert summary['year'] == 2050
        assert summary['is_working_year'] is False
    
    def test_get_annual_summary_invalid_year(self, tools):
        """Test get_annual_summary returns error for invalid year."""
        summary = tools.get_annual_summary(2000)
        
        assert 'error' in summary
        assert '2000' in summary['error']
    
    def test_get_tax_details(self, tools):
        """Test get_tax_details returns detailed breakdown."""
        details = tools.get_tax_details(2025)
        
        assert 'error' not in details
        assert details['year'] == 2025
        assert 'federal' in details
        assert 'fica' in details
        assert 'state' in details
        assert 'deductions' in details
        
        # Check federal details
        assert 'ordinary_income_tax' in details['federal']
        assert 'long_term_capital_gains_tax' in details['federal']
        assert 'marginal_bracket' in details['federal']
        
        # Check FICA details
        assert 'social_security' in details['fica']
        assert 'medicare' in details['fica']
        
        # Check deductions
        assert 'standard_deduction' in details['deductions']
        assert 'max_401k' in details['deductions']
    
    def test_get_income_breakdown_working_year(self, tools):
        """Test get_income_breakdown for a working year."""
        breakdown = tools.get_income_breakdown(2025)
        
        assert 'error' not in breakdown
        assert breakdown['year'] == 2025
        assert breakdown['is_working_year'] is True
        assert 'gross_income' in breakdown
        assert 'earned_income' in breakdown
        assert 'investment_income' in breakdown
        
        earned = breakdown['earned_income']
        assert 'base_salary' in earned
        assert 'bonus' in earned
    
    def test_get_income_breakdown_retirement_year(self, tools):
        """Test get_income_breakdown for a retirement year."""
        breakdown = tools.get_income_breakdown(2050)
        
        assert 'error' not in breakdown
        assert breakdown['is_working_year'] is False
        assert 'earned_income' not in breakdown
        assert 'investment_income' in breakdown
    
    def test_get_deferred_comp_info(self, tools):
        """Test get_deferred_comp_info returns expected data."""
        info = tools.get_deferred_comp_info(2025)
        
        assert 'error' not in info
        assert info['year'] == 2025
        assert 'is_working_year' in info
        assert 'contribution' in info
        assert 'disbursement' in info
        assert 'end_of_year_balance' in info
    
    def test_get_deferred_comp_info_invalid_year(self, tools):
        """Test get_deferred_comp_info returns error for invalid year."""
        info = tools.get_deferred_comp_info(2000)
        
        assert 'error' in info
    
    def test_get_retirement_balances_specific_year(self, tools):
        """Test get_retirement_balances for a specific year."""
        balances = tools.get_retirement_balances(2030)
        
        if 'error' not in balances:
            assert balances['year'] == 2030
            assert 'balances' in balances
            assert '401k_balance' in balances['balances']
    
    def test_get_retirement_balances_all_years(self, tools):
        """Test get_retirement_balances returns all years when no year specified."""
        balances = tools.get_retirement_balances()
        
        assert 'final_balances' in balances
        assert 'yearly_balances' in balances
        assert len(balances['yearly_balances']) > 0
    
    def test_get_investment_balances_no_investments(self, tools):
        """Test get_investment_balances handles missing investments config."""
        # quickexample doesn't have investments configured
        balances = tools.get_investment_balances()
        
        # Should either return message about no investments or empty balances
        assert 'message' in balances or 'initial_balances' in balances
    
    def test_compare_years(self, tools):
        """Test compare_years returns comparison data."""
        comparison = tools.compare_years(2025, 2030)
        
        assert 'error' not in comparison
        assert 'comparison' in comparison
        assert 'gross_income' in comparison
        assert 'federal_tax' in comparison
        assert 'take_home_pay' in comparison
        
        # Check comparison structure
        income_comp = comparison['gross_income']
        assert 'year_2025' in income_comp
        assert 'year_2030' in income_comp
        assert 'difference' in income_comp
        assert 'percent_change' in income_comp
    
    def test_compare_years_invalid_year(self, tools):
        """Test compare_years handles invalid years."""
        comparison = tools.compare_years(2000, 2025)
        assert 'error' in comparison
        
        comparison = tools.compare_years(2025, 2100)
        assert 'error' in comparison
    
    def test_get_lifetime_totals(self, tools):
        """Test get_lifetime_totals returns aggregate data."""
        totals = tools.get_lifetime_totals()
        
        assert 'lifetime_totals' in totals
        assert 'working_years_totals' in totals
        assert 'retirement_years_totals' in totals
        assert 'effective_lifetime_tax_rate' in totals
        
        lifetime = totals['lifetime_totals']
        assert 'gross_income' in lifetime
        assert 'federal_tax' in lifetime
        assert 'total_tax' in lifetime
        assert 'take_home_pay' in lifetime
    
    def test_search_financial_data_with_year(self, tools):
        """Test search_financial_data with a specific year."""
        result = tools.search_financial_data('salary', 2025)
        
        assert 'query' in result
        assert 'year' in result
        assert result['year'] == 2025
    
    def test_search_financial_data_all_years(self, tools):
        """Test search_financial_data across all years."""
        result = tools.search_financial_data('federal tax')
        
        assert 'query' in result
        assert 'years' in result
        assert len(result['years']) > 0
    
    def test_search_financial_data_espp(self, tools):
        """Test search for ESPP data."""
        result = tools.search_financial_data('espp', 2025)
        
        assert 'results' in result or 'message' in result
    
    def test_search_financial_data_medicare(self, tools):
        """Test search for Medicare data."""
        result = tools.search_financial_data('medicare', 2025)
        
        assert 'results' in result
    
    def test_search_financial_data_unknown_term(self, tools):
        """Test search with unknown term returns helpful message."""
        result = tools.search_financial_data('xyzabc123', 2025)
        
        assert 'message' in result


class TestMultiProgramTools:
    """Tests for MultiProgramTools class."""
    
    @pytest.fixture
    def multi_tools(self, test_base_path):
        """Create a MultiProgramTools instance."""
        return MultiProgramTools(test_base_path)
    
    def test_init_discovers_programs(self, multi_tools):
        """Test that initialization discovers available programs."""
        assert len(multi_tools.programs) > 0
        # We know testprogram exists in our fixture
        assert 'testprogram' in multi_tools.programs
    
    def test_init_sets_default_program(self, multi_tools):
        """Test that a default program is set."""
        assert multi_tools.default_program is not None
        assert multi_tools.default_program in multi_tools.programs
    
    def test_init_with_explicit_default(self, test_base_path):
        """Test initialization with explicit default program."""
        tools = MultiProgramTools(test_base_path, default_program='testprogram')
        assert tools.default_program == 'testprogram'
    
    def test_list_programs(self, multi_tools):
        """Test list_programs returns program information."""
        result = multi_tools.list_programs()
        
        assert 'available_programs' in result
        assert 'default_program' in result
        assert 'programs_info' in result
        
        assert len(result['available_programs']) > 0
        
        # Check program info structure
        for program_name in result['available_programs']:
            info = result['programs_info'][program_name]
            assert 'first_year' in info
            assert 'last_working_year' in info
            assert 'last_planning_year' in info
    
    def test_get_program_overview_with_program(self, multi_tools):
        """Test get_program_overview with explicit program."""
        result = multi_tools.get_program_overview('testprogram')
        
        assert 'program' in result
        assert result['program'] == 'testprogram'
        assert 'planning_horizon' in result
    
    def test_get_program_invalid_program(self, multi_tools):
        """Test that invalid program name raises error."""
        with pytest.raises(ValueError) as exc_info:
            multi_tools.get_program_overview('nonexistent_program')
        assert 'not found' in str(exc_info.value)
    
    def test_list_available_years_with_program(self, multi_tools):
        """Test list_available_years with explicit program."""
        result = multi_tools.list_available_years('testprogram')
        
        assert 'program' in result
        assert 'working_years' in result
        assert 'retirement_years' in result
    
    def test_get_annual_summary_with_program(self, multi_tools):
        """Test get_annual_summary with explicit program."""
        result = multi_tools.get_annual_summary(2025, 'testprogram')
        
        assert 'program' in result
        assert result['year'] == 2025
        assert 'gross_income' in result
    
    def test_get_tax_details_with_program(self, multi_tools):
        """Test get_tax_details with explicit program."""
        result = multi_tools.get_tax_details(2025, 'testprogram')
        
        assert 'program' in result
        assert 'federal' in result
        assert 'fica' in result
    
    def test_get_income_breakdown_with_program(self, multi_tools):
        """Test get_income_breakdown with explicit program."""
        result = multi_tools.get_income_breakdown(2025, 'testprogram')
        
        assert 'program' in result
        assert 'gross_income' in result
    
    def test_get_deferred_comp_info_with_program(self, multi_tools):
        """Test get_deferred_comp_info with explicit program."""
        result = multi_tools.get_deferred_comp_info(2025, 'testprogram')
        
        assert 'program' in result
        assert 'contribution' in result
    
    def test_get_retirement_balances_with_program(self, multi_tools):
        """Test get_retirement_balances with explicit program."""
        result = multi_tools.get_retirement_balances(None, 'testprogram')
        
        assert 'program' in result
    
    def test_get_investment_balances_with_program(self, multi_tools):
        """Test get_investment_balances with explicit program."""
        result = multi_tools.get_investment_balances(None, 'testprogram')
        
        assert 'program' in result
    
    def test_compare_years_with_program(self, multi_tools):
        """Test compare_years with explicit program."""
        result = multi_tools.compare_years(2025, 2030, 'testprogram')
        
        assert 'program' in result
        assert 'comparison' in result
    
    def test_get_lifetime_totals_with_program(self, multi_tools):
        """Test get_lifetime_totals with explicit program."""
        result = multi_tools.get_lifetime_totals('testprogram')
        
        assert 'program' in result
        assert 'lifetime_totals' in result
    
    def test_search_financial_data_with_program(self, multi_tools):
        """Test search_financial_data with explicit program."""
        result = multi_tools.search_financial_data('salary', 2025, 'testprogram')
        
        assert 'program' in result
        assert 'query' in result

    def test_reload_programs(self, multi_tools):
        """Test reload_programs refreshes the program cache."""
        # Get initial state
        initial_programs = set(multi_tools.programs.keys())
        
        # Reload programs
        result = multi_tools.reload_programs()
        
        # Check result structure
        assert result['status'] == 'success'
        assert 'programs_loaded' in result
        assert 'default_program' in result
        assert 'changes' in result
        assert 'added' in result['changes']
        assert 'removed' in result['changes']
        assert 'reloaded' in result['changes']
        
        # Programs should still be loaded
        assert len(multi_tools.programs) > 0
        assert 'testprogram' in multi_tools.programs
        
        # Since we didn't add/remove any files, everything should be reloaded
        assert set(result['changes']['reloaded']) == initial_programs

    def test_reload_programs_detects_new_program(self, test_base_path):
        """Test reload_programs detects newly added programs."""
        tools = MultiProgramTools(test_base_path)
        initial_count = len(tools.programs)
        
        # Create a new program by copying testprogram
        new_program_dir = os.path.join(test_base_path, 'input-parameters', 'newprogram')
        shutil.copytree(
            os.path.join(test_base_path, 'input-parameters', 'testprogram'),
            new_program_dir
        )
        
        try:
            # Reload and check
            result = tools.reload_programs()
            
            assert 'newprogram' in result['changes']['added']
            assert 'newprogram' in tools.programs
            assert len(tools.programs) == initial_count + 1
        finally:
            # Cleanup
            shutil.rmtree(new_program_dir, ignore_errors=True)

    def test_reload_programs_detects_removed_program(self, test_base_path):
        """Test reload_programs detects removed programs."""
        # Create a temporary program first
        temp_program_dir = os.path.join(test_base_path, 'input-parameters', 'tempprogram')
        shutil.copytree(
            os.path.join(test_base_path, 'input-parameters', 'testprogram'),
            temp_program_dir
        )
        
        tools = MultiProgramTools(test_base_path)
        assert 'tempprogram' in tools.programs
        initial_count = len(tools.programs)
        
        # Remove the program
        shutil.rmtree(temp_program_dir)
        
        # Reload and check
        result = tools.reload_programs()
        
        assert 'tempprogram' in result['changes']['removed']
        assert 'tempprogram' not in tools.programs
        assert len(tools.programs) == initial_count - 1


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_load_invalid_program(self, test_base_path):
        """Test that loading an invalid program raises an error."""
        with pytest.raises(FileNotFoundError):
            FinancialPlannerTools(test_base_path, 'nonexistent_program')
    
    def test_multi_tools_with_invalid_base_path(self):
        """Test MultiProgramTools with invalid base path."""
        tools = MultiProgramTools('/nonexistent/path')
        assert len(tools.programs) == 0
    
    def test_get_retirement_balances_invalid_year(self, test_base_path):
        """Test get_retirement_balances with invalid year."""
        tools = FinancialPlannerTools(test_base_path, 'testprogram')
        result = tools.get_retirement_balances(1900)
        
        assert 'error' in result
    
    def test_yearly_results_consistency(self, test_base_path):
        """Test that cached yearly results are consistent."""
        tools = FinancialPlannerTools(test_base_path, 'testprogram')
        
        # Get results twice
        result1 = tools.get_annual_summary(2025)
        result2 = tools.get_annual_summary(2025)
        
        # Should be identical
        assert result1['gross_income'] == result2['gross_income']
        assert result1['take_home_pay'] == result2['take_home_pay']
    
    def test_tax_amounts_are_reasonable(self, test_base_path):
        """Test that tax amounts are within reasonable bounds."""
        tools = FinancialPlannerTools(test_base_path, 'testprogram')
        summary = tools.get_annual_summary(2025)
        
        # Tax should be positive but less than gross income
        assert summary['total_tax'] >= 0
        assert summary['total_tax'] < summary['gross_income']
        
        # Take home should be positive
        assert summary['take_home_pay'] > 0
        
        # Take home + tax should approximately equal gross income (within rounding)
        total = summary['take_home_pay'] + summary['total_tax'] + summary['total_deferral']
        assert abs(total - summary['gross_income']) < 100  # Allow small rounding difference
    
    def test_effective_tax_rate_bounds(self, test_base_path):
        """Test that effective tax rate is within reasonable bounds."""
        tools = FinancialPlannerTools(test_base_path, 'testprogram')
        summary = tools.get_annual_summary(2025)
        
        # Effective rate should be between 0% and 60%
        assert 0 <= summary['effective_tax_rate'] < 60


class TestCompareProgramsTools:
    """Tests for the compare_programs functionality in MultiProgramTools."""
    
    @pytest.fixture
    def multi_tools_with_two_programs(self, test_base_path):
        """Create MultiProgramTools with two test programs."""
        # Create a second test program with different values
        input_params_dir = os.path.join(test_base_path, 'input-parameters')
        testprogram2_dir = os.path.join(input_params_dir, 'testprogram2')
        os.makedirs(testprogram2_dir, exist_ok=True)
        
        # Copy and modify the spec for the second program
        with open(os.path.join(input_params_dir, 'testprogram', 'spec.json'), 'r') as f:
            spec = json.load(f)
        
        # Modify to create a different scenario (higher salary, longer working years)
        spec['income']['baseSalary'] = 150000
        spec['lastWorkingYear'] = 2040
        
        with open(os.path.join(testprogram2_dir, 'spec.json'), 'w') as f:
            json.dump(spec, f)
        
        tools = MultiProgramTools(test_base_path)
        yield tools
        
        # Cleanup the second program
        shutil.rmtree(testprogram2_dir, ignore_errors=True)
    
    def test_compare_programs_returns_structure(self, multi_tools_with_two_programs):
        """Test that compare_programs returns the expected structure."""
        result = multi_tools_with_two_programs.compare_programs('testprogram', 'testprogram2')
        
        assert 'programs' in result
        assert 'metrics' in result
        assert 'summary' in result
        assert 'recommendation' in result
    
    def test_compare_programs_includes_all_metrics(self, multi_tools_with_two_programs):
        """Test that all expected metrics are compared."""
        result = multi_tools_with_two_programs.compare_programs('testprogram', 'testprogram2')
        
        expected_metrics = [
            'lifetime_income', 'lifetime_taxes', 'take_home', 'tax_efficiency',
            'working_income', 'working_take_home', 'retirement_income', 
            'retirement_take_home', 'retirement_assets', 'assets_at_retirement'
        ]
        
        for metric in expected_metrics:
            assert metric in result['metrics'], f"Missing metric: {metric}"
    
    def test_compare_programs_metric_structure(self, multi_tools_with_two_programs):
        """Test that each metric comparison has expected fields."""
        result = multi_tools_with_two_programs.compare_programs('testprogram', 'testprogram2')
        
        for metric_name, metric_data in result['metrics'].items():
            assert 'description' in metric_data
            assert 'testprogram' in metric_data
            assert 'testprogram2' in metric_data
            assert 'difference' in metric_data
            assert 'percent_difference' in metric_data
            assert 'better' in metric_data
            assert 'higher_is_better' in metric_data
    
    def test_compare_programs_summary_has_wins(self, multi_tools_with_two_programs):
        """Test that summary includes win counts."""
        result = multi_tools_with_two_programs.compare_programs('testprogram', 'testprogram2')
        
        assert 'wins' in result['summary']
        assert 'testprogram' in result['summary']['wins']
        assert 'testprogram2' in result['summary']['wins']
        assert 'tied' in result['summary']['wins']
        assert 'overall_better' in result['summary']
        assert 'metrics_compared' in result['summary']
    
    def test_compare_programs_with_specific_metrics(self, multi_tools_with_two_programs):
        """Test comparing only specific metrics."""
        result = multi_tools_with_two_programs.compare_programs(
            'testprogram', 'testprogram2',
            metrics=['lifetime_income', 'take_home']
        )
        
        assert len(result['metrics']) == 2
        assert 'lifetime_income' in result['metrics']
        assert 'take_home' in result['metrics']
        assert result['summary']['metrics_compared'] == 2
    
    def test_compare_programs_invalid_program(self, multi_tools_with_two_programs):
        """Test error handling for invalid program name."""
        result = multi_tools_with_two_programs.compare_programs('testprogram', 'nonexistent')
        
        assert 'error' in result
        assert 'nonexistent' in result['error']
    
    def test_compare_programs_invalid_metrics(self, multi_tools_with_two_programs):
        """Test error handling for invalid metrics."""
        result = multi_tools_with_two_programs.compare_programs(
            'testprogram', 'testprogram2',
            metrics=['invalid_metric']
        )
        
        assert 'error' in result
        assert 'Available metrics' in result['error']
    
    def test_compare_programs_recommendation_text(self, multi_tools_with_two_programs):
        """Test that recommendation is a meaningful string."""
        result = multi_tools_with_two_programs.compare_programs('testprogram', 'testprogram2')
        
        assert isinstance(result['recommendation'], str)
        assert len(result['recommendation']) > 20  # Should be a meaningful sentence
    
    def test_compare_programs_self_comparison(self, multi_tools_with_two_programs):
        """Test comparing a program to itself results in ties."""
        result = multi_tools_with_two_programs.compare_programs('testprogram', 'testprogram')
        
        # All metrics should be tied when comparing to self
        for metric_data in result['metrics'].values():
            assert metric_data['difference'] == 0
            assert metric_data['better'] == 'tie'
        
        assert result['summary']['overall_better'] == 'tie'
