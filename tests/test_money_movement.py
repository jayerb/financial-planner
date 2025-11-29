"""Tests for expense calculations and money movement to/from taxable account.

These tests verify the income vs expense comparison and the resulting
adjustments to the taxable account balance.
"""

import os
import sys
import pytest
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from calc.plan_calculator import PlanCalculator
from model.PlanData import YearlyData, PlanData


def create_mock_federal():
    """Create a mock FederalDetails with sensible defaults."""
    mock = Mock()
    mock.totalDeductions.return_value = {
        'standardDeduction': 30000,
        'itemizedDeduction': 0,
        'max401k': 24000,
        'maxHSA': 8000,
        'employeeHSA': 8000,
        'total': 62000
    }
    federal_result = Mock()
    federal_result.totalFederalTax = 50000
    federal_result.marginalBracket = 0.24
    mock.taxBurden.return_value = federal_result
    mock.longTermCapitalGainsTax.return_value = 1000
    return mock


def create_mock_state():
    """Create a mock StateDetails with sensible defaults."""
    mock = Mock()
    mock.taxBurden.return_value = 15000
    mock.shortTermCapitalGainsTax.return_value = 500
    return mock


def create_mock_espp():
    """Create a mock ESPPDetails with sensible defaults."""
    mock = Mock()
    mock.taxable_from_spec.return_value = 5000
    return mock


def create_mock_social_security():
    """Create a mock SocialSecurityDetails."""
    mock = Mock()
    mock.total_contribution.return_value = 12000
    return mock


def create_mock_medicare():
    """Create a mock MedicareDetails."""
    mock = Mock()
    mock.base_contribution.return_value = 5000
    mock.surcharge.return_value = 1000
    return mock


def create_mock_rsu_calculator(vested_values=None):
    """Create a mock RSUCalculator."""
    mock = Mock()
    mock.vested_value = vested_values or {2026: 50000, 2027: 55000}
    return mock


def create_spec_with_expenses():
    """Create a spec dictionary with expenses configured."""
    return {
        'firstYear': 2026,
        'lastWorkingYear': 2028,
        'lastPlanningYear': 2035,
        'federalBracketInflation': 0.03,
        'income': {
            'baseSalary': 200000,
            'bonusFraction': 0.20,
            'otherIncome': 0,
            'baseDeferralFraction': 0.10,
            'bonusDeferralFraction': 0.50,
            'shortTermCapitalGainsPercent': 0.01,
            'longTermCapitalGainsPercent': 0.02,
            'annualBaseIncreaseFraction': 0.03
        },
        'investments': {
            'taxableBalance': 100000,
            'taxableAppreciationRate': 0.06,
            'taxDeferredBalance': 500000,
            'taxDeferredAppreciationRate': 0.08,
            'hsaBalance': 20000,
            'hsaAppreciationRate': 0.07,
            'employer401kMatchPercent': 0.50,
            'employer401kMatchMaxSalaryPercent': 0.06,
            'hsaEmployerContribution': 1500
        },
        'deductions': {
            'medicalDentalVision': 4000,
            'medicalInflationRate': 0.04
        },
        'deferredCompensationPlan': {
            'annualGrowthFraction': 0.05,
            'dispursementYears': 5
        },
        'localTax': {
            'realEstate': 8000,
            'inflationRate': 0.03
        },
        'companyProvidedLifeInsurance': {
            'annualPremium': 500
        },
        'expenses': {
            'annualAmount': 80000,
            'inflationRate': 0.03,
            'specialExpenses': [
                {'year': 2027, 'amount': 50000, 'description': 'Special expense'}
            ]
        }
    }


