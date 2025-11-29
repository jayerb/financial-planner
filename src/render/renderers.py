"""Renderer classes for displaying financial planning results.

This module contains renderer classes that handle the presentation logic
for different types of financial planning outputs. Each renderer takes
calculated results and formats them for display.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

from calc.balance_calculator import BalanceResult


class BaseRenderer(ABC):
    """Abstract base class for all renderers."""
    
    @abstractmethod
    def render(self, data: Any) -> None:
        """Render the data to output.
        
        Args:
            data: The data to render (type depends on the specific renderer)
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
    
    def render(self, results: Dict) -> None:
        """Render the tax details breakdown.
        
        Args:
            results: Dictionary containing tax calculation results from TakeHomeCalculator
        """
        # Calculate total taxes for summary
        total_federal = results['federal_tax']
        total_fica = results['total_social_security'] + results['medicare_charge'] + results['medicare_surcharge']
        total_state = results.get('state_tax', 0)
        total_taxes = total_federal + total_fica + total_state

        print()
        print("=" * 60)
        print(f"{'TAX SUMMARY FOR ' + str(self.tax_year):^60}")
        print("=" * 60)
        
        print()
        print("-" * 60)
        print("INCOME")
        print("-" * 60)
        print(f"  {'Gross Income:':<40} ${results['gross_income']:>14,.2f}")
        print(f"  {'RSU Vested:':<40} ${results['rsu_vested_value']:>14,.2f}")
        
        print()
        print("-" * 60)
        print("DEDUCTIONS")
        print("-" * 60)
        deductions = results['deductions']
        standard_deduction = deductions['standardDeduction']
        itemized_deduction = deductions.get('itemizedDeduction', 0)
        # Show which deduction type is being used
        if itemized_deduction > standard_deduction:
            print(f"  {'Itemized Deduction (SALT):':<40} ${itemized_deduction:>14,.2f}  <- used")
            print(f"  {'Standard Deduction:':<40} ${standard_deduction:>14,.2f}")
        else:
            print(f"  {'Standard Deduction:':<40} ${standard_deduction:>14,.2f}  <- used")
            if itemized_deduction > 0:
                print(f"  {'Itemized Deduction (SALT):':<40} ${itemized_deduction:>14,.2f}")
        print(f"  {'401(k) Contribution:':<40} ${deductions['max401k']:>14,.2f}")
        # Show employee HSA contribution (the tax-deductible portion)
        employee_hsa = deductions.get('employeeHSA', deductions['maxHSA'])
        max_hsa = deductions['maxHSA']
        if employee_hsa != max_hsa:
            print(f"  {'HSA Contribution (Employee):':<40} ${employee_hsa:>14,.2f}")
            employer_hsa = max_hsa - employee_hsa
            print(f"  {'HSA Contribution (Employer):':<40} ${employer_hsa:>14,.2f}")
        else:
            print(f"  {'HSA Contribution:':<40} ${max_hsa:>14,.2f}")
        print(f"  {'Medical/Dental/Vision:':<40} ${deductions['medicalDentalVision']:>14,.2f}")
        print(f"  {'-' * 40}")
        print(f"  {'Total Deductions:':<40} ${results['total_deductions']:>14,.2f}")
        
        print()
        print("-" * 60)
        print("DEFERRED INCOME (reduces Federal/State tax only)")
        print("-" * 60)
        print(f"  {'Base Salary Deferral:':<40} ${results.get('base_deferral', 0):>14,.2f}")
        print(f"  {'Bonus Deferral:':<40} ${results.get('bonus_deferral', 0):>14,.2f}")
        print(f"  {'-' * 40}")
        print(f"  {'Total Deferred:':<40} ${results.get('total_deferral', 0):>14,.2f}")
        
        print()
        print(f"  {'Adjusted Gross Income:':<40} ${results['adjusted_gross_income']:>14,.2f}")
        
        print()
        print("-" * 60)
        print("FEDERAL TAXES")
        print("-" * 60)
        print(f"  {'Ordinary Income Tax:':<40} ${results['ordinary_income_tax']:>14,.2f}")
        print(f"  {'Long-Term Capital Gains Tax:':<40} ${results['long_term_capital_gains_tax']:>14,.2f}")
        print(f"  {'-' * 40}")
        print(f"  {'Total Federal Tax:':<40} ${results['federal_tax']:>14,.2f}")
        print(f"  {'Marginal Bracket:':<40} {results['marginal_bracket']:>14.2%}")
        
        print()
        print("-" * 60)
        print("FICA TAXES")
        print("-" * 60)
        print(f"  {'Social Security + MA PFML:':<40} ${results['total_social_security']:>14,.2f}")
        print(f"  {'Medicare:':<40} ${results['medicare_charge']:>14,.2f}")
        print(f"  {'Medicare Surcharge:':<40} ${results['medicare_surcharge']:>14,.2f}")
        print(f"  {'-' * 40}")
        print(f"  {'Total FICA:':<40} ${total_fica:>14,.2f}")
        
        print()
        print("-" * 60)
        print("STATE TAXES")
        print("-" * 60)
        print(f"  {'State Income Tax:':<40} ${results.get('state_income_tax', 0):>14,.2f}")
        print(f"  {'State Short-Term Capital Gains Tax:':<40} ${results.get('state_short_term_capital_gains_tax', 0):>14,.2f}")
        print(f"  {'-' * 40}")
        print(f"  {'Total State Tax:':<40} ${total_state:>14,.2f}")
        
        print()
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        total_deferral = results.get('total_deferral', 0)
        print(f"  {'Gross Income:':<40} ${results['gross_income']:>14,.2f}")
        print(f"  {'Total Deductions:':<40} ${results['total_deductions']:>14,.2f}")
        print(f"  {'Total Deferred Income:':<40} ${total_deferral:>14,.2f}")
        print(f"  {'Total Federal Tax:':<40} ${total_federal:>14,.2f}")
        print(f"  {'Total FICA:':<40} ${total_fica:>14,.2f}")
        print(f"  {'Total State Tax:':<40} ${total_state:>14,.2f}")
        print(f"  {'-' * 40}")
        print(f"  {'TOTAL TAXES PAID:':<40} ${total_taxes:>14,.2f}")
        print(f"  {'TOTAL TO DEFERRED ACCOUNT:':<40} ${total_deferral:>14,.2f}")
        print()
        print("=" * 60)
        print(f"{'TAKE HOME PAY:':^44} ${results['take_home_pay']:>14,.2f}")
        print("=" * 60)
        print()


