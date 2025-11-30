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
from calc.rsu_calculator import RSUCalculator
from calc.plan_calculator import PlanCalculator
from model.PlanData import PlanData, YearlyData


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
        self._calculate_plan()
    
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
        
        # Plan calculator (replaces TakeHomeCalculator, BalanceCalculator, DeferredCompCalculator, InvestmentCalculator)
        self.plan_calculator = PlanCalculator(
            self.fed, self.state, self.espp,
            self.social_security, self.medicare, self.rsu_calculator
        )
    
    def _calculate_plan(self):
        """Calculate the complete financial plan using PlanCalculator."""
        self.plan_data: PlanData = self.plan_calculator.calculate(self.spec)
    
    def get_program_overview(self) -> dict:
        """Get an overview of the financial plan."""
        income = self.spec.get('income', {})
        deferred_plan = self.spec.get('deferredCompensationPlan', {})
        rsu_config = self.spec.get('restrictedStockUnits', {})
        
        return {
            "program_name": self.program_name,
            "planning_horizon": {
                "first_year": self.plan_data.first_year,
                "last_working_year": self.plan_data.last_working_year,
                "last_planning_year": self.plan_data.last_planning_year,
                "working_years": self.plan_data.last_working_year - self.plan_data.first_year + 1,
                "retirement_years": self.plan_data.last_planning_year - self.plan_data.last_working_year
            },
            "income_sources": {
                "base_salary": income.get('baseSalary', 0),
                "bonus_fraction": income.get('bonusFraction', 0),
                "espp_discount": self.spec.get('esppDiscount', 0),
                "other_income": income.get('otherIncome', 0),
                "realized_short_term_capital_gains_percent": income.get('realizedShortTermCapitalGainsPercent', 0),
                "realized_long_term_capital_gains_percent": income.get('realizedLongTermCapitalGainsPercent', 0)
            },
            "deferred_compensation": {
                "base_deferral_fraction": income.get('baseDeferralFraction', 0),
                "bonus_deferral_fraction": income.get('bonusDeferralFraction', 0),
                "disbursement_years": deferred_plan.get('disbursementYears', 0),
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
        working_years = list(range(self.plan_data.first_year, self.plan_data.last_working_year + 1))
        retirement_years = list(range(self.plan_data.last_working_year + 1, self.plan_data.last_planning_year + 1))
        
        # Identify disbursement years (years with deferred comp disbursements)
        disbursement_years = []
        for year, yd in self.plan_data.yearly_data.items():
            if yd.deferred_comp_disbursement > 0:
                disbursement_years.append(year)
        
        return {
            "working_years": working_years,
            "retirement_years": retirement_years,
            "disbursement_years": sorted(disbursement_years),
            "total_years": len(working_years) + len(retirement_years)
        }
    
    def get_annual_summary(self, year: int) -> dict:
        """Get income and tax summary for a specific year."""
        yd = self.plan_data.get_year(year)
        if yd is None:
            return {"error": f"Year {year} is not in the planning horizon ({self.plan_data.first_year}-{self.plan_data.last_planning_year})"}
        
        return {
            "year": year,
            "is_working_year": yd.is_working_year,
            "gross_income": round(yd.gross_income, 2),
            "federal_tax": round(yd.federal_tax, 2),
            "fica_tax": round(yd.total_fica, 2),
            "state_tax": round(yd.state_tax, 2),
            "total_tax": round(yd.total_taxes, 2),
            "effective_tax_rate": round(yd.effective_tax_rate * 100, 1),
            "take_home_pay": round(yd.take_home_pay, 2),
            "total_deferral": round(yd.total_deferral, 2)
        }
    
    def get_tax_details(self, year: int) -> dict:
        """Get detailed tax breakdown for a specific year."""
        yd = self.plan_data.get_year(year)
        if yd is None:
            return {"error": f"Year {year} is not in the planning horizon"}
        
        return {
            "year": year,
            "federal": {
                "ordinary_income_tax": round(yd.ordinary_income_tax, 2),
                "long_term_capital_gains_tax": round(yd.long_term_capital_gains_tax, 2),
                "total_federal_tax": round(yd.federal_tax, 2),
                "marginal_bracket": f"{yd.marginal_bracket:.1%}"
            },
            "fica": {
                "social_security": round(yd.social_security_tax, 2),
                "medicare": round(yd.medicare_tax, 2),
                "medicare_surcharge": round(yd.medicare_surcharge, 2),
                "total_fica": round(yd.total_fica, 2)
            },
            "state": {
                "income_tax": round(yd.state_income_tax, 2),
                "short_term_capital_gains_tax": round(yd.state_short_term_capital_gains_tax, 2),
                "total_state_tax": round(yd.state_tax, 2)
            },
            "deductions": {
                "standard_deduction": round(yd.standard_deduction, 2),
                "max_401k": round(yd.max_401k, 2),
                "max_hsa": round(yd.max_hsa, 2),
                "employee_hsa": round(yd.employee_hsa, 2),
                "medical_dental_vision": round(yd.medical_dental_vision, 2),
                "total_deductions": round(yd.total_deductions, 2)
            },
            "adjusted_gross_income": round(yd.adjusted_gross_income, 2)
        }
    
    def get_income_breakdown(self, year: int) -> dict:
        """Get detailed income breakdown for a specific year."""
        yd = self.plan_data.get_year(year)
        if yd is None:
            return {"error": f"Year {year} is not in the planning horizon"}
        
        breakdown = {
            "year": year,
            "is_working_year": yd.is_working_year,
            "gross_income": round(yd.gross_income, 2)
        }
        
        if yd.is_working_year:
            breakdown["earned_income"] = {
                "base_salary": round(yd.base_salary, 2),
                "bonus": round(yd.bonus, 2),
                "other_income": round(yd.other_income, 2),
                "rsu_vested_value": round(yd.rsu_vested_value, 2),
                "espp_income": round(yd.espp_income, 2)
            }
        
        breakdown["investment_income"] = {
            "realized_short_term_capital_gains": round(yd.short_term_capital_gains, 2),
            "realized_long_term_capital_gains": round(yd.long_term_capital_gains, 2)
        }
        
        breakdown["deferred_comp_disbursement"] = round(yd.deferred_comp_disbursement, 2)
        
        return breakdown
    
    def get_deferred_comp_info(self, year: int) -> dict:
        """Get deferred compensation information for a specific year."""
        yd = self.plan_data.get_year(year)
        if yd is None:
            return {"error": f"Year {year} is not in the planning horizon"}
        
        return {
            "year": year,
            "is_working_year": yd.is_working_year,
            "contribution": round(yd.deferred_comp_contribution, 2),
            "base_deferral": round(yd.base_deferral, 2),
            "bonus_deferral": round(yd.bonus_deferral, 2),
            "disbursement": round(yd.deferred_comp_disbursement, 2),
            "end_of_year_balance": round(yd.balance_deferred_comp, 2)
        }
    
    def get_retirement_balances(self, year: Optional[int] = None) -> dict:
        """Get 401(k) and deferred comp balances."""
        if year is not None:
            yd = self.plan_data.get_year(year)
            if yd is None:
                return {"error": f"Year {year} not found in balance data"}
            
            return {
                "year": year,
                "balances": {
                    "401k_contribution": round(yd.total_401k_contribution, 2),
                    "401k_balance": round(yd.balance_ira, 2),
                    "deferred_contribution": round(yd.deferred_comp_contribution, 2),
                    "deferred_balance": round(yd.balance_deferred_comp, 2),
                    "total_retirement_assets": round(yd.balance_ira + yd.balance_deferred_comp, 2)
                }
            }
        
        # Return summary
        return {
            "final_balances": {
                "401k_balance": round(self.plan_data.final_401k_balance, 2),
                "deferred_balance": round(self.plan_data.final_deferred_comp_balance, 2),
                "total_retirement_assets": round(self.plan_data.total_retirement_assets, 2)
            },
            "yearly_balances": [
                {
                    "year": yd.year,
                    "401k_balance": round(yd.balance_ira, 2),
                    "deferred_balance": round(yd.balance_deferred_comp, 2)
                }
                for yd in sorted(self.plan_data.yearly_data.values(), key=lambda x: x.year)
            ]
        }
    
    def get_investment_balances(self, year: Optional[int] = None) -> dict:
        """Get investment account balances (taxable, tax-deferred, HSA)."""
        investments = self.spec.get('investments', {})
        
        # Check if investments are configured
        if not investments:
            return {
                "message": "No investment accounts configured in this program.",
                "hint": "Add an 'investments' section to your spec.json with taxableBalance, taxDeferredBalance, and/or hsaBalance."
            }
        
        if year is not None:
            yd = self.plan_data.get_year(year)
            if yd is None:
                return {"error": f"Year {year} is not in the planning horizon ({self.plan_data.first_year}-{self.plan_data.last_planning_year})"}
            
            result = {
                "year": year,
                "is_working_year": yd.is_working_year,
                "balances": {
                    "taxable_account": round(yd.balance_taxable, 2),
                    "tax_deferred_account": round(yd.balance_ira, 2),
                    "hsa_account": round(yd.balance_hsa, 2),
                    "total_investments": round(yd.total_assets, 2)
                },
                "appreciation_rates": {
                    "taxable": investments.get('taxableAppreciationRate', 0),
                    "tax_deferred": investments.get('taxDeferredAppreciationRate', 0),
                    "hsa": investments.get('hsaAppreciationRate', 0)
                }
            }
            
            # Include contributions if working year
            if yd.is_working_year:
                result["contributions"] = {
                    "401k_contribution": round(yd.employee_401k_contribution, 2),
                    "employer_match": round(yd.employer_401k_match, 2),
                    "hsa_contribution": round(yd.hsa_contribution, 2)
                }
            
            return result
        
        # Return all years summary
        first_yd = self.plan_data.get_year(self.plan_data.first_year)
        last_working_yd = self.plan_data.get_year(self.plan_data.last_working_year)
        final_yd = self.plan_data.get_year(self.plan_data.last_planning_year)
        
        return {
            "initial_balances": {
                "taxable": round(investments.get('taxableBalance', 0), 2),
                "tax_deferred": round(investments.get('taxDeferredBalance', 0), 2),
                "hsa": round(investments.get('hsaBalance', 0), 2)
            },
            "appreciation_rates": {
                "taxable": investments.get('taxableAppreciationRate', 0),
                "tax_deferred": investments.get('taxDeferredAppreciationRate', 0),
                "hsa": investments.get('hsaAppreciationRate', 0)
            },
            "at_retirement": {
                "year": self.plan_data.last_working_year,
                "taxable": round(last_working_yd.balance_taxable if last_working_yd else 0, 2),
                "tax_deferred": round(last_working_yd.balance_ira if last_working_yd else 0, 2),
                "hsa": round(last_working_yd.balance_hsa if last_working_yd else 0, 2),
                "total": round(last_working_yd.total_assets if last_working_yd else 0, 2)
            },
            "final_balances": {
                "year": self.plan_data.last_planning_year,
                "taxable": round(final_yd.balance_taxable if final_yd else 0, 2),
                "tax_deferred": round(final_yd.balance_ira if final_yd else 0, 2),
                "hsa": round(final_yd.balance_hsa if final_yd else 0, 2),
                "total": round(final_yd.total_assets if final_yd else 0, 2)
            },
            "yearly_totals": [
                {"year": yd.year, "total": round(yd.total_assets, 2)}
                for yd in sorted(self.plan_data.yearly_data.values(), key=lambda x: x.year)
            ]
        }

    def compare_years(self, year1: int, year2: int) -> dict:
        """Compare financial metrics between two years."""
        yd1 = self.plan_data.get_year(year1)
        if yd1 is None:
            return {"error": f"Year {year1} is not in the planning horizon"}
        yd2 = self.plan_data.get_year(year2)
        if yd2 is None:
            return {"error": f"Year {year2} is not in the planning horizon"}
        
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
            "gross_income": compare_metric(yd1.gross_income, yd2.gross_income),
            "federal_tax": compare_metric(yd1.federal_tax, yd2.federal_tax),
            "total_tax": compare_metric(yd1.total_taxes, yd2.total_taxes),
            "take_home_pay": compare_metric(yd1.take_home_pay, yd2.take_home_pay)
        }
    
    def get_lifetime_totals(self) -> dict:
        """Get lifetime totals across the planning horizon."""
        totals = {
            "gross_income": 0.0,
            "federal_tax": 0.0,
            "fica": 0.0,
            "state_tax": 0.0,
            "total_tax": 0.0,
            "take_home_pay": 0.0,
            "total_deferred": 0.0
        }
        
        working_totals = dict(totals)
        retirement_totals = dict(totals)
        
        for year, yd in self.plan_data.yearly_data.items():
            target = working_totals if yd.is_working_year else retirement_totals
            target["gross_income"] += yd.gross_income
            target["federal_tax"] += yd.federal_tax
            target["fica"] += yd.total_fica
            target["state_tax"] += yd.state_tax
            target["total_tax"] += yd.total_taxes
            target["take_home_pay"] += yd.take_home_pay
            target["total_deferred"] += yd.total_deferral
        
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
        
        # Map common terms to YearlyData field names
        term_mapping = {
            "espp": ["espp_income"],
            "rsu": ["rsu_vested_value"],
            "stock": ["rsu_vested_value", "espp_income"],
            "salary": ["base_salary"],
            "bonus": ["bonus"],
            "federal": ["federal_tax", "ordinary_income_tax"],
            "state": ["state_tax", "state_income_tax"],
            "fica": ["social_security_tax", "medicare_tax", "medicare_surcharge", "total_fica"],
            "social security": ["social_security_tax"],
            "medicare": ["medicare_tax", "medicare_surcharge"],
            "take home": ["take_home_pay"],
            "gross": ["gross_income"],
            "deferred": ["total_deferral", "deferred_comp_disbursement"],
            "disbursement": ["deferred_comp_disbursement"],
            "capital gain": ["short_term_capital_gains", "long_term_capital_gains"],
            "ltcg": ["long_term_capital_gains", "long_term_capital_gains_tax"],
            "marginal": ["marginal_bracket"],
            "effective": ["effective_tax_rate"],
            "deduction": ["total_deductions", "standard_deduction"],
            "401k": ["max_401k", "employee_401k_contribution", "employer_401k_match", "balance_ira"],
            "hsa": ["max_hsa", "employee_hsa", "hsa_contribution", "balance_hsa"],
            "balance": ["balance_ira", "balance_deferred_comp", "balance_hsa", "balance_taxable", "total_assets"],
            "expense": ["annual_expenses", "special_expenses", "travel_expenses", "total_expenses"],
            "travel": ["travel_expenses"],
            "contribution": ["employee_401k_contribution", "employer_401k_match", "hsa_contribution", "deferred_comp_contribution"]
        }
        
        # Find matching terms
        matched_keys = []
        for term, keys in term_mapping.items():
            if term in query_lower:
                matched_keys.extend(keys)
        
        if not matched_keys:
            return {
                "query": query,
                "message": "No matching financial metrics found. Try terms like: ESPP, RSU, salary, federal tax, state tax, FICA, take home, gross income, deferred, capital gains, 401k, HSA, balance, expense, contribution, etc."
            }
        
        # Get results
        if year is not None:
            yd = self.plan_data.get_year(year)
            if yd is None:
                return {"error": f"Year {year} is not in the planning horizon"}
            
            found_data = {"year": year, "query": query, "results": {}}
            
            for key in matched_keys:
                if hasattr(yd, key):
                    value = getattr(yd, key)
                    if isinstance(value, float):
                        found_data["results"][key] = round(value, 2)
                    else:
                        found_data["results"][key] = value
            
            return found_data
        else:
            # Return data for all years
            all_years_data = {"query": query, "years": {}}
            
            for yr, yd in sorted(self.plan_data.yearly_data.items()):
                year_data = {}
                
                for key in matched_keys:
                    if hasattr(yd, key):
                        value = getattr(yd, key)
                        if isinstance(value, float):
                            year_data[key] = round(value, 2)
                        else:
                            year_data[key] = value
                
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
    
    def get_investment_balances(self, year: Optional[int] = None, program: Optional[str] = None) -> dict:
        """Get investment account balances (taxable, tax-deferred, HSA)."""
        result = self._get_program(program, require_explicit=True).get_investment_balances(year)
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
