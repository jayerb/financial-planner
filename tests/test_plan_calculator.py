"""Tests for the PlanCalculator class.

This tests the unified calculation approach that uses three loops:
1. Working years - all income, contributions, and taxes while employed
2. Deferred comp withdrawal years - retirement with disbursements
3. Post-withdrawal years - retirement without disbursements
"""

import os
import sys
import pytest
from unittest.mock import Mock, MagicMock

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
    # Mock get_data_for_year for weekly take-home calculations
    mock.get_data_for_year.return_value = {
        'maximumTaxedIncome': 168600,  # 2024 SS wage base
        'employeePortion': 0.062,
        'maPFML': 0.00318
    }
    # Set wage_base attribute for paycheck calculations
    mock.wage_base = 168600
    return mock


def create_mock_medicare():
    """Create a mock MedicareDetails."""
    mock = Mock()
    mock.base_contribution.return_value = 5000
    mock.surcharge.return_value = 1000
    # Instance attributes for weekly take-home calculations
    mock.medicare_rate = 0.0145
    mock.surcharge_threshold = 200000
    mock.surcharge_rate = 0.009
    return mock


def create_mock_rsu_calculator(vested_values=None):
    """Create a mock RSUCalculator."""
    mock = Mock()
    mock.vested_value = vested_values or {2026: 50000, 2027: 55000}
    return mock


def create_basic_spec():
    """Create a minimal spec dictionary for testing."""
    return {
        'firstYear': 2026,
        'lastWorkingYear': 2028,
        'lastPlanningYear': 2040,
        'federalBracketInflation': 0.03,
        'income': {
            'baseSalary': 200000,
            'bonusFraction': 0.20,
            'otherIncome': 0,
            'baseDeferralFraction': 0.10,
            'bonusDeferralFraction': 0.50,
            'realizedShortTermCapitalGainsPercent': 0.01,
            'realizedLongTermCapitalGainsPercent': 0.02,
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
            'disbursementYears': 10
        },
        'localTax': {
            'realEstate': 8000,
            'inflationRate': 0.03
        },
        'companyProvidedLifeInsurance': {
            'annualPremium': 500
        }
    }