class BalancesRenderer(BaseRenderer):
    """Renderer for accumulated balance display."""
    
    def render(self, result: BalanceResult) -> None:
        """Render the accumulated balances.
        
        Args:
            result: BalanceResult containing yearly balances and final totals
        """
        print()
        print("=" * 116)
        print(f"{'ACCUMULATED BALANCES':^116}")
        print("=" * 116)
        print()
        print(f"  {'Year':<8} {'401(k) Contrib':>16} {'401(k) Balance':>18} {'Deferred Contrib':>18} {'Deferred Balance':>18} {'HSA Contrib':>14} {'HSA Balance':>16}")
        print(f"  {'-' * 8} {'-' * 16} {'-' * 18} {'-' * 18} {'-' * 18} {'-' * 14} {'-' * 16}")
        
        for yb in result.yearly_balances:
            print(f"  {yb.year:<8} ${yb.contrib_401k:>14,.2f} ${yb.balance_401k:>16,.2f} ${yb.deferred_contrib:>16,.2f} ${yb.deferred_balance:>16,.2f} ${yb.contrib_hsa:>12,.2f} ${yb.balance_hsa:>14,.2f}")
        
        print()
        print("=" * 116)
        print(f"{'FINAL BALANCES':^116}")
        print("=" * 116)
        print(f"  {'401(k) Balance:':<40} ${result.final_401k_balance:>18,.2f}")
        print(f"  {'Deferred Compensation Balance:':<40} ${result.final_deferred_balance:>18,.2f}")
        print(f"  {'HSA Balance:':<40} ${result.final_hsa_balance:>18,.2f}")
        print(f"  {'-' * 60}")
        print(f"  {'TOTAL RETIREMENT ASSETS:':<40} ${result.total_retirement_assets:>18,.2f}")
        print("=" * 116)
        print()