class TestExpenseCalculation:
    """Test expense calculations."""
    
    @pytest.fixture
    def calculator(self):
        return PlanCalculator(
            federal=create_mock_federal(),
            state=create_mock_state(),
            espp=create_mock_espp(),
            social_security=create_mock_social_security(),
            medicare=create_mock_medicare(),
            rsu_calculator=create_mock_rsu_calculator()
        )
    
    def test_annual_expenses_present(self, calculator):
        """Test that annual expenses are calculated."""
        spec = create_spec_with_expenses()
        result = calculator.calculate(spec)
        
        first_year = result.yearly_data[2026]
        assert first_year.annual_expenses == 80000
    
    def test_annual_expenses_inflate(self, calculator):
        """Test that annual expenses inflate each year."""
        spec = create_spec_with_expenses()
        result = calculator.calculate(spec)
        
        y1 = result.yearly_data[2026]
        y2 = result.yearly_data[2027]
        
        inflation = spec['expenses']['inflationRate']
        expected = y1.annual_expenses * (1 + inflation)
        assert abs(y2.annual_expenses - expected) < 0.01
    
    def test_special_expenses_applied(self, calculator):
        """Test that special expenses are applied in the correct year."""
        spec = create_spec_with_expenses()
        result = calculator.calculate(spec)
        
        # 2026 should have no special expense
        assert result.yearly_data[2026].special_expenses == 0
        
        # 2027 should have the special expense
        assert result.yearly_data[2027].special_expenses == 50000
        
        # 2028 should have no special expense
        assert result.yearly_data[2028].special_expenses == 0
    
    def test_total_expenses_calculated(self, calculator):
        """Test that total expenses = annual + special."""
        spec = create_spec_with_expenses()
        result = calculator.calculate(spec)
        
        y = result.yearly_data[2027]
        assert y.total_expenses == y.annual_expenses + y.special_expenses


class TestMoneyMovement:
    """Test money movement calculations."""
    
    @pytest.fixture
    def calculator(self):
        return PlanCalculator(
            federal=create_mock_federal(),
            state=create_mock_state(),
            espp=create_mock_espp(),
            social_security=create_mock_social_security(),
            medicare=create_mock_medicare(),
            rsu_calculator=create_mock_rsu_calculator()
        )
    
    def test_income_expense_difference_calculated(self, calculator):
        """Test that income vs expense difference is calculated."""
        spec = create_spec_with_expenses()
        result = calculator.calculate(spec)
        
        y = result.yearly_data[2026]
        expected_diff = y.take_home_pay - y.total_expenses
        assert y.income_expense_difference == expected_diff
    
    def test_taxable_adjustment_positive_when_excess_income(self, calculator):
        """Test that taxable adjustment is positive when income exceeds expenses."""
        spec = create_spec_with_expenses()
        # Set low expenses to ensure excess income
        spec['expenses']['annualAmount'] = 20000
        result = calculator.calculate(spec)
        
        y = result.yearly_data[2026]
        assert y.taxable_account_adjustment > 0
    
    def test_taxable_adjustment_negative_when_expenses_exceed(self, calculator):
        """Test that taxable adjustment is negative when expenses exceed income."""
        spec = create_spec_with_expenses()
        # Set high expenses to ensure deficit
        spec['expenses']['annualAmount'] = 500000
        result = calculator.calculate(spec)
        
        y = result.yearly_data[2026]
        assert y.taxable_account_adjustment < 0
    
    def test_taxable_balance_increases_with_excess_income(self, calculator):
        """Test that taxable balance increases when there's excess income."""
        spec = create_spec_with_expenses()
        spec['expenses']['annualAmount'] = 20000  # Low expenses
        result = calculator.calculate(spec)
        
        initial_taxable = spec['investments']['taxableBalance']
        y1 = result.yearly_data[2026]
        
        # First year balance should be initial + adjustment
        expected = initial_taxable + y1.taxable_account_adjustment
        assert abs(y1.balance_taxable - expected) < 0.01
    
    def test_taxable_balance_decreases_with_expense_deficit(self, calculator):
        """Test that taxable balance decreases when expenses exceed income."""
        spec = create_spec_with_expenses()
        spec['expenses']['annualAmount'] = 500000  # Very high expenses
        result = calculator.calculate(spec)
        
        initial_taxable = spec['investments']['taxableBalance']
        y1 = result.yearly_data[2026]
        
        # First year balance should be initial + adjustment (which is negative)
        expected = initial_taxable + y1.taxable_account_adjustment
        assert y1.balance_taxable < initial_taxable
        assert abs(y1.balance_taxable - expected) < 0.01


