import os
import json
from typing import Optional


class ESPPDetails:
    """Encapsulates ESPP taxable benefit calculations.

    The ESPP max value comes from `reference/federal-details.json` as `maxESPPValue`.
    By design the ESPP max is treated as a fixed program limit and is NOT inflated.
    """

    def __init__(self):
        ref_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'reference', 'federal-details.json'))
        with open(ref_path, 'r') as f:
            data = json.load(f)

        # read base program cap; do not inflate this value
        self.max_espp = data.get('maxESPPValue', 0)

    def taxable_benefit(self, discount_fraction: float) -> float:
        """Return the taxable benefit (dollars) from ESPP discount.

        discount_fraction: e.g., 0.15 for 15% discount
        """
        if discount_fraction is None:
            return 0.0
        try:
            return float(self.max_espp) * float(discount_fraction)
        except Exception:
            return 0.0

    def taxable_from_spec(self, spec: dict) -> float:
        """Convenience: read `esppDiscount` from a spec dict and return taxable benefit."""
        discount = spec.get('esppDiscount', 0) if spec else 0
        return self.taxable_benefit(discount)
