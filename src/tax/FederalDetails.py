
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

		# Get the last specified year to use as base for inflation
		last_specified_year = tax_years[-1]["year"]
		last_brackets = self.brackets_by_year[last_specified_year]
		last_deductions = self.deductions_by_year[last_specified_year]

		# Build inflated brackets for years after the last specified year
		year = last_specified_year + 1
		brackets = last_brackets
		deductions = last_deductions
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

	def totalDeductions(self, year: int) -> float:
		"""
		Returns the total deductions (standard deduction + max 401k + max HSA) for the given year.
		Uses specified values for years in the JSON, or inflated values for future years.
		"""
		if year not in self.deductions_by_year:
			raise ValueError(f"No deduction data available for year {year}")
		d = self.deductions_by_year[year]
		return d["standardDeduction"] + d["max401k"] + d["maxHSA"]
