"""Tests for the interactive shell functionality."""

import pytest
import sys
import os
from io import StringIO

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from shell import FinancialPlanShell, get_yearly_fields


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
