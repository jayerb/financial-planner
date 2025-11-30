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
        print("INCOME BREAKDOWN")
        print("-" * 60)
        print(f"  {'Base Salary:':<40} ${yd.base_salary:>14,.2f}")
        print(f"  {'Bonus:':<40} ${yd.bonus:>14,.2f}")
        if yd.other_income > 0:
            print(f"  {'Other Income:':<40} ${yd.other_income:>14,.2f}")
        if yd.rsu_vested_value > 0:
            print(f"  {'RSUs Vested:':<40} ${yd.rsu_vested_value:>14,.2f}")
        if yd.espp_income > 0:
            print(f"  {'ESPP Income:':<40} ${yd.espp_income:>14,.2f}")
        if yd.short_term_capital_gains > 0:
            print(f"  {'Short-Term Capital Gains:':<40} ${yd.short_term_capital_gains:>14,.2f}")
        if yd.long_term_capital_gains > 0:
            print(f"  {'Long-Term Capital Gains:':<40} ${yd.long_term_capital_gains:>14,.2f}")
        if yd.deferred_comp_disbursement > 0:
            print(f"  {'Deferred Comp Disbursement:':<40} ${yd.deferred_comp_disbursement:>14,.2f}")
        print(f"  {'-' * 40}")
        print(f"  {'Gross Income:':<40} ${yd.gross_income:>14,.2f}")
        print()
        print(f"  {'Taxable Income (AGI):':<40} ${yd.adjusted_gross_income:>14,.2f}")
        
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
        print("=" * 136)
        print(f"{'ACCUMULATED BALANCES':^136}")
        print("=" * 136)
        print()
        print(f"  {'Year':<8} {'401(k) Contrib':>16} {'401(k) Balance':>18} {'Deferred Contrib':>18} {'Deferred Balance':>18} {'HSA Contrib':>14} {'HSA Balance':>16} {'Taxable Bal':>16}")
        print(f"  {'-' * 8} {'-' * 16} {'-' * 18} {'-' * 18} {'-' * 18} {'-' * 14} {'-' * 16} {'-' * 16}")
        
        for year in sorted(data.yearly_data.keys()):
            yd = data.yearly_data[year]
            print(f"  {year:<8} ${yd.total_401k_contribution:>14,.2f} ${yd.balance_ira:>16,.2f} ${yd.deferred_comp_contribution:>16,.2f} ${yd.balance_deferred_comp:>16,.2f} ${yd.hsa_contribution:>12,.2f} ${yd.balance_hsa:>14,.2f} ${yd.balance_taxable:>14,.2f}")
        
        print()
        print("=" * 136)
        print(f"{'FINAL BALANCES':^136}")
        print("=" * 136)
        print(f"  {'401(k) Balance:':<40} ${data.final_401k_balance:>18,.2f}")
        print(f"  {'Deferred Compensation Balance:':<40} ${data.final_deferred_comp_balance:>18,.2f}")
        print(f"  {'HSA Balance:':<40} ${data.final_hsa_balance:>18,.2f}")
        print(f"  {'Taxable Account Balance:':<40} ${data.final_taxable_balance:>18,.2f}")
        print(f"  {'-' * 60}")
        print(f"  {'TOTAL ASSETS:':<40} ${data.total_retirement_assets:>18,.2f}")
        print("=" * 136)
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


class MoneyMovementRenderer(BaseRenderer):
    """Renderer for yearly expenses vs income and money movement to/from taxable account."""
    
    def render(self, data: PlanData) -> None:
        """Render the yearly money movement breakdown.
        
        Shows take-home pay, expenses, and the net adjustment to taxable account.
        Positive adjustment = excess income added to taxable account.
        Negative adjustment = withdrawal from taxable account to cover expenses.
        
        Args:
            data: PlanData containing all yearly calculations
        """
        print()
        print("=" * 148)
        print(f"{'MONEY MOVEMENT - INCOME VS EXPENSES':^148}")
        print("=" * 148)
        print()
        print(f"  {'Year':<6} {'Take Home':>14} {'Annual Exp':>14} {'Special Exp':>14} {'Total Exp':>14} {'IRA W/D':>14} {'Taxable Adj':>14} {'Taxable Bal':>16} {'IRA Bal':>16}")
        print(f"  {'-' * 6} {'-' * 14} {'-' * 14} {'-' * 14} {'-' * 14} {'-' * 14} {'-' * 14} {'-' * 16} {'-' * 16}")
        
        total_take_home = 0
        total_annual_expenses = 0
        total_special_expenses = 0
        total_expenses = 0
        total_ira_withdrawal = 0
        total_adjustment = 0
        
        for year in sorted(data.yearly_data.keys()):
            yd = data.yearly_data[year]
            
            # Format adjustment with +/- sign
            adj_str = f"+${yd.taxable_account_adjustment:>11,.0f}" if yd.taxable_account_adjustment >= 0 else f"-${abs(yd.taxable_account_adjustment):>11,.0f}"
            ira_str = f"${yd.ira_withdrawal:>12,.0f}" if yd.ira_withdrawal > 0 else f"{'':>14}"
            
            print(f"  {year:<6} ${yd.take_home_pay:>12,.0f} ${yd.annual_expenses:>12,.0f} ${yd.special_expenses:>12,.0f} ${yd.total_expenses:>12,.0f} {ira_str:>14} {adj_str:>14} ${yd.balance_taxable:>14,.0f} ${yd.balance_ira:>14,.0f}")
            
            total_take_home += yd.take_home_pay
            total_annual_expenses += yd.annual_expenses
            total_special_expenses += yd.special_expenses
            total_expenses += yd.total_expenses
            total_ira_withdrawal += yd.ira_withdrawal
            total_adjustment += yd.taxable_account_adjustment
        
        print(f"  {'-' * 6} {'-' * 14} {'-' * 14} {'-' * 14} {'-' * 14} {'-' * 14} {'-' * 14} {'-' * 16} {'-' * 16}")
        
        adj_total_str = f"+${total_adjustment:>11,.0f}" if total_adjustment >= 0 else f"-${abs(total_adjustment):>11,.0f}"
        
        print(f"  {'TOTAL':<6} ${total_take_home:>12,.0f} ${total_annual_expenses:>12,.0f} ${total_special_expenses:>12,.0f} ${total_expenses:>12,.0f} ${total_ira_withdrawal:>12,.0f} {adj_total_str:>14}")
        print()
        print("=" * 148)
        print()


