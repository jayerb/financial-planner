"""Renderer classes for displaying financial planning results.

This module contains renderer classes that handle the presentation logic
for different types of financial planning outputs. Each renderer takes
the unified PlanData structure and extracts the fields it needs.
"""

from abc import ABC, abstractmethod
from typing import Any

from model.PlanData import PlanData, YearlyData


class BaseRenderer(ABC):
    """Abstract base class for all renderers."""
    
    @abstractmethod
    def render(self, data: PlanData) -> None:
        """Render the data to output.
        
        Args:
            data: The PlanData containing all yearly calculations
        """
        pass


class TaxDetailsRenderer(BaseRenderer):
    """Renderer for detailed tax breakdown display."""
    
    def __init__(self, tax_year: int):
        """Initialize with the tax year to display.
        
        Args:
            tax_year: The tax year for the results being rendered
        """
        self.tax_year = tax_year
    
    def render(self, data: PlanData) -> None:
        """Render the tax details breakdown.
        
        Args:
            data: PlanData containing all yearly calculations
        """
        yd = data.get_year(self.tax_year)
        if not yd:
            print(f"No data available for year {self.tax_year}")
            return

        print()
        print("=" * 60)
        print(f"{'TAX SUMMARY FOR ' + str(self.tax_year):^60}")
        print("=" * 60)
        
        print()
        print("-" * 60)
        print("INCOME")
        print("-" * 60)
        print(f"  {'Gross Income:':<40} ${yd.gross_income:>14,.2f}")
        print(f"  {'RSU Vested:':<40} ${yd.rsu_vested_value:>14,.2f}")
        
        print()
        print("-" * 60)
        print("DEDUCTIONS")
        print("-" * 60)
        # Show which deduction type is being used
        if yd.itemized_deduction > yd.standard_deduction:
            print(f"  {'Itemized Deduction (SALT):':<40} ${yd.itemized_deduction:>14,.2f}  <- used")
            print(f"  {'Standard Deduction:':<40} ${yd.standard_deduction:>14,.2f}")
        else:
            print(f"  {'Standard Deduction:':<40} ${yd.standard_deduction:>14,.2f}  <- used")
            if yd.itemized_deduction > 0:
                print(f"  {'Itemized Deduction (SALT):':<40} ${yd.itemized_deduction:>14,.2f}")
        print(f"  {'401(k) Contribution:':<40} ${yd.max_401k:>14,.2f}")
        # Show employee HSA contribution (the tax-deductible portion)
        if yd.employee_hsa != yd.max_hsa:
            print(f"  {'HSA Contribution (Employee):':<40} ${yd.employee_hsa:>14,.2f}")
            print(f"  {'HSA Contribution (Employer):':<40} ${yd.employer_hsa:>14,.2f}")
        else:
            print(f"  {'HSA Contribution:':<40} ${yd.max_hsa:>14,.2f}")
        print(f"  {'Medical/Dental/Vision:':<40} ${yd.medical_dental_vision:>14,.2f}")
        print(f"  {'-' * 40}")
        print(f"  {'Total Deductions:':<40} ${yd.total_deductions:>14,.2f}")
        
        print()
        print("-" * 60)
        print("DEFERRED INCOME (reduces Federal/State tax only)")
        print("-" * 60)
        print(f"  {'Base Salary Deferral:':<40} ${yd.base_deferral:>14,.2f}")
        print(f"  {'Bonus Deferral:':<40} ${yd.bonus_deferral:>14,.2f}")
        print(f"  {'-' * 40}")
        print(f"  {'Total Deferred:':<40} ${yd.total_deferral:>14,.2f}")
        
        print()
        print(f"  {'Adjusted Gross Income:':<40} ${yd.adjusted_gross_income:>14,.2f}")
        
        print()
        print("-" * 60)
        print("FEDERAL TAXES")
        print("-" * 60)
        print(f"  {'Ordinary Income Tax:':<40} ${yd.ordinary_income_tax:>14,.2f}")
        print(f"  {'Long-Term Capital Gains Tax:':<40} ${yd.long_term_capital_gains_tax:>14,.2f}")
        print(f"  {'-' * 40}")
        print(f"  {'Total Federal Tax:':<40} ${yd.federal_tax:>14,.2f}")
        print(f"  {'Marginal Bracket:':<40} {yd.marginal_bracket:>14.2%}")
        
        print()
        print("-" * 60)
        print("FICA TAXES")
        print("-" * 60)
        print(f"  {'Social Security + MA PFML:':<40} ${yd.social_security_tax:>14,.2f}")
        print(f"  {'Medicare:':<40} ${yd.medicare_tax:>14,.2f}")
        print(f"  {'Medicare Surcharge:':<40} ${yd.medicare_surcharge:>14,.2f}")
        print(f"  {'-' * 40}")
        print(f"  {'Total FICA:':<40} ${yd.total_fica:>14,.2f}")
        
        print()
        print("-" * 60)
        print("STATE TAXES")
        print("-" * 60)
        print(f"  {'State Income Tax:':<40} ${yd.state_income_tax:>14,.2f}")
        print(f"  {'State Short-Term Capital Gains Tax:':<40} ${yd.state_short_term_capital_gains_tax:>14,.2f}")
        print(f"  {'-' * 40}")
        print(f"  {'Total State Tax:':<40} ${yd.state_tax:>14,.2f}")
        
        print()
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"  {'Gross Income:':<40} ${yd.gross_income:>14,.2f}")
        print(f"  {'Total Deductions:':<40} ${yd.total_deductions:>14,.2f}")
        print(f"  {'Total Deferred Income:':<40} ${yd.total_deferral:>14,.2f}")
        print(f"  {'Total Federal Tax:':<40} ${yd.federal_tax:>14,.2f}")
        print(f"  {'Total FICA:':<40} ${yd.total_fica:>14,.2f}")
        print(f"  {'Total State Tax:':<40} ${yd.state_tax:>14,.2f}")
        print(f"  {'-' * 40}")
        print(f"  {'TOTAL TAXES PAID:':<40} ${yd.total_taxes:>14,.2f}")
        print(f"  {'TOTAL TO DEFERRED ACCOUNT:':<40} ${yd.total_deferral:>14,.2f}")
        print()
        print("=" * 60)
        print(f"{'TAKE HOME PAY:':^44} ${yd.take_home_pay:>14,.2f}")
        print("=" * 60)
        print()


