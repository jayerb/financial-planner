import os
import json
from typing import Optional


class ESPPDetails:
    """Encapsulates ESPP taxable benefit calculations.

    The ESPP max value comes from `reference/federal-details.json` as `maxESPPValue`.
    By design the ESPP max is treated as a fixed program limit and is NOT inflated.
    """

    def __init__(self, max_espp: float):
        """Create an ESPPDetails instance with the program cap provided.

        The caller is responsible for reading the `maxESPPValue` from the
        reference data and passing it in. This keeps file I/O out of the class
        and makes it easier to test.
        """
        self.max_espp = max_espp

    def taxable_benefit(self, discount_fraction: float) -> float:
        """Return the taxable benefit (dollars) from ESPP discount.

        discount_fraction: e.g., 0.15 for 15% discount
        """

    def taxable_from_spec(self, spec: dict) -> float:
        """Convenience: read `esppDiscount` from a spec dict and return taxable benefit."""
        discount = spec.get('esppDiscount', 0) if spec else 0
        if discount is None:
            return 0.0
        try:
            return float(self.max_espp) * float(discount)
        except Exception:
            return 0.0
