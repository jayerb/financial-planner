import json
import os


class SocialSecurityDetails:
    """Holds Social Security and MA PFML statutory details and computes contributions.

    Loads statutory values from reference file and builds year-by-year data.
    For years beyond those specified in the JSON, values are projected using
    the annualIncreaseMaximum rate.
    """

    def __init__(self, inflation_rate: float, final_year: int):
        """Initialize by loading from reference file and building year data.

        Args:
            inflation_rate: Annual increase rate for projecting future years.
            final_year: Last year to generate data for (inclusive).
        """
        self.inflation_rate = inflation_rate
        self.final_year = final_year
        self.data_by_year = {}
        self._load_and_build_data()

    def _load_and_build_data(self):
        """Load data from JSON and build projections for future years."""
        ref_path = os.path.join(os.path.dirname(__file__), '../../reference/social-security.json')
        with open(ref_path, 'r') as f:
            data = json.load(f)

        tax_years = data.get("taxYears", [])
        if not tax_years:
            raise ValueError("social-security.json must contain a 'taxYears' array with at least one entry")

        # Get the annual increase rate for projections (defaults to inflation_rate if not specified)
        self.annual_increase = data.get("annualIncreaseMaximum", self.inflation_rate)

        # Sort tax years to ensure they're in order
        tax_years = sorted(tax_years, key=lambda x: x["year"])

        # Validate that years are sequential
        for i in range(1, len(tax_years)):
            if tax_years[i]["year"] != tax_years[i-1]["year"] + 1:
                raise ValueError(f"Tax years must be sequential. Gap found between {tax_years[i-1]['year']} and {tax_years[i]['year']}")

        # Load all specified years directly
        for year_data in tax_years:
            year = year_data["year"]
            self.data_by_year[year] = {
                "maximumTaxedIncome": year_data.get("maximumTaxedIncome", 0),
                "employeePortion": year_data.get("employeePortion", 0),
                "maPFML": year_data.get("maPFML", 0)
            }

        # Get the last specified year to use as base for projections
        last_specified_year = tax_years[-1]["year"]
        last_data = self.data_by_year[last_specified_year]

        # Build projected data for years after the last specified year
        year = last_specified_year + 1
        current_data = dict(last_data)
        while year <= self.final_year:
            # Only maximum taxed income increases; rates stay the same
            current_data = {
                "maximumTaxedIncome": current_data["maximumTaxedIncome"] * (1 + self.annual_increase),
                "employeePortion": current_data["employeePortion"],
                "maPFML": current_data["maPFML"]
            }
            self.data_by_year[year] = dict(current_data)
            year += 1

    def total_contribution(self, gross_income: float, year: int) -> float:
        """Calculate total Social Security + MA PFML contribution for a given year.

        Args:
            gross_income: The employee's gross income.
            year: The tax year to calculate for.

        Returns:
            The total contribution amount.
        """
        if year not in self.data_by_year:
            raise ValueError(f"No Social Security data available for year {year}")

        data = self.data_by_year[year]
        taxable_income = min(gross_income, data["maximumTaxedIncome"])
        return taxable_income * (data["employeePortion"] + data["maPFML"])

    def get_data_for_year(self, year: int) -> dict:
        """Get the Social Security data for a specific year.

        Args:
            year: The tax year to get data for.

        Returns:
            Dictionary with maximumTaxedIncome, employeePortion, and maPFML.
        """
        if year not in self.data_by_year:
            raise ValueError(f"No Social Security data available for year {year}")
        return self.data_by_year[year]

    def combined_rate(self, year: int) -> float:
        """Return the combined rate (employee portion + MA PFML) for a given year."""
        data = self.get_data_for_year(year)
        return data["employeePortion"] + data["maPFML"]