class BalancesRenderer(BaseRenderer):
    """Renderer for accumulated balance display."""
    
    def render(self, data: PlanData) -> None:
        """Render the accumulated balances.
        
        Args:
            data: PlanData containing all yearly calculations
        """
        print()
        print("=" * 116)
        print(f"{'ACCUMULATED BALANCES':^116}")
        print("=" * 116)
        print()
        print(f"  {'Year':<8} {'401(k) Contrib':>16} {'401(k) Balance':>18} {'Deferred Contrib':>18} {'Deferred Balance':>18} {'HSA Contrib':>14} {'HSA Balance':>16}")
        print(f"  {'-' * 8} {'-' * 16} {'-' * 18} {'-' * 18} {'-' * 18} {'-' * 14} {'-' * 16}")
        
        for year in sorted(data.yearly_data.keys()):
            yd = data.yearly_data[year]
            print(f"  {year:<8} ${yd.total_401k_contribution:>14,.2f} ${yd.balance_401k:>16,.2f} ${yd.deferred_comp_contribution:>16,.2f} ${yd.balance_deferred_comp:>16,.2f} ${yd.hsa_contribution:>12,.2f} ${yd.balance_hsa:>14,.2f}")
        
        print()
        print("=" * 116)
        print(f"{'FINAL BALANCES':^116}")
        print("=" * 116)
        print(f"  {'401(k) Balance:':<40} ${data.final_401k_balance:>18,.2f}")
        print(f"  {'Deferred Compensation Balance:':<40} ${data.final_deferred_comp_balance:>18,.2f}")
        print(f"  {'HSA Balance:':<40} ${data.final_hsa_balance:>18,.2f}")
        print(f"  {'-' * 60}")
        print(f"  {'TOTAL RETIREMENT ASSETS:':<40} ${data.total_retirement_assets:>18,.2f}")
        print("=" * 116)
        print()