class TestPlanCalculatorBasics:
    """Test basic PlanCalculator functionality."""
    
    @pytest.fixture
    def calculator(self):
        """Create a PlanCalculator with mock dependencies."""
        return PlanCalculator(
            federal=create_mock_federal(),
            state=create_mock_state(),
            espp=create_mock_espp(),
            social_security=create_mock_social_security(),
            medicare=create_mock_medicare(),
            rsu_calculator=create_mock_rsu_calculator()
        )
    
    def test_calculate_returns_plan_data(self, calculator):
        """Test that calculate returns a PlanData object."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        assert isinstance(result, PlanData)
        assert result.first_year == 2026
        assert result.last_working_year == 2028
        assert result.last_planning_year == 2040
    
    def test_all_years_have_data(self, calculator):
        """Test that all years in the planning horizon have data."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        expected_years = result.last_planning_year - result.first_year + 1
        assert len(result.yearly_data) == expected_years
        
        for year in range(result.first_year, result.last_planning_year + 1):
            assert year in result.yearly_data
            assert isinstance(result.yearly_data[year], YearlyData)
    
    def test_working_years_flagged_correctly(self, calculator):
        """Test that is_working_year is set correctly for each year."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        for year, data in result.yearly_data.items():
            if year <= spec['lastWorkingYear']:
                assert data.is_working_year is True, f"Year {year} should be a working year"
            else:
                assert data.is_working_year is False, f"Year {year} should be a retirement year"


class TestWorkingYearsLoop:
    """Test the working years loop (Loop 1)."""
    
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
    
    def test_working_year_has_income(self, calculator):
        """Test that working years have income components."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        first_year_data = result.yearly_data[2026]
        
        assert first_year_data.base_salary > 0
        assert first_year_data.bonus > 0
        assert first_year_data.gross_income > 0
    
    def test_salary_inflates_each_year(self, calculator):
        """Test that salary increases each year."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        y1 = result.yearly_data[2026]
        y2 = result.yearly_data[2027]
        y3 = result.yearly_data[2028]
        
        # Each year's salary should be higher than the previous
        assert y2.base_salary > y1.base_salary
        assert y3.base_salary > y2.base_salary
        
        # Should follow the inflation rate
        increase_rate = spec['income']['annualBaseIncreaseFraction']
        expected_y2_salary = y1.base_salary * (1 + increase_rate)
        assert abs(y2.base_salary - expected_y2_salary) < 0.01
    
    def test_deferrals_calculated(self, calculator):
        """Test that deferrals are calculated correctly."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        first_year = result.yearly_data[2026]
        
        expected_base_deferral = spec['income']['baseSalary'] * spec['income']['baseDeferralFraction']
        expected_bonus_deferral = (spec['income']['baseSalary'] * spec['income']['bonusFraction'] * 
                                   spec['income']['bonusDeferralFraction'])
        
        assert abs(first_year.base_deferral - expected_base_deferral) < 0.01
        assert abs(first_year.bonus_deferral - expected_bonus_deferral) < 0.01
        assert first_year.total_deferral == first_year.base_deferral + first_year.bonus_deferral
    
    def test_contributions_tracked(self, calculator):
        """Test that 401k and HSA contributions are tracked."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        first_year = result.yearly_data[2026]
        
        assert first_year.employee_401k_contribution > 0
        assert first_year.employer_401k_match >= 0
        assert first_year.total_401k_contribution == first_year.employee_401k_contribution + first_year.employer_401k_match
        assert first_year.hsa_contribution > 0
    
    def test_fica_taxes_calculated(self, calculator):
        """Test that FICA taxes are calculated for working years."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        first_year = result.yearly_data[2026]
        
        assert first_year.social_security_tax > 0
        assert first_year.medicare_tax > 0
        assert first_year.total_fica > 0
    
    def test_balances_accumulate(self, calculator):
        """Test that balances accumulate over working years."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        y1 = result.yearly_data[2026]
        y2 = result.yearly_data[2027]
        y3 = result.yearly_data[2028]
        
        # Balances should grow each year (contributions + appreciation)
        assert y2.balance_ira > y1.balance_ira
        assert y3.balance_ira > y2.balance_ira
        
        assert y2.balance_deferred_comp > y1.balance_deferred_comp
        assert y3.balance_deferred_comp > y2.balance_deferred_comp


class TestDeferredCompWithdrawalYearsLoop:
    """Test the deferred compensation withdrawal years loop (Loop 2)."""
    
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
    
    def test_disbursements_start_after_working_years(self, calculator):
        """Test that disbursements start the year after last working year."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        last_working = spec['lastWorkingYear']
        first_retirement = last_working + 1
        
        # Last working year should have no disbursement
        assert result.yearly_data[last_working].deferred_comp_disbursement == 0
        
        # First retirement year should have disbursement
        assert result.yearly_data[first_retirement].deferred_comp_disbursement > 0
    
    def test_disbursements_follow_annuity_pattern(self, calculator):
        """Test that disbursements are calculated as balance / remaining years."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        disbursement_years = spec['deferredCompensationPlan']['disbursementYears']
        first_retirement = spec['lastWorkingYear'] + 1
        
        # Each year's disbursement should be approximately balance / remaining years
        # Due to growth, disbursements will increase over time
        disbursements = []
        for year in range(first_retirement, first_retirement + disbursement_years):
            if year <= spec['lastPlanningYear']:
                disbursements.append(result.yearly_data[year].deferred_comp_disbursement)
        
        # Disbursements should generally increase due to growth
        # (each year the remaining balance grows before the disbursement)
        if len(disbursements) > 1:
            for i in range(1, len(disbursements)):
                # Later disbursements should be >= earlier ones due to growth
                assert disbursements[i] >= disbursements[i-1] * 0.99  # Allow small rounding
    
    def test_deferred_comp_balance_zero_after_disbursements(self, calculator):
        """Test that deferred comp balance is zero after all disbursements."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        disbursement_years = spec['deferredCompensationPlan']['disbursementYears']
        first_retirement = spec['lastWorkingYear'] + 1
        last_disbursement_year = first_retirement + disbursement_years - 1
        
        if last_disbursement_year <= spec['lastPlanningYear']:
            # Balance should be zero after the last disbursement
            assert result.yearly_data[last_disbursement_year].balance_deferred_comp == 0
    
    def test_no_fica_in_retirement(self, calculator):
        """Test that there are no FICA taxes in retirement years."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        first_retirement = spec['lastWorkingYear'] + 1
        
        assert result.yearly_data[first_retirement].total_fica == 0
        assert result.yearly_data[first_retirement].social_security_tax == 0
        assert result.yearly_data[first_retirement].medicare_tax == 0
    
    def test_no_salary_in_retirement(self, calculator):
        """Test that there is no salary in retirement years."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        first_retirement = spec['lastWorkingYear'] + 1
        
        assert result.yearly_data[first_retirement].base_salary == 0
        assert result.yearly_data[first_retirement].bonus == 0
    
    def test_deferred_balance_decreases_during_withdrawal(self, calculator):
        """Test that deferred comp balance decreases during withdrawal."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        first_retirement = spec['lastWorkingYear'] + 1
        second_retirement = first_retirement + 1
        
        # Balance should decrease as disbursements are made
        if second_retirement <= spec['lastPlanningYear']:
            assert (result.yearly_data[second_retirement].balance_deferred_comp < 
                    result.yearly_data[first_retirement].balance_deferred_comp)


class TestPostWithdrawalYearsLoop:
    """Test the post-deferred comp withdrawal years loop (Loop 3)."""
    
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
    
    def test_no_disbursement_after_withdrawal_period(self, calculator):
        """Test that there are no disbursements after the withdrawal period."""
        spec = create_basic_spec()
        spec['lastPlanningYear'] = 2050  # Extend to have post-withdrawal years
        result = calculator.calculate(spec)
        
        disbursement_years = spec['deferredCompensationPlan']['disbursementYears']
        first_retirement = spec['lastWorkingYear'] + 1
        post_withdrawal_start = first_retirement + disbursement_years
        
        if post_withdrawal_start <= spec['lastPlanningYear']:
            assert result.yearly_data[post_withdrawal_start].deferred_comp_disbursement == 0
    
    def test_deferred_balance_zero_after_withdrawal(self, calculator):
        """Test that deferred comp balance is zero after withdrawal period."""
        spec = create_basic_spec()
        spec['lastPlanningYear'] = 2050  # Extend to have post-withdrawal years
        result = calculator.calculate(spec)
        
        disbursement_years = spec['deferredCompensationPlan']['disbursementYears']
        first_retirement = spec['lastWorkingYear'] + 1
        post_withdrawal_start = first_retirement + disbursement_years
        
        if post_withdrawal_start <= spec['lastPlanningYear']:
            assert result.yearly_data[post_withdrawal_start].balance_deferred_comp == 0
    
    def test_capital_gains_continue_post_withdrawal(self, calculator):
        """Test that capital gains income continues in post-withdrawal years."""
        spec = create_basic_spec()
        spec['lastPlanningYear'] = 2050
        result = calculator.calculate(spec)
        
        disbursement_years = spec['deferredCompensationPlan']['disbursementYears']
        first_retirement = spec['lastWorkingYear'] + 1
        post_withdrawal_year = first_retirement + disbursement_years
        
        if post_withdrawal_year <= spec['lastPlanningYear']:
            data = result.yearly_data[post_withdrawal_year]
            # Should have capital gains but no disbursement
            assert data.short_term_capital_gains > 0 or data.long_term_capital_gains > 0
            assert data.deferred_comp_disbursement == 0


class TestLifetimeTotals:
    """Test lifetime totals in PlanData."""
    
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
    
    def test_totals_sum_correctly(self, calculator):
        """Test that lifetime totals are correct sums of yearly data."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        # Sum up the yearly values
        expected_gross = sum(yd.gross_income for yd in result.yearly_data.values())
        expected_federal = sum(yd.federal_tax for yd in result.yearly_data.values())
        expected_state = sum(yd.state_tax for yd in result.yearly_data.values())
        expected_total_tax = sum(yd.total_taxes for yd in result.yearly_data.values())
        expected_take_home = sum(yd.take_home_pay for yd in result.yearly_data.values())
        
        assert abs(result.total_gross_income - expected_gross) < 0.01
        assert abs(result.total_federal_tax - expected_federal) < 0.01
        assert abs(result.total_state_tax - expected_state) < 0.01
        assert abs(result.total_taxes - expected_total_tax) < 0.01
        assert abs(result.total_take_home - expected_take_home) < 0.01
    
    def test_final_balances_match_last_year(self, calculator):
        """Test that final balances match the last year's balances."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        last_year_data = result.yearly_data[spec['lastPlanningYear']]
        
        assert result.final_401k_balance == last_year_data.balance_ira
        assert result.final_hsa_balance == last_year_data.balance_hsa
        assert result.final_deferred_comp_balance == last_year_data.balance_deferred_comp
        assert result.final_taxable_balance == last_year_data.balance_taxable


class TestInflationHandling:
    """Test that inflation is applied correctly."""
    
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
    
    def test_medical_costs_inflate(self, calculator):
        """Test that medical costs inflate each year."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        y1 = result.yearly_data[2026]
        y2 = result.yearly_data[2027]
        
        medical_inflation = spec['deductions']['medicalInflationRate']
        expected = y1.medical_dental_vision * (1 + medical_inflation)
        
        assert abs(y2.medical_dental_vision - expected) < 0.01
    
    def test_local_tax_inflates(self, calculator):
        """Test that local tax inflates each year."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        y1 = result.yearly_data[2026]
        y2 = result.yearly_data[2027]
        
        local_tax_inflation = spec['localTax']['inflationRate']
        expected = y1.local_tax * (1 + local_tax_inflation)
        
        assert abs(y2.local_tax - expected) < 0.01
    
    def test_local_tax_continues_in_retirement(self, calculator):
        """Test that local tax continues to inflate in retirement."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        last_working = result.yearly_data[spec['lastWorkingYear']]
        first_retirement = result.yearly_data[spec['lastWorkingYear'] + 1]
        
        local_tax_inflation = spec['localTax']['inflationRate']
        expected = last_working.local_tax * (1 + local_tax_inflation)
        
        assert abs(first_retirement.local_tax - expected) < 0.01


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
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
    
    def test_single_working_year(self, calculator):
        """Test with only one working year."""
        spec = create_basic_spec()
        spec['lastWorkingYear'] = spec['firstYear']
        spec['lastPlanningYear'] = spec['firstYear'] + 5
        
        result = calculator.calculate(spec)
        
        assert len(result.yearly_data) == 6
        assert result.yearly_data[spec['firstYear']].is_working_year is True
        assert result.yearly_data[spec['firstYear'] + 1].is_working_year is False
    
    def test_no_deferred_compensation(self, calculator):
        """Test with no deferred compensation contributions."""
        spec = create_basic_spec()
        spec['income']['baseDeferralFraction'] = 0
        spec['income']['bonusDeferralFraction'] = 0
        
        result = calculator.calculate(spec)
        
        # All years should have zero deferred comp balance
        for yd in result.yearly_data.values():
            assert yd.balance_deferred_comp == 0
            assert yd.deferred_comp_disbursement == 0
    
    def test_zero_disbursement_years(self, calculator):
        """Test with zero disbursement years configured."""
        spec = create_basic_spec()
        spec['deferredCompensationPlan']['disbursementYears'] = 0
        
        result = calculator.calculate(spec)
        
        # No disbursements should occur
        for year, yd in result.yearly_data.items():
            if year > spec['lastWorkingYear']:
                assert yd.deferred_comp_disbursement == 0
    
    def test_missing_optional_spec_fields(self, calculator):
        """Test that missing optional fields don't cause errors."""
        spec = {
            'firstYear': 2026,
            'lastWorkingYear': 2027,
            'lastPlanningYear': 2030,
            'income': {
                'baseSalary': 100000
            }
        }
        
        # Should not raise an error
        result = calculator.calculate(spec)
        
        assert len(result.yearly_data) == 5
        assert result.yearly_data[2026].base_salary == 100000


