"""Tests for the investment calculator."""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from calc.investment_calculator import InvestmentCalculator


def test_investment_calculator_initial_balances():
    """Test that first year returns initial balances."""
    spec = {
        'investments': {
            'taxableBalance': 100000.0,
            'taxableAppreciationRate': 0.07,
            'taxDeferredBalance': 200000.0,
            'taxDeferredAppreciationRate': 0.06,
            'hsaBalance': 15000.0,
            'hsaAppreciationRate': 0.05
        }
    }
    
    calc = InvestmentCalculator(spec, first_year=2025, last_year=2030)
    balances = calc.get_balances(2025)
    
    assert balances['taxable'] == 100000.0
    assert balances['tax_deferred'] == 200000.0
    assert balances['hsa'] == 15000.0
    assert balances['total'] == 315000.0


def test_investment_calculator_appreciation_applied():
    """Test that appreciation is applied correctly for subsequent years."""
    spec = {
        'investments': {
            'taxableBalance': 100000.0,
            'taxableAppreciationRate': 0.10,  # 10% for easy calculation
            'taxDeferredBalance': 200000.0,
            'taxDeferredAppreciationRate': 0.10,
            'hsaBalance': 10000.0,
            'hsaAppreciationRate': 0.10
        }
    }
    
    calc = InvestmentCalculator(spec, first_year=2025, last_year=2030)
    
    # Year 2 should have 10% appreciation
    balances_2026 = calc.get_balances(2026)
    assert balances_2026['taxable'] == pytest.approx(110000.0)
    assert balances_2026['tax_deferred'] == pytest.approx(220000.0)
    assert balances_2026['hsa'] == pytest.approx(11000.0)
    
    # Year 3 should have another 10% appreciation (compound)
    balances_2027 = calc.get_balances(2027)
    assert balances_2027['taxable'] == pytest.approx(121000.0)  # 100000 * 1.1 * 1.1
    assert balances_2027['tax_deferred'] == pytest.approx(242000.0)
    assert balances_2027['hsa'] == pytest.approx(12100.0)


def test_investment_calculator_different_rates():
    """Test that different appreciation rates are applied correctly."""
    spec = {
        'investments': {
            'taxableBalance': 100000.0,
            'taxableAppreciationRate': 0.05,  # 5%
            'taxDeferredBalance': 100000.0,
            'taxDeferredAppreciationRate': 0.10,  # 10%
            'hsaBalance': 100000.0,
            'hsaAppreciationRate': 0.0  # 0%
        }
    }
    
    calc = InvestmentCalculator(spec, first_year=2025, last_year=2030)
    balances = calc.get_balances(2026)
    
    assert balances['taxable'] == pytest.approx(105000.0)  # 5% growth
    assert balances['tax_deferred'] == pytest.approx(110000.0)  # 10% growth
    assert balances['hsa'] == pytest.approx(100000.0)  # 0% growth


def test_investment_calculator_no_investments():
    """Test that calculator handles missing investments gracefully."""
    spec = {}  # No investments section
    
    calc = InvestmentCalculator(spec, first_year=2025, last_year=2030)
    balances = calc.get_balances(2025)
    
    assert balances['taxable'] == 0.0
    assert balances['tax_deferred'] == 0.0
    assert balances['hsa'] == 0.0
    assert balances['total'] == 0.0


def test_investment_calculator_partial_investments():
    """Test that calculator handles partial investment configuration."""
    spec = {
        'investments': {
            'taxableBalance': 50000.0,
            'taxableAppreciationRate': 0.07
            # No tax_deferred or HSA
        }
    }
    
    calc = InvestmentCalculator(spec, first_year=2025, last_year=2030)
    balances = calc.get_balances(2025)
    
    assert balances['taxable'] == 50000.0
    assert balances['tax_deferred'] == 0.0
    assert balances['hsa'] == 0.0


def test_investment_calculator_get_all_balances():
    """Test getting balances for all years."""
    spec = {
        'investments': {
            'taxableBalance': 100000.0,
            'taxableAppreciationRate': 0.10
        }
    }
    
    calc = InvestmentCalculator(spec, first_year=2025, last_year=2027)
    all_balances = calc.get_all_balances()
    
    assert len(all_balances) == 3
    assert 2025 in all_balances
    assert 2026 in all_balances
    assert 2027 in all_balances
    assert all_balances[2025]['taxable'] == pytest.approx(100000.0)
    assert all_balances[2026]['taxable'] == pytest.approx(110000.0)
    assert all_balances[2027]['taxable'] == pytest.approx(121000.0)


def test_investment_calculator_final_balances():
    """Test getting final year balances."""
    spec = {
        'investments': {
            'taxableBalance': 100000.0,
            'taxableAppreciationRate': 0.10
        }
    }
    
    calc = InvestmentCalculator(spec, first_year=2025, last_year=2027)
    final = calc.get_final_balances()
    
    assert final['taxable'] == pytest.approx(121000.0)  # 100000 * 1.1^2


def test_investment_calculator_retirement_balances():
    """Test getting balances at retirement year."""
    spec = {
        'investments': {
            'taxableBalance': 100000.0,
            'taxableAppreciationRate': 0.10
        }
    }
    
    calc = InvestmentCalculator(spec, first_year=2025, last_year=2030)
    retirement = calc.get_balance_at_retirement(2027)
    
    assert retirement['taxable'] == pytest.approx(121000.0)  # 100000 * 1.1^2 (2025 -> 2026 -> 2027)


