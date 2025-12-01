"""Renderer classes for displaying financial planning results.

This module contains renderer classes that handle the presentation logic
for different types of financial planning outputs. Each renderer takes
the unified PlanData structure and extracts the fields it needs.
"""

import json
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from model.PlanData import PlanData, YearlyData
from model.field_metadata import get_short_name, get_field_info, wrap_header


# Path to built-in custom renderer configuration file (in source)
CUSTOM_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config', 'custom.json')

# Path to user's custom renderer configuration directory (at workspace root)
USER_CONFIG_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '../../report-config'))


def format_multiline_headers(columns: List[tuple], year_width: int = 6) -> tuple[List[str], str]:
    """Format column headers with multi-line wrapping support.
    
    Args:
        columns: List of (header_text, width) tuples for each column
        year_width: Width of the Year column (default 6)
        
    Returns:
        Tuple of (list of header lines, separator line)
    """
    # Wrap each column header
    wrapped_headers = []
    for header, width in columns:
        lines = wrap_header(header, width)
        wrapped_headers.append((lines, width))
    
    # Find max number of lines needed
    max_lines = max(len(lines) for lines, _ in wrapped_headers) if wrapped_headers else 1
    
    # Pad all headers to have the same number of lines (pad at top)
    for i, (lines, width) in enumerate(wrapped_headers):
        while len(lines) < max_lines:
            lines.insert(0, "")
    
    # Build header lines
    header_lines = []
    for line_idx in range(max_lines):
        if line_idx == max_lines - 1:
            # Last line includes "Year" label
            header_line = f"  {'Year':<{year_width}}"
        else:
            # Non-last lines have empty space for Year column
            header_line = f"  {'':<{year_width}}"
        
        for lines, width in wrapped_headers:
            header_line += f" {lines[line_idx]:>{width}}"
        header_lines.append(header_line)
    
    # Build separator line
    sep_line = f"  {'-' * year_width}"
    for _, width in wrapped_headers:
        sep_line += f" {'-' * width}"
    
    return header_lines, sep_line


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


def parse_year_range(year_range: str, data: PlanData) -> tuple:
    """Parse a year range string into start and end years.
    
    Args:
        year_range: String in format 'startYear-endYear', 'startYear-', or '-endYear'
        data: PlanData to get default years from
        
    Returns:
        Tuple of (start_year, end_year)
    """
    if '-' not in year_range:
        # Single year
        year = int(year_range)
        return (year, year)
    
    parts = year_range.split('-')
    start_year = int(parts[0]) if parts[0] else data.first_year
    end_year = int(parts[1]) if parts[1] else data.last_planning_year
    return (start_year, end_year)