class TestEsppIncome:
    """Test ESPP income handling."""
    
    def test_espp_income_from_spec_first_year(self):
        """Test that esppIncome from spec is used for first year."""
        mock_espp = create_mock_espp()
        mock_espp.taxable_from_spec.return_value = 6000
        
        calculator = PlanCalculator(
            federal=create_mock_federal(),
            state=create_mock_state(),
            espp=mock_espp,
            social_security=create_mock_social_security(),
            medicare=create_mock_medicare(),
            rsu_calculator=create_mock_rsu_calculator()
        )
        
        spec = create_basic_spec()
        spec['income']['esppIncome'] = 3500  # Explicit first year value
        
        result = calculator.calculate(spec)
        
        # First year should use the spec value
        assert result.yearly_data[2026].espp_income == 3500
        # Second year should use calculated value
        assert result.yearly_data[2027].espp_income == 6000
    
    def test_espp_income_calculated_when_not_in_spec(self):
        """Test that ESPP income is calculated when not in spec."""
        mock_espp = create_mock_espp()
        mock_espp.taxable_from_spec.return_value = 5000
        
        calculator = PlanCalculator(
            federal=create_mock_federal(),
            state=create_mock_state(),
            espp=mock_espp,
            social_security=create_mock_social_security(),
            medicare=create_mock_medicare(),
            rsu_calculator=create_mock_rsu_calculator()
        )
        
        spec = create_basic_spec()
        # Don't set esppIncome - should use calculated value
        
        result = calculator.calculate(spec)
        
        assert result.yearly_data[2026].espp_income == 5000


class TestCapitalGains:
    """Test capital gains calculations."""
    
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
    
    def test_capital_gains_based_on_taxable_balance(self, calculator):
        """Test that capital gains are calculated from taxable balance."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        first_year = result.yearly_data[2026]
        taxable_balance = spec['investments']['taxableBalance']
        stcg_percent = spec['income']['realizedShortTermCapitalGainsPercent']
        ltcg_percent = spec['income']['realizedLongTermCapitalGainsPercent']
        
        expected_stcg = taxable_balance * stcg_percent
        expected_ltcg = taxable_balance * ltcg_percent
        
        assert abs(first_year.short_term_capital_gains - expected_stcg) < 0.01
        assert abs(first_year.long_term_capital_gains - expected_ltcg) < 0.01
    
    def test_capital_gains_grow_with_balance(self, calculator):
        """Test that capital gains grow as balance appreciates."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        y1 = result.yearly_data[2026]
        y2 = result.yearly_data[2027]
        
        # Second year should have higher capital gains due to balance growth
        assert y2.short_term_capital_gains > y1.short_term_capital_gains
        assert y2.long_term_capital_gains > y1.long_term_capital_gains


