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
        
        # HSA balance growth should be appreciation + contributions
        expected_hsa_balance = y1.balance_hsa + y2.appreciation_hsa + y2.hsa_contribution
        assert abs(y2.balance_hsa - expected_hsa_balance) < 0.01
        
        # Deferred comp balance growth should be appreciation + contributions
        expected_deferred_balance = (y1.balance_deferred_comp + y2.appreciation_deferred_comp + 
                                     y2.deferred_comp_contribution)
        assert abs(y2.balance_deferred_comp - expected_deferred_balance) < 0.01