class BalancesRenderer(BaseRenderer):
    """Renderer for accumulated balance display."""
    
    def __init__(self, start_year: int = None, end_year: int = None):
        """Initialize with optional year range.
        
        Args:
            start_year: First year to display (defaults to plan's first year)
            end_year: Last year to display (defaults to plan's last planning year)
        """
        self.start_year = start_year
        self.end_year = end_year
    
    def render(self, data: PlanData) -> None:
        """Render the accumulated balances.
        
        Args:
            data: PlanData containing all yearly calculations
        """
        print()
        print("=" * 150)
        print(f"{'ACCUMULATED BALANCES':^150}")
        print("=" * 150)
        print()
        
        # Define columns with their headers and widths (using field metadata)
        columns = [
            (get_short_name("total_401k_contribution"), 18),
            (get_short_name("balance_ira"), 16),
            (get_short_name("deferred_comp_contribution"), 18),
            (get_short_name("balance_deferred_comp"), 16),
            (get_short_name("hsa_contribution"), 14),
            (get_short_name("balance_hsa"), 14),
            (get_short_name("balance_taxable"), 16),
        ]
        
        header_lines, sep_line = format_multiline_headers(columns, year_width=8)
        for line in header_lines:
            print(line)
        print(sep_line)
        
        start = self.start_year if self.start_year is not None else data.first_year
        end = self.end_year if self.end_year is not None else data.last_planning_year
        
        for year in sorted(data.yearly_data.keys()):
            if year < start or year > end:
                continue
            yd = data.yearly_data[year]
            print(f"  {year:<8} ${yd.total_401k_contribution:>16,.2f} ${yd.balance_ira:>14,.2f} ${yd.deferred_comp_contribution:>16,.2f} ${yd.balance_deferred_comp:>14,.2f} ${yd.hsa_contribution:>12,.2f} ${yd.balance_hsa:>12,.2f} ${yd.balance_taxable:>14,.2f}")
        
        print()
        print("=" * 150)
        print(f"{'FINAL BALANCES':^150}")
        print("=" * 150)
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
    
    def __init__(self, start_year: int = None, end_year: int = None):
        """Initialize with optional year range.
        
        Args:
            start_year: First year to display (defaults to plan's first year)
            end_year: Last year to display (defaults to plan's last planning year)
        """
        self.start_year = start_year
        self.end_year = end_year
    
    def render(self, data: PlanData) -> None:
        """Render a summary table of income and taxes for each year.
        
        Args:
            data: PlanData containing all yearly calculations
        """
        print()
        print("=" * 118)
        print(f"{'ANNUAL INCOME AND TAX SUMMARY':^118}")
        print("=" * 118)
        print()
        
        # Define columns with their headers and widths (using field metadata)
        columns = [
            (get_short_name("gross_income"), 14),
            (get_short_name("federal_tax"), 14),
            (get_short_name("total_fica"), 14),
            (get_short_name("state_tax"), 14),
            (get_short_name("total_taxes"), 14),
            (get_short_name("effective_tax_rate"), 12),
            (get_short_name("take_home_pay"), 14),
        ]
        
        header_lines, sep_line = format_multiline_headers(columns)
        for line in header_lines:
            print(line)
        print(sep_line)
        
        start = self.start_year if self.start_year is not None else data.first_year
        end = self.end_year if self.end_year is not None else data.last_planning_year
        
        # Track totals for the filtered range
        total_gross = 0.0
        total_federal = 0.0
        total_fica = 0.0
        total_state = 0.0
        total_taxes = 0.0
        total_take_home = 0.0
        
        for year in sorted(data.yearly_data.keys()):
            if year < start or year > end:
                continue
            yd = data.yearly_data[year]
            print(f"  {year:<6} ${yd.gross_income:>12,.0f} ${yd.federal_tax:>12,.0f} ${yd.total_fica:>12,.0f} ${yd.state_tax:>12,.0f} ${yd.total_taxes:>12,.0f} {yd.effective_tax_rate:>11.1%} ${yd.take_home_pay:>12,.0f}")
            total_gross += yd.gross_income
            total_federal += yd.federal_tax
            total_fica += yd.total_fica
            total_state += yd.state_tax
            total_taxes += yd.total_taxes
            total_take_home += yd.take_home_pay
        
        print(sep_line)
        
        # Calculate overall effective rate for filtered range
        overall_eff_rate = total_taxes / total_gross if total_gross > 0 else 0
        
        print(f"  {'TOTAL':<6} ${total_gross:>12,.0f} ${total_federal:>12,.0f} ${total_fica:>12,.0f} ${total_state:>12,.0f} ${total_taxes:>12,.0f} {overall_eff_rate:>11.1%} ${total_take_home:>12,.0f}")
        print()
        print("=" * 118)
        print()


class ContributionsRenderer(BaseRenderer):
    """Renderer for yearly contributions to investment accounts."""
    
    def __init__(self, start_year: int = None, end_year: int = None):
        """Initialize with optional year range.
        
        Args:
            start_year: First year to display (defaults to plan's first year)
            end_year: Last year to display (defaults to plan's last planning year)
        """
        self.start_year = start_year
        self.end_year = end_year
    
    def render(self, data: PlanData) -> None:
        """Render the yearly contributions breakdown.
        
        Args:
            data: PlanData containing all yearly calculations
        """
        print()
        print("=" * 136)
        print(f"{'YEARLY CONTRIBUTIONS':^136}")
        print("=" * 136)
        print()
        
        # Define columns with their headers and widths (using field metadata)
        columns = [
            (get_short_name("employee_401k_contribution"), 14),
            (get_short_name("employer_401k_match"), 14),
            (get_short_name("total_401k_contribution"), 14),
            (get_short_name("employee_hsa"), 12),
            (get_short_name("employer_hsa"), 12),
            (get_short_name("deferred_comp_contribution"), 14),
            (get_short_name("taxable_contribution"), 14),
            (get_short_name("total_contributions"), 14),
        ]
        
        header_lines, sep_line = format_multiline_headers(columns)
        for line in header_lines:
            print(line)
        print(sep_line)
        
        start = self.start_year if self.start_year is not None else data.first_year
        end = self.end_year if self.end_year is not None else data.last_planning_year
        
        total_401k_employee = 0
        total_401k_employer = 0
        total_401k = 0
        total_hsa_employee = 0
        total_hsa_employer = 0
        total_deferred = 0
        total_taxable = 0
        total_all = 0
        
        for year in sorted(data.yearly_data.keys()):
            if year < start or year > end:
                continue
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
        
        print(sep_line)
        print(f"  {'TOTAL':<6} ${total_401k_employee:>12,.0f} ${total_401k_employer:>12,.0f} ${total_401k:>12,.0f} ${total_hsa_employee:>10,.0f} ${total_hsa_employer:>10,.0f} ${total_deferred:>12,.0f} ${total_taxable:>12,.0f} ${total_all:>12,.0f}")
        print()
        print("=" * 136)
        print()


