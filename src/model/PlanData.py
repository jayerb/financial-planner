"""Unified data model for financial planning results.

This module contains data classes that hold all calculated results
for the financial plan, organized by year. Each renderer can extract
the specific fields it needs from this unified structure.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class YearlyData:
    """All financial data for a single year.
    
    This unified structure contains everything calculated for a year:
    income, taxes, deductions, contributions, and balances.
    """
    year: int
    is_working_year: bool
    
    # Income
    base_salary: float = 0.0
    bonus: float = 0.0
    other_income: float = 0.0
    espp_income: float = 0.0
    rsu_vested_value: float = 0.0
    short_term_capital_gains: float = 0.0  # Realized short-term capital gains (taxed as ordinary income)
    long_term_capital_gains: float = 0.0   # Realized long-term capital gains (taxed at preferential rates)
    deferred_comp_disbursement: float = 0.0
    gross_income: float = 0.0  # Total taxable income including realized capital gains
    earned_income_for_fica: float = 0.0
    
    # Deductions
    standard_deduction: float = 0.0
    itemized_deduction: float = 0.0
    max_401k: float = 0.0
    max_hsa: float = 0.0
    employee_hsa: float = 0.0
    employer_hsa: float = 0.0
    medical_dental_vision: float = 0.0
    total_deductions: float = 0.0
    
    # Deferrals
    base_deferral: float = 0.0
    bonus_deferral: float = 0.0
    total_deferral: float = 0.0
    
    # Adjusted income
    adjusted_gross_income: float = 0.0
    
    # Federal taxes
    ordinary_income_tax: float = 0.0
    long_term_capital_gains_tax: float = 0.0
    federal_tax: float = 0.0
    marginal_bracket: float = 0.0
    
    # FICA taxes
    social_security_tax: float = 0.0
    medicare_tax: float = 0.0
    medicare_surcharge: float = 0.0
    total_fica: float = 0.0
    pay_period_ss_limit_reached: int = 0  # Pay period (1-26) when SS limit is reached based on base salary
    
    # State taxes
    state_income_tax: float = 0.0
    state_short_term_capital_gains_tax: float = 0.0
    state_tax: float = 0.0
    
    # Local taxes
    local_tax: float = 0.0
    
    # Total taxes and take home
    total_taxes: float = 0.0
    effective_tax_rate: float = 0.0
    take_home_pay: float = 0.0
    
    # Contributions
    employee_401k_contribution: float = 0.0
    employer_401k_match: float = 0.0
    total_401k_contribution: float = 0.0
    hsa_contribution: float = 0.0  # Total (employee + employer)
    deferred_comp_contribution: float = 0.0
    taxable_contribution: float = 0.0
    total_contributions: float = 0.0
    
    # Expenses and money movement
    annual_expenses: float = 0.0
    special_expenses: float = 0.0
    travel_expenses: float = 0.0
    medical_premium: float = 0.0  # Medical/insurance premium for the year (tracked for all years)
    medical_premium_expense: float = 0.0  # Medical premium as expense (only in retirement, not covered by employer)
    total_expenses: float = 0.0
    income_expense_difference: float = 0.0  # take_home - total_expenses
    hsa_withdrawal: float = 0.0  # Tax-free HSA withdrawal for qualified medical expenses
    ira_withdrawal: float = 0.0  # Amount withdrawn from 401k/IRA to cover expenses
    taxable_account_adjustment: float = 0.0  # positive = add to taxable, negative = withdraw
    
    # Account appreciation (growth for the year)
    appreciation_ira: float = 0.0
    appreciation_deferred_comp: float = 0.0
    appreciation_hsa: float = 0.0
    appreciation_taxable: float = 0.0
    total_appreciation: float = 0.0
    
    # Account balances (end of year)
    balance_ira: float = 0.0
    balance_deferred_comp: float = 0.0
    balance_hsa: float = 0.0
    balance_taxable: float = 0.0
    total_assets: float = 0.0


@dataclass
class PlanData:
    """Complete financial plan data across all years.
    
    Contains yearly data for each year in the planning horizon,
    plus summary totals and metadata about the plan.
    """
    first_year: int
    last_working_year: int
    last_planning_year: int
    
    # Yearly data indexed by year
    yearly_data: Dict[int, YearlyData] = field(default_factory=dict)
    
    # Lifetime totals
    total_gross_income: float = 0.0
    total_federal_tax: float = 0.0
    total_fica: float = 0.0
    total_state_tax: float = 0.0
    total_taxes: float = 0.0
    total_take_home: float = 0.0
    
    # Final balances
    final_401k_balance: float = 0.0
    final_deferred_comp_balance: float = 0.0
    final_hsa_balance: float = 0.0
    final_taxable_balance: float = 0.0
    total_retirement_assets: float = 0.0
    
    def get_year(self, year: int) -> Optional[YearlyData]:
        """Get data for a specific year."""
        return self.yearly_data.get(year)
    
    def working_years(self) -> Dict[int, YearlyData]:
        """Get data for working years only."""
        return {y: d for y, d in self.yearly_data.items() if d.is_working_year}
    
    def retirement_years(self) -> Dict[int, YearlyData]:
        """Get data for retirement years only."""
        return {y: d for y, d in self.yearly_data.items() if not d.is_working_year}
