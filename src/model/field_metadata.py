"""Field metadata for YearlyData fields.

This module provides descriptions and short names for all YearlyData fields.
Short names are used as column headers in tables and the shell 'get' command.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class FieldInfo:
    """Metadata for a single field."""
    short_name: str  # Column header (unique, concise)
    description: str  # Full description of the field


# Field metadata dictionary mapping field names to their info
FIELD_METADATA: Dict[str, FieldInfo] = {
    # Year Info
    "year": FieldInfo("Year", "Calendar year"),
    "is_working_year": FieldInfo("Working Year", "True if still employed, False if retired"),
    
    # Income
    "base_salary": FieldInfo("Base Salary", "Annual base salary before deductions"),
    "bonus": FieldInfo("Bonus", "Annual bonus payment"),
    "other_income": FieldInfo("Other Income", "Additional income (interest, dividends, etc.)"),
    "espp_income": FieldInfo("ESPP Income", "Employee Stock Purchase Plan taxable income"),
    "rsu_vested_value": FieldInfo("RSU Vested", "Value of RSUs vested during the year"),
    "short_term_capital_gains": FieldInfo("Short-Term Capital Gains", "Short-term capital gains (held < 1 year)"),
    "long_term_capital_gains": FieldInfo("Long-Term Capital Gains", "Long-term capital gains (held >= 1 year)"),
    "total_capital_gains": FieldInfo("Total Capital Gains", "Total capital gains (short-term + long-term)"),
    "deferred_comp_disbursement": FieldInfo("Deferred Comp Disbursement", "Deferred compensation disbursement"),
    "gross_income": FieldInfo("Gross Income", "Total taxable income before deductions"),
    "earned_income_for_fica": FieldInfo("FICA Income", "Income subject to FICA taxes"),
    
    # Deductions
    "standard_deduction": FieldInfo("Standard Deduction", "Standard deduction amount"),
    "itemized_deduction": FieldInfo("Itemized Deduction", "Itemized deduction amount (SALT, etc.)"),
    "max_401k": FieldInfo("Max 401(k)", "Maximum 401(k) contribution limit"),
    "max_hsa": FieldInfo("Max HSA", "Maximum HSA contribution limit"),
    "employee_hsa": FieldInfo("Employee HSA", "Employee HSA contribution"),
    "employer_hsa": FieldInfo("Employer HSA", "Employer HSA contribution"),
    "medical_dental_vision": FieldInfo("Medical/Dental/Vision", "Pre-tax medical, dental, vision premiums"),
    "total_deductions": FieldInfo("Total Deductions", "Total deductions from gross income"),
    
    # Deferrals
    "base_deferral": FieldInfo("Base Deferral", "Salary deferred to deferred comp plan"),
    "bonus_deferral": FieldInfo("Bonus Deferral", "Bonus deferred to deferred comp plan"),
    "total_deferral": FieldInfo("Total Deferral", "Total deferred compensation"),
    
    # Adjusted Income
    "adjusted_gross_income": FieldInfo("AGI", "Adjusted gross income (after deductions)"),
    
    # Federal Taxes
    "ordinary_income_tax": FieldInfo("Ordinary Income Tax", "Federal tax on ordinary income"),
    "long_term_capital_gains_tax": FieldInfo("Long-Term CG Tax", "Federal tax on long-term capital gains"),
    "federal_tax": FieldInfo("Federal Tax", "Total federal income tax"),
    "marginal_bracket": FieldInfo("Marginal Bracket", "Marginal federal tax bracket"),
    
    # FICA Taxes
    "social_security_tax": FieldInfo("Social Security Tax", "Social Security tax (includes state PFML)"),
    "medicare_tax": FieldInfo("Medicare Tax", "Medicare tax"),
    "medicare_surcharge": FieldInfo("Medicare Surcharge", "Additional Medicare surcharge (high income)"),
    "total_fica": FieldInfo("Total FICA", "Total FICA taxes (SS + Medicare)"),
    
    # State Taxes
    "state_income_tax": FieldInfo("State Income Tax", "State income tax"),
    "state_short_term_capital_gains_tax": FieldInfo("State Short-Term CG Tax", "State short-term capital gains tax"),
    "state_tax": FieldInfo("Total State Tax", "Total state taxes"),
    
    # Local Taxes
    "local_tax": FieldInfo("Local Tax", "Local/city income tax"),
    
    # Tax Summary
    "total_taxes": FieldInfo("Total Taxes", "Total taxes paid (federal + FICA + state + local)"),
    "effective_tax_rate": FieldInfo("Eff Rate", "Effective tax rate (total taxes / gross income)"),
    "take_home_pay": FieldInfo("Take Home", "Net income after all taxes"),
    
    # Paycheck Take-Home Pay (working years)
    "paycheck_take_home_initial": FieldInfo("Paycheck Initial", "Paycheck take-home with Social Security tax"),
    "paycheck_take_home_after_ss_limit": FieldInfo("Paycheck After SS", "Paycheck take-home after SS wage base exceeded"),
    "paycheck_take_home_after_medicare_surcharge": FieldInfo("Paycheck After Surcharge", "Paycheck take-home after Medicare surcharge"),
    "pay_period_ss_limit_reached": FieldInfo("SS Limit Period", "Pay period when SS wage base exceeded (0 if never)"),
    "pay_period_medicare_surcharge_starts": FieldInfo("Surcharge Period", "Pay period when Medicare surcharge starts (0 if never)"),
    "pay_schedule": FieldInfo("Pay Schedule", "Pay frequency (e.g., BiWeekly, Monthly, SemiMonthly)"),
    "pay_periods_per_year": FieldInfo("Pay Periods", "Number of pay periods per year"),
    "annual_pretax_deductions": FieldInfo("Annual Pretax", "Total annual pre-tax deductions (401k, HSA, etc.)"),
    "annual_posttax_deductions": FieldInfo("Annual Posttax", "Total annual post-tax deductions (ESPP)"),
    
    # Pay Statement (per pay period amounts)
    "paycheck_gross": FieldInfo("Gross Pay", "Gross pay per pay period"),
    "paycheck_federal_tax": FieldInfo("Federal W/H", "Federal tax withholding per pay period"),
    "paycheck_state_tax": FieldInfo("State W/H", "State tax withholding per pay period"),
    "paycheck_social_security": FieldInfo("SS W/H", "Social Security tax per pay period"),
    "paycheck_medicare": FieldInfo("Medicare W/H", "Medicare tax per pay period"),
    "paycheck_401k": FieldInfo("401(k) Ded", "401(k) contribution per pay period"),
    "paycheck_hsa": FieldInfo("HSA Ded", "HSA contribution per pay period"),
    "paycheck_deferred_comp": FieldInfo("Def Comp Ded", "Deferred compensation per pay period"),
    "paycheck_medical_dental": FieldInfo("Med/Dental Ded", "Medical/dental/vision deduction per pay period"),
    "paycheck_espp": FieldInfo("ESPP Ded", "ESPP contribution per pay period (post-tax)"),
    "paycheck_net": FieldInfo("Net Pay", "Net pay per pay period (take-home)"),
    
    # Bonus Paycheck (annual bonus payment)
    "bonus_paycheck_gross": FieldInfo("Bonus Gross", "Gross bonus amount"),
    "bonus_paycheck_federal_tax": FieldInfo("Bonus Federal", "Federal tax on bonus (supplemental rate)"),
    "bonus_paycheck_state_tax": FieldInfo("Bonus State", "State tax on bonus"),
    "bonus_paycheck_social_security": FieldInfo("Bonus SS", "Social Security tax on bonus"),
    "bonus_paycheck_medicare": FieldInfo("Bonus Medicare", "Medicare tax on bonus"),
    "bonus_paycheck_deferred_comp": FieldInfo("Bonus Deferred", "Deferred compensation from bonus"),
    "bonus_paycheck_net": FieldInfo("Bonus Net", "Net bonus after all deductions"),
    
    # Contributions
    "employee_401k_contribution": FieldInfo("Employee 401(k)", "Employee 401(k) contribution"),
    "employer_401k_match": FieldInfo("Employer Match", "Employer 401(k) matching contribution"),
    "total_401k_contribution": FieldInfo("Total 401(k)", "Total 401(k) contributions (employee + employer)"),
    "hsa_contribution": FieldInfo("HSA Contribution", "Total HSA contribution (employee + employer)"),
    "deferred_comp_contribution": FieldInfo("Deferred Contribution", "Deferred compensation contribution"),
    "taxable_contribution": FieldInfo("Taxable Contribution", "Contribution to taxable brokerage account"),
    "total_contributions": FieldInfo("Total Contributions", "Total retirement contributions"),
    
    # Expenses and Money Movement
    "annual_expenses": FieldInfo("Annual Expenses", "Annual living expenses"),
    "special_expenses": FieldInfo("Special Expenses", "One-time special expenses"),
    "travel_expenses": FieldInfo("Travel Expenses", "Annual travel expenses"),
    "medical_premium": FieldInfo("Medical Premium", "Medical/insurance premium (tracked all years)"),
    "medical_premium_expense": FieldInfo("Medical Premium Expense", "Medical premium expense (retirement only)"),
    "total_expenses": FieldInfo("Total Expenses", "Total annual expenses"),
    "income_expense_difference": FieldInfo("Net Cash Flow", "Take home minus total expenses"),
    "hsa_withdrawal": FieldInfo("HSA Withdrawal", "HSA withdrawal for medical expenses"),
    "ira_withdrawal": FieldInfo("IRA Withdrawal", "401(k)/IRA withdrawal to cover expenses"),
    "taxable_account_adjustment": FieldInfo("Taxable Adjustment", "Taxable account deposit/withdrawal"),
    
    # Account Appreciation
    "appreciation_ira": FieldInfo("IRA Appreciation", "401(k)/IRA investment growth"),
    "appreciation_deferred_comp": FieldInfo("Deferred Appreciation", "Deferred comp investment growth"),
    "appreciation_hsa": FieldInfo("HSA Appreciation", "HSA investment growth"),
    "appreciation_taxable": FieldInfo("Taxable Appreciation", "Taxable account investment growth"),
    "total_appreciation": FieldInfo("Total Appreciation", "Total investment appreciation"),
    
    # Account Balances
    "balance_ira": FieldInfo("IRA Balance", "401(k)/IRA end-of-year balance"),
    "balance_deferred_comp": FieldInfo("Deferred Balance", "Deferred comp end-of-year balance"),
    "balance_hsa": FieldInfo("HSA Balance", "HSA end-of-year balance"),
    "balance_taxable": FieldInfo("Taxable Balance", "Taxable account end-of-year balance"),
    "total_assets": FieldInfo("Total Assets", "Total end-of-year assets"),
}


def get_short_name(field_name: str) -> str:
    """Get the short name for a field, or the field name if not found."""
    info = FIELD_METADATA.get(field_name)
    return info.short_name if info else field_name


def get_description(field_name: str) -> str:
    """Get the description for a field, or empty string if not found."""
    info = FIELD_METADATA.get(field_name)
    return info.description if info else ""


def get_field_info(field_name: str) -> FieldInfo | None:
    """Get the full FieldInfo for a field, or None if not found."""
    return FIELD_METADATA.get(field_name)


def wrap_header(text: str, max_width: int) -> list[str]:
    """Wrap a header text into multiple lines to fit within max_width.
    
    Words are split on spaces and distributed across lines to minimize
    the total number of lines while staying within max_width.
    
    Args:
        text: The header text to wrap
        max_width: Maximum width per line
        
    Returns:
        List of strings, each representing a line
    """
    if len(text) <= max_width:
        return [text]
    
    words = text.split()
    lines = []
    current_line = ""
    
    for word in words:
        if not current_line:
            current_line = word
        elif len(current_line) + 1 + len(word) <= max_width:
            current_line += " " + word
        else:
            lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    return lines
