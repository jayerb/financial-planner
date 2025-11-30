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
        premium_inflation = insurance_spec.get('premiumInflationRate', 0.04)
        
        # Expense parameters
        expenses_spec = spec.get('expenses', {})
        initial_annual_expenses = expenses_spec.get('annualAmount', 0)
        expense_inflation = expenses_spec.get('inflationRate', 0.03)
        special_expenses = {se['year']: se['amount'] for se in expenses_spec.get('specialExpenses', [])}
        
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
        current_insurance_premium = initial_insurance_premium
        current_hsa_withdrawal = initial_hsa_withdrawal
        
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
                current_insurance_premium = current_insurance_premium * (1 + premium_inflation)
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
            
            # Expenses and money movement
            yd.annual_expenses = current_annual_expenses
            yd.special_expenses = special_expenses.get(year, 0)
            yd.medical_premium = current_insurance_premium  # Track premium (employer covers during working years)
            yd.medical_premium_expense = 0  # Employer covers premium during working years
            yd.total_expenses = yd.annual_expenses + yd.special_expenses + yd.medical_premium_expense
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
            current_insurance_premium = current_insurance_premium * (1 + premium_inflation)
            current_hsa_withdrawal = current_hsa_withdrawal * (1 + hsa_withdrawal_inflation)
            
            yd.local_tax = current_local_tax
            yd.medical_premium = current_insurance_premium  # Track premium for reference
            
            # Calculate disbursement as balance / remaining disbursement years
            remaining_disbursement_years = disbursement_end - year + 1
            yearly_disbursement = balance_deferred_comp / remaining_disbursement_years if remaining_disbursement_years > 0 else balance_deferred_comp
            yd.deferred_comp_disbursement = yearly_disbursement
            
            # Realized capital gains (withdrawn from taxable account)
            yd.short_term_capital_gains = balance_taxable * short_term_cg_percent
            yd.long_term_capital_gains = balance_taxable * long_term_cg_percent
            
            # Gross income from disbursement and realized capital gains
            yd.gross_income = yd.deferred_comp_disbursement + yd.short_term_capital_gains + yd.long_term_capital_gains
            
            # Federal deductions (only standard deduction in retirement)
            deductions = self.federal.totalDeductions(year, 0, 0, yd.local_tax)
            yd.standard_deduction = deductions['standardDeduction']
            yd.total_deductions = yd.standard_deduction
            
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
            yd.medical_premium_expense = current_insurance_premium  # Must pay own premium in retirement
            yd.total_expenses = yd.annual_expenses + yd.special_expenses + yd.medical_premium_expense
            yd.income_expense_difference = yd.take_home_pay - yd.total_expenses
            yd.taxable_account_adjustment = yd.income_expense_difference
            
            # Adjust taxable account balance based on income vs expenses
            balance_taxable += yd.taxable_account_adjustment
            
            # Update deferred comp balance
            balance_deferred_comp -= yearly_disbursement
            
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
            current_insurance_premium = current_insurance_premium * (1 + premium_inflation)
            current_hsa_withdrawal = current_hsa_withdrawal * (1 + hsa_withdrawal_inflation)
            
            yd.local_tax = current_local_tax
            yd.medical_premium = current_insurance_premium  # Track premium for reference
            
            # Realized capital gains only (no disbursement)
            yd.short_term_capital_gains = balance_taxable * short_term_cg_percent
            yd.long_term_capital_gains = balance_taxable * long_term_cg_percent
            
            # Gross income from realized capital gains only
            yd.gross_income = yd.short_term_capital_gains + yd.long_term_capital_gains
            
            # Federal deductions (standard deduction only)
            deductions = self.federal.totalDeductions(year, 0, 0, yd.local_tax)
            yd.standard_deduction = deductions['standardDeduction']
            yd.total_deductions = yd.standard_deduction
            
            # Adjusted gross income
            yd.adjusted_gross_income = yd.gross_income - yd.total_deductions
            
            # Federal taxes
            federal_result = self.federal.taxBurden(yd.adjusted_gross_income, year)
            yd.ordinary_income_tax = federal_result.totalFederalTax
            yd.marginal_bracket = federal_result.marginalBracket
            yd.long_term_capital_gains_tax = self.federal.longTermCapitalGainsTax(
                yd.adjusted_gross_income, yd.long_term_capital_gains, year)
            yd.federal_tax = yd.ordinary_income_tax + yd.long_term_capital_gains_tax
            
            # State taxes (gross_income already includes LTCG)
            state_taxable = yd.gross_income
            yd.state_income_tax = self.state.taxBurden(state_taxable, 0, year=year, employer_hsa_contribution=0)
            yd.state_short_term_capital_gains_tax = self.state.shortTermCapitalGainsTax(yd.short_term_capital_gains)
            yd.state_tax = yd.state_income_tax + yd.state_short_term_capital_gains_tax
            
            # Total taxes and take home (no FICA)
            yd.total_taxes = yd.federal_tax + yd.state_tax
            yd.effective_tax_rate = yd.total_taxes / yd.gross_income if yd.gross_income > 0 else 0
            yd.take_home_pay = yd.gross_income - yd.total_taxes
            
            # Expenses and money movement
            yd.annual_expenses = current_annual_expenses
            yd.special_expenses = special_expenses.get(year, 0)
            yd.medical_premium_expense = current_insurance_premium  # Must pay own premium in retirement
            yd.total_expenses = yd.annual_expenses + yd.special_expenses + yd.medical_premium_expense
            yd.income_expense_difference = yd.take_home_pay - yd.total_expenses
            
            # Calculate expense shortfall (amount needed beyond take-home pay)
            expense_shortfall = max(0, yd.total_expenses - yd.take_home_pay)
            
            # Calculate IRA annuity: balance divided by remaining years in plan
            remaining_years = last_planning_year - year + 1
            ira_annuity = balance_401k / remaining_years if remaining_years > 0 else 0
            
            # Withdraw from IRA up to the lesser of annuity or expense shortfall
            if expense_shortfall > 0 and balance_401k > 0:
                yd.ira_withdrawal = min(ira_annuity, expense_shortfall, balance_401k)
                balance_401k -= yd.ira_withdrawal
                expense_shortfall -= yd.ira_withdrawal
            
            # Any remaining shortfall comes from taxable account
            # If there's excess income, it goes to taxable account
            if expense_shortfall > 0:
                # Still need money after IRA withdrawal - take from taxable
                yd.taxable_account_adjustment = -expense_shortfall
            else:
                # Excess income (take_home + ira_withdrawal - expenses) goes to taxable
                yd.taxable_account_adjustment = yd.take_home_pay + yd.ira_withdrawal - yd.total_expenses
            
            # Adjust taxable account balance
            balance_taxable += yd.taxable_account_adjustment
            
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
