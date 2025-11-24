import os
import json
from tax.FederalDetails import FederalDetails
from tax.StateDetails import StateDetails
from tax.ESPPDetails import ESPPDetails


def calculate_take_home(spec: dict, tax_year: int = 2026) -> dict:
    """Calculate financials (gross income, taxes, deductions, take-home) from a spec dict.
    Returns a dict with keys:
      gross_income, total_deductions, adjusted_gross_income, federal_result (FederalResult),
      federal_tax, marginal_bracket, total_social_security, medicare_charge, medicare_surcharge, take_home_pay
    """
    final_year = spec.get('lastYear')
    inflation_rate = spec.get('federalBracketInflation')
    if final_year is None or inflation_rate is None:
        raise ValueError("spec must contain 'lastYear' and 'federalBracketInflation' fields.")

    fed = FederalDetails(inflation_rate, final_year)

    income_details = spec.get('income', {})
    base_salary = income_details.get('baseSalary', 0)
    bonus_fraction = income_details.get('bonusFraction', 0)
    other_income = income_details.get('otherIncome', 0)
    gross_income = base_salary + (base_salary * bonus_fraction) + other_income

    # ESPP: include taxable benefit from ESPP discount in gross income
    espp = ESPPDetails()
    espp_income = espp.taxable_from_spec(spec)
    gross_income = gross_income + espp_income

    total_deductions = fed.totalDeductions(tax_year)
    medical_dental_vision = spec.get('deductions', {}).get('medicalDentalVision', 0)
    adjusted_gross_income = gross_income - total_deductions - medical_dental_vision

    federal_result = fed.taxBurden(adjusted_gross_income, tax_year)
    federal_tax = federal_result.totalFederalTax
    marginal_bracket = federal_result.marginalBracket

    # Social Security
    ss_path = os.path.join(os.path.dirname(__file__), '../../reference/social-security.json')
    # adjust path: module is in src/calc so go up two levels
    ss_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'reference', 'social-security.json'))
    with open(ss_path, 'r') as f:
        ss = json.load(f)
    max_taxed_income = ss.get('maximumTaxedIncome', 0)
    employee_portion = ss.get('employeePortion', 0)
    ma_pfml = ss.get('maPFML', 0)
    ss_income = min(gross_income, max_taxed_income)
    total_social_security = ss_income * (employee_portion + ma_pfml)

    # Medicare
    medicare_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'reference', 'flat-tax-details.json'))
    with open(medicare_path, 'r') as f:
        medicare_details = json.load(f)
    medicare_rate = medicare_details.get('medicare', 0)
    surcharge_threshold = medicare_details.get('surchargeThreshold', 0)
    surcharge_rate = medicare_details.get('surchargeRate', 0)

    medical_dental_vision = spec.get('deductions', {}).get('medicalDentalVision', 0)
    life_premium = spec.get('companyProvidedLifeInsurance', {}).get('annualPremium', 0)
    medicare_base = gross_income - medical_dental_vision + life_premium
    medicare_charge = medicare_base * medicare_rate
    medicare_surcharge = 0
    if gross_income > surcharge_threshold:
        medicare_surcharge = (gross_income - surcharge_threshold) * surcharge_rate
    total_medicare = medicare_charge + medicare_surcharge

    # State tax: use StateDetails which accounts for 401k/HSA contributions and medical deductions
    state = StateDetails(inflation_rate, final_year)
    state_tax = state.taxBurden(gross_income, medical_dental_vision, year=tax_year)

    take_home_pay = gross_income - federal_tax - total_social_security - total_medicare - state_tax

    return {
        'gross_income': gross_income,
        'total_deductions': total_deductions,
        'adjusted_gross_income': adjusted_gross_income,
        'federal_result': federal_result,
        'federal_tax': federal_tax,
        'marginal_bracket': marginal_bracket,
        'total_social_security': total_social_security,
        'medicare_charge': medicare_charge,
        'medicare_surcharge': medicare_surcharge,
        'state_tax': state_tax,
        'take_home_pay': take_home_pay,
    }
