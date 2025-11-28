"""Financial Planner Tools for MCP Server.

This module provides the tool implementations that wrap the financial
planning calculators and expose their data through MCP.
"""

import os
import sys
import json
from typing import Any, Dict, List, Optional

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tax.FederalDetails import FederalDetails
from tax.StateDetails import StateDetails
from tax.ESPPDetails import ESPPDetails
from tax.SocialSecurityDetails import SocialSecurityDetails
from tax.MedicareDetails import MedicareDetails
from calc.take_home import TakeHomeCalculator
from calc.rsu_calculator import RSUCalculator
from calc.balance_calculator import BalanceCalculator
from calc.deferred_comp_calculator import DeferredCompCalculator


class FinancialPlannerTools:
    """Tools that wrap financial planning calculators for MCP access."""
    
    def __init__(self, base_path: str, program_name: str):
        """Initialize with paths and load the financial plan.
        
        Args:
            base_path: Path to the financial-planner root directory
            program_name: Name of the program folder in input-parameters
        """
        self.base_path = base_path
        self.program_name = program_name
        self.spec = self._load_spec()
        self._init_calculators()
        self._cache_results()
    
    def _load_spec(self) -> dict:
        """Load the program specification."""
        spec_path = os.path.join(
            self.base_path, 'input-parameters', self.program_name, 'spec.json'
        )
        with open(spec_path, 'r') as f:
            return json.load(f)
    
    def _init_calculators(self):
        """Initialize all calculators."""
        inflation_rate = self.spec.get('federalBracketInflation')
        final_year = self.spec.get('lastPlanningYear')
        first_year = self.spec.get('firstYear', 2026)
        last_working_year = self.spec.get('lastWorkingYear', first_year + 10)
        
        # Store key dates
        self.first_year = first_year
        self.last_working_year = last_working_year
        self.last_planning_year = final_year
        
        # Federal details
        self.fed = FederalDetails(inflation_rate, final_year)
        
        # State details
        self.state = StateDetails(inflation_rate, final_year)
        
        # ESPP details
        fed_ref_path = os.path.join(self.base_path, 'reference', 'federal-details.json')
        with open(fed_ref_path, 'r') as f:
            fed_ref = json.load(f)
        max_espp = fed_ref.get('maxESPPValue', 0)
        self.espp = ESPPDetails(max_espp)
        
        # Social Security details
        self.social_security = SocialSecurityDetails(inflation_rate, final_year)
        
        # Medicare details
        medicare_ref_path = os.path.join(self.base_path, 'reference', 'flat-tax-details.json')
        with open(medicare_ref_path, 'r') as f:
            medicare_ref = json.load(f)
        self.medicare = MedicareDetails(
            medicare_rate=medicare_ref.get('medicare', 0),
            surcharge_threshold=medicare_ref.get('surchargeThreshold', 0),
            surcharge_rate=medicare_ref.get('surchargeRate', 0)
        )
        
        # RSU calculator
        rsu_config = self.spec.get('restrictedStockUnits', {})
        self.rsu_calculator = RSUCalculator(
            previous_grants=rsu_config.get('previousGrants', []).copy(),
            first_year=first_year,
            last_year=last_working_year,
            first_year_stock_price=rsu_config.get('currentStockPrice', 0),
            first_year_grant_value=rsu_config.get('initialAnnualGrantValue', 0),
            annual_grant_increase=rsu_config.get('annualGrantIncreaseFraction', 0),
            expected_share_price_growth_fraction=rsu_config.get('expectedSharePriceGrowthFraction', 0)
        )
        
        # Take home calculator
        self.calculator = TakeHomeCalculator(
            self.fed, self.state, self.espp, 
            self.social_security, self.medicare, self.rsu_calculator
        )
        
        # Calculate yearly deferrals for deferred comp calculator
        yearly_deferrals = {}
        for year in range(first_year, last_working_year + 1):
            results = self.calculator.calculate(self.spec, year)
            yearly_deferrals[year] = results.get('total_deferral', 0)
        
        # Deferred comp calculator
        self.deferred_comp = DeferredCompCalculator(self.spec, yearly_deferrals)
        self.calculator.set_deferred_comp_calculator(self.deferred_comp)
        
        # Balance calculator
        self.balance_calculator = BalanceCalculator(self.calculator, self.fed)
    
    def _cache_results(self):
        """Pre-calculate and cache results for all years."""
        self.yearly_results: Dict[int, dict] = {}
        for year in range(self.first_year, self.last_planning_year + 1):
            self.yearly_results[year] = self.calculator.calculate(self.spec, year)
        
        # Calculate balance results
        self.balance_result = self.balance_calculator.calculate(self.spec)
    
    def get_program_overview(self) -> dict:
        """Get an overview of the financial plan."""
        income = self.spec.get('income', {})
        deferred_plan = self.spec.get('deferredCompensationPlan', {})
        rsu_config = self.spec.get('restrictedStockUnits', {})
        
        return {
            "program_name": self.program_name,
            "planning_horizon": {
                "first_year": self.first_year,
                "last_working_year": self.last_working_year,
                "last_planning_year": self.last_planning_year,
                "working_years": self.last_working_year - self.first_year + 1,
                "retirement_years": self.last_planning_year - self.last_working_year
            },
            "income_sources": {
                "base_salary": income.get('baseSalary', 0),
                "bonus_fraction": income.get('bonusFraction', 0),
                "espp_discount": self.spec.get('esppDiscount', 0),
                "other_income": income.get('otherIncome', 0),
                "short_term_capital_gains": income.get('shortTermCapitalGains', 0),
                "long_term_capital_gains": income.get('longTermCapitalGains', 0)
            },
            "deferred_compensation": {
                "base_deferral_fraction": income.get('baseDeferralFraction', 0),
                "bonus_deferral_fraction": income.get('bonusDeferralFraction', 0),
                "disbursement_years": deferred_plan.get('dispursementYears', 0),
                "growth_rate": deferred_plan.get('annualGrowthFraction', 0)
            },
            "rsu_info": {
                "current_stock_price": rsu_config.get('currentStockPrice', 0),
                "expected_growth": rsu_config.get('expectedSharePriceGrowthFraction', 0),
                "vesting_period": rsu_config.get('vestingPeriodYears', 4)
            },
            "inflation_assumption": self.spec.get('federalBracketInflation', 0)
        }
    
    def list_available_years(self) -> dict:
        """List all years in the plan."""
        working_years = list(range(self.first_year, self.last_working_year + 1))
        retirement_years = list(range(self.last_working_year + 1, self.last_planning_year + 1))
        
        # Identify disbursement years
        disbursement_years = []
        for year in retirement_years:
            if self.deferred_comp.get_disbursement(year) > 0:
                disbursement_years.append(year)
        
        return {
            "working_years": working_years,
            "retirement_years": retirement_years,
            "disbursement_years": disbursement_years,
            "total_years": len(working_years) + len(retirement_years)
        }
    
    def get_annual_summary(self, year: int) -> dict:
        """Get income and tax summary for a specific year."""
        if year not in self.yearly_results:
            return {"error": f"Year {year} is not in the planning horizon ({self.first_year}-{self.last_planning_year})"}
        
        results = self.yearly_results[year]
        
        federal_tax = results['federal_tax']
        fica = results['total_social_security'] + results['medicare_charge'] + results['medicare_surcharge']
        state_tax = results.get('state_tax', 0)
        total_tax = federal_tax + fica + state_tax
        gross_income = results['gross_income']
        
        return {
            "year": year,
            "is_working_year": year <= self.last_working_year,
            "gross_income": round(gross_income, 2),
            "federal_tax": round(federal_tax, 2),
            "fica_tax": round(fica, 2),
            "state_tax": round(state_tax, 2),
            "total_tax": round(total_tax, 2),
            "effective_tax_rate": round(total_tax / gross_income * 100, 1) if gross_income > 0 else 0,
            "take_home_pay": round(results['take_home_pay'], 2),
            "total_deferral": round(results.get('total_deferral', 0), 2)
        }
    
    def get_tax_details(self, year: int) -> dict:
        """Get detailed tax breakdown for a specific year."""
        if year not in self.yearly_results:
            return {"error": f"Year {year} is not in the planning horizon"}
        
        results = self.yearly_results[year]
        
        return {
            "year": year,
            "federal": {
                "ordinary_income_tax": round(results['ordinary_income_tax'], 2),
                "long_term_capital_gains_tax": round(results['long_term_capital_gains_tax'], 2),
                "total_federal_tax": round(results['federal_tax'], 2),
                "marginal_bracket": f"{results['marginal_bracket']:.1%}"
            },
            "fica": {
                "social_security": round(results['total_social_security'], 2),
                "medicare": round(results['medicare_charge'], 2),
                "medicare_surcharge": round(results['medicare_surcharge'], 2),
                "total_fica": round(
                    results['total_social_security'] + 
                    results['medicare_charge'] + 
                    results['medicare_surcharge'], 2
                )
            },
            "state": {
                "income_tax": round(results.get('state_income_tax', 0), 2),
                "short_term_capital_gains_tax": round(results.get('state_short_term_capital_gains_tax', 0), 2),
                "total_state_tax": round(results.get('state_tax', 0), 2)
            },
            "deductions": {
                "standard_deduction": round(results['deductions']['standardDeduction'], 2),
                "max_401k": round(results['deductions']['max401k'], 2),
                "max_hsa": round(results['deductions']['maxHSA'], 2),
                "medical_dental_vision": round(results['deductions'].get('medicalDentalVision', 0), 2),
                "total_deductions": round(results['total_deductions'], 2)
            },
            "adjusted_gross_income": round(results['adjusted_gross_income'], 2)
        }
    
    def get_income_breakdown(self, year: int) -> dict:
        """Get detailed income breakdown for a specific year."""
        if year not in self.yearly_results:
            return {"error": f"Year {year} is not in the planning horizon"}
        
        results = self.yearly_results[year]
        is_working = year <= self.last_working_year
        
        income = self.spec.get('income', {})
        
        breakdown = {
            "year": year,
            "is_working_year": is_working,
            "gross_income": round(results['gross_income'], 2)
        }
        
        if is_working:
            base_salary = income.get('baseSalary', 0)
            bonus_fraction = income.get('bonusFraction', 0)
            breakdown["earned_income"] = {
                "base_salary": round(base_salary, 2),
                "bonus": round(base_salary * bonus_fraction, 2),
                "other_income": round(income.get('otherIncome', 0), 2),
                "rsu_vested_value": round(results.get('rsu_vested_value', 0), 2),
                "espp_income": round(results.get('espp_income', 0), 2)
            }
        
        breakdown["investment_income"] = {
            "short_term_capital_gains": round(results.get('short_term_capital_gains', 0), 2),
            "long_term_capital_gains": round(results.get('long_term_capital_gains', 0), 2)
        }
        
        breakdown["deferred_comp_disbursement"] = round(
            results.get('deferred_comp_disbursement', 0), 2
        )
        
        return breakdown
    
    def get_deferred_comp_info(self, year: int) -> dict:
        """Get deferred compensation information for a specific year."""
        if year < self.first_year or year > self.last_planning_year:
            return {"error": f"Year {year} is not in the planning horizon"}
        
        results = self.yearly_results.get(year, {})
        
        return {
            "year": year,
            "is_working_year": year <= self.last_working_year,
            "contribution": round(results.get('total_deferral', 0), 2) if year <= self.last_working_year else 0,
            "base_deferral": round(results.get('base_deferral', 0), 2) if year <= self.last_working_year else 0,
            "bonus_deferral": round(results.get('bonus_deferral', 0), 2) if year <= self.last_working_year else 0,
            "disbursement": round(self.deferred_comp.get_disbursement(year), 2),
            "end_of_year_balance": round(self.deferred_comp.get_balance(year), 2)
        }
    
    def get_retirement_balances(self, year: Optional[int] = None) -> dict:
        """Get 401(k) and deferred comp balances."""
        if year is not None:
            # Find the specific year in balance results
            for yb in self.balance_result.yearly_balances:
                if yb.year == year:
                    return {
                        "year": year,
                        "balances": {
                            "401k_contribution": round(yb.contrib_401k, 2),
                            "401k_balance": round(yb.balance_401k, 2),
                            "deferred_contribution": round(yb.deferred_contrib, 2),
                            "deferred_balance": round(yb.deferred_balance, 2),
                            "total_retirement_assets": round(yb.balance_401k + yb.deferred_balance, 2)
                        }
                    }
            return {"error": f"Year {year} not found in balance data"}
        
        # Return summary
        return {
            "final_balances": {
                "401k_balance": round(self.balance_result.final_401k_balance, 2),
                "deferred_balance": round(self.balance_result.final_deferred_balance, 2),
                "total_retirement_assets": round(self.balance_result.total_retirement_assets, 2)
            },
            "yearly_balances": [
                {
                    "year": yb.year,
                    "401k_balance": round(yb.balance_401k, 2),
                    "deferred_balance": round(yb.deferred_balance, 2)
                }
                for yb in self.balance_result.yearly_balances
            ]
        }
    
    def compare_years(self, year1: int, year2: int) -> dict:
        """Compare financial metrics between two years."""
        if year1 not in self.yearly_results:
            return {"error": f"Year {year1} is not in the planning horizon"}
        if year2 not in self.yearly_results:
            return {"error": f"Year {year2} is not in the planning horizon"}
        
        r1 = self.yearly_results[year1]
        r2 = self.yearly_results[year2]
        
        def compare_metric(v1: float, v2: float) -> dict:
            diff = v2 - v1
            pct = (diff / v1 * 100) if v1 != 0 else 0
            return {
                f"year_{year1}": round(v1, 2),
                f"year_{year2}": round(v2, 2),
                "difference": round(diff, 2),
                "percent_change": round(pct, 1)
            }
        
        return {
            "comparison": f"{year1} vs {year2}",
            "gross_income": compare_metric(r1['gross_income'], r2['gross_income']),
            "federal_tax": compare_metric(r1['federal_tax'], r2['federal_tax']),
            "total_tax": compare_metric(
                r1['federal_tax'] + r1['total_social_security'] + r1['medicare_charge'] + r1['medicare_surcharge'] + r1.get('state_tax', 0),
                r2['federal_tax'] + r2['total_social_security'] + r2['medicare_charge'] + r2['medicare_surcharge'] + r2.get('state_tax', 0)
            ),
            "take_home_pay": compare_metric(r1['take_home_pay'], r2['take_home_pay'])
        }
    
    def get_lifetime_totals(self) -> dict:
        """Get lifetime totals across the planning horizon."""
        totals = {
            "gross_income": 0,
            "federal_tax": 0,
            "fica": 0,
            "state_tax": 0,
            "total_tax": 0,
            "take_home_pay": 0,
            "total_deferred": 0
        }
        
        working_totals = dict(totals)
        retirement_totals = dict(totals)
        
        for year, results in self.yearly_results.items():
            fica = results['total_social_security'] + results['medicare_charge'] + results['medicare_surcharge']
            total_tax = results['federal_tax'] + fica + results.get('state_tax', 0)
            
            target = working_totals if year <= self.last_working_year else retirement_totals
            target["gross_income"] += results['gross_income']
            target["federal_tax"] += results['federal_tax']
            target["fica"] += fica
            target["state_tax"] += results.get('state_tax', 0)
            target["total_tax"] += total_tax
            target["take_home_pay"] += results['take_home_pay']
            target["total_deferred"] += results.get('total_deferral', 0)
        
        # Combine totals
        for key in totals:
            totals[key] = working_totals[key] + retirement_totals[key]
        
        # Round all values
        for d in [totals, working_totals, retirement_totals]:
            for key in d:
                d[key] = round(d[key], 2)
        
        return {
            "lifetime_totals": totals,
            "working_years_totals": working_totals,
            "retirement_years_totals": retirement_totals,
            "effective_lifetime_tax_rate": round(totals["total_tax"] / totals["gross_income"] * 100, 1) if totals["gross_income"] > 0 else 0
        }
    
    def search_financial_data(self, query: str, year: Optional[int] = None) -> dict:
        """Search for specific financial metrics based on a query."""
        query_lower = query.lower()
        
        # Map common terms to result keys
        term_mapping = {
            "espp": ["espp_income"],
            "rsu": ["rsu_vested_value"],
            "stock": ["rsu_vested_value", "espp_income"],
            "salary": ["base_salary"],
            "bonus": ["bonus"],
            "federal": ["federal_tax", "ordinary_income_tax"],
            "state": ["state_tax", "state_income_tax"],
            "fica": ["total_social_security", "medicare_charge", "medicare_surcharge"],
            "social security": ["total_social_security"],
            "medicare": ["medicare_charge", "medicare_surcharge"],
            "take home": ["take_home_pay"],
            "gross": ["gross_income"],
            "deferred": ["total_deferral", "deferred_comp_disbursement"],
            "disbursement": ["deferred_comp_disbursement"],
            "capital gain": ["short_term_capital_gains", "long_term_capital_gains"],
            "ltcg": ["long_term_capital_gains", "long_term_capital_gains_tax"],
            "marginal": ["marginal_bracket"],
            "effective": ["effective_tax_rate"],
            "deduction": ["total_deductions", "standard_deduction"],
            "401k": ["max401k"],
            "hsa": ["maxHSA"]
        }
        
        # Find matching terms
        matched_keys = []
        for term, keys in term_mapping.items():
            if term in query_lower:
                matched_keys.extend(keys)
        
        if not matched_keys:
            return {
                "query": query,
                "message": "No matching financial metrics found. Try terms like: ESPP, RSU, salary, federal tax, state tax, FICA, take home, gross income, deferred, capital gains, etc."
            }
        
        # Get results
        if year is not None:
            if year not in self.yearly_results:
                return {"error": f"Year {year} is not in the planning horizon"}
            
            results = self.yearly_results[year]
            income = self.spec.get('income', {})
            
            found_data = {"year": year, "query": query, "results": {}}
            
            for key in matched_keys:
                if key in results:
                    found_data["results"][key] = round(results[key], 2)
                elif key == "base_salary" and year <= self.last_working_year:
                    found_data["results"][key] = round(income.get('baseSalary', 0), 2)
                elif key == "bonus" and year <= self.last_working_year:
                    base = income.get('baseSalary', 0)
                    frac = income.get('bonusFraction', 0)
                    found_data["results"][key] = round(base * frac, 2)
                elif key in results.get('deductions', {}):
                    found_data["results"][key] = round(results['deductions'][key], 2)
            
            return found_data
        else:
            # Return data for all years
            all_years_data = {"query": query, "years": {}}
            
            for yr, results in self.yearly_results.items():
                income = self.spec.get('income', {})
                year_data = {}
                
                for key in matched_keys:
                    if key in results:
                        year_data[key] = round(results[key], 2)
                
                if year_data:
                    all_years_data["years"][yr] = year_data
            
            return all_years_data