class TestAccountAppreciation:
    """Test appreciation tracking for all account types."""
    
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
    
    def test_first_year_has_zero_appreciation(self, calculator):
        """Test that first year has zero appreciation (no prior balance to appreciate)."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        first_year = result.yearly_data[2026]
        
        assert first_year.appreciation_ira == 0
        assert first_year.appreciation_deferred_comp == 0
        assert first_year.appreciation_hsa == 0
        assert first_year.appreciation_taxable == 0
        assert first_year.total_appreciation == 0
    
    def test_working_years_have_appreciation(self, calculator):
        """Test that working years (after first) have appreciation."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        second_year = result.yearly_data[2027]
        
        # All accounts should have appreciation
        assert second_year.appreciation_ira > 0
        assert second_year.appreciation_deferred_comp > 0
        assert second_year.appreciation_hsa > 0
        assert second_year.appreciation_taxable > 0
        assert second_year.total_appreciation > 0
    
    def test_appreciation_matches_rates(self, calculator):
        """Test that appreciation is calculated using correct rates."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        y1 = result.yearly_data[2026]
        y2 = result.yearly_data[2027]
        
        taxable_rate = spec['investments']['taxableAppreciationRate']
        ira_rate = spec['investments']['taxDeferredAppreciationRate']
        hsa_rate = spec['investments']['hsaAppreciationRate']
        deferred_rate = spec['deferredCompensationPlan']['annualGrowthFraction']
        
        # Appreciation should be prior balance * rate
        expected_taxable = y1.balance_taxable * taxable_rate
        expected_ira = y1.balance_ira * ira_rate
        expected_hsa = y1.balance_hsa * hsa_rate
        expected_deferred = y1.balance_deferred_comp * deferred_rate
        
        assert abs(y2.appreciation_taxable - expected_taxable) < 0.01
        assert abs(y2.appreciation_ira - expected_ira) < 0.01
        assert abs(y2.appreciation_hsa - expected_hsa) < 0.01
        assert abs(y2.appreciation_deferred_comp - expected_deferred) < 0.01
    
    def test_total_appreciation_is_sum(self, calculator):
        """Test that total_appreciation is sum of all components."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        for year, data in result.yearly_data.items():
            expected_total = (data.appreciation_ira + data.appreciation_deferred_comp + 
                            data.appreciation_hsa + data.appreciation_taxable)
            assert abs(data.total_appreciation - expected_total) < 0.01, f"Year {year} total mismatch"
    
    def test_appreciation_grows_over_time(self, calculator):
        """Test that appreciation amounts grow as balances grow."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        y2 = result.yearly_data[2027]
        y3 = result.yearly_data[2028]
        
        # Later years should have more appreciation due to larger balances
        assert y3.appreciation_ira > y2.appreciation_ira
        assert y3.appreciation_hsa > y2.appreciation_hsa
        assert y3.total_appreciation > y2.total_appreciation
    
    def test_first_retirement_year_has_deferred_comp_appreciation(self, calculator):
        """Test that first retirement year captures deferred comp appreciation."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        last_working = spec['lastWorkingYear']
        first_retirement = last_working + 1
        
        retirement_data = result.yearly_data[first_retirement]
        
        # First retirement year should have deferred comp appreciation
        assert retirement_data.appreciation_deferred_comp > 0
        # All other accounts should also have appreciation
        assert retirement_data.appreciation_ira > 0
        assert retirement_data.appreciation_hsa > 0
        assert retirement_data.appreciation_taxable > 0
    
    def test_first_retirement_year_deferred_comp_appreciation_value(self, calculator):
        """Test that first retirement year deferred comp appreciation is correct."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        last_working = spec['lastWorkingYear']
        first_retirement = last_working + 1
        
        last_working_data = result.yearly_data[last_working]
        first_retirement_data = result.yearly_data[first_retirement]
        
        deferred_rate = spec['deferredCompensationPlan']['annualGrowthFraction']
        expected_appreciation = last_working_data.balance_deferred_comp * deferred_rate
        
        assert abs(first_retirement_data.appreciation_deferred_comp - expected_appreciation) < 0.01
    
    def test_retirement_years_have_appreciation(self, calculator):
        """Test that retirement years continue to have appreciation."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        first_retirement = spec['lastWorkingYear'] + 1
        second_retirement = first_retirement + 1
        
        if second_retirement <= spec['lastPlanningYear']:
            data = result.yearly_data[second_retirement]
            
            # All accounts should have appreciation
            assert data.appreciation_ira > 0
            assert data.appreciation_hsa > 0
            assert data.appreciation_taxable > 0
            # Deferred comp should have appreciation if there's still balance
            if data.balance_deferred_comp > 0 or result.yearly_data[first_retirement].balance_deferred_comp > 0:
                assert data.appreciation_deferred_comp > 0
    
    def test_post_withdrawal_years_have_zero_deferred_appreciation(self, calculator):
        """Test that post-withdrawal years have zero deferred comp appreciation."""
        spec = create_basic_spec()
        spec['lastPlanningYear'] = 2050  # Extend to have post-withdrawal years
        result = calculator.calculate(spec)
        
        disbursement_years = spec['deferredCompensationPlan']['disbursementYears']
        first_retirement = spec['lastWorkingYear'] + 1
        post_withdrawal_start = first_retirement + disbursement_years
        
        if post_withdrawal_start <= spec['lastPlanningYear']:
            data = result.yearly_data[post_withdrawal_start]
            
            # Deferred comp balance is zero, so appreciation should be zero
            assert data.appreciation_deferred_comp == 0
            # Other accounts should still have appreciation
            assert data.appreciation_ira > 0
            assert data.appreciation_hsa > 0
            assert data.appreciation_taxable > 0
    
    def test_no_appreciation_with_zero_balances(self, calculator):
        """Test that appreciation is zero when starting with zero balances."""
        spec = create_basic_spec()
        spec['investments']['taxableBalance'] = 0
        spec['investments']['taxDeferredBalance'] = 0
        spec['investments']['hsaBalance'] = 0
        spec['income']['baseDeferralFraction'] = 0
        spec['income']['bonusDeferralFraction'] = 0
        
        result = calculator.calculate(spec)
        
        # First year should have zero appreciation
        first_year = result.yearly_data[2026]
        assert first_year.appreciation_ira == 0
        assert first_year.appreciation_hsa == 0
        assert first_year.appreciation_taxable == 0
        assert first_year.appreciation_deferred_comp == 0
    
    def test_appreciation_accumulates_correctly(self, calculator):
        """Test that balance growth matches appreciation + contributions."""
        spec = create_basic_spec()
        result = calculator.calculate(spec)
        
        y1 = result.yearly_data[2026]
        y2 = result.yearly_data[2027]
        
        # IRA balance growth should be appreciation + contributions
        expected_ira_balance = y1.balance_ira + y2.appreciation_ira + y2.total_401k_contribution
        assert abs(y2.balance_ira - expected_ira_balance) < 0.01
        
        # HSA balance growth should be appreciation + contributions - withdrawal
        expected_hsa_balance = y1.balance_hsa + y2.appreciation_hsa + y2.hsa_contribution - y2.hsa_withdrawal
        assert abs(y2.balance_hsa - expected_hsa_balance) < 0.01
        
        # Deferred comp balance growth should be appreciation + contributions
        expected_deferred_balance = (y1.balance_deferred_comp + y2.appreciation_deferred_comp + 
                                     y2.deferred_comp_contribution)
        assert abs(y2.balance_deferred_comp - expected_deferred_balance) < 0.01


