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
    "is_working_year": FieldInfo("Working", "True if still employed, False if retired"),
    
    # Income
    "base_salary": FieldInfo("Salary", "Annual base salary before deductions"),
    "bonus": FieldInfo("Bonus", "Annual bonus payment"),
    "other_income": FieldInfo("Other Inc", "Additional income (interest, dividends, etc.)"),
    "espp_income": FieldInfo("ESPP", "Employee Stock Purchase Plan taxable income"),
    "rsu_vested_value": FieldInfo("RSU Vest", "Value of RSUs vested during the year"),
    "short_term_capital_gains": FieldInfo("ST Gains", "Short-term capital gains (held < 1 year)"),
    "long_term_capital_gains": FieldInfo("LT Gains", "Long-term capital gains (held >= 1 year)"),
    "deferred_comp_disbursement": FieldInfo("Def Disb", "Deferred compensation disbursement"),
    "gross_income": FieldInfo("Gross Inc", "Total taxable income before deductions"),
    "earned_income_for_fica": FieldInfo("FICA Inc", "Income subject to FICA taxes"),
    
    # Deductions
    "standard_deduction": FieldInfo("Std Ded", "Standard deduction amount"),
    "itemized_deduction": FieldInfo("Item Ded", "Itemized deduction amount (SALT, etc.)"),
    "max_401k": FieldInfo("Max 401k", "Maximum 401(k) contribution limit"),
    "max_hsa": FieldInfo("Max HSA", "Maximum HSA contribution limit"),
    "employee_hsa": FieldInfo("Emp HSA", "Employee HSA contribution"),
    "employer_hsa": FieldInfo("Empr HSA", "Employer HSA contribution"),
    "medical_dental_vision": FieldInfo("Med/Dnt/Vis", "Pre-tax medical, dental, vision premiums"),
    "total_deductions": FieldInfo("Tot Ded", "Total deductions from gross income"),
    
    # Deferrals
    "base_deferral": FieldInfo("Base Def", "Salary deferred to deferred comp plan"),
    "bonus_deferral": FieldInfo("Bonus Def", "Bonus deferred to deferred comp plan"),
    "total_deferral": FieldInfo("Tot Def", "Total deferred compensation"),
    
    # Adjusted Income
    "adjusted_gross_income": FieldInfo("AGI", "Adjusted gross income (after deductions)"),
    
    # Federal Taxes
    "ordinary_income_tax": FieldInfo("Ord Tax", "Federal tax on ordinary income"),
    "long_term_capital_gains_tax": FieldInfo("LTCG Tax", "Federal tax on long-term capital gains"),
    "federal_tax": FieldInfo("Fed Tax", "Total federal income tax"),
    "marginal_bracket": FieldInfo("Marg %", "Marginal federal tax bracket"),
    
    # FICA Taxes
    "social_security_tax": FieldInfo("SS Tax", "Social Security tax (includes state PFML)"),
    "medicare_tax": FieldInfo("Med Tax", "Medicare tax"),
    "medicare_surcharge": FieldInfo("Med Surch", "Additional Medicare surcharge (high income)"),
    "total_fica": FieldInfo("FICA", "Total FICA taxes (SS + Medicare)"),
    
    # State Taxes
    "state_income_tax": FieldInfo("State Tax", "State income tax"),
    "state_short_term_capital_gains_tax": FieldInfo("ST ST CG", "State short-term capital gains tax"),
    "state_tax": FieldInfo("Tot State", "Total state taxes"),
    
    # Local Taxes
    "local_tax": FieldInfo("Local Tax", "Local/city income tax"),
    
    # Tax Summary
    "total_taxes": FieldInfo("Tot Taxes", "Total taxes paid (federal + FICA + state + local)"),
    "effective_tax_rate": FieldInfo("Eff Rate", "Effective tax rate (total taxes / gross income)"),
    "take_home_pay": FieldInfo("Take Home", "Net income after all taxes"),
    
    # Contributions
    "employee_401k_contribution": FieldInfo("Emp 401k", "Employee 401(k) contribution"),
    "employer_401k_match": FieldInfo("Match", "Employer 401(k) matching contribution"),
    "total_401k_contribution": FieldInfo("Tot 401k", "Total 401(k) contributions (employee + employer)"),
    "hsa_contribution": FieldInfo("HSA Contr", "Total HSA contribution (employee + employer)"),
    "deferred_comp_contribution": FieldInfo("Def Contr", "Deferred compensation contribution"),
    "taxable_contribution": FieldInfo("Tax Contr", "Contribution to taxable brokerage account"),
    "total_contributions": FieldInfo("Tot Contr", "Total retirement contributions"),
    
    # Expenses and Money Movement
    "annual_expenses": FieldInfo("Ann Exp", "Annual living expenses"),
    "special_expenses": FieldInfo("Spec Exp", "One-time special expenses"),
    "medical_premium": FieldInfo("Med Prem", "Medical/insurance premium (tracked all years)"),
    "medical_premium_expense": FieldInfo("Med Exp", "Medical premium expense (retirement only)"),
    "total_expenses": FieldInfo("Tot Exp", "Total annual expenses"),
    "income_expense_difference": FieldInfo("Net Cash", "Take home minus total expenses"),
    "hsa_withdrawal": FieldInfo("HSA Wdraw", "HSA withdrawal for medical expenses"),
    "ira_withdrawal": FieldInfo("IRA Wdraw", "401(k)/IRA withdrawal to cover expenses"),
    "taxable_account_adjustment": FieldInfo("Tax Adj", "Taxable account deposit/withdrawal"),
    
    # Account Appreciation
    "appreciation_ira": FieldInfo("IRA Appr", "401(k)/IRA investment growth"),
    "appreciation_deferred_comp": FieldInfo("Def Appr", "Deferred comp investment growth"),
    "appreciation_hsa": FieldInfo("HSA Appr", "HSA investment growth"),
    "appreciation_taxable": FieldInfo("Tax Appr", "Taxable account investment growth"),
    "total_appreciation": FieldInfo("Tot Appr", "Total investment appreciation"),
    
    # Account Balances
    "balance_ira": FieldInfo("IRA Bal", "401(k)/IRA end-of-year balance"),
    "balance_deferred_comp": FieldInfo("Def Bal", "Deferred comp end-of-year balance"),
    "balance_hsa": FieldInfo("HSA Bal", "HSA end-of-year balance"),
    "balance_taxable": FieldInfo("Tax Bal", "Taxable account end-of-year balance"),
    "total_assets": FieldInfo("Tot Assets", "Total end-of-year assets"),
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