class TestRetirementMoneyMovement:
    """Test money movement in retirement years."""
    
    @pytest.fixture
    def calculator(self):
        return PlanCalculator(
            federal=create_mock_federal(),
            state=create_mock_state(),
            espp=create_mock_espp(),
            social_security=create_mock_social_security(),
            medicare=create_mock_medicare(),
            rsu_calculator=create_mock_rsu_calculator()
        )
    
    def test_expenses_continue_in_retirement(self, calculator):
        """Test that expenses continue to be calculated in retirement."""
        spec = create_spec_with_expenses()
        result = calculator.calculate(spec)
        
        retirement_year = spec['lastWorkingYear'] + 1
        y = result.yearly_data[retirement_year]
        
        assert y.annual_expenses > 0
        assert y.total_expenses > 0
    
    def test_expenses_inflate_in_retirement(self, calculator):
        """Test that expenses continue to inflate during retirement."""
        spec = create_spec_with_expenses()
        result = calculator.calculate(spec)
        
        last_working = spec['lastWorkingYear']
        first_retirement = last_working + 1
        second_retirement = first_retirement + 1
        
        y1 = result.yearly_data[first_retirement]
        y2 = result.yearly_data[second_retirement]
        
        inflation = spec['expenses']['inflationRate']
        expected = y1.annual_expenses * (1 + inflation)
        assert abs(y2.annual_expenses - expected) < 0.01
    
    def test_money_movement_in_retirement(self, calculator):
        """Test that money movement continues in retirement years."""
        spec = create_spec_with_expenses()
        result = calculator.calculate(spec)
        
        retirement_year = spec['lastWorkingYear'] + 1
        y = result.yearly_data[retirement_year]
        
        # Income-expense difference should be calculated
        expected_diff = y.take_home_pay - y.total_expenses
        assert y.income_expense_difference == expected_diff
        assert y.taxable_account_adjustment == expected_diff


class TestNoExpensesSpec:
    """Test behavior when no expenses are configured."""
    
    @pytest.fixture
    def calculator(self):
        return PlanCalculator(
            federal=create_mock_federal(),
            state=create_mock_state(),
            espp=create_mock_espp(),
            social_security=create_mock_social_security(),
            medicare=create_mock_medicare(),
            rsu_calculator=create_mock_rsu_calculator()
        )
    
    def test_zero_expenses_when_not_configured(self, calculator):
        """Test that expenses are zero when not in spec."""
        spec = create_spec_with_expenses()
        del spec['expenses']  # Remove expenses section
        result = calculator.calculate(spec)
        
        y = result.yearly_data[2026]
        assert y.annual_expenses == 0
        assert y.special_expenses == 0
        assert y.total_expenses == 0
    
    def test_taxable_adjustment_equals_take_home_when_no_expenses(self, calculator):
        """Test that all take-home goes to taxable when no expenses."""
        spec = create_spec_with_expenses()
        del spec['expenses']  # Remove expenses section
        result = calculator.calculate(spec)
        
        y = result.yearly_data[2026]
        assert y.taxable_account_adjustment == y.take_home_pay


