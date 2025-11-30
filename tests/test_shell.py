"""Tests for the interactive shell functionality."""

import pytest
import sys
import os
from io import StringIO

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from shell import FinancialPlanShell, get_yearly_fields, load_plan
from render.renderers import RENDERER_REGISTRY


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


class TestRenderCommand:
    """Test the render command functionality."""
    
    @pytest.fixture
    def shell_with_plan(self):
        """Create a shell with a loaded plan."""
        plan_data = load_plan('quickexample')
        return FinancialPlanShell(plan_data, 'quickexample')
    
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
