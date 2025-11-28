"""Calculator for deferred compensation plan growth and disbursements."""

from typing import Dict


class DeferredCompCalculator:
    """Calculator for deferred compensation plan balances and disbursements.
    
    Tracks the growth of deferred compensation during working years,
    then calculates annual disbursements during retirement years.
    
    The disbursement is calculated as: balance / remaining_disbursement_years
    Each year, the balance grows by the growth rate before the disbursement is taken.
    """
    
    def __init__(self, spec: dict, yearly_deferrals: Dict[int, float]):
        """Initialize with spec and pre-calculated yearly deferrals.
        
        Args:
            spec: The program specification dictionary
            yearly_deferrals: Dictionary mapping year to deferral amount for working years
        """
        self.first_year = spec.get('firstYear', 2026)
        self.last_working_year = spec.get('lastWorkingYear', self.first_year + 10)
        self.last_planning_year = spec.get('lastPlanningYear', self.last_working_year + 30)
        
        deferred_plan = spec.get('deferredCompensationPlan', {})
        self.growth_rate = deferred_plan.get('annualGrowthFraction', 0.05)
        self.disbursement_years = deferred_plan.get('dispursementYears', 10)
        
        self.initial_balance = spec.get('initialDeferredBalance', 0)
        self.yearly_deferrals = yearly_deferrals
        
        # Pre-calculate balances and disbursements for all years
        self._balances: Dict[int, float] = {}
        self._disbursements: Dict[int, float] = {}
        self._calculate_all_years()
    
    def _calculate_all_years(self) -> None:
        """Calculate balances and disbursements for all years in the planning horizon."""
        balance = self.initial_balance
        disbursement_start_year = self.last_working_year + 1
        disbursement_end_year = disbursement_start_year + self.disbursement_years - 1
        
        for year in range(self.first_year, self.last_planning_year + 1):
            # Apply growth to existing balance
            balance = balance * (1 + self.growth_rate)
            
            if year <= self.last_working_year:
                # Working years: add contributions, no disbursements
                deferral = self.yearly_deferrals.get(year, 0)
                balance += deferral
                self._disbursements[year] = 0
            elif year <= disbursement_end_year:
                # Disbursement years: calculate and subtract disbursement
                remaining_years = disbursement_end_year - year + 1
                disbursement = balance / remaining_years
                balance -= disbursement
                self._disbursements[year] = disbursement
            else:
                # After disbursement period: no more disbursements
                self._disbursements[year] = 0
            
            self._balances[year] = balance
    
    def get_balance(self, year: int) -> float:
        """Get the deferred compensation balance at end of year.
        
        Args:
            year: The tax year
            
        Returns:
            The balance at the end of the specified year
        """
        return self._balances.get(year, 0)
    
    def get_disbursement(self, year: int) -> float:
        """Get the disbursement amount for a given year.
        
        Args:
            year: The tax year
            
        Returns:
            The disbursement amount for the year (0 during working years)
        """
        return self._disbursements.get(year, 0)