class CashFlowRenderer(BaseRenderer):
    """Renderer for cash flow showing expenses and funding sources breakdown."""
    
    def render(self, data: PlanData) -> None:
        """Render the cash flow breakdown.
        
        Shows total expenses for each year and how they are funded from
        different sources: take-home pay, deferred comp disbursements,
        IRA/401k withdrawals, and taxable account withdrawals.
        Also shows account balances at end of each year.
        
        Args:
            data: PlanData containing all yearly calculations
        """
        print()
        print("=" * 180)
        print(f"{'CASH FLOW - EXPENSE FUNDING BY SOURCE':^180}")
        print("=" * 180)
        print()
        print(f"  {'Year':<6} {'Total Exp':>14} {'|':^3} {'Take Home':>14} {'Def Comp':>14} {'IRA/401k':>14} {'Taxable':>14} {'|':^3} {'Surplus':>14} {'|':^3} {'Def Comp Bal':>14} {'IRA/401k Bal':>16} {'Taxable Bal':>14}")
        print(f"  {'-' * 6} {'-' * 14} {'-':^3} {'-' * 14} {'-' * 14} {'-' * 14} {'-' * 14} {'-':^3} {'-' * 14} {'-':^3} {'-' * 14} {'-' * 16} {'-' * 14}")
        
        total_expenses = 0
        total_take_home_used = 0
        total_deferred_comp_used = 0
        total_ira_used = 0
        total_taxable_used = 0
        total_surplus = 0
        
        for year in sorted(data.yearly_data.keys()):
            yd = data.yearly_data[year]
            
            # Calculate how expenses are funded
            expenses = yd.total_expenses
            
            # Available income sources (in order of priority)
            # 1. Take-home pay (after-tax income from work or capital gains)
            # 2. Deferred comp disbursements (already included in take_home_pay for retirement)
            # 3. IRA/401k withdrawals
            # 4. Taxable account withdrawals (if needed)
            
            # For working years: take_home_pay covers expenses, excess goes to taxable
            # For retirement: take_home_pay includes deferred comp disbursement income
            
            remaining_expenses = expenses
            
            # Take-home pay (net of deferred comp for clearer breakdown)
            if yd.is_working_year:
                take_home_available = yd.take_home_pay
                deferred_comp_income = 0
            else:
                # In retirement, take_home_pay includes the after-tax value of deferred comp
                # We want to show deferred comp separately
                deferred_comp_income = yd.deferred_comp_disbursement - (
                    yd.federal_tax + yd.state_tax) if yd.deferred_comp_disbursement > 0 else 0
                # Approximate: take_home is from capital gains and deferred comp
                # We'll attribute take_home proportionally
                if yd.gross_income > 0:
                    deferred_comp_fraction = yd.deferred_comp_disbursement / yd.gross_income
                    deferred_comp_income = yd.take_home_pay * deferred_comp_fraction
                    take_home_available = yd.take_home_pay - deferred_comp_income
                else:
                    deferred_comp_income = 0
                    take_home_available = yd.take_home_pay
            
            # Fund from take-home pay first
            take_home_used = min(take_home_available, remaining_expenses)
            remaining_expenses -= take_home_used
            
            # Fund from deferred comp (retirement years)
            deferred_comp_used = min(deferred_comp_income, remaining_expenses)
            remaining_expenses -= deferred_comp_used
            
            # Fund from IRA/401k withdrawal
            ira_used = min(yd.ira_withdrawal, remaining_expenses)
            remaining_expenses -= ira_used
            
            # Fund from taxable account (negative adjustment means withdrawal)
            taxable_withdrawal = -yd.taxable_account_adjustment if yd.taxable_account_adjustment < 0 else 0
            taxable_used = min(taxable_withdrawal, remaining_expenses)
            remaining_expenses -= taxable_used
            
            # Calculate surplus (positive taxable adjustment or excess income)
            surplus = yd.taxable_account_adjustment if yd.taxable_account_adjustment > 0 else 0
            
            # Format output
            take_home_str = f"${take_home_used:>12,.0f}" if take_home_used > 0 else f"{'':>14}"
            deferred_str = f"${deferred_comp_used:>12,.0f}" if deferred_comp_used > 0 else f"{'':>14}"
            ira_str = f"${ira_used:>12,.0f}" if ira_used > 0 else f"{'':>14}"
            taxable_str = f"${taxable_used:>12,.0f}" if taxable_used > 0 else f"{'':>14}"
            surplus_str = f"+${surplus:>11,.0f}" if surplus > 0 else f"{'':>14}"
            
            print(f"  {year:<6} ${yd.total_expenses:>12,.0f} {'|':^3} {take_home_str:>14} {deferred_str:>14} {ira_str:>14} {taxable_str:>14} {'|':^3} {surplus_str:>14} {'|':^3} ${yd.balance_deferred_comp:>12,.0f} ${yd.balance_ira:>14,.0f} ${yd.balance_taxable:>12,.0f}")
            
            # Accumulate totals
            total_expenses += yd.total_expenses
            total_take_home_used += take_home_used
            total_deferred_comp_used += deferred_comp_used
            total_ira_used += ira_used
            total_taxable_used += taxable_used
            total_surplus += surplus
        
        print(f"  {'-' * 6} {'-' * 14} {'-':^3} {'-' * 14} {'-' * 14} {'-' * 14} {'-' * 14} {'-':^3} {'-' * 14} {'-':^3} {'-' * 14} {'-' * 16} {'-' * 14}")
        
        # Format totals
        surplus_total_str = f"+${total_surplus:>11,.0f}" if total_surplus > 0 else f"{'':>14}"
        
        # Get final balances
        final_year = max(data.yearly_data.keys())
        final_yd = data.yearly_data[final_year]
        
        print(f"  {'TOTAL':<6} ${total_expenses:>12,.0f} {'|':^3} ${total_take_home_used:>12,.0f} ${total_deferred_comp_used:>12,.0f} ${total_ira_used:>12,.0f} ${total_taxable_used:>12,.0f} {'|':^3} {surplus_total_str:>14} {'|':^3} ${final_yd.balance_deferred_comp:>12,.0f} ${final_yd.balance_ira:>14,.0f} ${final_yd.balance_taxable:>12,.0f}")
        print()
        
        # Summary section
        total_funded = total_take_home_used + total_deferred_comp_used + total_ira_used + total_taxable_used
        print(f"  {'Funding Sources Summary:':40}")
        print(f"    {'Take-Home Pay:':<36} ${total_take_home_used:>14,.0f} ({100*total_take_home_used/total_funded if total_funded > 0 else 0:>5.1f}%)")
        print(f"    {'Deferred Compensation:':<36} ${total_deferred_comp_used:>14,.0f} ({100*total_deferred_comp_used/total_funded if total_funded > 0 else 0:>5.1f}%)")
        print(f"    {'IRA/401k Withdrawals:':<36} ${total_ira_used:>14,.0f} ({100*total_ira_used/total_funded if total_funded > 0 else 0:>5.1f}%)")
        print(f"    {'Taxable Account Withdrawals:':<36} ${total_taxable_used:>14,.0f} ({100*total_taxable_used/total_funded if total_funded > 0 else 0:>5.1f}%)")
        print(f"    {'-' * 52}")
        print(f"    {'Total Expenses Funded:':<36} ${total_funded:>14,.0f}")
        print(f"    {'Total Surplus to Taxable:':<36} ${total_surplus:>14,.0f}")
        print()
        
        # Final balances summary
        print(f"  {'Final Account Balances:':40}")
        print(f"    {'Deferred Compensation:':<36} ${final_yd.balance_deferred_comp:>14,.0f}")
        print(f"    {'IRA/401k:':<36} ${final_yd.balance_ira:>14,.0f}")
        print(f"    {'Taxable Account:':<36} ${final_yd.balance_taxable:>14,.0f}")
        print(f"    {'-' * 52}")
        total_final_balance = final_yd.balance_deferred_comp + final_yd.balance_ira + final_yd.balance_taxable
        print(f"    {'Total Assets:':<36} ${total_final_balance:>14,.0f}")
        print()
        print("=" * 180)
        print()


# Registry mapping mode names to renderer classes
RENDERER_REGISTRY = {
    'TaxDetails': TaxDetailsRenderer,
    'Balances': BalancesRenderer,
    'AnnualSummary': AnnualSummaryRenderer,
    'Contributions': ContributionsRenderer,
    'MoneyMovement': MoneyMovementRenderer,
    'CashFlow': CashFlowRenderer,
}
