from typing import Dict

from tax.FederalDetails import FederalDetails
from tax.StateDetails import StateDetails
from tax.ESPPDetails import ESPPDetails
from tax.SocialSecurityDetails import SocialSecurityDetails
from tax.MedicareDetails import MedicareDetails
from calc.rsu_calculator import RSUCalculator


class TakeHomeCalculator:
    """Calculator that computes take-home pay using injected detail providers.

    Pass hydrated instances of `FederalDetails`, `StateDetails`, and `ESPPDetails`
    into the constructor. This keeps file I/O in the caller (e.g., `Program.py`) and
    makes the calculation logic easy to unit test.
    """

    def __init__(self, federal: FederalDetails, state: StateDetails, espp: ESPPDetails,
                 social_security: SocialSecurityDetails, medicare: MedicareDetails,
                 rsu_calculator: RSUCalculator):
        self.federal = federal
        self.state = state
        self.espp = espp
        self.social_security = social_security
        self.medicare = medicare
        self.rsu_calculator = rsu_calculator

    def calculate(self, spec: dict, tax_year: int = 2026) -> Dict:
        final_year = spec.get('lastPlanningYear')
        inflation_rate = spec.get('federalBracketInflation')
        if final_year is None or inflation_rate is None:
            raise ValueError("spec must contain 'lastYear' and 'federalBracketInflation' fields.")

        income_details = spec.get('income', {})
        base_salary = income_details.get('baseSalary', 0)
        bonus_fraction = income_details.get('bonusFraction', 0)
        other_income = income_details.get('otherIncome', 0)
        gross_income = base_salary + (base_salary * bonus_fraction) + other_income

        # ESPP: use injected ESPPDetails
        espp_income = income_details.get('esppIncome', self.espp.taxable_from_spec(spec))
        gross_income = gross_income + espp_income

        # RSU: add vested RSU value to gross income
        rsu_vested_value = self.rsu_calculator.vested_value[tax_year]
        gross_income = gross_income + rsu_vested_value

        total_deductions = self.federal.totalDeductions(tax_year)
        medical_dental_vision = spec.get('deductions', {}).get('medicalDentalVision', 0)
        adjusted_gross_income = gross_income - total_deductions - medical_dental_vision

        federal_result = self.federal.taxBurden(adjusted_gross_income, tax_year)
        federal_tax = federal_result.totalFederalTax
        marginal_bracket = federal_result.marginalBracket

        # Social Security
        total_social_security = self.social_security.total_contribution(gross_income, tax_year)

        # Medicare
        life_premium = spec.get('companyProvidedLifeInsurance', {}).get('annualPremium', 0)
        medicare_base = gross_income - medical_dental_vision + life_premium
        medicare_charge = self.medicare.base_contribution(medicare_base)
        medicare_surcharge = self.medicare.surcharge(gross_income)
        total_medicare = medicare_charge + medicare_surcharge

        # State tax: use injected StateDetails
        state_tax = self.state.taxBurden(gross_income, medical_dental_vision, year=tax_year)

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
            'rsu_vested_value': rsu_vested_value
        }