class MoneyMovementRenderer(BaseRenderer):
    """Renderer for yearly expenses vs income and money movement to/from taxable account."""
    
    def __init__(self, start_year: int = None, end_year: int = None):
        """Initialize with optional year range.
        
        Args:
            start_year: First year to display (defaults to plan's first year)
            end_year: Last year to display (defaults to plan's last planning year)
        """
        self.start_year = start_year
        self.end_year = end_year
    
    def render(self, data: PlanData) -> None:
        """Render the yearly money movement breakdown.
        
        Shows take-home pay, expenses, and the net adjustment to taxable account.
        Positive adjustment = excess income added to taxable account.
        Negative adjustment = withdrawal from taxable account to cover expenses.
        
        Args:
            data: PlanData containing all yearly calculations
        """
        print()
        print("=" * 152)
        print(f"{'MONEY MOVEMENT - INCOME VS EXPENSES':^152}")
        print("=" * 152)
        print()
        
        # Define columns with their headers and widths (using field metadata)
        columns = [
            (get_short_name("take_home_pay"), 14),
            (get_short_name("annual_expenses"), 14),
            (get_short_name("special_expenses"), 14),
            (get_short_name("total_expenses"), 14),
            (get_short_name("ira_withdrawal"), 14),
            (get_short_name("taxable_account_adjustment"), 14),
            (get_short_name("balance_taxable"), 16),
            (get_short_name("balance_ira"), 16),
        ]
        
        header_lines, sep_line = format_multiline_headers(columns)
        for line in header_lines:
            print(line)
        print(sep_line)
        
        start = self.start_year if self.start_year is not None else data.first_year
        end = self.end_year if self.end_year is not None else data.last_planning_year
        
        total_take_home = 0
        total_annual_expenses = 0
        total_special_expenses = 0
        total_expenses = 0
        total_ira_withdrawal = 0
        total_adjustment = 0
        
        for year in sorted(data.yearly_data.keys()):
            if year < start or year > end:
                continue
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
        
        print(sep_line)
        
        adj_total_str = f"+${total_adjustment:>11,.0f}" if total_adjustment >= 0 else f"-${abs(total_adjustment):>11,.0f}"
        
        print(f"  {'TOTAL':<6} ${total_take_home:>12,.0f} ${total_annual_expenses:>12,.0f} ${total_special_expenses:>12,.0f} ${total_expenses:>12,.0f} ${total_ira_withdrawal:>12,.0f} {adj_total_str:>14}")
        print()
        print("=" * 152)
        print()