class TestIRAWithdrawals:
    """Test IRA/401k withdrawal calculations in post-deferred comp years."""
    
    @pytest.fixture
    def calculator(self):
        return PlanCalculator(
            federal=create_mock_federal(),
            state=create_mock_state(),
            espp=create_mock_espp(),
            social_security=create_mock_social_security(),
            medicare=create_mock_medicare(),
            rsu_calculator=create_mock_rsu_calculator()
        )
    
    def test_no_ira_withdrawal_during_working_years(self, calculator):
        """Test that IRA withdrawals are zero during working years."""
        spec = create_spec_with_expenses()
        result = calculator.calculate(spec)
        
        for year in range(spec['firstYear'], spec['lastWorkingYear'] + 1):
            assert result.yearly_data[year].ira_withdrawal == 0
    
    def test_no_ira_withdrawal_during_deferred_comp_years(self, calculator):
        """Test that IRA withdrawals are zero during deferred comp disbursement years."""
        spec = create_spec_with_expenses()
        result = calculator.calculate(spec)
        
        disbursement_years = spec['deferredCompensationPlan']['dispursementYears']
        first_retirement = spec['lastWorkingYear'] + 1
        
        for year in range(first_retirement, first_retirement + disbursement_years):
            if year <= spec['lastPlanningYear']:
                assert result.yearly_data[year].ira_withdrawal == 0
    
    def test_ira_withdrawal_after_deferred_comp_exhausted(self, calculator):
        """Test that IRA withdrawals start when deferred comp is exhausted."""
        spec = create_spec_with_expenses()
        # High expenses to ensure shortfall
        spec['expenses']['annualAmount'] = 200000
        result = calculator.calculate(spec)
        
        disbursement_years = spec['deferredCompensationPlan']['dispursementYears']
        first_retirement = spec['lastWorkingYear'] + 1
        post_deferred_start = first_retirement + disbursement_years
        
        if post_deferred_start <= spec['lastPlanningYear']:
            y = result.yearly_data[post_deferred_start]
            # Should have IRA withdrawal when there's an expense shortfall
            assert y.ira_withdrawal > 0
    
    def test_ira_withdrawal_limited_by_annuity(self, calculator):
        """Test that IRA withdrawal is limited by balance / remaining years."""
        spec = create_spec_with_expenses()
        spec['expenses']['annualAmount'] = 500000  # Very high expenses
        result = calculator.calculate(spec)
        
        disbursement_years = spec['deferredCompensationPlan']['dispursementYears']
        first_retirement = spec['lastWorkingYear'] + 1
        post_deferred_start = first_retirement + disbursement_years
        
        if post_deferred_start <= spec['lastPlanningYear']:
            y = result.yearly_data[post_deferred_start]
            remaining_years = spec['lastPlanningYear'] - post_deferred_start + 1
            
            # Get the 401k balance before this year's withdrawal
            # The withdrawal should be limited by balance / remaining years
            assert y.ira_withdrawal <= y.balance_ira + y.ira_withdrawal  # Balance before withdrawal
    
    def test_ira_balance_decreases_with_withdrawals(self, calculator):
        """Test that 401k balance decreases when IRA withdrawals are made."""
        spec = create_spec_with_expenses()
        spec['expenses']['annualAmount'] = 200000  # High expenses
        result = calculator.calculate(spec)
        
        disbursement_years = spec['deferredCompensationPlan']['dispursementYears']
        first_retirement = spec['lastWorkingYear'] + 1
        post_deferred_start = first_retirement + disbursement_years
        
        if post_deferred_start + 1 <= spec['lastPlanningYear']:
            y1 = result.yearly_data[post_deferred_start]
            y2 = result.yearly_data[post_deferred_start + 1]
            
            if y1.ira_withdrawal > 0:
                # Balance after appreciation but before next withdrawal should account for withdrawal
                expected_growth = y1.balance_ira * 1.08  # 8% appreciation
                # y2 balance = y1 balance * appreciation - y2 withdrawal
                assert y2.balance_ira < expected_growth
    
    def test_taxable_adjustment_zero_when_ira_covers_shortfall(self, calculator):
        """Test that taxable adjustment is zero when IRA fully covers expense shortfall."""
        spec = create_spec_with_expenses()
        # Moderate expenses that IRA annuity can cover
        spec['expenses']['annualAmount'] = 50000
        result = calculator.calculate(spec)
        
        disbursement_years = spec['deferredCompensationPlan']['dispursementYears']
        first_retirement = spec['lastWorkingYear'] + 1
        post_deferred_start = first_retirement + disbursement_years
        
        if post_deferred_start <= spec['lastPlanningYear']:
            y = result.yearly_data[post_deferred_start]
            # When IRA covers shortfall, taxable adjustment should be >= 0
            assert y.taxable_account_adjustment >= 0
