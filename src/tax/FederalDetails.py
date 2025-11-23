# import required modules
import json
import os

class FederalDetails:
	def __init__(self, inflation_rate: float, final_year: int):
		"""
		inflation_rate: e.g., 0.03 for 3% inflation
		final_year: last year to generate brackets for (inclusive)
		"""
		self.inflation_rate = inflation_rate
		self.final_year = final_year
		self.brackets_by_year = {}
		self._load_and_build_brackets()

	def _load_and_build_brackets(self):
		# Load initial brackets from JSON
		ref_path = os.path.join(os.path.dirname(__file__), '../../reference/federal-details.json')
		with open(ref_path, 'r') as f:
			data = json.load(f)
		base_year = data["taxYear"]
		# Extract brackets for the base year
		base_brackets = []
		for i in range(1, 8):
			b = data[f"bracket{i}"]
			# Ensure rate is in decimal form
			rate = b["rate"]
			if rate > 1:
				rate = rate / 100.0
			base_brackets.append({
				"maxIncome": b["maxIncome"],
				"rate": rate,
				"baseAmount": b["baseAmount"]
			})
		# Build brackets for each year
		year = base_year
		brackets = base_brackets
		while year <= self.final_year:
			# Deep copy for this year
			self.brackets_by_year[year] = [dict(b) for b in brackets]
			# Inflate for next year
			brackets = [
				{
					"maxIncome": b["maxIncome"] * (1 + self.inflation_rate),
					"rate": b["rate"],
					"baseAmount": b["baseAmount"] * (1 + self.inflation_rate)
				}
				for b in brackets
			]
			year += 1

	def taxBurden(self, income: float, year: int) -> float:
		"""
		Returns the total federal tax burden for a given income and year.
		"""
		if year not in self.brackets_by_year:
			raise ValueError(f"No tax brackets available for year {year}")
		brackets = self.brackets_by_year[year]
		for b in brackets:
			if income <= b["maxIncome"]:
				return b["baseAmount"] + (income - (0 if brackets.index(b) == 0 else brackets[brackets.index(b)-1]["maxIncome"])) * b["rate"]
		# Should not reach here
		raise ValueError("Income exceeds all bracket definitions.")

	def totalDeductions(self, year: int) -> float:
		"""
		Returns the total deductions (standard deduction + max 401k + max HSA) for the given year,
		inflating each value by the inflation rate for each year after the base year.
		"""
		ref_path = os.path.join(os.path.dirname(__file__), '../../reference/federal-details.json')
		with open(ref_path, 'r') as f:
			data = json.load(f)
		base_year = data["taxYear"]
		std_ded = data.get("standardDeduction", 0)
		max_401k = data.get("maxContributions", {}).get("401k", 0)
		max_hsa = data.get("maxContributions", {}).get("HSA", 0)
		years = year - base_year
		if years < 0:
			raise ValueError(f"Year {year} is before base year {base_year}")
		inflation = (1 + self.inflation_rate) ** years
		total = std_ded * inflation + max_401k * inflation + max_hsa * inflation
		return total