class CashFlowRenderer(BaseRenderer):
    """Renderer for cash flow showing expenses and funding sources breakdown."""
    
    def __init__(self, start_year: int = None, end_year: int = None):
        """Initialize with optional year range.
        
        Args:
            start_year: First year to display (defaults to plan's first year)
            end_year: Last year to display (defaults to plan's last planning year)
        """
        self.start_year = start_year
        self.end_year = end_year
    
    def render(self, data: PlanData) -> None:
        """Render the cash flow breakdown.
        
        Shows total expenses for each year and how they are funded from
        different sources: take-home pay, deferred comp disbursements,
        IRA/401k withdrawals, and taxable account withdrawals.
        Also shows account balances at end of each year.
        
        Args:
            data: PlanData containing all yearly calculations
        """
        report_width = 152
        print()
        print("=" * report_width)
        print(f"{'CASH FLOW - EXPENSE FUNDING BY SOURCE':^{report_width}}")
        print("=" * report_width)
        print()
        
        # Build multi-line headers for the complex CashFlow layout
        # Column groups: Expenses | Funding Sources | Surplus | Account Balances
        # All columns are 12 characters wide for consistency (using field metadata where applicable)
        expense_cols = [(get_short_name("total_expenses"), 12)]
        funding_cols = [
            (get_short_name("take_home_pay"), 12),
            (get_short_name("total_capital_gains"), 12),
            ("Deferred Comp", 12),  # Funding source, not a field
            ("IRA/401k", 12),  # Funding source, not a field
            ("Taxable", 12),  # Funding source, not a field
        ]
        surplus_cols = [("Surplus", 12)]  # Calculated value, not a field
        balance_cols = [
            (get_short_name("balance_deferred_comp"), 12),
            (get_short_name("balance_ira"), 12),
            (get_short_name("balance_taxable"), 12),
        ]
        
        # Get wrapped headers for each group
        all_cols = expense_cols + funding_cols + surplus_cols + balance_cols
        wrapped = []
        for header, width in all_cols:
            lines = wrap_header(header, width)
            wrapped.append((lines, width))
        
        max_lines = max(len(lines) for lines, _ in wrapped)
        
        # Pad headers
        for lines, _ in wrapped:
            while len(lines) < max_lines:
                lines.insert(0, "")
        
        # Print header lines with separators
        for line_idx in range(max_lines):
            if line_idx == max_lines - 1:
                header_line = f"  {'Year':<6}"
            else:
                header_line = f"  {'':<6}"
            
            col_idx = 0
            # Expense column
            lines, width = wrapped[col_idx]
            header_line += f" {lines[line_idx]:>{width}}"
            header_line += f" {'|':^3}"
            col_idx += 1
            
            # Funding columns
            for i in range(5):
                lines, width = wrapped[col_idx]
                header_line += f" {lines[line_idx]:>{width}}"
                col_idx += 1
            header_line += f" {'|':^3}"
            
            # Surplus column
            lines, width = wrapped[col_idx]
            header_line += f" {lines[line_idx]:>{width}}"
            header_line += f" {'|':^3}"
            col_idx += 1
            
            # Balance columns
            for i in range(3):
                lines, width = wrapped[col_idx]
                header_line += f" {lines[line_idx]:>{width}}"
                col_idx += 1
            
            print(header_line)
        
        # Print separator
        sep_line = f"  {'-' * 6} {'-' * 12} {'-':^3} {'-' * 12} {'-' * 12} {'-' * 12} {'-' * 12} {'-' * 12} {'-':^3} {'-' * 12} {'-':^3} {'-' * 12} {'-' * 12} {'-' * 12}"
        print(sep_line)
        
        start = self.start_year if self.start_year is not None else data.first_year
        end = self.end_year if self.end_year is not None else data.last_planning_year
        
        total_expenses = 0
        total_take_home_used = 0
        total_capital_gains = 0
        total_deferred_comp_used = 0
        total_ira_used = 0
        total_taxable_used = 0
        total_surplus = 0
        
        for year in sorted(data.yearly_data.keys()):
            if year < start or year > end:
                continue
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
            
            # Calculate total capital gains for the year
            capital_gains = yd.short_term_capital_gains + yd.long_term_capital_gains
            
            # Format output (12-char columns)
            take_home_str = f"${take_home_used:>10,.0f}" if take_home_used > 0 else f"{'':>12}"
            cap_gains_str = f"${capital_gains:>10,.0f}" if capital_gains > 0 else f"{'':>12}"
            deferred_str = f"${deferred_comp_used:>10,.0f}" if deferred_comp_used > 0 else f"{'':>12}"
            ira_str = f"${ira_used:>10,.0f}" if ira_used > 0 else f"{'':>12}"
            taxable_str = f"${taxable_used:>10,.0f}" if taxable_used > 0 else f"{'':>12}"
            surplus_str = f"+${surplus:>9,.0f}" if surplus > 0 else f"{'':>12}"
            # Balance columns - format as exactly 12-char strings ($ at position 1 to align with leftmost dash)
            def_bal_str = f"${yd.balance_deferred_comp:>11,.0f}"
            ira_bal_str = f"${yd.balance_ira:>11,.0f}"
            tax_bal_str = f"${yd.balance_taxable:>11,.0f}"
            
            print(f"  {year:<6} ${yd.total_expenses:>10,.0f} {'|':^3} {take_home_str:>12} {cap_gains_str:>12} {deferred_str:>12} {ira_str:>12} {taxable_str:>12} {'|':^3} {surplus_str:>12} {'|':^3} {def_bal_str} {ira_bal_str} {tax_bal_str}")
            
            # Accumulate totals
            total_expenses += yd.total_expenses
            total_take_home_used += take_home_used
            total_capital_gains += capital_gains
            total_deferred_comp_used += deferred_comp_used
            total_ira_used += ira_used
            total_taxable_used += taxable_used
            total_surplus += surplus
        
        print(f"  {'-' * 6} {'-' * 12} {'-':^3} {'-' * 12} {'-' * 12} {'-' * 12} {'-' * 12} {'-' * 12} {'-':^3} {'-' * 12} {'-':^3} {'-' * 12} {'-' * 12} {'-' * 12}")
        
        # Format totals (12-char columns)
        surplus_total_str = f"+${total_surplus:>9,.0f}" if total_surplus > 0 else f"{'':>12}"
        cap_gains_total_str = f"${total_capital_gains:>10,.0f}" if total_capital_gains > 0 else f"{'':>12}"
        
        # Get final balances for the filtered range
        final_year = min(end, max(data.yearly_data.keys()))
        final_yd = data.yearly_data[final_year]
        
        # Balance columns - format as exactly 12-char strings ($ at position 1 to align with leftmost dash)
        def_bal_total_str = f"${final_yd.balance_deferred_comp:>11,.0f}"
        ira_bal_total_str = f"${final_yd.balance_ira:>11,.0f}"
        tax_bal_total_str = f"${final_yd.balance_taxable:>11,.0f}"
        
        print(f"  {'TOTAL':<6} ${total_expenses:>10,.0f} {'|':^3} ${total_take_home_used:>10,.0f} {cap_gains_total_str:>12} ${total_deferred_comp_used:>10,.0f} ${total_ira_used:>10,.0f} ${total_taxable_used:>10,.0f} {'|':^3} {surplus_total_str:>12} {'|':^3} {def_bal_total_str} {ira_bal_total_str} {tax_bal_total_str}")
        print()
        
        # Summary section
        total_funded = total_take_home_used + total_deferred_comp_used + total_ira_used + total_taxable_used
        print(f"  {'Funding Sources Summary:':40}")
        print(f"    {'Take-Home Pay:':<36} ${total_take_home_used:>14,.0f} ({100*total_take_home_used/total_funded if total_funded > 0 else 0:>5.1f}%)")
        print(f"    {'Capital Gains (included in Take-Home):':<36} ${total_capital_gains:>14,.0f}")
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
        print("=" * report_width)
        print()