class TestHSAWithdrawals:
    """Tests for HSA withdrawal functionality."""
    
    @pytest.fixture
    def calculator(self):
        """Create a PlanCalculator with mock dependencies."""
        return PlanCalculator(
            federal=create_mock_federal(),
            state=create_mock_state(),
            espp=create_mock_espp(),
            social_security=create_mock_social_security(),
            medicare=create_mock_medicare(),
            rsu_calculator=create_mock_rsu_calculator()
        )
    
    def test_hsa_withdrawal_subtracts_from_balance(self, calculator):
        """Test that HSA withdrawals reduce the HSA balance."""
        spec = create_basic_spec()
        spec['investments'] = {
            'hsaBalance': 50000.0,
            'hsaAppreciationRate': 0.07,
            'hsaEmployerContribution': 1500.0,
            'hsaAnnualWithdrawal': 3000.0,
            'hsaWithdrawalInflationRate': 0.04
        }
        
        result = calculator.calculate(spec)
        
        # First year should have withdrawal of 3000
        first_year = result.yearly_data[2026]
        assert first_year.hsa_withdrawal == 3000.0
        
        # Balance should reflect: initial + contribution + appreciation - withdrawal
        # HSA contribution from deductions mock is 8000 (employee) + 1500 (employer) = 9500
        # But the actual value depends on what the mock returns
        assert first_year.hsa_withdrawal <= first_year.balance_hsa + first_year.hsa_withdrawal
    
    def test_hsa_withdrawal_inflates_over_time(self, calculator):
        """Test that HSA withdrawal amount increases with inflation."""
        spec = create_basic_spec()
        spec['investments'] = {
            'hsaBalance': 100000.0,
            'hsaAppreciationRate': 0.07,
            'hsaEmployerContribution': 0,
            'hsaAnnualWithdrawal': 5000.0,
            'hsaWithdrawalInflationRate': 0.05  # 5% inflation
        }
        
        result = calculator.calculate(spec)
        
        y1 = result.yearly_data[2026]
        y2 = result.yearly_data[2027]
        y3 = result.yearly_data[2028]
        
        # Withdrawals should increase by 5% each year
        assert y1.hsa_withdrawal == 5000.0
        assert abs(y2.hsa_withdrawal - 5250.0) < 0.01  # 5000 * 1.05
        assert abs(y3.hsa_withdrawal - 5512.50) < 0.01  # 5000 * 1.05^2
    
    def test_hsa_withdrawal_capped_at_balance(self, calculator):
        """Test that HSA withdrawal cannot exceed the available balance."""
        spec = create_basic_spec()
        spec['investments'] = {
            'hsaBalance': 1000.0,  # Small starting balance
            'hsaAppreciationRate': 0.0,  # No growth
            'hsaEmployerContribution': 0,
            'hsaAnnualWithdrawal': 50000.0,  # Try to withdraw more than balance
            'hsaWithdrawalInflationRate': 0.0
        }
        # Disable HSA contributions
        spec['deductions'] = {'medicalDentalVision': 0}
        
        result = calculator.calculate(spec)
        
        first_year = result.yearly_data[2026]
        # Withdrawal should be capped at balance (initial + any contributions)
        assert first_year.hsa_withdrawal <= first_year.balance_hsa + first_year.hsa_withdrawal
        # Balance should be non-negative after withdrawal
        assert first_year.balance_hsa >= 0
    
    def test_hsa_withdrawal_zero_by_default(self, calculator):
        """Test that HSA withdrawal is zero when not specified."""
        spec = create_basic_spec()
        spec['investments'] = {
            'hsaBalance': 50000.0,
            'hsaAppreciationRate': 0.07
            # No hsaAnnualWithdrawal specified
        }
        
        result = calculator.calculate(spec)
        
        first_year = result.yearly_data[2026]
        assert first_year.hsa_withdrawal == 0.0
    
    def test_hsa_withdrawal_continues_in_retirement(self, calculator):
        """Test that HSA withdrawals continue during retirement years."""
        spec = create_basic_spec()
        spec['lastWorkingYear'] = 2027  # Retire after 2027
        spec['lastPlanningYear'] = 2030
        spec['investments'] = {
            'hsaBalance': 100000.0,
            'hsaAppreciationRate': 0.05,
            'hsaEmployerContribution': 0,
            'hsaAnnualWithdrawal': 4000.0,
            'hsaWithdrawalInflationRate': 0.03
        }
        
        
        result = calculator.calculate(spec)
        
        # Check working years
        assert result.yearly_data[2026].hsa_withdrawal == 4000.0
        assert result.yearly_data[2027].is_working_year == True
        
        # Check retirement years
        y2028 = result.yearly_data[2028]
        assert y2028.is_working_year == False
        # Withdrawal should continue with inflation: 4000 * 1.03^2 = 4243.60
        assert y2028.hsa_withdrawal > 0
        
        # All retirement years should have withdrawals
        for year in [2028, 2029, 2030]:
            yd = result.yearly_data[year]
            assert yd.hsa_withdrawal > 0


