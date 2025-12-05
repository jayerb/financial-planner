"""Unified plan calculator that builds yearly data in three phases.

This calculator creates a complete PlanData object containing all
financial calculations for every year in the planning horizon.

The calculation is organized into three distinct loops:
1. Working years - income, contributions, taxes while employed
2. Deferred comp withdrawal years - retirement with disbursements
3. Post-withdrawal years - retirement without disbursements
"""

from model.PlanData import YearlyData, PlanData
from tax.FederalDetails import FederalDetails
from tax.StateDetails import StateDetails
from tax.ESPPDetails import ESPPDetails
from tax.SocialSecurityDetails import SocialSecurityDetails
from tax.MedicareDetails import MedicareDetails
from calc.rsu_calculator import RSUCalculator


class PlanCalculator:
    """Calculator that builds complete plan data in three phases.
    
    Uses incremental calculations based on prior year values to avoid
    redundant inflation calculations.
    """
    
    def __init__(self, 
                 federal: FederalDetails,
                 state: StateDetails,
                 espp: ESPPDetails,
                 social_security: SocialSecurityDetails,
                 medicare: MedicareDetails,
                 rsu_calculator: RSUCalculator):
        self.federal = federal
        self.state = state
        self.espp = espp
        self.social_security = social_security
        self.medicare = medicare
        self.rsu_calculator = rsu_calculator
    
    def calculate(self, spec: dict) -> PlanData:
        """Calculate complete financial plan data for all years.
        
        Args:
            spec: The program specification dictionary
            
        Returns:
            PlanData containing all yearly calculations and totals
        """
        first_year = spec.get('firstYear', 2026)
        last_working_year = spec.get('lastWorkingYear', first_year + 10)
        last_planning_year = spec.get('lastPlanningYear', last_working_year + 30)
        inflation_rate = spec.get('federalBracketInflation', 0.03)
        
        # Extract spec values
        income_spec = spec.get('income', {})
        investments_spec = spec.get('investments', {})
        deductions_spec = spec.get('deductions', {})
        deferred_comp_spec = spec.get('deferredCompensationPlan', {})
        local_tax_spec = spec.get('localTax', {})
        pay_schedule_spec = spec.get('paySchedule', {})
        
        # Pay schedule: BiWeekly = 26 pay periods, BiMonthly = 24 pay periods
        pay_schedule = pay_schedule_spec.get('schedule', 'BiWeekly')
        pay_periods_per_year = 26 if pay_schedule == 'BiWeekly' else 24
        bonus_pay_period = pay_schedule_spec.get('bonusPayPeriod', 17)
        
        # Initial values from spec
        initial_base_salary = income_spec.get('baseSalary', 0)
        bonus_fraction = income_spec.get('bonusFraction', 0)
        salary_increase_rate = income_spec.get('annualBaseIncreaseFraction', 0)
        other_income = income_spec.get('otherIncome', 0)
        base_deferral_fraction = income_spec.get('baseDeferralFraction', 0)
        bonus_deferral_fraction = income_spec.get('bonusDeferralFraction', 0)
        short_term_cg_percent = income_spec.get('realizedShortTermCapitalGainsPercent', 0)
        long_term_cg_percent = income_spec.get('realizedLongTermCapitalGainsPercent', 0)
        
        # Investment parameters
        initial_taxable = investments_spec.get('taxableBalance', 0)
        taxable_appreciation = investments_spec.get('taxableAppreciationRate', 0.06)
        initial_tax_deferred = investments_spec.get('taxDeferredBalance', 0)
        tax_deferred_appreciation = investments_spec.get('taxDeferredAppreciationRate', 0.08)
        initial_hsa = investments_spec.get('hsaBalance', 0)
        hsa_appreciation = investments_spec.get('hsaAppreciationRate', 0.07)
        employer_401k_match_percent = investments_spec.get('employer401kMatchPercent', 0)
        employer_401k_match_max_salary_percent = investments_spec.get('employer401kMatchMaxSalaryPercent', 0)
        initial_employer_hsa = investments_spec.get('hsaEmployerContribution', 0)
        initial_hsa_withdrawal = investments_spec.get('hsaAnnualWithdrawal', 0)
        hsa_withdrawal_inflation = investments_spec.get('hsaWithdrawalInflationRate', 0.04)
        
        # Birth year for Medicare eligibility calculation (age 65)
        birth_year = spec.get('birthYear', first_year - 55)  # Default assumes age 55 at first year
        medicare_eligibility_year = birth_year + 65
        
        # Deferred comp parameters
        deferred_comp_growth = deferred_comp_spec.get('annualGrowthFraction', 0.05)
        disbursement_years = deferred_comp_spec.get('disbursementYears', 10)
        
        # Medical parameters
        initial_medical = deductions_spec.get('medicalDentalVision', 0)
        medical_inflation = deductions_spec.get('medicalInflationRate', 0.04)
        
        # Local tax parameters
        initial_local_tax = local_tax_spec.get('realEstate', 0)
        local_tax_inflation = local_tax_spec.get('inflationRate', 0.03)
        
        # Insurance parameters
        insurance_spec = spec.get('insurance', {})
        initial_insurance_premium = insurance_spec.get('fullInsurancePremiums', 0)
        initial_medicare_premium = insurance_spec.get('medicarePremiums', 0)
        premium_inflation = insurance_spec.get('premiumInflationRate', 0.04)
        
        # Expense parameters
        expenses_spec = spec.get('expenses', {})
        initial_annual_expenses = expenses_spec.get('annualAmount', 0)
        expense_inflation = expenses_spec.get('inflationRate', 0.03)
        special_expenses = {se['year']: se['amount'] for se in expenses_spec.get('specialExpenses', [])}
        initial_travel_expenses = expenses_spec.get('travelAmount', 0)
        travel_inflation = expenses_spec.get('travelInflationRate', expense_inflation)  # Default to general expense inflation
        travel_retirement_multiplier = expenses_spec.get('travelRetirementMultiplier', 1.0)
        
        # Life insurance
        life_premium = spec.get('companyProvidedLifeInsurance', {}).get('annualPremium', 0)
        
        # Initialize plan data
        plan = PlanData(
            first_year=first_year,
            last_working_year=last_working_year,
            last_planning_year=last_planning_year
        )
        
        # Track running values that get inflated/accumulated year over year
        current_salary = initial_base_salary
        current_medical = initial_medical
        current_employer_hsa = initial_employer_hsa
        current_local_tax = initial_local_tax
        current_annual_expenses = initial_annual_expenses
        current_travel_expenses = initial_travel_expenses
        current_insurance_premium = initial_insurance_premium
        current_medicare_premium = initial_medicare_premium
        current_hsa_withdrawal = initial_hsa_withdrawal
        current_max_hsa = 0  # Will be set from last working year for retirement contributions
        
        # Track balances
        balance_taxable = initial_taxable
        balance_401k = initial_tax_deferred
        balance_hsa = initial_hsa
        balance_deferred_comp = 0.0
        
        # Deferred comp disbursement boundaries
        disbursement_start = last_working_year + 1
        disbursement_end = disbursement_start + disbursement_years - 1
        
        # ============================================================
        # LOOP 1: Working Years
        # ============================================================
        for year in range(first_year, last_working_year + 1):
            yd = YearlyData(year=year, is_working_year=True)
            
            # Apply inflation from prior year (except first year)
            if year > first_year:
                current_salary = current_salary * (1 + salary_increase_rate)
                current_medical = current_medical * (1 + medical_inflation)
                current_employer_hsa = current_employer_hsa * (1 + inflation_rate)
                current_local_tax = current_local_tax * (1 + local_tax_inflation)
                current_annual_expenses = current_annual_expenses * (1 + expense_inflation)
                current_travel_expenses = current_travel_expenses * (1 + travel_inflation)
                current_insurance_premium = current_insurance_premium * (1 + premium_inflation)
                current_medicare_premium = current_medicare_premium * (1 + premium_inflation)
                current_hsa_withdrawal = current_hsa_withdrawal * (1 + hsa_withdrawal_inflation)
                
                # Calculate appreciation amounts before applying growth
                yd.appreciation_taxable = balance_taxable * taxable_appreciation
                yd.appreciation_ira = balance_401k * tax_deferred_appreciation
                yd.appreciation_hsa = balance_hsa * hsa_appreciation
                yd.appreciation_deferred_comp = balance_deferred_comp * deferred_comp_growth
                yd.total_appreciation = (yd.appreciation_taxable + yd.appreciation_ira + 
                                        yd.appreciation_hsa + yd.appreciation_deferred_comp)
                
                # Apply growth to balances
                balance_taxable = balance_taxable + yd.appreciation_taxable
                balance_401k = balance_401k + yd.appreciation_ira
                balance_hsa = balance_hsa + yd.appreciation_hsa
                balance_deferred_comp = balance_deferred_comp + yd.appreciation_deferred_comp
            
            # Income
            yd.base_salary = current_salary
            yd.bonus = current_salary * bonus_fraction
            yd.other_income = other_income
            yd.medical_dental_vision = current_medical
            yd.local_tax = current_local_tax
            yd.medical_premium = current_insurance_premium  # Track premium (employer covers during working years)
            
            # Deferrals
            yd.base_deferral = current_salary * base_deferral_fraction
            yd.bonus_deferral = yd.bonus * bonus_deferral_fraction
            yd.total_deferral = yd.base_deferral + yd.bonus_deferral
            
            # ESPP income
            if year == first_year and 'esppIncome' in income_spec:
                yd.espp_income = income_spec.get('esppIncome', 0)
            else:
                yd.espp_income = self.espp.taxable_from_spec(spec)
            
            # RSU income
            yd.rsu_vested_value = self.rsu_calculator.vested_value.get(year, 0)
            
            # Realized capital gains (withdrawn from taxable account)
            yd.short_term_capital_gains = balance_taxable * short_term_cg_percent
            yd.long_term_capital_gains = balance_taxable * long_term_cg_percent
            
            # HSA contributions
            yd.employer_hsa = current_employer_hsa
            
            # Gross income (includes all realized capital gains)
            yd.gross_income = (yd.base_salary + yd.bonus + yd.other_income + 
                              yd.short_term_capital_gains + yd.long_term_capital_gains +
                              yd.espp_income + yd.rsu_vested_value)
            
            # Earned income for FICA excludes capital gains
            yd.earned_income_for_fica = (yd.base_salary + yd.bonus + yd.other_income + 
                                         yd.espp_income + yd.rsu_vested_value)
            
            # State tax (for SALT itemized deduction)
            # gross_income already includes LTCG now
            state_taxable = yd.gross_income - yd.total_deferral
            preliminary_state_tax = self.state.taxBurden(state_taxable, yd.medical_dental_vision, 
                                                          year=year, employer_hsa_contribution=yd.employer_hsa)
            
            # Federal deductions
            deductions = self.federal.totalDeductions(year, yd.employer_hsa, 
                                                       preliminary_state_tax, yd.local_tax)
            
            yd.standard_deduction = deductions['standardDeduction']
            yd.itemized_deduction = deductions.get('itemizedDeduction', 0)
            yd.max_401k = deductions['max401k']
            yd.max_hsa = deductions['maxHSA']
            yd.employee_hsa = deductions.get('employeeHSA', deductions['maxHSA'])
            yd.total_deductions = deductions['total'] + yd.medical_dental_vision
            
            # Adjusted gross income
            yd.adjusted_gross_income = yd.gross_income - yd.total_deductions - yd.total_deferral
            
            # Federal taxes
            federal_result = self.federal.taxBurden(yd.adjusted_gross_income, year)
            yd.ordinary_income_tax = federal_result.totalFederalTax
            yd.marginal_bracket = federal_result.marginalBracket
            yd.long_term_capital_gains_tax = self.federal.longTermCapitalGainsTax(
                yd.adjusted_gross_income, yd.long_term_capital_gains, year)
            yd.federal_tax = yd.ordinary_income_tax + yd.long_term_capital_gains_tax
            
            # FICA taxes
            yd.social_security_tax = self.social_security.total_contribution(yd.earned_income_for_fica, year)
            medicare_base = yd.earned_income_for_fica - yd.medical_dental_vision + life_premium
            yd.medicare_tax = self.medicare.base_contribution(medicare_base)
            yd.medicare_surcharge = self.medicare.surcharge(yd.earned_income_for_fica)
            yd.total_fica = yd.social_security_tax + yd.medicare_tax + yd.medicare_surcharge
            
            # State taxes
            yd.state_income_tax = preliminary_state_tax
            yd.state_short_term_capital_gains_tax = self.state.shortTermCapitalGainsTax(yd.short_term_capital_gains)
            yd.state_tax = yd.state_income_tax + yd.state_short_term_capital_gains_tax
            
            # Total taxes and take home
            yd.total_taxes = yd.federal_tax + yd.total_fica + yd.state_tax
            yd.effective_tax_rate = yd.total_taxes / yd.gross_income if yd.gross_income > 0 else 0
            yd.take_home_pay = yd.gross_income - yd.total_taxes - yd.total_deferral
            
            # Paycheck take-home pay calculations (for working years)
            # These show how take-home changes as SS wage base and Medicare surcharge thresholds are crossed
            self._calculate_paycheck_take_home(yd, year, life_premium, pay_periods_per_year, bonus_pay_period)
            
            # Expenses and money movement
            yd.annual_expenses = current_annual_expenses
            yd.special_expenses = special_expenses.get(year, 0)
            yd.travel_expenses = current_travel_expenses
            yd.medical_premium = current_insurance_premium  # Track premium (employer covers during working years)
            yd.medical_premium_expense = 0  # Employer covers premium during working years
            yd.total_expenses = yd.annual_expenses + yd.special_expenses + yd.travel_expenses + yd.medical_premium_expense
            yd.income_expense_difference = yd.take_home_pay - yd.total_expenses
            yd.taxable_account_adjustment = yd.income_expense_difference
            
            # Adjust taxable account balance based on income vs expenses
            balance_taxable += yd.taxable_account_adjustment
            
            # Contributions
            yd.employee_401k_contribution = yd.max_401k
            matchable_compensation = yd.base_salary + yd.bonus - yd.total_deferral
            max_matchable = matchable_compensation * employer_401k_match_max_salary_percent
            matchable_contribution = min(yd.employee_401k_contribution, max_matchable)
            yd.employer_401k_match = matchable_contribution * employer_401k_match_percent
            yd.total_401k_contribution = yd.employee_401k_contribution + yd.employer_401k_match
            yd.hsa_contribution = yd.employee_hsa + yd.employer_hsa
            yd.deferred_comp_contribution = yd.total_deferral
            yd.total_contributions = (yd.total_401k_contribution + yd.hsa_contribution + 
                                      yd.deferred_comp_contribution + yd.taxable_contribution)
            
            # Update balances
            balance_401k += yd.total_401k_contribution
            balance_hsa += yd.hsa_contribution
            balance_deferred_comp += yd.deferred_comp_contribution
            
            # HSA withdrawal (tax-free for qualified medical expenses)
            yd.hsa_withdrawal = min(current_hsa_withdrawal, balance_hsa)  # Can't withdraw more than balance
            balance_hsa -= yd.hsa_withdrawal
            
            yd.balance_ira = balance_401k
            yd.balance_hsa = balance_hsa
            yd.balance_deferred_comp = balance_deferred_comp
            yd.balance_taxable = balance_taxable
            yd.total_assets = yd.balance_ira + yd.balance_hsa + yd.balance_deferred_comp + yd.balance_taxable
            
            # Add to plan and update totals
            plan.yearly_data[year] = yd
            plan.total_gross_income += yd.gross_income
            plan.total_federal_tax += yd.federal_tax
            plan.total_fica += yd.total_fica
            plan.total_state_tax += yd.state_tax
            plan.total_taxes += yd.total_taxes
            plan.total_take_home += yd.take_home_pay
            
            # Track max_hsa for retirement contributions (use last working year's value)
            current_max_hsa = yd.max_hsa
        
        # Apply final growth to deferred comp before disbursement phase
        # Track this appreciation for the first retirement year
        first_retirement_year_deferred_comp_appreciation = balance_deferred_comp * deferred_comp_growth
        balance_deferred_comp = balance_deferred_comp + first_retirement_year_deferred_comp_appreciation
        
        # ============================================================
        # LOOP 2: Deferred Compensation Withdrawal Years
        # ============================================================
        for year in range(disbursement_start, min(disbursement_end + 1, last_planning_year + 1)):
            yd = YearlyData(year=year, is_working_year=False)
            
            # Calculate appreciation amounts before applying growth
            # For first retirement year, deferred comp growth was already applied before this loop
            if year == disbursement_start:
                # Taxable, 401k, HSA get appreciation this year; deferred comp appreciation was tracked above
                yd.appreciation_taxable = balance_taxable * taxable_appreciation
                yd.appreciation_ira = balance_401k * tax_deferred_appreciation
                yd.appreciation_hsa = balance_hsa * hsa_appreciation
                yd.appreciation_deferred_comp = first_retirement_year_deferred_comp_appreciation
            else:
                yd.appreciation_deferred_comp = balance_deferred_comp * deferred_comp_growth
                yd.appreciation_taxable = balance_taxable * taxable_appreciation
                yd.appreciation_ira = balance_401k * tax_deferred_appreciation
                yd.appreciation_hsa = balance_hsa * hsa_appreciation
                balance_deferred_comp = balance_deferred_comp + yd.appreciation_deferred_comp
            
            yd.total_appreciation = (yd.appreciation_taxable + yd.appreciation_ira + 
                                    yd.appreciation_hsa + yd.appreciation_deferred_comp)
            
            # Apply growth to balances (except deferred comp for first year - already done)
            balance_taxable = balance_taxable + yd.appreciation_taxable
            balance_401k = balance_401k + yd.appreciation_ira
            balance_hsa = balance_hsa + yd.appreciation_hsa
            
            current_local_tax = current_local_tax * (1 + local_tax_inflation)
            current_annual_expenses = current_annual_expenses * (1 + expense_inflation)
            # Apply retirement multiplier in first retirement year, then normal inflation
            if year == disbursement_start:
                current_travel_expenses = current_travel_expenses * travel_retirement_multiplier
            else:
                current_travel_expenses = current_travel_expenses * (1 + travel_inflation)
            current_insurance_premium = current_insurance_premium * (1 + premium_inflation)
            current_medicare_premium = current_medicare_premium * (1 + premium_inflation)
            current_hsa_withdrawal = current_hsa_withdrawal * (1 + hsa_withdrawal_inflation)
            # Double HSA withdrawal at Medicare eligibility (medical expenses typically increase)
            if year == medicare_eligibility_year:
                current_hsa_withdrawal = current_hsa_withdrawal * 2
            current_max_hsa = current_max_hsa * (1 + inflation_rate)  # Inflate HSA limit
            
            yd.local_tax = current_local_tax
            # Track appropriate premium based on Medicare eligibility
            if year >= medicare_eligibility_year:
                yd.medical_premium = current_medicare_premium
            else:
                yd.medical_premium = current_insurance_premium
            
            # HSA contributions allowed until Medicare eligibility (age 65)
            if year < medicare_eligibility_year:
                yd.max_hsa = current_max_hsa
                yd.employee_hsa = current_max_hsa  # Full contribution in retirement (no employer)
                yd.hsa_contribution = yd.employee_hsa
            
            # Calculate disbursement as balance / remaining disbursement years
            remaining_disbursement_years = disbursement_end - year + 1
            yearly_disbursement = balance_deferred_comp / remaining_disbursement_years if remaining_disbursement_years > 0 else balance_deferred_comp
            yd.deferred_comp_disbursement = yearly_disbursement
            
            # Realized capital gains (withdrawn from taxable account)
            yd.short_term_capital_gains = balance_taxable * short_term_cg_percent
            yd.long_term_capital_gains = balance_taxable * long_term_cg_percent
            
            # Gross income from disbursement and realized capital gains
            yd.gross_income = yd.deferred_comp_disbursement + yd.short_term_capital_gains + yd.long_term_capital_gains
            
            # Federal deductions (standard deduction + HSA if before Medicare)
            deductions = self.federal.totalDeductions(year, 0, 0, yd.local_tax)
            yd.standard_deduction = deductions['standardDeduction']
            # Include HSA contribution in total deductions if before Medicare eligibility
            yd.total_deductions = yd.standard_deduction + yd.employee_hsa
            
            # Adjusted gross income
            yd.adjusted_gross_income = yd.gross_income - yd.total_deductions
            
            # Federal taxes
            federal_result = self.federal.taxBurden(yd.adjusted_gross_income, year)
            yd.ordinary_income_tax = federal_result.totalFederalTax
            yd.marginal_bracket = federal_result.marginalBracket
            yd.long_term_capital_gains_tax = self.federal.longTermCapitalGainsTax(
                yd.adjusted_gross_income, yd.long_term_capital_gains, year)
            yd.federal_tax = yd.ordinary_income_tax + yd.long_term_capital_gains_tax
            
            # State taxes
            state_taxable = yd.gross_income + yd.long_term_capital_gains
            yd.state_income_tax = self.state.taxBurden(state_taxable, 0, year=year, employer_hsa_contribution=0)
            yd.state_short_term_capital_gains_tax = self.state.shortTermCapitalGainsTax(yd.short_term_capital_gains)
            yd.state_tax = yd.state_income_tax + yd.state_short_term_capital_gains_tax
            
            # Total taxes and take home (no FICA in retirement)
            yd.total_taxes = yd.federal_tax + yd.state_tax
            yd.effective_tax_rate = yd.total_taxes / yd.gross_income if yd.gross_income > 0 else 0
            yd.take_home_pay = yd.gross_income - yd.total_taxes
            
            # Expenses and money movement
            yd.annual_expenses = current_annual_expenses
            yd.special_expenses = special_expenses.get(year, 0)
            yd.travel_expenses = current_travel_expenses
            yd.medical_premium_expense = yd.medical_premium  # Use appropriate premium based on Medicare eligibility
            yd.total_expenses = yd.annual_expenses + yd.special_expenses + yd.travel_expenses + yd.medical_premium_expense
            yd.income_expense_difference = yd.take_home_pay - yd.total_expenses
            # HSA contribution comes from cash flow (reduces taxable account)
            yd.taxable_account_adjustment = yd.income_expense_difference - yd.hsa_contribution
            
            # Adjust taxable account balance based on income vs expenses
            balance_taxable += yd.taxable_account_adjustment
            
            # Update deferred comp balance
            balance_deferred_comp -= yearly_disbursement
            
            # HSA contribution (before Medicare eligibility)
            balance_hsa += yd.hsa_contribution
            
            # HSA withdrawal (tax-free for qualified medical expenses)
            yd.hsa_withdrawal = min(current_hsa_withdrawal, balance_hsa)  # Can't withdraw more than balance
            balance_hsa -= yd.hsa_withdrawal
            
            yd.balance_ira = balance_401k
            yd.balance_hsa = balance_hsa
            yd.balance_deferred_comp = max(0, balance_deferred_comp)
            yd.balance_taxable = balance_taxable
            yd.total_assets = yd.balance_ira + yd.balance_hsa + yd.balance_deferred_comp + yd.balance_taxable
            
            # Add to plan and update totals
            plan.yearly_data[year] = yd
            plan.total_gross_income += yd.gross_income
            plan.total_federal_tax += yd.federal_tax
            plan.total_state_tax += yd.state_tax
            plan.total_taxes += yd.total_taxes
            plan.total_take_home += yd.take_home_pay
        
        # ============================================================
        # LOOP 3: Post-Deferred Comp Years (if any)
        # ============================================================
        post_disbursement_start = disbursement_end + 1
        for year in range(post_disbursement_start, last_planning_year + 1):
            yd = YearlyData(year=year, is_working_year=False)
            
            # Calculate appreciation amounts before applying growth
            yd.appreciation_taxable = balance_taxable * taxable_appreciation
            yd.appreciation_ira = balance_401k * tax_deferred_appreciation
            yd.appreciation_hsa = balance_hsa * hsa_appreciation
            yd.appreciation_deferred_comp = 0  # Deferred comp is depleted
            yd.total_appreciation = (yd.appreciation_taxable + yd.appreciation_ira + 
                                    yd.appreciation_hsa)
            
            # Apply growth to balances
            balance_taxable = balance_taxable + yd.appreciation_taxable
            balance_401k = balance_401k + yd.appreciation_ira
            balance_hsa = balance_hsa + yd.appreciation_hsa
            
            current_local_tax = current_local_tax * (1 + local_tax_inflation)
            current_annual_expenses = current_annual_expenses * (1 + expense_inflation)
            # Normal inflation for travel (retirement multiplier was applied in first retirement year)
            current_travel_expenses = current_travel_expenses * (1 + travel_inflation)
            current_insurance_premium = current_insurance_premium * (1 + premium_inflation)
            current_medicare_premium = current_medicare_premium * (1 + premium_inflation)
            current_hsa_withdrawal = current_hsa_withdrawal * (1 + hsa_withdrawal_inflation)
            # Double HSA withdrawal at Medicare eligibility (medical expenses typically increase)
            if year == medicare_eligibility_year:
                current_hsa_withdrawal = current_hsa_withdrawal * 2
            current_max_hsa = current_max_hsa * (1 + inflation_rate)  # Inflate HSA limit
            
            yd.local_tax = current_local_tax
            # Track appropriate premium based on Medicare eligibility
            if year >= medicare_eligibility_year:
                yd.medical_premium = current_medicare_premium
            else:
                yd.medical_premium = current_insurance_premium
            
            # HSA contributions allowed until Medicare eligibility (age 65)
            if year < medicare_eligibility_year:
                yd.max_hsa = current_max_hsa
                yd.employee_hsa = current_max_hsa  # Full contribution in retirement (no employer)
                yd.hsa_contribution = yd.employee_hsa
            
            # Realized capital gains only (no disbursement)
            yd.short_term_capital_gains = balance_taxable * short_term_cg_percent
            yd.long_term_capital_gains = balance_taxable * long_term_cg_percent
            
            # Expenses (needed to calculate IRA withdrawal requirement)
            yd.annual_expenses = current_annual_expenses
            yd.special_expenses = special_expenses.get(year, 0)
            yd.travel_expenses = current_travel_expenses
            yd.medical_premium_expense = yd.medical_premium  # Use appropriate premium based on Medicare eligibility
            yd.total_expenses = yd.annual_expenses + yd.special_expenses + yd.travel_expenses + yd.medical_premium_expense
            
            # Federal deductions (standard deduction + HSA if before Medicare)
            deductions = self.federal.totalDeductions(year, 0, 0, yd.local_tax)
            yd.standard_deduction = deductions['standardDeduction']
            # Include HSA contribution in total deductions if before Medicare eligibility
            yd.total_deductions = yd.standard_deduction + yd.employee_hsa
            
            # Calculate IRA annuity: balance divided by remaining years in plan
            # This is the minimum withdrawal to spread IRA evenly over remaining years
            # The goal is to deplete the IRA by the end of the plan
            remaining_years = last_planning_year - year + 1
            ira_annuity = balance_401k / remaining_years if remaining_years > 0 else balance_401k
            
            # Base income from capital gains (before any IRA withdrawal)
            base_income = yd.short_term_capital_gains + yd.long_term_capital_gains
            
            # First pass: calculate taxes assuming IRA annuity withdrawal
            # We always withdraw at least the annuity amount to draw down the IRA
            yd.gross_income = base_income + ira_annuity
            yd.adjusted_gross_income = max(0, yd.gross_income - yd.total_deductions)
            
            federal_result = self.federal.taxBurden(yd.adjusted_gross_income, year)
            annuity_federal_tax = federal_result.totalFederalTax
            annuity_ltcg_tax = self.federal.longTermCapitalGainsTax(
                yd.adjusted_gross_income, yd.long_term_capital_gains, year)
            
            state_taxable = yd.gross_income
            annuity_state_tax = self.state.taxBurden(state_taxable, 0, year=year, employer_hsa_contribution=0)
            annuity_state_stcg_tax = self.state.shortTermCapitalGainsTax(yd.short_term_capital_gains)
            
            annuity_total_taxes = annuity_federal_tax + annuity_ltcg_tax + annuity_state_tax + annuity_state_stcg_tax
            annuity_take_home = yd.gross_income - annuity_total_taxes
            
            # Calculate expense shortfall (includes HSA contribution as a cash outflow)
            total_cash_needs = yd.total_expenses + yd.hsa_contribution
            expense_shortfall = max(0, total_cash_needs - annuity_take_home)
            
            # Start with the IRA annuity as the minimum withdrawal
            # If there's still a shortfall after the annuity, we need more
            if expense_shortfall > 0 and balance_401k > ira_annuity:
                # Iteratively solve for the additional withdrawal amount needed
                # Start with a gross-up estimate and refine
                
                # Initial estimate using marginal rate
                marginal_rate = federal_result.marginalBracket + 0.05  # Add ~5% for state
                if marginal_rate < 1:
                    additional_withdrawal = expense_shortfall / (1 - marginal_rate)
                else:
                    additional_withdrawal = expense_shortfall
                
                withdrawal_estimate = ira_annuity + additional_withdrawal
                # Cap at available balance
                withdrawal_estimate = min(withdrawal_estimate, balance_401k)
                
                # Iterate to find the correct withdrawal amount
                # (taxes depend on withdrawal, so we need to converge)
                for _ in range(5):  # 5 iterations should be enough to converge
                    test_gross = base_income + withdrawal_estimate
                    test_agi = max(0, test_gross - yd.total_deductions)
                    
                    test_federal = self.federal.taxBurden(test_agi, year)
                    test_ltcg = self.federal.longTermCapitalGainsTax(test_agi, yd.long_term_capital_gains, year)
                    test_state = self.state.taxBurden(test_gross, 0, year=year, employer_hsa_contribution=0)
                    test_state_stcg = self.state.shortTermCapitalGainsTax(yd.short_term_capital_gains)
                    
                    test_total_taxes = test_federal.totalFederalTax + test_ltcg + test_state + test_state_stcg
                    test_take_home = test_gross - test_total_taxes
                    
                    # How much more do we need?
                    remaining_shortfall = total_cash_needs - test_take_home
                    
                    if remaining_shortfall <= 0:
                        # We have enough, but don't reduce below what's needed
                        break
                    
                    # Need to withdraw more - gross up the remaining shortfall
                    additional_needed = remaining_shortfall / (1 - test_federal.marginalBracket - 0.05)
                    withdrawal_estimate = min(withdrawal_estimate + additional_needed, balance_401k)
                
                yd.ira_withdrawal = withdrawal_estimate
            else:
                # Just use the annuity withdrawal (to draw down IRA over time)
                yd.ira_withdrawal = min(ira_annuity, balance_401k)
            
            balance_401k -= yd.ira_withdrawal
            
            # Now recalculate everything with the IRA withdrawal included in income
            # IRA withdrawals are taxable as ordinary income
            yd.gross_income = base_income + yd.ira_withdrawal
            
            # Adjusted gross income
            yd.adjusted_gross_income = max(0, yd.gross_income - yd.total_deductions)
            
            # Federal taxes (IRA withdrawal is ordinary income)
            federal_result = self.federal.taxBurden(yd.adjusted_gross_income, year)
            yd.ordinary_income_tax = federal_result.totalFederalTax
            yd.marginal_bracket = federal_result.marginalBracket
            yd.long_term_capital_gains_tax = self.federal.longTermCapitalGainsTax(
                yd.adjusted_gross_income, yd.long_term_capital_gains, year)
            yd.federal_tax = yd.ordinary_income_tax + yd.long_term_capital_gains_tax
            
            # State taxes (IRA withdrawal is also state taxable)
            state_taxable = yd.gross_income
            yd.state_income_tax = self.state.taxBurden(state_taxable, 0, year=year, employer_hsa_contribution=0)
            yd.state_short_term_capital_gains_tax = self.state.shortTermCapitalGainsTax(yd.short_term_capital_gains)
            yd.state_tax = yd.state_income_tax + yd.state_short_term_capital_gains_tax
            
            # Total taxes and take home (no FICA)
            yd.total_taxes = yd.federal_tax + yd.state_tax
            yd.effective_tax_rate = yd.total_taxes / yd.gross_income if yd.gross_income > 0 else 0
            yd.take_home_pay = yd.gross_income - yd.total_taxes
            
            # Money movement
            yd.income_expense_difference = yd.take_home_pay - yd.total_expenses
            
            # Any remaining shortfall comes from taxable account
            # If there's excess income, it goes to taxable account
            actual_shortfall = max(0, total_cash_needs - yd.take_home_pay)
            if actual_shortfall > 0:
                # Still need money after IRA withdrawal - take from taxable
                yd.taxable_account_adjustment = -actual_shortfall
            else:
                # Excess income (take_home - expenses - hsa_contribution) goes to taxable
                yd.taxable_account_adjustment = yd.take_home_pay - yd.total_expenses - yd.hsa_contribution
            
            # Adjust taxable account balance
            balance_taxable += yd.taxable_account_adjustment
            
            # HSA contribution (before Medicare eligibility)
            balance_hsa += yd.hsa_contribution
            
            # HSA withdrawal (tax-free for qualified medical expenses)
            yd.hsa_withdrawal = min(current_hsa_withdrawal, balance_hsa)  # Can't withdraw more than balance
            balance_hsa -= yd.hsa_withdrawal
            
            yd.balance_ira = balance_401k
            yd.balance_hsa = balance_hsa
            yd.balance_deferred_comp = 0
            yd.balance_taxable = balance_taxable
            yd.total_assets = yd.balance_ira + yd.balance_hsa + yd.balance_taxable
            
            # Add to plan and update totals
            plan.yearly_data[year] = yd
            plan.total_gross_income += yd.gross_income
            plan.total_federal_tax += yd.federal_tax
            plan.total_state_tax += yd.state_tax
            plan.total_taxes += yd.total_taxes
            plan.total_take_home += yd.take_home_pay
        
        # Set final balances
        final_year_data = plan.yearly_data.get(last_planning_year)
        if final_year_data:
            plan.final_401k_balance = final_year_data.balance_ira
            plan.final_deferred_comp_balance = final_year_data.balance_deferred_comp
            plan.final_hsa_balance = final_year_data.balance_hsa
            plan.final_taxable_balance = final_year_data.balance_taxable
            plan.total_retirement_assets = final_year_data.total_assets
        
        return plan

    def _calculate_paycheck_take_home(self, yd: YearlyData, year: int, life_premium: float, pay_periods_per_year: int, bonus_pay_period: int) -> None:
        """Calculate paycheck take-home pay at different phases of the year.
        
        This calculates:
        1. Initial paycheck take-home (with full SS tax)
        2. Paycheck take-home after SS wage base is exceeded (no more SS tax)
        3. Paycheck take-home after Medicare surcharge kicks in
        
        Also calculates which pay period each threshold is crossed.
        
        The paycheck is based on base salary only (not bonus, RSUs, etc.) since
        those are typically paid separately or vest at different times.
        
        Args:
            yd: The YearlyData object to update
            year: The tax year
            life_premium: Company-provided life insurance premium (taxable)
            pay_periods_per_year: Number of pay periods (26 for BiWeekly, 24 for BiMonthly)
            bonus_pay_period: The pay period number after which the bonus is paid
        """
        if not yd.is_working_year:
            return
        
        # Get SS data for the year
        ss_data = self.social_security.get_data_for_year(year)
        ss_wage_base = ss_data["maximumTaxedIncome"]
        ss_rate = ss_data["employeePortion"] + ss_data["maPFML"]
        
        # Get Medicare data
        medicare_rate = self.medicare.medicare_rate
        medicare_surcharge_threshold = self.medicare.surcharge_threshold
        medicare_surcharge_rate = self.medicare.surcharge_rate
        
        # Calculate per-paycheck gross pay from base salary only
        # Bonus, RSUs, etc. are paid separately and not included in regular paychecks
        paycheck_gross = yd.base_salary / pay_periods_per_year
        
        # Per-paycheck deductions for tax calculation (pro-rated annual amounts)
        # Medical/dental/vision is pre-tax for federal/state but not for SS wage calculation
        paycheck_medical_deduction = yd.medical_dental_vision / pay_periods_per_year
        
        # Medicare base includes life premium (taxable benefit)
        paycheck_life_premium = life_premium / pay_periods_per_year
        paycheck_medicare_base = paycheck_gross - paycheck_medical_deduction + paycheck_life_premium
        
        # Calculate per-paycheck tax rates (federal + state are roughly constant through the year)
        # Use marginal rate as approximation for paycheck withholding
        paycheck_federal_rate = yd.marginal_bracket
        # Estimate state rate from annual values
        paycheck_state_rate = yd.state_tax / yd.gross_income if yd.gross_income > 0 else 0.05
        
        # Per-paycheck deferred compensation contribution (based on base salary deferral only)
        # Bonus deferrals happen when bonus is paid, not in regular paychecks
        paycheck_deferral = yd.base_deferral / pay_periods_per_year
        
        # Calculate per-pay-period 401(k) and HSA contributions
        paycheck_401k = yd.employee_401k_contribution / pay_periods_per_year
        paycheck_hsa = yd.employee_hsa / pay_periods_per_year
        
        # Populate pay statement fields (per pay period amounts)
        yd.paycheck_gross = paycheck_gross
        yd.paycheck_federal_tax = paycheck_gross * paycheck_federal_rate
        yd.paycheck_state_tax = paycheck_gross * paycheck_state_rate
        yd.paycheck_social_security = paycheck_gross * ss_rate
        yd.paycheck_medicare = paycheck_medicare_base * medicare_rate
        yd.paycheck_401k = paycheck_401k
        yd.paycheck_hsa = paycheck_hsa
        yd.paycheck_deferred_comp = paycheck_deferral
        yd.paycheck_medical_dental = paycheck_medical_deduction
        
        # Calculate net pay (gross - all taxes and deductions)
        yd.paycheck_net = (yd.paycheck_gross - yd.paycheck_federal_tax - yd.paycheck_state_tax -
                          yd.paycheck_social_security - yd.paycheck_medicare - yd.paycheck_401k -
                          yd.paycheck_hsa - yd.paycheck_deferred_comp - yd.paycheck_medical_dental)
        
        # 1. Calculate pay period when SS wage base is exceeded
        # We need to simulate cumulative income pay period by pay period
        # because the bonus is a lump sum that can cause a jump in cumulative income
        
        # Calculate FICA income per regular paycheck (excluding bonus)
        # Note: earned_income_for_fica includes bonus, so we subtract it
        regular_fica_income_per_period = (yd.earned_income_for_fica - yd.bonus) / pay_periods_per_year
        
        cumulative_income = 0.0
        yd.pay_period_ss_limit_reached = 0
        yd.pay_period_medicare_surcharge_starts = 0
        
        for period in range(1, pay_periods_per_year + 1):
            # Add regular paycheck income
            cumulative_income += regular_fica_income_per_period
            
            # Add bonus if this is the bonus pay period
            if period == bonus_pay_period:
                cumulative_income += yd.bonus
            
            # Check if SS limit reached in this period
            if yd.pay_period_ss_limit_reached == 0 and cumulative_income > ss_wage_base:
                yd.pay_period_ss_limit_reached = period
            
            # Check if Medicare surcharge starts in this period
            if yd.pay_period_medicare_surcharge_starts == 0 and cumulative_income > medicare_surcharge_threshold:
                yd.pay_period_medicare_surcharge_starts = period
                
            # If both found, we can stop simulating (optimization)
            if yd.pay_period_ss_limit_reached > 0 and yd.pay_period_medicare_surcharge_starts > 0:
                break
        
        # 3. Calculate paycheck take-home for each phase
        
        # Phase 1: Initial (with SS tax, before surcharge if applicable)
        # Taxes: Federal (marginal) + State + SS + Medicare base
        paycheck_ss_tax = paycheck_gross * ss_rate
        paycheck_medicare_tax = paycheck_medicare_base * medicare_rate
        paycheck_taxes_phase1 = (paycheck_gross * paycheck_federal_rate + 
                                 paycheck_gross * paycheck_state_rate +
                                 paycheck_ss_tax + paycheck_medicare_tax)
        yd.paycheck_take_home_initial = paycheck_gross - paycheck_taxes_phase1 - paycheck_deferral
        
        # Phase 2: After SS wage base exceeded (no more SS tax)
        paycheck_taxes_phase2 = (paycheck_gross * paycheck_federal_rate +
                                 paycheck_gross * paycheck_state_rate +
                                 paycheck_medicare_tax)
        yd.paycheck_take_home_after_ss_limit = paycheck_gross - paycheck_taxes_phase2 - paycheck_deferral
        
        # Phase 3: After Medicare surcharge kicks in
        paycheck_medicare_surcharge = paycheck_gross * medicare_surcharge_rate
        paycheck_taxes_phase3 = (paycheck_gross * paycheck_federal_rate +
                                 paycheck_gross * paycheck_state_rate +
                                 paycheck_medicare_tax + paycheck_medicare_surcharge)
        # Note: By the time surcharge kicks in, SS limit is usually already exceeded
        # So phase 3 typically doesn't have SS tax either
        if yd.pay_period_medicare_surcharge_starts > 0 and yd.pay_period_ss_limit_reached > 0:
            if yd.pay_period_medicare_surcharge_starts >= yd.pay_period_ss_limit_reached:
                # SS limit reached before surcharge - phase 3 has no SS tax
                yd.paycheck_take_home_after_medicare_surcharge = (paycheck_gross - paycheck_taxes_phase3 - 
                                                                   paycheck_deferral)
            else:
                # Surcharge before SS limit (unusual) - include SS tax
                paycheck_taxes_phase3_with_ss = paycheck_taxes_phase3 + paycheck_ss_tax
                yd.paycheck_take_home_after_medicare_surcharge = (paycheck_gross - paycheck_taxes_phase3_with_ss - 
                                                                   paycheck_deferral)
        elif yd.pay_period_medicare_surcharge_starts > 0:
            # Surcharge kicks in but SS limit never reached
            paycheck_taxes_phase3_with_ss = paycheck_taxes_phase3 + paycheck_ss_tax
            yd.paycheck_take_home_after_medicare_surcharge = (paycheck_gross - paycheck_taxes_phase3_with_ss - 
                                                               paycheck_deferral)
        else:
            # No surcharge this year
            yd.paycheck_take_home_after_medicare_surcharge = 0.0

        # Calculate bonus paycheck breakdown
        # Bonuses are typically paid as a lump sum and taxed at supplemental wage rates
        if yd.bonus > 0:
            self._calculate_bonus_paycheck(yd, year)

    def _calculate_bonus_paycheck(self, yd: YearlyData, year: int) -> None:
        """Calculate bonus paycheck breakdown.
        
        Bonuses are typically taxed at flat supplemental wage rates rather than
        using the progressive tax brackets. The federal supplemental rate is 22%
        for bonuses up to $1 million (37% above that).
        
        Args:
            yd: The YearlyData object to update
            year: The tax year
        """
        # Federal supplemental wage withholding rate (22% for amounts up to $1M)
        federal_supplemental_rate = 0.22
        
        # Get SS and Medicare rates
        ss_data = self.social_security.get_data_for_year(year)
        ss_rate = ss_data["employeePortion"] + ss_data["maPFML"]
        medicare_rate = self.medicare.medicare_rate
        
        # State rate - use effective rate from annual calculations
        state_rate = yd.state_tax / yd.gross_income if yd.gross_income > 0 else 0.05
        
        # Bonus gross amount
        yd.bonus_paycheck_gross = yd.bonus
        
        # Federal tax at supplemental rate
        yd.bonus_paycheck_federal_tax = yd.bonus * federal_supplemental_rate
        
        # State tax at effective rate
        yd.bonus_paycheck_state_tax = yd.bonus * state_rate
        
        # Social Security tax (applies to bonus, subject to wage base)
        # For simplicity, we calculate as if full rate applies
        # In reality, may be reduced if wage base already exceeded
        yd.bonus_paycheck_social_security = yd.bonus * ss_rate
        
        # Medicare tax at base rate (bonus typically triggers surcharge too)
        # For simplicity, use base rate; surcharge handled separately
        yd.bonus_paycheck_medicare = yd.bonus * medicare_rate
        
        # Deferred compensation from bonus
        yd.bonus_paycheck_deferred_comp = yd.bonus_deferral
        
        # Net bonus after all deductions
        yd.bonus_paycheck_net = (yd.bonus_paycheck_gross - 
                                  yd.bonus_paycheck_federal_tax -
                                  yd.bonus_paycheck_state_tax -
                                  yd.bonus_paycheck_social_security -
                                  yd.bonus_paycheck_medicare -
                                  yd.bonus_paycheck_deferred_comp)
