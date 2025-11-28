import os
import json
from typing import Optional


class StateDetails:
    def __init__(self, inflation_rate: float, final_year: int):
        self.inflation_rate = inflation_rate
        self.final_year = final_year

        # load flat-tax-details.json for state rate and standard deduction
        flat_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'reference', 'flat-tax-details.json'))
        with open(flat_path, 'r') as f:
            self.flat = json.load(f)

        # load federal-details.json to read base max contribution values
        fed_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'reference', 'federal-details.json'))
        with open(fed_path, 'r') as f:
            self.fed = json.load(f)

        # Handle new taxYears array format
        tax_years = self.fed.get('taxYears', [])
        if tax_years:
            # Use the first year's data as the base
            base_year_data = tax_years[0]
            self.base_year = base_year_data.get('year')
            self.base_max_contrib = base_year_data.get('maxContributions', {})
        else:
            # Fallback to old format
            self.base_year = self.fed.get('taxYear', None)
            self.base_max_contrib = self.fed.get('maxContributions', {})

    def _inflate(self, amount: float, to_year: int) -> float:
        if amount is None:
            return 0.0
        if self.base_year is None or to_year is None or self.inflation_rate is None:
            return amount
        years = to_year - self.base_year
        try:
            return amount * ((1.0 + float(self.inflation_rate)) ** years)
        except Exception:
            return amount

    def taxBurden(self, gross_income: float, medical_dental_vision: float, year: Optional[int] = None) -> float:
        """Calculate state tax burden given gross income and medical/dental/vision deductions.

        Calculation rules:
        - State taxable income = gross_income - (401k + HSA contributions) - medical_dental_vision - state_standard_deduction
        - State tax = state_rate * max(0, state taxable income)
        Contributions and deductions are inflated from the federal base year to the requested year.
        """
        tax_year = year if year is not None else self.final_year

        state = self.flat.get('state', {})
        state_rate = state.get('rate', 0)
        state_sd = state.get('standardDeduction', 0)

        # inflate state standard deduction to requested year (if inflation provided)
        state_sd_inflated = self._inflate(state_sd, tax_year)

        c401k = self.base_max_contrib.get('401k', 0)
        hsa = self.base_max_contrib.get('HSA', 0)

        c401k_inflated = self._inflate(c401k, tax_year)
        hsa_inflated = self._inflate(hsa, tax_year)

        state_taxable = gross_income - (c401k_inflated + hsa_inflated) - (medical_dental_vision or 0) - state_sd_inflated
        taxable = max(0.0, state_taxable)
        return taxable * state_rate

    def shortTermCapitalGainsTax(self, short_term_gains: float) -> float:
        """Calculate state short term capital gains tax.

        Args:
            short_term_gains: The amount of short term capital gains.

        Returns:
            The state tax on short term capital gains.
        """
        state = self.flat.get('state', {})
        stcg_rate = state.get('shortTermCapitalGains', 0)
        return max(0.0, short_term_gains) * stcg_rate