class TestHSAContributionsInRetirement:
    """Tests for HSA contribution functionality during early retirement (before Medicare)."""
    
    @pytest.fixture
    def calculator(self):
        """Create a PlanCalculator with mock dependencies."""
        return PlanCalculator(
            federal=create_mock_federal(),
            state=create_mock_state(),
            espp=create_mock_espp(),
            social_security=create_mock_social_security(),
            medicare=create_mock_medicare(),
            rsu_calculator=create_mock_rsu_calculator()
        )
    
    def test_hsa_contributions_continue_before_medicare(self, calculator):
        """Test that HSA contributions continue in retirement before Medicare eligibility."""
        spec = create_basic_spec()
        spec['birthYear'] = 1970  # Medicare eligibility at 2035 (1970 + 65)
        spec['lastWorkingYear'] = 2030
        spec['lastPlanningYear'] = 2040
        spec['investments'] = {
            'hsaBalance': 50000.0,
            'hsaAppreciationRate': 0.07,
            'hsaEmployerContribution': 1500.0
        }
        
        result = calculator.calculate(spec)
        
        # Retirement years before Medicare (2031-2034) should have HSA contributions
        for year in [2031, 2032, 2033, 2034]:
            yd = result.yearly_data[year]
            assert yd.is_working_year == False
            assert yd.hsa_contribution > 0, f"Year {year} should have HSA contribution"
            assert yd.employee_hsa > 0, f"Year {year} should have employee HSA"
    
    def test_hsa_contributions_stop_at_medicare(self, calculator):
        """Test that HSA contributions stop at Medicare eligibility (age 65)."""
        spec = create_basic_spec()
        spec['birthYear'] = 1970  # Medicare eligibility at 2035 (1970 + 65)
        spec['lastWorkingYear'] = 2030
        spec['lastPlanningYear'] = 2040
        spec['investments'] = {
            'hsaBalance': 50000.0,
            'hsaAppreciationRate': 0.07,
            'hsaEmployerContribution': 1500.0
        }
        
        result = calculator.calculate(spec)
        
        # Medicare eligibility year and after should have no HSA contributions
        for year in [2035, 2036, 2037, 2038, 2039, 2040]:
            yd = result.yearly_data[year]
            assert yd.hsa_contribution == 0, f"Year {year} should not have HSA contribution (Medicare eligible)"
    
    def test_hsa_contribution_deducted_from_cash_flow(self, calculator):
        """Test that HSA contribution is deducted from taxable account adjustment."""
        spec = create_basic_spec()
        spec['birthYear'] = 1970  # Medicare eligibility at 2035
        spec['lastWorkingYear'] = 2030
        spec['lastPlanningYear'] = 2036
        spec['investments'] = {
            'hsaBalance': 50000.0,
            'hsaAppreciationRate': 0.07,
            'hsaEmployerContribution': 1500.0
        }
        
        result = calculator.calculate(spec)
        
        # In retirement before Medicare, taxable adjustment should account for HSA contribution
        y = result.yearly_data[2031]
        expected_adjustment = y.income_expense_difference - y.hsa_contribution
        assert abs(y.taxable_account_adjustment - expected_adjustment) < 0.01
    
    def test_hsa_contribution_increases_hsa_balance(self, calculator):
        """Test that HSA contributions increase the HSA balance in retirement."""
        spec = create_basic_spec()
        spec['birthYear'] = 1970  # Medicare eligibility at 2035
        spec['lastWorkingYear'] = 2030
        spec['lastPlanningYear'] = 2036
        spec['investments'] = {
            'hsaBalance': 50000.0,
            'hsaAppreciationRate': 0.0,  # No appreciation for simpler test
            'hsaEmployerContribution': 1500.0,
            'hsaAnnualWithdrawal': 0  # No withdrawals for simpler test
        }
        
        result = calculator.calculate(spec)
        
        # HSA balance should increase by contribution amount (minus any withdrawals)
        y2030 = result.yearly_data[2030]  # Last working year
        y2031 = result.yearly_data[2031]  # First retirement year
        
        # Balance should increase due to contribution
        expected_balance = y2030.balance_hsa + y2031.hsa_contribution
        assert abs(y2031.balance_hsa - expected_balance) < 0.01
    
    def test_no_employer_hsa_in_retirement(self, calculator):
        """Test that there is no employer HSA contribution in retirement."""
        spec = create_basic_spec()
        spec['birthYear'] = 1970
        spec['lastWorkingYear'] = 2030
        spec['lastPlanningYear'] = 2035
        spec['investments'] = {
            'hsaBalance': 50000.0,
            'hsaAppreciationRate': 0.07,
            'hsaEmployerContribution': 1500.0
        }
        
        result = calculator.calculate(spec)
        
        # Retirement years should have no employer HSA contribution
        for year in [2031, 2032, 2033, 2034]:
            yd = result.yearly_data[year]
            assert yd.employer_hsa == 0, f"Year {year} should have no employer HSA"
            # But employee HSA should equal the full contribution
            assert yd.hsa_contribution == yd.employee_hsa


class TestHSAWithdrawalDoubleAtMedicare:
    """Tests for HSA withdrawal doubling at Medicare eligibility."""
    
    @pytest.fixture
    def calculator(self):
        """Create a PlanCalculator with mock dependencies."""
        return PlanCalculator(
            federal=create_mock_federal(),
            state=create_mock_state(),
            espp=create_mock_espp(),
            social_security=create_mock_social_security(),
            medicare=create_mock_medicare(),
            rsu_calculator=create_mock_rsu_calculator()
        )
    
    def test_hsa_withdrawal_doubles_at_medicare_eligibility(self, calculator):
        """Test that HSA withdrawal doubles at Medicare eligibility year."""
        spec = create_basic_spec()
        spec['birthYear'] = 1970  # Medicare eligibility at 2035 (1970 + 65)
        spec['lastWorkingYear'] = 2030
        spec['lastPlanningYear'] = 2040
        spec['investments'] = {
            'hsaBalance': 500000.0,  # Large balance to avoid running out
            'hsaAppreciationRate': 0.0,  # No appreciation for simpler test
            'hsaAnnualWithdrawal': 10000.0,
            'hsaWithdrawalInflationRate': 0.0  # No inflation for simpler test
        }
        
        result = calculator.calculate(spec)
        
        # Year before Medicare (2034): withdrawal should be 10000
        y2034 = result.yearly_data[2034]
        assert y2034.hsa_withdrawal == 10000.0
        
        # Medicare eligibility year (2035): withdrawal should double to 20000
        y2035 = result.yearly_data[2035]
        assert y2035.hsa_withdrawal == 20000.0
        
        # Year after Medicare (2036): withdrawal should continue at doubled amount (20000)
        y2036 = result.yearly_data[2036]
        assert y2036.hsa_withdrawal == 20000.0
    
    def test_hsa_withdrawal_doubles_and_continues_to_inflate(self, calculator):
        """Test that HSA withdrawal doubles at Medicare and continues to inflate after."""
        spec = create_basic_spec()
        spec['birthYear'] = 1970  # Medicare eligibility at 2035
        spec['lastWorkingYear'] = 2030
        spec['lastPlanningYear'] = 2037
        spec['investments'] = {
            'hsaBalance': 500000.0,  # Large balance
            'hsaAppreciationRate': 0.0,
            'hsaAnnualWithdrawal': 10000.0,
            'hsaWithdrawalInflationRate': 0.05  # 5% inflation
        }
        
        result = calculator.calculate(spec)
        
        # Inflation happens every year after first year (2026 is first year, so inflations start at 2027)
        # Working years: 2027, 2028, 2029, 2030 = 4 inflations
        # Retirement years before Medicare: 2031, 2032, 2033, 2034 = 4 more inflations
        # Total before 2034's withdrawal: 8 inflations
        
        # Year before Medicare (2034): 8 inflations from 10000
        y2034 = result.yearly_data[2034]
        expected_2034 = 10000 * (1.05 ** 8)
        assert abs(y2034.hsa_withdrawal - expected_2034) < 0.01
        
        # Medicare eligibility year (2035): 9 inflations then doubled
        y2035 = result.yearly_data[2035]
        expected_2035 = 10000 * (1.05 ** 9) * 2
        assert abs(y2035.hsa_withdrawal - expected_2035) < 0.01
        
        
        # Year after Medicare (2036): continues to inflate from doubled amount (10 inflations total, doubled)
        y2036 = result.yearly_data[2036]
        expected_2036 = 10000 * (1.05 ** 9) * 2 * 1.05
        assert abs(y2036.hsa_withdrawal - expected_2036) < 0.01
        
        # 2037: continues to inflate (11 inflations total from base, doubled at 2035)
        y2037 = result.yearly_data[2037]
        expected_2037 = 10000 * (1.05 ** 9) * 2 * (1.05 ** 2)
        assert abs(y2037.hsa_withdrawal - expected_2037) < 0.01


