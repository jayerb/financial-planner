import pytest
from unittest.mock import MagicMock
from calc.plan_calculator import PlanCalculator
from model.PlanData import YearlyData

class TestSSLimitCheck:
    """Test that Social Security tax calculations respect the annual limit."""
    
    @pytest.fixture
    def calculator(self):
        """Create a calculator instance with mocked dependencies."""
        fed = MagicMock()
        state = MagicMock()
        espp = MagicMock()
        ss = MagicMock()
        medicare = MagicMock()
        rsu = MagicMock()
        
        # Setup SS data
        # 2026 limit: 184,500
        # Rate: 6.2%
        self.ss_limit = 184500
        self.ss_rate = 0.062
        
        ss.get_data_for_year.return_value = {
            "maximumTaxedIncome": self.ss_limit,
            "employeePortion": self.ss_rate,
            "maPFML": 0.0
        }
        # Set wage_base attribute for paycheck calculations
        ss.wage_base = self.ss_limit
        
        # Setup Medicare data
        medicare.medicare_rate = 0.0145
        medicare.surcharge_threshold = 200000
        medicare.surcharge_rate = 0.009
        
        calc = PlanCalculator(fed, state, espp, ss, medicare, rsu)
        return calc
    
    def test_ss_tax_sum_matches_limit_bonus_after_limit(self, calculator):
        """
        Verify SS tax when bonus is paid AFTER the limit is reached.
        Bonus SS tax should be 0.
        """
        yd = YearlyData(year=2026, is_working_year=True)
        
        # Scenario:
        # Base: 200,000 (7,692.31 per period over 26 periods)
        # Bonus: 50,000 (paid at period 26, after pay_period_preceding_bonus=25)
        # Limit: 184,500
        # Limit reached at period 24 (200k/26 * 24 = 184,615.38 > 184,500)
        # Expected: Bonus paid after limit, so bonus SS = 0
        
        yd.base_salary = 200000
        yd.bonus = 50000
        yd.earned_income_for_fica = 250000
        yd.gross_income = 250000
        
        # Required fields
        yd.medical_dental_vision = 0
        yd.base_deferral = 0
        yd.bonus_deferral = 0
        yd.employee_401k_contribution = 0
        yd.employee_hsa = 0
        yd.marginal_bracket = 0.24
        yd.state_tax = 10000
        
        # Run calculation
        calculator._calculate_paycheck_take_home(yd, 2026, 0, 26, pay_period_preceding_bonus=25)
        
        regular_ss_per_check = yd.paycheck_social_security
        bonus_ss = yd.bonus_paycheck_social_security
        limit_period = yd.pay_period_ss_limit_reached
        
        max_ss_tax = self.ss_limit * self.ss_rate
        
        print(f"\nDebug Info (Bonus After Limit):")
        print(f"Regular SS per check: {regular_ss_per_check}")
        print(f"Bonus SS: {bonus_ss}")
        print(f"Limit Period: {limit_period}")
        print(f"Max SS Tax: {max_ss_tax}")
        
        # Bonus is paid at period 26 (after pay_period_preceding_bonus=25)
        # Limit is reached at period ~24
        # So bonus should have 0 SS tax
        bonus_payment_period = 25 + 1
        assert bonus_payment_period > limit_period, \
            f"Test expects bonus at period {bonus_payment_period} after limit at period {limit_period}"
        assert bonus_ss == 0.0, \
            f"Bonus paid after limit should have 0 SS tax, got {bonus_ss}"
        
        # Total SS paid should be approximately the max (from regular paychecks only)
        # Periods 1 through limit_period-1 pay full SS
        # Period limit_period pays partial SS (to reach the limit)
        # Periods after limit_period pay no SS
        # We approximate by checking that SS from limit_period full periods doesn't exceed max by more than one period
        total_ss_paid_upper_bound = limit_period * regular_ss_per_check
        assert total_ss_paid_upper_bound <= max_ss_tax + regular_ss_per_check, \
            f"SS paid exceeds max! Upper bound {total_ss_paid_upper_bound} vs Max {max_ss_tax}"

    def test_ss_tax_sum_matches_limit_bonus_pushes_over(self, calculator):
        """
        Verify SS tax when bonus PUSHES income over the limit.
        Bonus SS tax should be partial.
        """
        yd = YearlyData(year=2026, is_working_year=True)
        
        # Scenario:
        # Base salary: $130,000 (paid evenly over 26 periods = $5,000 per period)
        # Bonus: $150,000 (paid at period 11, after pay_period_preceding_bonus=10)
        # Social Security limit: $184,500
        # At period 11: cumulative = $5,000 * 11 + $150,000 = $205,000 > $184,500
        # Expected: Bonus pushes income over limit, so bonus SS is partial
        # Regular checks 1-11: $5,000 * 11 = $55,000
        # Remaining SS capacity at bonus: $184,500 - $55,000 = $129,500
        # Bonus SS tax: $129,500 * 0.062 = $8,029
        
        yd.base_salary = 130000
        yd.bonus = 150000
        yd.earned_income_for_fica = 280000
        yd.gross_income = 280000
        
        # Required fields
        yd.medical_dental_vision = 0
        yd.base_deferral = 0
        yd.bonus_deferral = 0
        yd.employee_401k_contribution = 0
        yd.employee_hsa = 0
        yd.marginal_bracket = 0.24
        yd.state_tax = 10000
        
        calculator._calculate_paycheck_take_home(yd, 2026, 0, 26, pay_period_preceding_bonus=10)
        
        regular_ss_per_check = yd.paycheck_social_security
        bonus_ss = yd.bonus_paycheck_social_security
        limit_period = yd.pay_period_ss_limit_reached
        
        max_ss_tax = self.ss_limit * self.ss_rate
        
        print(f"\nDebug Info (Bonus Pushes Over):")
        print(f"Regular SS per check: {regular_ss_per_check}")
        print(f"Bonus SS: {bonus_ss}")
        print(f"Limit Period: {limit_period}")
        print(f"Max SS Tax: {max_ss_tax}")
        
        # Bonus is paid at period 11 (after pay_period_preceding_bonus=10)
        # This bonus pushes income over the limit
        # So bonus should have partial SS tax
        bonus_payment_period = 10 + 1
        assert bonus_payment_period == limit_period, \
            f"Test expects bonus at period {bonus_payment_period} to push over limit at period {limit_period}"
        assert 0 < bonus_ss < yd.bonus * self.ss_rate, \
            f"Bonus should have partial SS tax, got {bonus_ss}"
        
        # Total SS paid should equal the max (within rounding)
        # Regular paychecks 1 through bonus_payment_period (period 11) each pay full SS
        # At period 11, the bonus pays partial SS to reach the limit
        # Regular paychecks after period 11 pay no SS (limit already reached)
        # Total SS = (regular checks 1-11) * regular_ss + bonus_ss ≈ max_ss_tax
        total_ss_from_regular_checks = bonus_payment_period * regular_ss_per_check
        total_ss_paid = total_ss_from_regular_checks + bonus_ss
        
        # Allow small rounding error (within $1)
        assert abs(total_ss_paid - max_ss_tax) < 1.0, \
            f"Total SS paid {total_ss_paid} should equal max {max_ss_tax}"
