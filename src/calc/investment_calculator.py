"""Investment balance calculator.

Tracks investment account balances over time with appreciation.
"""

from typing import Dict, Optional


class InvestmentCalculator:
    """Calculator for investment account balances over time.
    
    Tracks taxable, tax-deferred (401k/IRA), and HSA account balances,
    applying annual appreciation rates and adding yearly contributions.
    
    Employer 401k match is included in the tax-deferred contributions when provided.
    """
    
    def __init__(self, spec: dict, first_year: int, last_year: int,
                 last_working_year: Optional[int] = None,
                 yearly_contributions: Optional[Dict[int, dict]] = None):
        """Initialize the investment calculator.
        
        Args:
            spec: The program specification containing investment details
            first_year: First year of the planning horizon
            last_year: Last year of the planning horizon
            last_working_year: Last year of work (contributions only during working years)
            yearly_contributions: Optional dict mapping years to contribution amounts
                                  Each value should be a dict with keys:
                                  '401k' (or 'tax_deferred'), 'hsa', 'employer_match'
        """
        self.first_year = first_year
        self.last_year = last_year
        self.last_working_year = last_working_year or last_year
        self.yearly_contributions = yearly_contributions or {}
        
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
    
    def _get_contribution(self, year: int, account_type: str) -> float:
        """Get the contribution for a specific year and account type.
        
        Args:
            year: The year to get contribution for
            account_type: 'tax_deferred', 'hsa', or 'employer_match'
            
        Returns:
            The contribution amount, or 0 if not a working year or no contribution
        """
        if year > self.last_working_year:
            return 0.0
        
        year_contribs = self.yearly_contributions.get(year, {})
        
        if account_type == 'tax_deferred':
            # Support both '401k' and 'tax_deferred' keys
            return year_contribs.get('tax_deferred', year_contribs.get('401k', 0.0))
        elif account_type == 'hsa':
            return year_contribs.get('hsa', 0.0)
        elif account_type == 'employer_match':
            return year_contribs.get('employer_match', 0.0)
        
        return 0.0
    
    def _calculate_all_years(self) -> None:
        """Pre-calculate balances for all years.
        
        For each year:
        1. Add contributions at the beginning of the year (for working years)
        2. Apply appreciation to the total balance
        
        Employer match is added to the tax_deferred balance alongside employee contributions.
        """
        taxable = self.initial_taxable
        tax_deferred = self.initial_tax_deferred
        hsa = self.initial_hsa
        
        for year in range(self.first_year, self.last_year + 1):
            # Get contributions for this year (only during working years)
            tax_deferred_contrib = self._get_contribution(year, 'tax_deferred')
            employer_match = self._get_contribution(year, 'employer_match')
            hsa_contrib = self._get_contribution(year, 'hsa')
            
            # Total contribution to tax-deferred account includes employer match
            total_tax_deferred_contrib = tax_deferred_contrib + employer_match
            
            if year == self.first_year:
                # First year: add contributions, then store (no appreciation yet)
                tax_deferred = tax_deferred + total_tax_deferred_contrib
                hsa = hsa + hsa_contrib
                
                self._balances[year] = {
                    'taxable': taxable,
                    'tax_deferred': tax_deferred,
                    'hsa': hsa,
                    'total': taxable + tax_deferred + hsa,
                    'contributions': {
                        'tax_deferred': tax_deferred_contrib,
                        'employer_match': employer_match,
                        'hsa': hsa_contrib
                    }
                }
            else:
                # Subsequent years: apply appreciation from previous year, then add contributions
                taxable = taxable * (1 + self.taxable_rate)
                tax_deferred = tax_deferred * (1 + self.tax_deferred_rate) + total_tax_deferred_contrib
                hsa = hsa * (1 + self.hsa_rate) + hsa_contrib
                
                self._balances[year] = {
                    'taxable': taxable,
                    'tax_deferred': tax_deferred,
                    'hsa': hsa,
                    'total': taxable + tax_deferred + hsa,
                    'contributions': {
                        'tax_deferred': tax_deferred_contrib,
                        'employer_match': employer_match,
                        'hsa': hsa_contrib
                    }
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