class AnnualSummaryRenderer(BaseRenderer):
    """Renderer for annual income and tax burden summary table."""
    
    def render(self, data: PlanData) -> None:
        """Render a summary table of income and taxes for each year.
        
        Args:
            data: PlanData containing all yearly calculations
        """
        print()
        print("=" * 110)
        print(f"{'ANNUAL INCOME AND TAX SUMMARY':^110}")
        print("=" * 110)
        print()
        print(f"  {'Year':<6} {'Gross Income':>14} {'Federal Tax':>14} {'FICA':>14} {'State Tax':>14} {'Total Tax':>14} {'Eff Rate':>10} {'Take Home':>14}")
        print(f"  {'-' * 6} {'-' * 14} {'-' * 14} {'-' * 14} {'-' * 14} {'-' * 14} {'-' * 10} {'-' * 14}")
        
        for year in sorted(data.yearly_data.keys()):
            yd = data.yearly_data[year]
            print(f"  {year:<6} ${yd.gross_income:>12,.0f} ${yd.federal_tax:>12,.0f} ${yd.total_fica:>12,.0f} ${yd.state_tax:>12,.0f} ${yd.total_taxes:>12,.0f} {yd.effective_tax_rate:>9.1%} ${yd.take_home_pay:>12,.0f}")
        
        print(f"  {'-' * 6} {'-' * 14} {'-' * 14} {'-' * 14} {'-' * 14} {'-' * 14} {'-' * 10} {'-' * 14}")
        
        # Calculate overall effective rate
        overall_eff_rate = data.total_taxes / data.total_gross_income if data.total_gross_income > 0 else 0
        
        print(f"  {'TOTAL':<6} ${data.total_gross_income:>12,.0f} ${data.total_federal_tax:>12,.0f} ${data.total_fica:>12,.0f} ${data.total_state_tax:>12,.0f} ${data.total_taxes:>12,.0f} {overall_eff_rate:>9.1%} ${data.total_take_home:>12,.0f}")
        print()
        print("=" * 110)
        print()


class ContributionsRenderer(BaseRenderer):
    """Renderer for yearly contributions to investment accounts."""
    
    def render(self, data: PlanData) -> None:
        """Render the yearly contributions breakdown.
        
        Args:
            data: PlanData containing all yearly calculations
        """
        print()
        print("=" * 130)
        print(f"{'YEARLY CONTRIBUTIONS':^130}")
        print("=" * 130)
        print()
        print(f"  {'Year':<6} {'401(k) Emp':>14} {'401(k) Empr':>14} {'401(k) Total':>14} {'HSA Emp':>12} {'HSA Empr':>12} {'Deferred':>14} {'Taxable':>14} {'Total':>14}")
        print(f"  {'-' * 6} {'-' * 14} {'-' * 14} {'-' * 14} {'-' * 12} {'-' * 12} {'-' * 14} {'-' * 14} {'-' * 14}")
        
        total_401k_employee = 0
        total_401k_employer = 0
        total_401k = 0
        total_hsa_employee = 0
        total_hsa_employer = 0
        total_deferred = 0
        total_taxable = 0
        total_all = 0
        
        for year in sorted(data.yearly_data.keys()):
            yd = data.yearly_data[year]
            
            if not yd.is_working_year:
                break
            
            year_total = yd.total_401k_contribution + yd.hsa_contribution + yd.deferred_comp_contribution + yd.taxable_contribution
            
            print(f"  {year:<6} ${yd.employee_401k_contribution:>12,.0f} ${yd.employer_401k_match:>12,.0f} ${yd.total_401k_contribution:>12,.0f} ${yd.employee_hsa:>10,.0f} ${yd.employer_hsa:>10,.0f} ${yd.deferred_comp_contribution:>12,.0f} ${yd.taxable_contribution:>12,.0f} ${year_total:>12,.0f}")
            
            total_401k_employee += yd.employee_401k_contribution
            total_401k_employer += yd.employer_401k_match
            total_401k += yd.total_401k_contribution
            total_hsa_employee += yd.employee_hsa
            total_hsa_employer += yd.employer_hsa
            total_deferred += yd.deferred_comp_contribution
            total_taxable += yd.taxable_contribution
            total_all += year_total
        
        print(f"  {'-' * 6} {'-' * 14} {'-' * 14} {'-' * 14} {'-' * 12} {'-' * 12} {'-' * 14} {'-' * 14} {'-' * 14}")
        print(f"  {'TOTAL':<6} ${total_401k_employee:>12,.0f} ${total_401k_employer:>12,.0f} ${total_401k:>12,.0f} ${total_hsa_employee:>10,.0f} ${total_hsa_employer:>10,.0f} ${total_deferred:>12,.0f} ${total_taxable:>12,.0f} ${total_all:>12,.0f}")
        print()
        print("=" * 130)
        print()


# Registry mapping mode names to renderer classes
RENDERER_REGISTRY = {
    'TaxDetails': TaxDetailsRenderer,
    'Balances': BalancesRenderer,
    'AnnualSummary': AnnualSummaryRenderer,
    'Contributions': ContributionsRenderer,
}
