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


def test_stock_price_growth():
    """Test that stock price grows correctly over time."""
    calculator = RSUCalculator(
        current_stock_price=100.0,
        expected_share_price_growth_fraction=0.10  # 10% annual growth
    )

    # Price should be 100 at base year
    assert calculator.stock_price_for_year(2026, 2026) == 100.0

    # Price should be 110 after 1 year (10% growth)
    assert round(calculator.stock_price_for_year(2026, 2027), 2) == 110.0

    # Price should be 121 after 2 years (10% compounded)
    assert round(calculator.stock_price_for_year(2026, 2028), 2) == 121.0


def test_vested_shares_from_single_grant():
    """Test shares vesting calculation from a single grant."""
    calculator = RSUCalculator(
        current_stock_price=100.0,
        expected_share_price_growth_fraction=0.07
    )

    # Grant of 100 shares in 2024 with 4-year vest
    # Should vest 25 shares per year from 2025-2028

    # Before vesting starts
    assert calculator.vested_shares_from_grant(2024, 100, 4, 2024) == 0

    # During vesting period
    assert calculator.vested_shares_from_grant(2024, 100, 4, 2025) == 25
    assert calculator.vested_shares_from_grant(2024, 100, 4, 2026) == 25
    assert calculator.vested_shares_from_grant(2024, 100, 4, 2027) == 25
    assert calculator.vested_shares_from_grant(2024, 100, 4, 2028) == 25

    # After vesting ends
    assert calculator.vested_shares_from_grant(2024, 100, 4, 2029) == 0


def test_previous_grants_vesting():
    """Test that previous grants vest correctly."""
    calculator = RSUCalculator(
        current_stock_price=250.0,
        expected_share_price_growth_fraction=0.07
    )

    spec = create_spec(
        first_year=2026,
        previous_grants=[
            {'year': 2024, 'grantShares': 100, 'vestingPeriodYears': 4},
            {'year': 2025, 'grantShares': 200, 'vestingPeriodYears': 4}
        ]
    )

    result = calculator.calculate_vested_value(spec, 2026)

    # In 2026:
    # - 2024 grant: 25 shares vest (year 2 of 4)
    # - 2025 grant: 50 shares vest (year 1 of 4)
    # - 2026 grant: 0 shares (first vest is 2027)
    expected_previous_shares = 25 + 50  # = 75 from previous grants

    previous_vesting = [v for v in result['vesting_breakdown'] if v['grant_type'] == 'previous']
    total_previous_shares = sum(v['shares_vesting'] for v in previous_vesting)

    assert total_previous_shares == expected_previous_shares


def test_annual_grants_increase_over_time():
    """Test that annual grant values increase by the specified fraction."""
    calculator = RSUCalculator(
        current_stock_price=100.0,
        expected_share_price_growth_fraction=0.0  # No stock growth for simpler math
    )

    spec = create_spec(
        first_year=2026,
        initial_grant_value=10000,
        annual_increase=0.10,  # 10% increase each year
        vesting_period=4
    )

    # Calculate for 2030 to see grants from 2026-2029 vesting
    result = calculator.calculate_vested_value(spec, 2030)

    annual_vesting = [v for v in result['vesting_breakdown'] if v['grant_type'] == 'annual']

    # Check that grant values increased
    # 2026: $10,000
    # 2027: $11,000 (10% increase)
    # 2028: $12,100 (10% increase)
    # 2029: $13,310 (10% increase)

    for v in annual_vesting:
        if v['grant_year'] == 2026:
            assert round(v['grant_value'], 2) == 10000.00
        elif v['grant_year'] == 2027:
            assert round(v['grant_value'], 2) == 11000.00
        elif v['grant_year'] == 2028:
            assert round(v['grant_value'], 2) == 12100.00
        elif v['grant_year'] == 2029:
            assert round(v['grant_value'], 2) == 13310.00


def test_vested_value_calculation():
    """Test complete vested value calculation."""
    calculator = RSUCalculator(
        current_stock_price=100.0,
        expected_share_price_growth_fraction=0.0  # No growth for simpler verification
    )

    spec = create_spec(
        first_year=2026,
        initial_grant_value=10000,
        annual_increase=0.0,  # No increase for simpler math
        vesting_period=4
    )

    # In 2027, only the 2026 grant should have vested shares
    # Grant is $10,000 at $100/share = 100 shares
    # 25 shares vest per year, so 25 shares vest in 2027
    # Value = 25 shares * $100 = $2,500
    result = calculator.calculate_vested_value(spec, 2027)

    assert result['vested_shares'] == 25
    assert result['stock_price'] == 100.0
    assert result['vested_value'] == 2500.0


def test_vesting_schedule_multiple_years():
    """Test calculating vesting schedule for multiple years."""
    calculator = RSUCalculator(
        current_stock_price=100.0,
        expected_share_price_growth_fraction=0.0
    )

    spec = create_spec(
        first_year=2026,
        initial_grant_value=4000,  # 40 shares at $100
        annual_increase=0.0,
        vesting_period=4
    )

    schedule = calculator.calculate_vesting_schedule(spec, 2027, 2030)

    assert len(schedule) == 4
    assert schedule[0]['target_year'] == 2027
    assert schedule[3]['target_year'] == 2030


def test_stock_appreciation_increases_vested_value():
    """Test that stock price growth increases vested value."""
    # Calculator with 100% annual growth (for easy math)
    calculator = RSUCalculator(
        current_stock_price=100.0,
        expected_share_price_growth_fraction=1.0  # Doubles each year
    )

    spec = create_spec(
        first_year=2026,
        initial_grant_value=10000,
        annual_increase=0.0,
        vesting_period=4
    )

    # 2026 grant: $10,000 / $100 = 100 shares, vest 25/year
    # In 2027: stock price = $200, vest 25 shares = $5,000
    # In 2028: stock price = $400, vest 25 shares = $10,000
    result_2027 = calculator.calculate_vested_value(spec, 2027)
    result_2028 = calculator.calculate_vested_value(spec, 2028)

    assert result_2027['stock_price'] == 200.0
    assert result_2028['stock_price'] == 400.0

    # The 2026 grant portion value should double from 2027 to 2028
    grant_2026_in_2027 = next(
        v for v in result_2027['vesting_breakdown']
        if v['grant_type'] == 'annual' and v['grant_year'] == 2026
    )
    grant_2026_in_2028 = next(
        v for v in result_2028['vesting_breakdown']
        if v['grant_type'] == 'annual' and v['grant_year'] == 2026
    )

    # Same shares vest, but value doubles due to stock price
    assert grant_2026_in_2027['shares_vesting'] == grant_2026_in_2028['shares_vesting']
    assert grant_2026_in_2028['value'] == grant_2026_in_2027['value'] * 2
