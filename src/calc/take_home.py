from typing import Dict, Optional

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
                 rsu_calculator: RSUCalculator,
                 deferred_comp_calculator: Optional['DeferredCompCalculator'] = None):
        self.federal = federal
        self.state = state
        self.espp = espp
        self.social_security = social_security
        self.medicare = medicare
        self.rsu_calculator = rsu_calculator
        self.deferred_comp_calculator = deferred_comp_calculator
        self._taxable_balances: Dict[int, float] = {}
    
    def set_deferred_comp_calculator(self, calculator: 'DeferredCompCalculator') -> None:
        """Set the deferred compensation calculator after initialization.
        
        This is needed because the deferred comp calculator requires yearly deferrals
        which are computed by this calculator.
        
        Args:
            calculator: The DeferredCompCalculator instance
        """
        self.deferred_comp_calculator = calculator
    
    def set_taxable_balances(self, balances: Dict[int, float]) -> None:
        """Set the taxable account balances for each year.
        
        Used to calculate capital gains as a percentage of the account balance.
        
        Args:
            balances: Dictionary mapping year to taxable account balance
        """
        self._taxable_balances = balances

    def calculate(self, spec: dict, tax_year: int = 2026) -> Dict:
        final_year = spec.get('lastPlanningYear')
        inflation_rate = spec.get('federalBracketInflation')
        if final_year is None or inflation_rate is None:
            raise ValueError("spec must contain 'lastYear' and 'federalBracketInflation' fields.")

        first_year = spec.get('firstYear', 2026)
        last_working_year = spec.get('lastWorkingYear', first_year + 10)
        is_working_year = tax_year <= last_working_year
        
        # Get employer HSA contribution (base amount that will be inflated)
        investments = spec.get('investments', {})
        base_employer_hsa = investments.get('hsaEmployerContribution', 0.0)
        
        # Inflate employer HSA contribution from first year to tax year
        years_from_first = tax_year - first_year
        if years_from_first > 0 and is_working_year:
            employer_hsa_contribution = base_employer_hsa * ((1 + inflation_rate) ** years_from_first)
        elif is_working_year:
            employer_hsa_contribution = base_employer_hsa
        else:
            employer_hsa_contribution = 0.0

        first_year = spec.get('firstYear', 2026)
        last_working_year = spec.get('lastWorkingYear', first_year + 10)
        is_working_year = tax_year <= last_working_year

        income_details = spec.get('income', {})
        
        # Capital gains calculation - supports both fixed amounts and percentage-based
        # If percentage fields exist, calculate from taxable balance; otherwise use fixed amounts
        investments = spec.get('investments', {})
        taxable_balance = self._taxable_balances.get(tax_year, investments.get('taxableBalance', 0))
        
        if 'shortTermCapitalGainsPercent' in income_details:
            short_term_capital_gains = taxable_balance * income_details.get('shortTermCapitalGainsPercent', 0)
        else:
            short_term_capital_gains = income_details.get('shortTermCapitalGains', 0)
        
        if 'longTermCapitalGainsPercent' in income_details:
            long_term_capital_gains = taxable_balance * income_details.get('longTermCapitalGainsPercent', 0)
        else:
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
            
            # ESPP: use esppIncome from spec only for first year, then calculate from discount
            first_year = spec.get('firstYear', 2026)
            if tax_year == first_year and 'esppIncome' in income_details:
                espp_income = income_details.get('esppIncome', 0)
            else:
                espp_income = self.espp.taxable_from_spec(spec)
            
            # RSU: add vested RSU value to gross income
            rsu_vested_value = self.rsu_calculator.vested_value.get(tax_year, 0)
            
            # Medical/dental/vision with inflation
            base_medical = spec.get('deductions', {}).get('medicalDentalVision', 0)
            medical_inflation = spec.get('deductions', {}).get('medicalInflationRate', 0.0)
            if years_from_first > 0 and medical_inflation > 0:
                medical_dental_vision = base_medical * ((1 + medical_inflation) ** years_from_first)
            else:
                medical_dental_vision = base_medical
            
            life_premium = spec.get('companyProvidedLifeInsurance', {}).get('annualPremium', 0)
            
            # No deferred comp disbursement during working years
            deferred_comp_disbursement = 0
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
            
            # Get deferred compensation disbursement for this year
            if self.deferred_comp_calculator:
                deferred_comp_disbursement = self.deferred_comp_calculator.get_disbursement(tax_year)
            else:
                deferred_comp_disbursement = 0
        
        # Short-term capital gains are taxed as ordinary income (for income tax purposes)
        gross_income = base_salary + bonus_amount + other_income + short_term_capital_gains
        gross_income = gross_income + espp_income
        gross_income = gross_income + rsu_vested_value
        
        # Deferred comp disbursement is taxable income but NOT subject to FICA
        # Track it separately for FICA exclusion
        gross_income_for_tax = gross_income + deferred_comp_disbursement
        
        # FICA only applies to earned income (wages, salary, bonus, RSUs, ESPP)
        # Capital gains and deferred comp disbursements are NOT subject to FICA
        earned_income_for_fica = base_salary + bonus_amount + other_income + espp_income + rsu_vested_value

        # Get deductions with employer HSA contribution to calculate employee-only HSA deduction
        deductions = self.federal.totalDeductions(tax_year, employer_hsa_contribution)
        # Only include medical deductions during working years
        if is_working_year:
            deductions['medicalDentalVision'] = medical_dental_vision
            deductions['total'] = deductions['total'] + medical_dental_vision
        else:
            # Post-working: no 401k or HSA contributions, only standard deduction
            deductions['max401k'] = 0
            deductions['maxHSA'] = 0
            deductions['employeeHSA'] = 0
            deductions['medicalDentalVision'] = 0
            deductions['total'] = deductions['standardDeduction']
        total_deductions = deductions['total']
        
        # Adjusted gross income for federal/state taxes includes deferral reduction
        # Use gross_income_for_tax which includes deferred comp disbursement
        adjusted_gross_income = gross_income_for_tax - total_deductions - total_deferral

        federal_result = self.federal.taxBurden(adjusted_gross_income, tax_year)
        federal_tax = federal_result.totalFederalTax
        marginal_bracket = federal_result.marginalBracket

        # Calculate long-term capital gains tax using special brackets
        ltcg_tax = self.federal.longTermCapitalGainsTax(adjusted_gross_income, long_term_capital_gains, tax_year)
        federal_result.longTermCapitalGainsTax = ltcg_tax
        
        # Total federal tax includes both ordinary income tax and LTCG tax
        total_federal_tax = federal_tax + ltcg_tax

        # Social Security only applies to earned income (wages, salary, bonus, RSUs, ESPP)
        # Note: Deferrals do NOT reduce Social Security taxable income
        # Note: Capital gains and deferred comp disbursements are NOT subject to Social Security
        total_social_security = self.social_security.total_contribution(earned_income_for_fica, tax_year)

        # Medicare only applies to earned income (wages, salary, bonus, RSUs, ESPP)
        # Note: Deferrals do NOT reduce Medicare taxable income
        # Note: Capital gains and deferred comp disbursements are NOT subject to Medicare
        medicare_base = earned_income_for_fica - medical_dental_vision + life_premium
        medicare_charge = self.medicare.base_contribution(medicare_base)
        medicare_surcharge = self.medicare.surcharge(earned_income_for_fica)
        total_medicare = medicare_charge + medicare_surcharge

        # State tax: use injected StateDetails
        # State taxes are also reduced by deferrals (use adjusted_gross_income which includes deferral reduction)
        # Deferred comp disbursements ARE subject to state income tax
        state_taxable_income = gross_income_for_tax - total_deferral + long_term_capital_gains
        state_income_tax = self.state.taxBurden(state_taxable_income, medical_dental_vision, year=tax_year, employer_hsa_contribution=employer_hsa_contribution)
        state_short_term_capital_gains_tax = self.state.shortTermCapitalGainsTax(short_term_capital_gains)
        state_tax = state_income_tax + state_short_term_capital_gains_tax

        # Take home pay: gross income minus all taxes and deferrals (deferrals go to deferred account, not take-home)
        # Include deferred comp disbursement in take home (it's income received)
        take_home_pay = gross_income_for_tax - total_federal_tax - total_social_security - total_medicare - state_tax - total_deferral

        return {
            'gross_income': gross_income_for_tax,  # Total taxable income including deferred comp
            'earned_income_for_fica': earned_income_for_fica,
            'deferred_comp_disbursement': deferred_comp_disbursement,
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
            'rsu_vested_value': rsu_vested_value,
            'espp_income': espp_income
        }
