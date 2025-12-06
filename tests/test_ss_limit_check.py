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
        # Base: 200,000 (7,692 per period)
        # Bonus: 50,000 (paid at period 25)
        # Limit: 160,200
        # Limit reached at period ~21 (200k/26 * 21 = 161k)
        
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
        
        ss_paid_before_limit_check = (limit_period - 1) * regular_ss_per_check + bonus_ss
        
        print(f"Paid before limit check: {ss_paid_before_limit_check}")
        
        # This should fail if bonus_ss is calculated on full bonus
        assert ss_paid_before_limit_check <= max_ss_tax + 1.0, \
            f"Overpaying SS Tax! Paid {ss_paid_before_limit_check} vs Max {max_ss_tax}"

    def test_ss_tax_sum_matches_limit_bonus_pushes_over(self, calculator):
        """
        Verify SS tax when bonus PUSHES income over the limit.
        Bonus SS tax should be partial.
        """
        yd = YearlyData(year=2026, is_working_year=True)
        
        # Scenario:
        # Base: 130,000 (5,000 per period)
        # Bonus: 100,000 (paid at period 10)
        # Limit: 184,500
        
        # Period 1-9: 45k
        # Period 10: 45k + 5k + 100k = 150k. (Under limit)
        # Wait, I need bonus to push OVER limit.
        
        # Base 130k. Bonus 100k.
        # Period 10 cumulative before bonus: 9*5k + 5k = 50k.
        # With bonus: 150k. Still under 160.2k.
        
        # Let's try Base 130k. Bonus 150k.
        # Period 10: 50k + 150k = 200k. Over limit.
        # Limit reached at period 10.
        
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
        
        # If limit reached at period 10 (bonus period), then
        # periods 1-9 paid full SS.
        # Period 10 regular check paid full SS (since 50k < 160k).
        # Bonus paid partial SS.
        
        # So total paid = 10 * regular_ss + bonus_ss
        # This should be close to max_ss_tax
        
        total_paid = limit_period * regular_ss_per_check + bonus_ss
        
        # If bonus_ss is full (150k * 6.2% = 9300), total will be huge.
        # 10 * 310 + 9300 = 3100 + 9300 = 12400.
        # Max tax = 9932.
        
        assert total_paid <= max_ss_tax + 1.0, \
            f"Overpaying SS Tax! Paid {total_paid} vs Max {max_ss_tax}"