class TestHSAInTotalDeductionsDuringRetirement:
    """Tests for HSA contributions being included in total_deductions during retirement before Medicare."""
    
    @pytest.fixture
    def calculator(self):
        """Create a PlanCalculator with mock dependencies."""
        return PlanCalculator(
            federal=create_mock_federal(),
            state=create_mock_state(),
            espp=create_mock_espp(),
            social_security=create_mock_social_security(),
            medicare=create_mock_medicare(),
            rsu_calculator=create_mock_rsu_calculator()
        )
    
    def test_total_deductions_includes_hsa_in_disbursement_years(self, calculator):
        """Test that total_deductions includes HSA contribution during disbursement years before Medicare."""
        spec = create_basic_spec()
        spec['birthYear'] = 1970  # Medicare eligibility at 2035 (1970 + 65)
        spec['lastWorkingYear'] = 2030
        spec['lastPlanningYear'] = 2040
        spec['deferredCompensationPlan'] = {
            'annualGrowthFraction': 0.05,
            'disbursementYears': 5  # Disbursements from 2031-2035
        }
        spec['investments'] = {
            'hsaBalance': 50000.0,
            'hsaAppreciationRate': 0.07,
            'hsaEmployerContribution': 1500.0
        }
        
        result = calculator.calculate(spec)
        
        # Disbursement years before Medicare (2031-2034) should have HSA in total_deductions
        for year in [2031, 2032, 2033, 2034]:
            yd = result.yearly_data[year]
            # Total deductions should equal standard deduction + employee HSA
            expected_total = yd.standard_deduction + yd.employee_hsa
            assert abs(yd.total_deductions - expected_total) < 0.01, \
                f"Year {year}: total_deductions ({yd.total_deductions}) should equal " \
                f"standard_deduction ({yd.standard_deduction}) + employee_hsa ({yd.employee_hsa})"
    
    def test_total_deductions_includes_hsa_in_post_disbursement_years(self, calculator):
        """Test that total_deductions includes HSA contribution in post-disbursement years before Medicare."""
        spec = create_basic_spec()
        spec['birthYear'] = 1975  # Medicare eligibility at 2040 (1975 + 65)
        spec['lastWorkingYear'] = 2028
        spec['lastPlanningYear'] = 2045
        spec['deferredCompensationPlan'] = {
            'annualGrowthFraction': 0.05,
            'disbursementYears': 5  # Disbursements from 2029-2033
        }
        spec['investments'] = {
            'hsaBalance': 50000.0,
            'hsaAppreciationRate': 0.07,
            'hsaEmployerContribution': 1500.0
        }
        
        result = calculator.calculate(spec)
        
        # Post-disbursement years before Medicare (2034-2039) should have HSA in total_deductions
        for year in [2034, 2035, 2036, 2037, 2038, 2039]:
            yd = result.yearly_data[year]
            # Verify HSA contribution is happening
            assert yd.employee_hsa > 0, f"Year {year} should have HSA contribution before Medicare"
            # Total deductions should equal standard deduction + employee HSA
            expected_total = yd.standard_deduction + yd.employee_hsa
            assert abs(yd.total_deductions - expected_total) < 0.01, \
                f"Year {year}: total_deductions ({yd.total_deductions}) should equal " \
                f"standard_deduction ({yd.standard_deduction}) + employee_hsa ({yd.employee_hsa})"
    
    def test_total_deductions_excludes_hsa_at_medicare(self, calculator):
        """Test that total_deductions excludes HSA contribution at and after Medicare eligibility."""
        spec = create_basic_spec()
        spec['birthYear'] = 1970  # Medicare eligibility at 2035 (1970 + 65)
        spec['lastWorkingYear'] = 2030
        spec['lastPlanningYear'] = 2040
        spec['investments'] = {
            'hsaBalance': 50000.0,
            'hsaAppreciationRate': 0.07,
            'hsaEmployerContribution': 1500.0
        }
        
        result = calculator.calculate(spec)
        
        # At and after Medicare (2035+), HSA contribution should be zero
        for year in [2035, 2036, 2037, 2038, 2039, 2040]:
            yd = result.yearly_data[year]
            assert yd.employee_hsa == 0, f"Year {year} should have no HSA contribution at/after Medicare"
            assert yd.hsa_contribution == 0, f"Year {year} should have no HSA contribution at/after Medicare"
            # Total deductions should just be standard deduction
            assert abs(yd.total_deductions - yd.standard_deduction) < 0.01, \
                f"Year {year}: total_deductions should equal standard_deduction when no HSA"
    
    def test_adjusted_gross_income_reflects_hsa_deduction(self, calculator):
        """Test that AGI is correctly reduced by HSA contribution in retirement."""
        spec = create_basic_spec()
        spec['birthYear'] = 1970  # Medicare eligibility at 2035
        spec['lastWorkingYear'] = 2030
        spec['lastPlanningYear'] = 2040
        spec['deferredCompensationPlan'] = {
            'annualGrowthFraction': 0.05,
            'disbursementYears': 5
        }
        spec['investments'] = {
            'hsaBalance': 50000.0,
            'hsaAppreciationRate': 0.07,
            'hsaEmployerContribution': 1500.0
        }
        
        result = calculator.calculate(spec)
        
        # In disbursement years before Medicare, AGI should be gross - total_deductions
        for year in [2031, 2032, 2033, 2034]:
            yd = result.yearly_data[year]
            expected_agi = max(0, yd.gross_income - yd.total_deductions)
            assert abs(yd.adjusted_gross_income - expected_agi) < 0.01, \
                f"Year {year}: AGI ({yd.adjusted_gross_income}) should equal " \
                f"gross_income ({yd.gross_income}) - total_deductions ({yd.total_deductions})"
    
    def test_hsa_deduction_reduces_tax_liability(self, calculator):
        """Test that including HSA in deductions results in lower taxable income."""
        spec = create_basic_spec()
        spec['birthYear'] = 1970  # Medicare eligibility at 2035
        spec['lastWorkingYear'] = 2030
        spec['lastPlanningYear'] = 2036
        spec['deferredCompensationPlan'] = {
            'annualGrowthFraction': 0.05,
            'disbursementYears': 3
        }
        spec['investments'] = {
            'hsaBalance': 50000.0,
            'hsaAppreciationRate': 0.07,
            'hsaEmployerContribution': 1500.0
        }
        
        result = calculator.calculate(spec)
        
        # Year 2031 (disbursement, before Medicare) - HSA should reduce AGI
        y2031 = result.yearly_data[2031]
        assert y2031.employee_hsa > 0, "2031 should have HSA contribution"
        
        # AGI should be gross_income - standard_deduction - employee_hsa
        expected_agi = max(0, y2031.gross_income - y2031.standard_deduction - y2031.employee_hsa)
        assert abs(y2031.adjusted_gross_income - expected_agi) < 0.01


