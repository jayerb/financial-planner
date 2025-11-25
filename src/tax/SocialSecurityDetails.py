class SocialSecurityDetails:
    """Holds Social Security and MA PFML statutory details and computes contributions.

    Constructed with statutory values loaded from reference files. Calculation
    methods accept variable program inputs (e.g., gross income).
    """

    def __init__(self, maximum_taxed_income: float, employee_portion: float, ma_pfml: float):
        """Initialize with statutory details.

        Args:
            maximum_taxed_income: The income cap subject to Social Security tax.
            employee_portion: The employee's Social Security tax rate.
            ma_pfml: The MA Paid Family and Medical Leave rate.
        """
        self.maximum_taxed_income = maximum_taxed_income
        self.employee_portion = employee_portion
        self.ma_pfml = ma_pfml

    def total_contribution(self, gross_income: float) -> float:
        """Calculate total Social Security + MA PFML contribution.

        Args:
            gross_income: The employee's gross income.

        Returns:
            The total contribution amount.
        """
        taxable_income = min(gross_income, self.maximum_taxed_income)
        return taxable_income * (self.employee_portion + self.ma_pfml)

    @property
    def combined_rate(self) -> float:
        """Return the combined rate (employee portion + MA PFML)."""
        return self.employee_portion + self.ma_pfml