class AnnualSummaryRenderer(BaseRenderer):
    """Renderer for annual income and tax burden summary table."""
    
    def render(self, yearly_results: Dict[int, Dict]) -> None:
        """Render a summary table of income and taxes for each year.
        
        Args:
            yearly_results: Dictionary mapping year to tax calculation results
        """
        print()
        print("=" * 110)
        print(f"{'ANNUAL INCOME AND TAX SUMMARY':^110}")
        print("=" * 110)
        print()
        print(f"  {'Year':<6} {'Gross Income':>14} {'Federal Tax':>14} {'FICA':>14} {'State Tax':>14} {'Total Tax':>14} {'Eff Rate':>10} {'Take Home':>14}")
        print(f"  {'-' * 6} {'-' * 14} {'-' * 14} {'-' * 14} {'-' * 14} {'-' * 14} {'-' * 10} {'-' * 14}")
        
        total_gross = 0
        total_federal = 0
        total_fica = 0
        total_state = 0
        total_taxes = 0
        total_take_home = 0
        
        for year in sorted(yearly_results.keys()):
            results = yearly_results[year]
            
            gross_income = results['gross_income']
            federal_tax = results['federal_tax']
            fica = results['total_social_security'] + results['medicare_charge'] + results['medicare_surcharge']
            state_tax = results.get('state_tax', 0)
            year_total_tax = federal_tax + fica + state_tax
            take_home = results['take_home_pay']
            
            # Effective tax rate
            eff_rate = year_total_tax / gross_income if gross_income > 0 else 0
            
            print(f"  {year:<6} ${gross_income:>12,.0f} ${federal_tax:>12,.0f} ${fica:>12,.0f} ${state_tax:>12,.0f} ${year_total_tax:>12,.0f} {eff_rate:>9.1%} ${take_home:>12,.0f}")
            
            total_gross += gross_income
            total_federal += federal_tax
            total_fica += fica
            total_state += state_tax
            total_taxes += year_total_tax
            total_take_home += take_home
        
        print(f"  {'-' * 6} {'-' * 14} {'-' * 14} {'-' * 14} {'-' * 14} {'-' * 14} {'-' * 10} {'-' * 14}")
        
        # Calculate overall effective rate
        overall_eff_rate = total_taxes / total_gross if total_gross > 0 else 0
        
        print(f"  {'TOTAL':<6} ${total_gross:>12,.0f} ${total_federal:>12,.0f} ${total_fica:>12,.0f} ${total_state:>12,.0f} ${total_taxes:>12,.0f} {overall_eff_rate:>9.1%} ${total_take_home:>12,.0f}")
        print()
        print("=" * 110)
        print()


class ContributionsRenderer(BaseRenderer):
    """Renderer for yearly contributions to investment accounts."""
    
    def render(self, data: Dict) -> None:
        """Render the yearly contributions breakdown.
        
        Args:
            data: Dictionary containing:
                - yearly_results: Dict[int, Dict] from TakeHomeCalculator
                - investment_balances: Dict[int, dict] from InvestmentCalculator
                - last_working_year: int
        """
        yearly_results = data['yearly_results']
        investment_balances = data.get('investment_balances', {})
        last_working_year = data.get('last_working_year', max(yearly_results.keys()))
        
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
        
        for year in sorted(yearly_results.keys()):
            if year > last_working_year:
                break
                
            results = yearly_results[year]
            deductions = results.get('deductions', {})
            
            # 401(k) contributions
            employee_401k = deductions.get('max401k', 0)
            
            # Get employer match from investment balances if available
            inv_balance = investment_balances.get(year, {})
            contributions = inv_balance.get('contributions', {})
            employer_401k = contributions.get('employer_match', 0)
            total_401k_year = employee_401k + employer_401k
            
            # HSA contributions
            employee_hsa = deductions.get('employeeHSA', deductions.get('maxHSA', 0))
            max_hsa = deductions.get('maxHSA', 0)
            employer_hsa = max_hsa - employee_hsa
            
            # Deferred compensation
            deferred = results.get('total_deferral', 0)
            
            # Taxable account contribution (take home minus spending)
            # For now, we'll show 0 as taxable contributions aren't explicitly tracked
            taxable_contrib = 0
            
            # Total contributions for this year
            year_total = total_401k_year + employee_hsa + employer_hsa + deferred + taxable_contrib
            
            print(f"  {year:<6} ${employee_401k:>12,.0f} ${employer_401k:>12,.0f} ${total_401k_year:>12,.0f} ${employee_hsa:>10,.0f} ${employer_hsa:>10,.0f} ${deferred:>12,.0f} ${taxable_contrib:>12,.0f} ${year_total:>12,.0f}")
            
            total_401k_employee += employee_401k
            total_401k_employer += employer_401k
            total_401k += total_401k_year
            total_hsa_employee += employee_hsa
            total_hsa_employer += employer_hsa
            total_deferred += deferred
            total_taxable += taxable_contrib
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