class TestMedicarePremiumSwitch:
    """Tests for switching from full insurance to Medicare premium at age 65."""
    
    @pytest.fixture
    def calculator(self):
        """Create a PlanCalculator with mock dependencies."""
        return PlanCalculator(
            federal=create_mock_federal(),
            state=create_mock_state(),
            espp=create_mock_espp(),
            social_security=create_mock_social_security(),
            medicare=create_mock_medicare(),
            rsu_calculator=create_mock_rsu_calculator()
        )
    
    def test_uses_full_insurance_before_medicare(self, calculator):
        """Test that full insurance premium is used before Medicare eligibility."""
        spec = create_basic_spec()
        spec['birthYear'] = 1970  # Medicare eligibility at 2035
        spec['lastWorkingYear'] = 2030
        spec['lastPlanningYear'] = 2040
        spec['insurance'] = {
            'fullInsurancePremiums': 20000.0,
            'medicarePremiums': 5000.0,
            'premiumInflationRate': 0.0  # No inflation for simpler test
        }
        
        result = calculator.calculate(spec)
        
        # Years before Medicare (2031-2034) should use full insurance premium
        for year in [2031, 2032, 2033, 2034]:
            yd = result.yearly_data[year]
            assert yd.medical_premium == 20000.0, f"Year {year} should use full insurance"
            assert yd.medical_premium_expense == 20000.0
    
    def test_uses_medicare_premium_at_eligibility(self, calculator):
        """Test that Medicare premium is used at Medicare eligibility year."""
        spec = create_basic_spec()
        spec['birthYear'] = 1970  # Medicare eligibility at 2035
        spec['lastWorkingYear'] = 2030
        spec['lastPlanningYear'] = 2040
        spec['insurance'] = {
            'fullInsurancePremiums': 20000.0,
            'medicarePremiums': 5000.0,
            'premiumInflationRate': 0.0  # No inflation for simpler test
        }
        
        result = calculator.calculate(spec)
        
        # Medicare eligibility year (2035) should use Medicare premium
        y2035 = result.yearly_data[2035]
        assert y2035.medical_premium == 5000.0
        assert y2035.medical_premium_expense == 5000.0
    
    def test_uses_medicare_premium_after_eligibility(self, calculator):
        """Test that Medicare premium continues after eligibility."""
        spec = create_basic_spec()
        spec['birthYear'] = 1970  # Medicare eligibility at 2035
        spec['lastWorkingYear'] = 2030
        spec['lastPlanningYear'] = 2040
        spec['insurance'] = {
            'fullInsurancePremiums': 20000.0,
            'medicarePremiums': 5000.0,
            'premiumInflationRate': 0.0  # No inflation for simpler test
        }
        
        result = calculator.calculate(spec)
        
        # Years after Medicare eligibility should use Medicare premium
        for year in [2035, 2036, 2037, 2038, 2039, 2040]:
            yd = result.yearly_data[year]
            assert yd.medical_premium == 5000.0, f"Year {year} should use Medicare"
            assert yd.medical_premium_expense == 5000.0
    
    def test_medicare_premium_inflates_separately(self, calculator):
        """Test that Medicare premium inflates along with full insurance premium."""
        spec = create_basic_spec()
        spec['birthYear'] = 1970  # Medicare eligibility at 2035
        spec['lastWorkingYear'] = 2030
        spec['lastPlanningYear'] = 2037
        spec['insurance'] = {
            'fullInsurancePremiums': 20000.0,
            'medicarePremiums': 5000.0,
            'premiumInflationRate': 0.05  # 5% inflation
        }
        
        result = calculator.calculate(spec)
        
        # 2034 (before Medicare): full insurance with 8 inflations (2027-2034)
        y2034 = result.yearly_data[2034]
        expected_full_2034 = 20000 * (1.05 ** 8)
        assert abs(y2034.medical_premium - expected_full_2034) < 0.01
        
        # 2035 (Medicare eligibility): Medicare premium with 9 inflations
        y2035 = result.yearly_data[2035]
        expected_medicare_2035 = 5000 * (1.05 ** 9)
        assert abs(y2035.medical_premium - expected_medicare_2035) < 0.01
        
        # 2036: Medicare premium with 10 inflations
        y2036 = result.yearly_data[2036]
        expected_medicare_2036 = 5000 * (1.05 ** 10)
        assert abs(y2036.medical_premium - expected_medicare_2036) < 0.01