class MultiProgramTools:
    """Manager for multiple financial planning programs.
    
    Discovers all available programs and caches their calculations,
    allowing queries to specify which program to use.
    """
    
    def __init__(self, base_path: str, default_program: Optional[str] = None):
        """Initialize and discover all available programs.
        
        Args:
            base_path: Path to the financial-planner root directory
            default_program: Default program to use when none specified
        """
        self.base_path = base_path
        self.programs: Dict[str, FinancialPlannerTools] = {}
        self.default_program = default_program
        self._discover_programs()
    
    def _discover_programs(self):
        """Discover and load all available programs."""
        input_params_path = os.path.join(self.base_path, 'input-parameters')
        
        if not os.path.exists(input_params_path):
            return
        
        for name in os.listdir(input_params_path):
            program_dir = os.path.join(input_params_path, name)
            spec_path = os.path.join(program_dir, 'spec.json')
            
            if os.path.isdir(program_dir) and os.path.exists(spec_path):
                try:
                    self.programs[name] = FinancialPlannerTools(self.base_path, name)
                except Exception as e:
                    # Log but don't fail on individual program errors
                    print(f"Warning: Failed to load program '{name}': {e}", file=sys.stderr)
        
        # Set default if not specified
        if self.default_program is None and self.programs:
            self.default_program = list(self.programs.keys())[0]
    
    def _get_program(self, program: Optional[str] = None, require_explicit: bool = False) -> FinancialPlannerTools:
        """Get the specified program or default.
        
        Args:
            program: Program name to use, or None for default
            require_explicit: If True, raise error when program not specified and multiple exist
        """
        if program is None and len(self.programs) > 1 and require_explicit:
            available = list(self.programs.keys())
            raise ValueError(
                f"Multiple programs available: {available}. Please specify which program to query."
            )
        
        program_name = program or self.default_program
        
        if program_name not in self.programs:
            available = list(self.programs.keys())
            raise ValueError(
                f"Program '{program_name}' not found. Available programs: {available}"
            )
        
        return self.programs[program_name]
    
    def list_programs(self) -> dict:
        """List all available programs."""
        programs_info = {}
        for name, tools in self.programs.items():
            programs_info[name] = {
                "first_year": tools.first_year,
                "last_working_year": tools.last_working_year,
                "last_planning_year": tools.last_planning_year,
                "base_salary": tools.spec.get('income', {}).get('baseSalary', 0)
            }
        
        return {
            "available_programs": list(self.programs.keys()),
            "default_program": self.default_program,
            "programs_info": programs_info
        }
    
    def get_program_overview(self, program: Optional[str] = None) -> dict:
        """Get an overview of the specified financial plan."""
        result = self._get_program(program, require_explicit=True).get_program_overview()
        result["program"] = program or self.default_program
        return result
    
    def list_available_years(self, program: Optional[str] = None) -> dict:
        """List all years in the specified plan."""
        result = self._get_program(program, require_explicit=True).list_available_years()
        result["program"] = program or self.default_program
        return result
    
    def get_annual_summary(self, year: int, program: Optional[str] = None) -> dict:
        """Get income and tax summary for a specific year."""
        result = self._get_program(program, require_explicit=True).get_annual_summary(year)
        result["program"] = program or self.default_program
        return result
    
    def get_tax_details(self, year: int, program: Optional[str] = None) -> dict:
        """Get detailed tax breakdown for a specific year."""
        result = self._get_program(program, require_explicit=True).get_tax_details(year)
        result["program"] = program or self.default_program
        return result
    
    def get_income_breakdown(self, year: int, program: Optional[str] = None) -> dict:
        """Get detailed income breakdown for a specific year."""
        result = self._get_program(program, require_explicit=True).get_income_breakdown(year)
        result["program"] = program or self.default_program
        return result
    
    def get_deferred_comp_info(self, year: int, program: Optional[str] = None) -> dict:
        """Get deferred compensation information for a specific year."""
        result = self._get_program(program, require_explicit=True).get_deferred_comp_info(year)
        result["program"] = program or self.default_program
        return result
    
    def get_retirement_balances(self, year: Optional[int] = None, program: Optional[str] = None) -> dict:
        """Get 401(k) and deferred comp balances."""
        result = self._get_program(program, require_explicit=True).get_retirement_balances(year)
        result["program"] = program or self.default_program
        return result
    
    def compare_years(self, year1: int, year2: int, program: Optional[str] = None) -> dict:
        """Compare financial metrics between two years."""
        result = self._get_program(program, require_explicit=True).compare_years(year1, year2)
        result["program"] = program or self.default_program
        return result
    
    def get_lifetime_totals(self, program: Optional[str] = None) -> dict:
        """Get lifetime totals across the planning horizon."""
        result = self._get_program(program, require_explicit=True).get_lifetime_totals()
        result["program"] = program or self.default_program
        return result
    
    def search_financial_data(self, query: str, year: Optional[int] = None, program: Optional[str] = None) -> dict:
        """Search for specific financial metrics based on a query."""
        result = self._get_program(program, require_explicit=True).search_financial_data(query, year)
        result["program"] = program or self.default_program
        return result
