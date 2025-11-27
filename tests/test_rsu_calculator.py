import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from calc.rsu_calculator import RSUCalculator


def create_spec(first_year=2026, initial_grant_value=10000, annual_increase=0.05,
                vesting_period=4, previous_grants=None):
    """Create a minimal spec dictionary for RSU testing."""
    spec = {
        'firstYear': first_year,
        'lastYear': first_year + 50,
        'restrictedStockUnits': {
            'initialAnnualGrantValue': initial_grant_value,
            'annualGrantIncreaseFraction': annual_increase,
            'vestingPeriodYears': vesting_period,
            'previousGrants': previous_grants or []
        }
    }
    return spec


def test_vested_value_calculation():
    """Test complete vested value calculation."""
    previous_grants = [            {
                "year": 2022,
                "grantShares": 100,
                "vestingPeriodYears": 4
            },
            {
                "year": 2023,
                "grantShares": 120,
                "vestingPeriodYears": 4
            },
            {
                "year": 2024,
                "grantShares": 140,
                "vestingPeriodYears": 4
            },
            {
                "year": 2025,
                "grantShares": 160,
                "vestingPeriodYears": 4
            }
        ]
    calculator = RSUCalculator(
        previous_grants=previous_grants,
        first_year_grant_value=100000*1.05,
        first_year_stock_price=250.00*1.07,
        expected_share_price_growth_fraction=0.07
    )
    # the number of shares vesting in 2026 is 100/4 + 120/4 + 140/4 + 160/4 = 130
    # the stock price in 2026 is 250 * 1.07 = 267.50
    # so the vested value in 2026 is 130 * 267.50 = 34775.00
    vested_value_2026 = calculator.vested_value[2026]
    assert round(vested_value_2026, 2) == 34775.00
    # the number of shares vesting in 2027 is 120/4 + 140/4 + 160/4 + new grant shares
    # new grant value in 2026 is 100000 * 1.05^1 = 105000
    # new grant shares = 105000 / (250 * 1.07) = 392.52336449
    # total shares vesting in 2027 = 30 + 35 + 40 + 392.52336449/4 = 203.13084112
    # stock price in 2027 = 250 * 1.07^2 = 286.225
    # vested value in 2027 = 203.13084112 * 286.225 = 58141.125
    vested_value_2027 = calculator.vested_value[2027]
    assert round(vested_value_2027, 2) == 58141.13
    vested_value_2028 = calculator.vested_value[2028]
    # the vested value in 2028 is
    # shares vesting: 140/4 + 160/4 + 392.52336449/4 + new grant shares
    # new grant value in 2027 is 100000 * 1.05^2 = 110250
    # new grant shares = 110250 / (250 * 1.07^2) = 385.18647917
    # total shares vesting in 2028 = 35 + 40 + 98.13084112 + 385.18647917/4 = 269.42746091
    # stock price in 2028 = 250 * 1.07^3 = 306.26075
    # vested value in 2028 = 269.42746091 * 306.26075 = 82515.05624889
    assert round(vested_value_2028, 2) == 82515.06