class CustomRenderer(BaseRenderer):
    """A generalized renderer that displays a table of specified fields.
    
    This renderer can be dynamically configured with a title and list of fields
    to display, making it easy to create custom views of the financial data.
    """
    
    # Maximum width for a column header before wrapping
    MAX_HEADER_WIDTH = 14
    
    def __init__(self, title: str, fields: List[str], start_year: int = None, end_year: int = None, show_totals: bool = True):
        """Initialize with a title and list of fields to display.
        
        Args:
            title: The title to display at the top of the table
            fields: List of field names from YearlyData to display as columns
            start_year: First year to display (defaults to plan's first year)
            end_year: Last year to display (defaults to plan's last planning year)
            show_totals: Whether to show a totals row at the bottom (default True)
        """
        self.title = title
        self.fields = fields
        self.start_year = start_year
        self.end_year = end_year
        self.show_totals = show_totals
    
    def _get_column_width(self, field: str) -> int:
        """Get the display width for a column based on the field type.
        
        For long field names, uses the max header width for wrapping.
        """
        short_name = get_short_name(field)
        if len(short_name) > self.MAX_HEADER_WIDTH:
            # For long names, get the max line width after wrapping
            wrapped = wrap_header(short_name, self.MAX_HEADER_WIDTH)
            return max(max(len(line) for line in wrapped), 12)
        return max(len(short_name) + 2, 12)
    
    def _get_header_lines(self) -> list[list[str]]:
        """Get wrapped header lines for all columns.
        
        Returns:
            List of lists, where each inner list contains the wrapped lines
            for one column header.
        """
        headers = []
        for field in self.fields:
            short_name = get_short_name(field)
            width = self._get_column_width(field)
            wrapped = wrap_header(short_name, width)
            headers.append(wrapped)
        return headers
    
    def _format_value(self, value: Any, field: str, width: int) -> str:
        """Format a value for display based on its type."""
        if value is None:
            return f"{'N/A':>{width}}"
        elif isinstance(value, bool):
            return f"{'Yes' if value else 'No':>{width}}"
        elif isinstance(value, float):
            # Check if it's a rate/percentage field
            if 'rate' in field.lower() or 'bracket' in field.lower() or 'fraction' in field.lower():
                return f"{value:>{width-1}.1%}"
            else:
                return f"${value:>{width-2},.0f}"
        elif isinstance(value, int):
            if field == 'year':
                return f"{value:<{width}}"
            return f"{value:>{width},}"
        else:
            return f"{str(value):>{width}}"
    
    def render(self, data: PlanData) -> None:
        """Render a table with the specified fields.
        
        Args:
            data: PlanData containing all yearly calculations
        """
        # Calculate column widths
        col_widths = {}
        for field in self.fields:
            col_widths[field] = self._get_column_width(field)
        
        # Calculate total table width
        year_width = 6
        total_width = year_width + 2 + sum(col_widths.values()) + len(self.fields) * 2
        total_width = max(total_width, len(self.title) + 10)
        
        # Print header
        print()
        print("=" * total_width)
        print(f"{self.title.upper():^{total_width}}")
        print("=" * total_width)
        print()
        
        # Print column headers (may span multiple lines)
        wrapped_headers = self._get_header_lines()
        max_header_lines = max(len(h) for h in wrapped_headers) if wrapped_headers else 1
        
        # Pad all headers to have the same number of lines
        for i, header_lines in enumerate(wrapped_headers):
            while len(header_lines) < max_header_lines:
                header_lines.insert(0, "")  # Pad at the top
        
        # Print each header line
        for line_idx in range(max_header_lines):
            if line_idx == max_header_lines - 1:
                # Last line includes "Year" label
                header_line = f"  {'Year':<{year_width}}"
            else:
                # Non-last lines have empty space for Year column
                header_line = f"  {'':<{year_width}}"
            
            for i, field in enumerate(self.fields):
                width = col_widths[field]
                text = wrapped_headers[i][line_idx]
                header_line += f" {text:>{width}}"
            print(header_line)
        
        # Print separator line
        sep = f"  {'-' * year_width}"
        for field in self.fields:
            sep += f" {'-' * col_widths[field]}"
        print(sep)
        
        # Determine year range
        start = self.start_year if self.start_year is not None else data.first_year
        end = self.end_year if self.end_year is not None else data.last_planning_year
        
        # Track totals for numeric fields
        totals = {field: 0.0 for field in self.fields}
        row_count = 0
        
        # Print data rows
        for year in sorted(data.yearly_data.keys()):
            if year < start or year > end:
                continue
            
            yd = data.yearly_data[year]
            row = f"  {year:<{year_width}}"
            
            for field in self.fields:
                value = getattr(yd, field, None)
                width = col_widths[field]
                row += f" {self._format_value(value, field, width)}"
                
                # Accumulate totals for numeric non-rate fields
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    if 'rate' not in field.lower() and 'bracket' not in field.lower() and 'fraction' not in field.lower() and field != 'year':
                        totals[field] += value
            
            print(row)
            row_count += 1
        
        # Print totals row if enabled
        if self.show_totals and row_count > 0:
            print(sep)
            total_row = f"  {'TOTAL':<{year_width}}"
            for field in self.fields:
                width = col_widths[field]
                value = totals[field]
                
                # Skip totals for rate/bracket fields, year, and boolean fields
                if 'rate' in field.lower() or 'bracket' in field.lower() or 'fraction' in field.lower() or field == 'year' or field == 'is_working_year':
                    total_row += f" {'':>{width}}"
                else:
                    total_row += f" ${value:>{width-2},.0f}"
            
            print(total_row)
        
        print()
        print("=" * total_width)
        print()


