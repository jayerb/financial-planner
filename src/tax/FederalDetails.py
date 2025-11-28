
import json
import os
from model.FederalResult import FederalResult

class FederalDetails:
	def __init__(self, inflation_rate: float, final_year: int):
		"""
		inflation_rate: e.g., 0.03 for 3% inflation
		final_year: last year to generate brackets for (inclusive)
		"""
		self.inflation_rate = inflation_rate
		self.final_year = final_year
		self.brackets_by_year = {}
		self.deductions_by_year = {}
		self.ltcg_brackets_by_year = {}
		self._load_and_build_brackets()

	def _load_and_build_brackets(self):
		# Load initial brackets from JSON
		ref_path = os.path.join(os.path.dirname(__file__), '../../reference/federal-details.json')
		with open(ref_path, 'r') as f:
			data = json.load(f)

		tax_years = data.get("taxYears", [])
		if not tax_years:
			raise ValueError("federal-details.json must contain a 'taxYears' array with at least one entry")

		# Sort tax years to ensure they're in order
		tax_years = sorted(tax_years, key=lambda x: x["year"])

		# Validate that years are sequential
		for i in range(1, len(tax_years)):
			if tax_years[i]["year"] != tax_years[i-1]["year"] + 1:
				raise ValueError(f"Tax years must be sequential. Gap found between {tax_years[i-1]['year']} and {tax_years[i]['year']}")

		# Load all specified years directly
		for year_data in tax_years:
			year = year_data["year"]
			brackets = []
			for b in year_data["brackets"]:
				rate = b["rate"]
				if rate > 1:
					rate = rate / 100.0
				brackets.append({
					"maxIncome": b["maxIncome"],
					"rate": rate,
					"baseAmount": b["baseAmount"]
				})
			self.brackets_by_year[year] = brackets

			# Store deductions for this year
			self.deductions_by_year[year] = {
				"standardDeduction": year_data.get("standardDeduction", 0),
				"max401k": year_data.get("maxContributions", {}).get("401k", 0),
				"maxHSA": year_data.get("maxContributions", {}).get("HSA", 0)
			}

			# Load qualified dividend / LTCG brackets for this year
			ltcg_brackets = []
			for b in year_data.get("qualifedDivLTCGBrackets", []):
				rate = b["rate"]
				if rate > 1:
					rate = rate / 100.0
				ltcg_brackets.append({
					"maxIncome": b["maxIncome"],
					"rate": rate
				})
			self.ltcg_brackets_by_year[year] = ltcg_brackets

		# Get the last specified year to use as base for inflation
		last_specified_year = tax_years[-1]["year"]
		last_brackets = self.brackets_by_year[last_specified_year]
		last_deductions = self.deductions_by_year[last_specified_year]
		last_ltcg_brackets = self.ltcg_brackets_by_year[last_specified_year]

		# Build inflated brackets for years after the last specified year
		year = last_specified_year + 1
		brackets = last_brackets
		deductions = last_deductions
		ltcg_brackets = last_ltcg_brackets
		while year <= self.final_year:
			# Inflate brackets
			brackets = [
				{
					"maxIncome": b["maxIncome"] * (1 + self.inflation_rate),
					"rate": b["rate"],
					"baseAmount": b["baseAmount"] * (1 + self.inflation_rate)
				}
				for b in brackets
			]
			self.brackets_by_year[year] = [dict(b) for b in brackets]

			# Inflate deductions
			deductions = {
				"standardDeduction": deductions["standardDeduction"] * (1 + self.inflation_rate),
				"max401k": deductions["max401k"] * (1 + self.inflation_rate),
				"maxHSA": deductions["maxHSA"] * (1 + self.inflation_rate)
			}
			self.deductions_by_year[year] = dict(deductions)

			# Inflate LTCG brackets
			ltcg_brackets = [
				{
					"maxIncome": b["maxIncome"] * (1 + self.inflation_rate),
					"rate": b["rate"]
				}
				for b in ltcg_brackets
			]
			self.ltcg_brackets_by_year[year] = [dict(b) for b in ltcg_brackets]

			year += 1

	def taxBurden(self, income: float, year: int) -> FederalResult:
		"""
		Returns a FederalResult with the total federal tax burden and marginal bracket for a given income and year.
		"""
		if year not in self.brackets_by_year:
			raise ValueError(f"No tax brackets available for year {year}")
		brackets = self.brackets_by_year[year]
		for b in brackets:
			if income <= b["maxIncome"]:
				total_tax = b["baseAmount"] + (income - (0 if brackets.index(b) == 0 else brackets[brackets.index(b)-1]["maxIncome"])) * b["rate"]
				return FederalResult(totalFederalTax=total_tax, marginalBracket=b["rate"])
		# Should not reach here
		raise ValueError("Income exceeds all bracket definitions.")

	def totalDeductions(self, year: int) -> dict:
		"""
		Returns a dictionary with itemized deductions and total for the given year.
		Uses specified values for years in the JSON, or inflated values for future years.
		
		Returns:
			dict with keys: standardDeduction, max401k, maxHSA, total
		"""
		if year not in self.deductions_by_year:
			raise ValueError(f"No deduction data available for year {year}")
		d = self.deductions_by_year[year]
		total = d["standardDeduction"] + d["max401k"] + d["maxHSA"]
		return {
			"standardDeduction": d["standardDeduction"],
			"max401k": d["max401k"],
			"maxHSA": d["maxHSA"],
			"total": total
		}

	def longTermCapitalGainsTax(self, ordinary_taxable_income: float, ltcg_amount: float, year: int) -> float:
		"""
		Calculates the tax on long-term capital gains (LTCG) and qualified dividends.
		
		LTCG are taxed at preferential rates (0%, 15%, or 20%) that are lower than
		ordinary income tax rates. The rate that applies depends on your TOTAL taxable
		income (ordinary income + LTCG), not just the LTCG amount.
		
		KEY CONCEPT - "STACKING":
		LTCG is "stacked on top of" ordinary income to determine which bracket(s) it
		falls into. This means:
		1. Ordinary income fills the bottom of the income scale first
		2. LTCG then fills the remaining space in the brackets
		3. LTCG gets taxed at the rate of whichever bracket(s) it lands in
		
		EXAMPLE (2025 MFJ brackets: 0% up to $96,700, 15% up to $600,050, 20% above):
		- Ordinary taxable income: $80,000
		- Long-term capital gains: $30,000
		- Total taxable income: $110,000
		
		The LTCG "starts" at $80,000 and extends to $110,000:
		- $16,700 ($80,000 → $96,700) taxed at 0% = $0
		- $13,300 ($96,700 → $110,000) taxed at 15% = $1,995
		- Total LTCG tax: $1,995
		
		This stacking approach ensures LTCG benefits from the lowest available rates.
		If ordinary income already exceeds a bracket threshold, LTCG skips that bracket.
		
		Args:
			ordinary_taxable_income: Taxable income excluding LTCG (after deductions).
			                         This is where the LTCG "stacking" starts from.
			ltcg_amount: Long-term capital gains and qualified dividends amount
			year: Tax year (used to look up the correct LTCG brackets)
			
		Returns:
			The federal tax owed on the long-term capital gains
		"""
		if year not in self.ltcg_brackets_by_year:
			raise ValueError(f"No LTCG tax brackets available for year {year}")
		
		if ltcg_amount <= 0:
			return 0.0
		
		brackets = self.ltcg_brackets_by_year[year]
		total_income = ordinary_taxable_income + ltcg_amount
		ltcg_tax = 0.0
		
		# income_floor: The starting point for LTCG taxation (where ordinary income ends)
		# This is where LTCG gets "stacked" on top of ordinary income
		income_floor = max(0, ordinary_taxable_income)
		remaining_ltcg = ltcg_amount
		
		for b in brackets:
			if remaining_ltcg <= 0:
				break
			
			# Determine this bracket's income range
			# bracket_floor: The bottom of this bracket (top of previous bracket, or 0 for first)
			# bracket_ceiling: The top of this bracket (maxIncome)
			bracket_floor = 0 if brackets.index(b) == 0 else brackets[brackets.index(b) - 1]["maxIncome"]
			bracket_ceiling = b["maxIncome"]
			
			# Skip brackets that ordinary income has already filled completely
			# If ordinary income >= bracket ceiling, no LTCG falls in this bracket
			if income_floor >= bracket_ceiling:
				continue
			
			# Calculate the portion of LTCG that falls within this bracket:
			# - Start: The higher of (where ordinary income ends) or (bracket floor)
			# - End: The lower of (total income) or (bracket ceiling)
			taxable_in_bracket_start = max(income_floor, bracket_floor)
			taxable_in_bracket_end = min(total_income, bracket_ceiling)
			taxable_in_bracket = max(0, taxable_in_bracket_end - taxable_in_bracket_start)
			
			# Don't tax more LTCG than we actually have remaining
			taxable_in_bracket = min(taxable_in_bracket, remaining_ltcg)
			
			# Apply this bracket's rate to the LTCG portion in this bracket
			ltcg_tax += taxable_in_bracket * b["rate"]
			remaining_ltcg -= taxable_in_bracket
		
		return ltcg_tax
