"""Investment balance calculator.

Tracks investment account balances over time with appreciation.
"""

from typing import Dict, Optional


class InvestmentCalculator:
    """Calculator for investment account balances over time.
    
    Tracks taxable, tax-deferred (401k/IRA), and HSA account balances,
    applying annual appreciation rates.
    """
    
    def __init__(self, spec: dict, first_year: int, last_year: int):
        """Initialize the investment calculator.
        
        Args:
            spec: The program specification containing investment details
            first_year: First year of the planning horizon
            last_year: Last year of the planning horizon
        """
        self.first_year = first_year
        self.last_year = last_year
        
        investments = spec.get('investments', {})
        
        # Initial balances
        self.initial_taxable = investments.get('taxableBalance', 0.0)
        self.initial_tax_deferred = investments.get('taxDeferredBalance', 0.0)
        self.initial_hsa = investments.get('hsaBalance', 0.0)
        
        # Appreciation rates
        self.taxable_rate = investments.get('taxableAppreciationRate', 0.0)
        self.tax_deferred_rate = investments.get('taxDeferredAppreciationRate', 0.0)
        self.hsa_rate = investments.get('hsaAppreciationRate', 0.0)
        
        # Cache calculated balances
        self._balances: Dict[int, dict] = {}
        self._calculate_all_years()
    
    def _calculate_all_years(self) -> None:
        """Pre-calculate balances for all years."""
        taxable = self.initial_taxable
        tax_deferred = self.initial_tax_deferred
        hsa = self.initial_hsa
        
        for year in range(self.first_year, self.last_year + 1):
            if year == self.first_year:
                # First year uses initial balances
                self._balances[year] = {
                    'taxable': taxable,
                    'tax_deferred': tax_deferred,
                    'hsa': hsa,
                    'total': taxable + tax_deferred + hsa
                }
            else:
                # Apply appreciation from previous year
                taxable = taxable * (1 + self.taxable_rate)
                tax_deferred = tax_deferred * (1 + self.tax_deferred_rate)
                hsa = hsa * (1 + self.hsa_rate)
                
                self._balances[year] = {
                    'taxable': taxable,
                    'tax_deferred': tax_deferred,
                    'hsa': hsa,
                    'total': taxable + tax_deferred + hsa
                }
    
    def get_balances(self, year: int) -> Optional[dict]:
        """Get investment balances for a specific year.
        
        Args:
            year: The year to get balances for
            
        Returns:
            Dictionary with taxable, tax_deferred, hsa, and total balances,
            or None if year is outside planning horizon
        """
        return self._balances.get(year)
    
    def get_all_balances(self) -> Dict[int, dict]:
        """Get investment balances for all years.
        
        Returns:
            Dictionary mapping years to balance dictionaries
        """
        return self._balances.copy()
    
    def get_balance_at_retirement(self, last_working_year: int) -> dict:
        """Get investment balances at retirement.
        
        Args:
            last_working_year: The last year of work
            
        Returns:
            Dictionary with balances at end of last working year
        """
        return self._balances.get(last_working_year, {
            'taxable': 0,
            'tax_deferred': 0,
            'hsa': 0,
            'total': 0
        })
    
    def get_final_balances(self) -> dict:
        """Get investment balances at end of planning horizon.
        
        Returns:
            Dictionary with final balances
        """
        return self._balances.get(self.last_year, {
            'taxable': 0,
            'tax_deferred': 0,
            'hsa': 0,
            'total': 0
        })