def test_investment_calculator_year_outside_range():
    """Test that getting balances for year outside range returns None."""
    spec = {
        'investments': {
            'taxableBalance': 100000.0,
            'taxableAppreciationRate': 0.07
        }
    }
    
    calc = InvestmentCalculator(spec, first_year=2025, last_year=2030)
    
    assert calc.get_balances(2020) is None
    assert calc.get_balances(2035) is None


def test_investment_calculator_with_401k_contributions():
    """Test that 401k contributions are added to tax-deferred balance."""
    spec = {
        'investments': {
            'taxableBalance': 100000.0,
            'taxableAppreciationRate': 0.10,
            'taxDeferredBalance': 200000.0,
            'taxDeferredAppreciationRate': 0.10,
            'hsaBalance': 10000.0,
            'hsaAppreciationRate': 0.10
        }
    }
    
    yearly_contributions = {
        2025: {'tax_deferred': 23000.0, 'hsa': 4150.0},
        2026: {'tax_deferred': 23500.0, 'hsa': 4250.0},
        2027: {'tax_deferred': 24000.0, 'hsa': 4350.0}
    }
    
    calc = InvestmentCalculator(
        spec, first_year=2025, last_year=2030,
        last_working_year=2027,
        yearly_contributions=yearly_contributions
    )
    
    # First year: initial balance + first year contribution (no appreciation yet)
    balances_2025 = calc.get_balances(2025)
    assert balances_2025['tax_deferred'] == pytest.approx(223000.0)  # 200000 + 23000
    assert balances_2025['hsa'] == pytest.approx(14150.0)  # 10000 + 4150
    
    # Second year: (previous balance * 1.1) + contribution
    balances_2026 = calc.get_balances(2026)
    # (223000 * 1.1) + 23500 = 245300 + 23500 = 268800
    assert balances_2026['tax_deferred'] == pytest.approx(268800.0)
    # (14150 * 1.1) + 4250 = 15565 + 4250 = 19815
    assert balances_2026['hsa'] == pytest.approx(19815.0)
    
    # Third year: (previous balance * 1.1) + contribution  
    balances_2027 = calc.get_balances(2027)
    # (268800 * 1.1) + 24000 = 295680 + 24000 = 319680
    assert balances_2027['tax_deferred'] == pytest.approx(319680.0)


def test_investment_calculator_no_contributions_after_retirement():
    """Test that contributions stop after last working year."""
    spec = {
        'investments': {
            'taxDeferredBalance': 100000.0,
            'taxDeferredAppreciationRate': 0.10
        }
    }
    
    # Contributions are defined for 2025-2030, but last working year is 2026
    yearly_contributions = {
        2025: {'tax_deferred': 20000.0},
        2026: {'tax_deferred': 20000.0},
        2027: {'tax_deferred': 20000.0},  # Should be ignored
        2028: {'tax_deferred': 20000.0},  # Should be ignored
    }
    
    calc = InvestmentCalculator(
        spec, first_year=2025, last_year=2030,
        last_working_year=2026,
        yearly_contributions=yearly_contributions
    )
    
    # 2025: 100000 + 20000 = 120000
    assert calc.get_balances(2025)['tax_deferred'] == pytest.approx(120000.0)
    
    # 2026: 120000 * 1.1 + 20000 = 132000 + 20000 = 152000
    assert calc.get_balances(2026)['tax_deferred'] == pytest.approx(152000.0)
    
    # 2027: 152000 * 1.1 + 0 (no contribution, past last working year) = 167200
    assert calc.get_balances(2027)['tax_deferred'] == pytest.approx(167200.0)
    
    # 2028: 167200 * 1.1 = 183920
    assert calc.get_balances(2028)['tax_deferred'] == pytest.approx(183920.0)


def test_investment_calculator_contributions_tracked():
    """Test that contributions are tracked in the balance dict."""
    spec = {
        'investments': {
            'taxDeferredBalance': 100000.0,
            'taxDeferredAppreciationRate': 0.10
        }
    }
    
    yearly_contributions = {
        2025: {'tax_deferred': 23000.0, 'hsa': 4000.0},
        2026: {'tax_deferred': 24000.0, 'hsa': 4200.0}
    }
    
    calc = InvestmentCalculator(
        spec, first_year=2025, last_year=2030,
        last_working_year=2026,
        yearly_contributions=yearly_contributions
    )
    
    balances_2025 = calc.get_balances(2025)
    assert 'contributions' in balances_2025
    assert balances_2025['contributions']['tax_deferred'] == 23000.0
    assert balances_2025['contributions']['hsa'] == 4000.0
    
    balances_2027 = calc.get_balances(2027)
    assert balances_2027['contributions']['tax_deferred'] == 0.0  # Past working years


def test_investment_calculator_supports_401k_key():
    """Test that '401k' key is supported in addition to 'tax_deferred'."""
    spec = {
        'investments': {
            'taxDeferredBalance': 100000.0,
            'taxDeferredAppreciationRate': 0.0
        }
    }
    
    yearly_contributions = {
        2025: {'401k': 25000.0},  # Using '401k' instead of 'tax_deferred'
    }
    
    calc = InvestmentCalculator(
        spec, first_year=2025, last_year=2027,
        last_working_year=2027,
        yearly_contributions=yearly_contributions
    )
    
    assert calc.get_balances(2025)['tax_deferred'] == pytest.approx(125000.0)