def create_custom_renderer(title: str, fields: List[str], start_year: int = None, end_year: int = None, show_totals: bool = True) -> CustomRenderer:
    """Factory function to create a CustomRenderer.
    
    Args:
        title: The title to display at the top of the table
        fields: List of field names from YearlyData to display as columns
        start_year: First year to display (defaults to plan's first year)
        end_year: Last year to display (defaults to plan's last planning year)
        show_totals: Whether to show a totals row at the bottom (default True)
        
    Returns:
        A configured CustomRenderer instance
    """
    return CustomRenderer(title, fields, start_year, end_year, show_totals)


def load_custom_renderers() -> Dict[str, dict]:
    """Load custom renderer configurations from the built-in config file.
    
    Returns:
        Dictionary mapping renderer names to their configurations
    """
    if not os.path.exists(CUSTOM_CONFIG_PATH):
        return {}
    
    try:
        with open(CUSTOM_CONFIG_PATH, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not load custom renderers from {CUSTOM_CONFIG_PATH}: {e}")
        return {}


def load_user_custom_renderers() -> Dict[str, dict]:
    """Load custom renderer configurations from all JSON files in the user's report-config directory.
    
    Returns:
        Dictionary mapping renderer names to their configurations (with source file info)
    """
    if not os.path.exists(USER_CONFIG_DIR):
        return {}
    
    all_configs = {}
    
    try:
        for filename in sorted(os.listdir(USER_CONFIG_DIR)):
            if filename.endswith('.json'):
                filepath = os.path.join(USER_CONFIG_DIR, filename)
                try:
                    with open(filepath, 'r') as f:
                        file_configs = json.load(f)
                        for name, config in file_configs.items():
                            # Add source file info to the config
                            config['_source_file'] = filename
                            all_configs[name] = config
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Warning: Could not load custom renderers from {filepath}: {e}")
    except OSError as e:
        print(f"Warning: Could not read report-config directory: {e}")
    
    return all_configs


def get_all_custom_configs() -> Dict[str, dict]:
    """Get all custom renderer configurations from both built-in and user directories.
    
    User configurations take precedence over built-in configurations with the same name.
    
    Returns:
        Dictionary mapping renderer names to their configurations
    """
    configs = load_custom_renderers()  # Built-in configs first
    user_configs = load_user_custom_renderers()  # User configs override
    configs.update(user_configs)
    return configs


def list_user_configs() -> List[Dict[str, Any]]:
    """List all user-defined custom renderer configurations.
    
    Returns:
        List of dicts with 'name', 'title', 'fields', 'source_file' keys
    """
    configs = load_user_custom_renderers()
    result = []
    for name, config in configs.items():
        result.append({
            'name': name,
            'title': config.get('title', name),
            'fields': config.get('fields', []),
            'show_totals': config.get('show_totals', True),
            'source_file': config.get('_source_file', 'unknown')
        })
    return result


def get_user_config(name: str) -> Optional[dict]:
    """Get a specific user configuration by name.
    
    Args:
        name: The name of the renderer configuration
        
    Returns:
        The configuration dict if found, None otherwise
    """
    configs = load_user_custom_renderers()
    return configs.get(name)


def save_user_config(name: str, config: dict, filename: str = 'custom.json') -> bool:
    """Save a custom renderer configuration to the user's report-config directory.
    
    Args:
        name: The name for the renderer configuration
        config: Configuration dict with 'title', 'fields', and optionally 'show_totals'
        filename: The JSON file to save to (default: 'custom.json')
        
    Returns:
        True if saved successfully, False otherwise
    """
    # Ensure the directory exists
    if not os.path.exists(USER_CONFIG_DIR):
        try:
            os.makedirs(USER_CONFIG_DIR)
        except OSError as e:
            print(f"Error: Could not create report-config directory: {e}")
            return False
    
    filepath = os.path.join(USER_CONFIG_DIR, filename)
    
    # Load existing configs from the file
    existing_configs = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                existing_configs = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass  # Start with empty dict if file is corrupted
    
    # Remove internal source file tracking before saving
    save_config = {k: v for k, v in config.items() if not k.startswith('_')}
    
    # Add/update the configuration
    existing_configs[name] = save_config
    
    try:
        with open(filepath, 'w') as f:
            json.dump(existing_configs, f, indent=4)
        return True
    except IOError as e:
        print(f"Error: Could not save configuration: {e}")
        return False


def delete_user_config(name: str) -> bool:
    """Delete a custom renderer configuration from the user's report-config directory.
    
    Args:
        name: The name of the renderer configuration to delete
        
    Returns:
        True if deleted successfully, False otherwise
    """
    # Find which file contains this config
    config = get_user_config(name)
    if config is None:
        print(f"Error: Configuration '{name}' not found")
        return False
    
    source_file = config.get('_source_file')
    if not source_file:
        print(f"Error: Could not determine source file for '{name}'")
        return False
    
    filepath = os.path.join(USER_CONFIG_DIR, source_file)
    
    try:
        with open(filepath, 'r') as f:
            file_configs = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error: Could not read configuration file: {e}")
        return False
    
    if name not in file_configs:
        print(f"Error: Configuration '{name}' not found in {source_file}")
        return False
    
    del file_configs[name]
    
    try:
        if file_configs:
            # Save remaining configs
            with open(filepath, 'w') as f:
                json.dump(file_configs, f, indent=4)
        else:
            # Delete empty file
            os.remove(filepath)
        return True
    except IOError as e:
        print(f"Error: Could not update configuration file: {e}")
        return False


def reload_renderer_registry() -> None:
    """Reload custom renderer configurations into the registry.
    
    This should be called after saving or deleting configurations
    to make them immediately available.
    """
    global RENDERER_REGISTRY
    
    # Start with base renderers
    RENDERER_REGISTRY.clear()
    RENDERER_REGISTRY.update({
        'TaxDetails': TaxDetailsRenderer,
        'Balances': BalancesRenderer,
        'AnnualSummary': AnnualSummaryRenderer,
        'Contributions': ContributionsRenderer,
        'MoneyMovement': MoneyMovementRenderer,
        'CashFlow': CashFlowRenderer,
    })
    
    # Load all custom configs (built-in and user)
    custom_configs = get_all_custom_configs()
    for name, config in custom_configs.items():
        RENDERER_REGISTRY[name] = get_custom_renderer_factory(name, config)


def create_custom_renderer_from_config(name: str, config: dict, start_year: int = None, end_year: int = None) -> CustomRenderer:
    """Create a CustomRenderer from a configuration dictionary.
    
    Args:
        name: The name of the renderer (used as fallback title)
        config: Configuration dict with 'title', 'fields', and optionally 'show_totals'
        start_year: First year to display (defaults to plan's first year)
        end_year: Last year to display (defaults to plan's last planning year)
        
    Returns:
        A configured CustomRenderer instance
    """
    title = config.get('title', name)
    fields = config.get('fields', [])
    show_totals = config.get('show_totals', True)
    
    return CustomRenderer(title, fields, start_year, end_year, show_totals)


def get_custom_renderer_factory(name: str, config: dict):
    """Create a factory function for a custom renderer configuration.
    
    This is used to create callable factories that can be stored in RENDERER_REGISTRY.
    
    Args:
        name: The name of the renderer
        config: Configuration dict with 'title', 'fields', and optionally 'show_totals'
        
    Returns:
        A factory function that creates CustomRenderer instances with optional year range
    """
    def factory(start_year: int = None, end_year: int = None) -> CustomRenderer:
        return create_custom_renderer_from_config(name, config, start_year, end_year)
    return factory


# Registry mapping mode names to renderer classes
RENDERER_REGISTRY = {
    'TaxDetails': TaxDetailsRenderer,
    'Balances': BalancesRenderer,
    'AnnualSummary': AnnualSummaryRenderer,
    'Contributions': ContributionsRenderer,
    'MoneyMovement': MoneyMovementRenderer,
    'CashFlow': CashFlowRenderer,
}

# Load custom renderers from both built-in and user config directories and add to registry
_custom_configs = get_all_custom_configs()
for _name, _config in _custom_configs.items():
    RENDERER_REGISTRY[_name] = get_custom_renderer_factory(_name, _config)
