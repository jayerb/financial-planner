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

        first_year = spec.get('firstYear', 2026)
        last_working_year = spec.get('lastWorkingYear', first_year + 10)
        is_working_year = tax_year <= last_working_year

        income_details = spec.get('income', {})
        short_term_capital_gains = income_details.get('shortTermCapitalGains', 0)
        long_term_capital_gains = income_details.get('longTermCapitalGains', 0)
        
        # Working income only applies during working years
        if is_working_year:
            base_salary = income_details.get('baseSalary', 0)
            bonus_fraction = income_details.get('bonusFraction', 0)
            other_income = income_details.get('otherIncome', 0)
            
            # Calculate deferred income contributions
            base_deferral_fraction = income_details.get('baseDeferralFraction', 0)
            bonus_deferral_fraction = income_details.get('bonusDeferralFraction', 0)
            bonus_amount = base_salary * bonus_fraction
            base_deferral = base_salary * base_deferral_fraction
            bonus_deferral = bonus_amount * bonus_deferral_fraction
            total_deferral = base_deferral + bonus_deferral
            
            # ESPP: use injected ESPPDetails
            espp_income = income_details.get('esppIncome', self.espp.taxable_from_spec(spec))
            
            # RSU: add vested RSU value to gross income
            rsu_vested_value = self.rsu_calculator.vested_value.get(tax_year, 0)
            
            medical_dental_vision = spec.get('deductions', {}).get('medicalDentalVision', 0)
            life_premium = spec.get('companyProvidedLifeInsurance', {}).get('annualPremium', 0)
        else:
            # Post-working years: no salary, bonus, deferrals, ESPP, or RSUs
            base_salary = 0
            bonus_amount = 0
            other_income = 0
            base_deferral = 0
            bonus_deferral = 0
            total_deferral = 0
            espp_income = 0
            rsu_vested_value = 0
            medical_dental_vision = 0
            life_premium = 0
        
        # Short-term capital gains are taxed as ordinary income
        gross_income = base_salary + bonus_amount + other_income + short_term_capital_gains
        gross_income = gross_income + espp_income
        gross_income = gross_income + rsu_vested_value

        deductions = self.federal.totalDeductions(tax_year)
        # Only include medical deductions during working years
        if is_working_year:
            deductions['medicalDentalVision'] = medical_dental_vision
            deductions['total'] = deductions['total'] + medical_dental_vision
        else:
            # Post-working: no 401k or HSA contributions, only standard deduction
            deductions['max401k'] = 0
            deductions['maxHSA'] = 0
            deductions['medicalDentalVision'] = 0
            deductions['total'] = deductions['standardDeduction']
        total_deductions = deductions['total']
        
        # Adjusted gross income for federal/state taxes includes deferral reduction
        adjusted_gross_income = gross_income - total_deductions - total_deferral

        federal_result = self.federal.taxBurden(adjusted_gross_income, tax_year)
        federal_tax = federal_result.totalFederalTax
        marginal_bracket = federal_result.marginalBracket

        # Calculate long-term capital gains tax using special brackets
        ltcg_tax = self.federal.longTermCapitalGainsTax(adjusted_gross_income, long_term_capital_gains, tax_year)
        federal_result.longTermCapitalGainsTax = ltcg_tax
        
        # Total federal tax includes both ordinary income tax and LTCG tax
        total_federal_tax = federal_tax + ltcg_tax

        # Social Security (LTCG is not subject to Social Security tax)
        # Note: Deferrals do NOT reduce Social Security taxable income
        total_social_security = self.social_security.total_contribution(gross_income, tax_year)

        # Medicare
        # Note: Deferrals do NOT reduce Medicare taxable income
        medicare_base = gross_income - medical_dental_vision + life_premium
        medicare_charge = self.medicare.base_contribution(medicare_base)
        medicare_surcharge = self.medicare.surcharge(gross_income)
        total_medicare = medicare_charge + medicare_surcharge

        # State tax: use injected StateDetails
        # State taxes are also reduced by deferrals (use adjusted_gross_income which includes deferral reduction)
        state_taxable_income = gross_income - total_deferral + long_term_capital_gains
        state_income_tax = self.state.taxBurden(state_taxable_income, medical_dental_vision, year=tax_year)
        state_short_term_capital_gains_tax = self.state.shortTermCapitalGainsTax(short_term_capital_gains)
        state_tax = state_income_tax + state_short_term_capital_gains_tax

        # Take home pay: gross income minus all taxes and deferrals (deferrals go to deferred account, not take-home)
        take_home_pay = gross_income - total_federal_tax - total_social_security - total_medicare - state_tax - total_deferral

        return {
            'gross_income': gross_income,
            'total_deductions': total_deductions,
            'deductions': deductions,
            'base_deferral': base_deferral,
            'bonus_deferral': bonus_deferral,
            'total_deferral': total_deferral,
            'adjusted_gross_income': adjusted_gross_income,
            'federal_result': federal_result,
            'federal_tax': total_federal_tax,
            'ordinary_income_tax': federal_tax,
            'long_term_capital_gains_tax': ltcg_tax,
            'long_term_capital_gains': long_term_capital_gains,
            'short_term_capital_gains': short_term_capital_gains,
            'marginal_bracket': marginal_bracket,
            'total_social_security': total_social_security,
            'medicare_charge': medicare_charge,
            'medicare_surcharge': medicare_surcharge,
            'state_income_tax': state_income_tax,
            'state_short_term_capital_gains_tax': state_short_term_capital_gains_tax,
            'state_tax': state_tax,
            'take_home_pay': take_home_pay,
            'rsu_vested_value': rsu_vested_value
        }
