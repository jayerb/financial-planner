class MedicareDetails:
    """Holds Medicare statutory details and computes contributions.

    Constructed with statutory values loaded from reference files. Calculation
    methods accept variable program inputs (e.g., gross income, deductions).
    """

    def __init__(self, medicare_rate: float, surcharge_threshold: float, surcharge_rate: float):
        """Initialize with statutory details.

        Args:
            medicare_rate: The base Medicare tax rate.
            surcharge_threshold: Income threshold above which the surcharge applies.
            surcharge_rate: The additional Medicare surcharge rate.
        """
        self.medicare_rate = medicare_rate
        self.surcharge_threshold = surcharge_threshold
        self.surcharge_rate = surcharge_rate

    def base_contribution(self, medicare_base: float) -> float:
        """Calculate the base Medicare contribution.

        Args:
            medicare_base: The income base for Medicare (gross - medical + life premium).

        Returns:
            The base Medicare charge.
        """
        return medicare_base * self.medicare_rate

    def surcharge(self, gross_income: float) -> float:
        """Calculate the Medicare surcharge if applicable.

        Args:
            gross_income: The employee's gross income.

        Returns:
            The surcharge amount (0 if below threshold).
        """
        if gross_income > self.surcharge_threshold:
            return (gross_income - self.surcharge_threshold) * self.surcharge_rate
        return 0

    def total_contribution(self, medicare_base: float, gross_income: float) -> float:
        """Calculate total Medicare contribution including surcharge.

        Args:
            medicare_base: The income base for Medicare (gross - medical + life premium).
            gross_income: The employee's gross income (used for surcharge calculation).

        Returns:
            The total Medicare contribution.
        """
        return self.base_contribution(medicare_base) + self.surcharge(gross_income)
