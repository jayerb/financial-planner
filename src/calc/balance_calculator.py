from typing import Dict, List
from dataclasses import dataclass

from tax.FederalDetails import FederalDetails
from calc.take_home import TakeHomeCalculator


@dataclass
class YearlyBalance:
    """Represents the balance data for a single year."""
    year: int
    contrib_401k: float
    balance_401k: float
    deferred_contrib: float
    deferred_balance: float


@dataclass
class BalanceResult:
    """Contains all balance calculation results."""
    yearly_balances: List[YearlyBalance]
    final_401k_balance: float
    final_deferred_balance: float
    total_retirement_assets: float


class BalanceCalculator:
    """Calculator for accumulated retirement account balances.
    
    Computes year-by-year 401(k) and deferred compensation balances,
    accounting for contributions during working years and investment growth.
    """
    
    def __init__(self, calculator: TakeHomeCalculator, fed: FederalDetails):
        """Initialize with the take-home calculator and federal details.
        
        Args:
            calculator: TakeHomeCalculator instance for computing yearly contributions
            fed: FederalDetails instance for deduction lookups
        """
        self.calculator = calculator
        self.fed = fed
    
    def calculate(self, spec: dict) -> BalanceResult:
        """Calculate accumulated balances for all years in the planning horizon.
        
        Args:
            spec: The program specification dictionary
            
        Returns:
            BalanceResult containing yearly balances and final totals
        """
        first_year = spec.get('firstYear', 2026)
        last_working_year = spec.get('lastWorkingYear', first_year + 10)
        last_planning_year = spec.get('lastPlanningYear', last_working_year + 30)
        
        # Get growth assumptions from spec (default to reasonable values)
        deferred_growth_rate = spec.get('deferredCompGrowthRate', 0.06)
        retirement_401k_growth_rate = spec.get('401kGrowthRate', 0.07)
        
        # Initialize balances
        deferred_balance = spec.get('initialDeferredBalance', 0)
        balance_401k = spec.get('initial401kBalance', 0)
        
        yearly_balances: List[YearlyBalance] = []
        
        for year in range(first_year, last_planning_year + 1):
            # Get contributions for working years
            if year <= last_working_year:
                try:
                    results = self.calculator.calculate(spec, year)
                    contrib_401k = results['deductions']['max401k']
                    deferred_contrib = results.get('total_deferral', 0)
                except (KeyError, ValueError):
                    # If calculation fails for this year, use inflated values from federal details
                    try:
                        deductions = self.fed.totalDeductions(year)
                        contrib_401k = deductions['max401k']
                    except (KeyError, ValueError):
                        contrib_401k = 0
                    deferred_contrib = 0
            else:
                contrib_401k = 0
                deferred_contrib = 0
            
            # Apply growth to existing balance, then add new contributions
            balance_401k = balance_401k * (1 + retirement_401k_growth_rate) + contrib_401k
            deferred_balance = deferred_balance * (1 + deferred_growth_rate) + deferred_contrib
            
            yearly_balances.append(YearlyBalance(
                year=year,
                contrib_401k=contrib_401k,
                balance_401k=balance_401k,
                deferred_contrib=deferred_contrib,
                deferred_balance=deferred_balance
            ))
        
        return BalanceResult(
            yearly_balances=yearly_balances,
            final_401k_balance=balance_401k,
            final_deferred_balance=deferred_balance,
            total_retirement_assets=balance_401k + deferred_balance
        )
