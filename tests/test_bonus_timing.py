import os
import sys
import pytest
from unittest.mock import MagicMock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from calc.plan_calculator import PlanCalculator
from model.PlanData import YearlyData

class TestBonusPayPeriodImpact:
    """Test how bonus pay period affects SS limit and Medicare surcharge timing."""
    
    @pytest.fixture
    def calculator(self):
        """Create a calculator instance with mocked dependencies."""
        # Mock dependencies
        fed = MagicMock()
        state = MagicMock()
        espp = MagicMock()
        ss = MagicMock()
        medicare = MagicMock()
        rsu = MagicMock()
        
        # Setup SS data
        ss.get_data_for_year.return_value = {
            "maximumTaxedIncome": 160200,  # 2023 limit for example
            "employeePortion": 0.062,
            "maPFML": 0.0
        }
        
        # Setup Medicare data
        medicare.medicare_rate = 0.0145
        medicare.surcharge_threshold = 200000
        medicare.surcharge_rate = 0.009
        
        calc = PlanCalculator(fed, state, espp, ss, medicare, rsu)
        return calc
    
    def test_bonus_accelerates_ss_limit(self, calculator):
        """Test that a large bonus early in the year accelerates reaching SS limit."""
        yd = YearlyData(year=2026, is_working_year=True)
        
        # Setup income: Base 130k, Bonus 50k -> Total 180k (above 160.2k limit)
        # Without bonus timing, limit reached late in year
        # With bonus at period 5, limit reached at period 5
        yd.base_salary = 130000
        yd.bonus = 50000
        yd.earned_income_for_fica = 180000
        
        # Other required fields for calculation
        yd.medical_dental_vision = 0
        yd.base_deferral = 0
        yd.employee_401k_contribution = 0
        yd.employee_hsa = 0
        yd.marginal_bracket = 0.24
        yd.state_tax = 9000
        yd.gross_income = 180000
        
        # Run calculation with bonus at period 5
        calculator._calculate_paycheck_take_home(yd, 2026, 0, 26, pay_period_preceding_bonus=5)
        
        # SS limit (160.2k) should be reached at period 5
        # Period 1-4: 4 * (130k/26) = 20k
        # Period 5: 20k + 5k + 50k = 75k -> Wait, 130k/26 = 5k per period
        # Cumulative at 5: 5 * 5k + 50k = 75k. Still under 160.2k?
        # Ah, 130k base + 50k bonus = 180k total.
        # 160.2k limit.
        # Period 5 cumulative: 25k base + 50k bonus = 75k. Not reached yet.
        
        # Let's try a bigger bonus or later period
        # Base 130k -> 5k/period
        # Bonus 100k at period 10
        # Period 10 cumulative: 50k base + 100k bonus = 150k. Close to 160.2k
        
        # Let's try Base 104k (4k/period), Bonus 100k at period 10
        # Limit 160.2k
        # Period 10 cumulative: 40k + 100k = 140k. Still under.
        
        # Let's try Base 156k (6k/period), Bonus 50k at period 10
        # Limit 160.2k
        # Period 10 cumulative: 60k + 50k = 110k.
        # Period 18 cumulative: 108k + 50k = 158k.
        # Period 19 cumulative: 114k + 50k = 164k. Reached at 19.
        
        # Without bonus timing (uniform distribution):
        # Total 206k / 26 = 7.92k/period
        # 160.2k / 7.92k = 20.2 -> Reached at period 21.
        
        # So with bonus at 10, reached at 19. Without, reached at 21.
        
        yd.base_salary = 156000
        yd.bonus = 50000
        yd.earned_income_for_fica = 206000
        yd.gross_income = 206000
        
        calculator._calculate_paycheck_take_home(yd, 2026, 0, 26, pay_period_preceding_bonus=10)
        
        # Verify limit reached earlier than uniform distribution
        assert yd.pay_period_ss_limit_reached == 19
        
    def test_bonus_triggers_medicare_surcharge(self, calculator):
        """Test that bonus triggers Medicare surcharge."""
        yd = YearlyData(year=2026, is_working_year=True)
        
        # Threshold 200k
        # Base 156k (6k/period)
        # Bonus 60k at period 10
        # Total 216k
        
        # Period 10 cumulative: 60k + 60k = 120k. Under 200k.
        # Period 23 cumulative: 138k + 60k = 198k.
        # Period 24 cumulative: 144k + 60k = 204k. Reached at 24.
        
        yd.base_salary = 156000
        yd.bonus = 60000
        yd.earned_income_for_fica = 216000
        yd.gross_income = 216000
        yd.medical_dental_vision = 0
        yd.base_deferral = 0
        yd.employee_401k_contribution = 0
        yd.employee_hsa = 0
        yd.marginal_bracket = 0.24
        yd.state_tax = 10000
        
        calculator._calculate_paycheck_take_home(yd, 2026, 0, 26, pay_period_preceding_bonus=10)
        
        assert yd.pay_period_medicare_surcharge_starts == 24

    def test_late_bonus_delays_ss_limit(self, calculator):
        """Test that a late bonus delays reaching SS limit compared to uniform."""
        yd = YearlyData(year=2026, is_working_year=True)
        
        # Limit 160.2k
        # Base 130k (5k/period)
        # Bonus 50k at period 26 (preceding pay period is 25)
        # Total 180k
        
        # Uniform: 180k/26 = 6.92k/period. 160.2/6.92 = 23.1 -> Period 24.
        
        # With late bonus (paid on period 26):
        # Period 25 cumulative: 125k. Under.
        # Period 26 cumulative: 130k + 50k = 180k. Reached at 26.
        
        yd.base_salary = 130000
        yd.bonus = 50000
        yd.earned_income_for_fica = 180000
        yd.gross_income = 180000
        yd.medical_dental_vision = 0
        yd.base_deferral = 0
        yd.employee_401k_contribution = 0
        yd.employee_hsa = 0
        yd.marginal_bracket = 0.24
        yd.state_tax = 9000
        
        # pay_period_preceding_bonus=25 means bonus is paid in period 26
        calculator._calculate_paycheck_take_home(yd, 2026, 0, 26, pay_period_preceding_bonus=25)
        
        assert yd.pay_period_ss_limit_reached == 26
