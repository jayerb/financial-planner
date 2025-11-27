import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
from tax.FederalDetails import FederalDetails

class TestFederalDetails(unittest.TestCase):
    def setUp(self):
        # Use 3% inflation, test up to 2028
        self.inflation = 0.03
        self.final_year = 2028
        self.fed = FederalDetails(self.inflation, self.final_year)

    def test_total_deductions(self):
        # Values from reference/federal-details.json for 2025 (base year)
        std_ded = 31500.00
        max_401k = 23500.00
        max_hsa = 8550.00
        base_total = std_ded + max_401k + max_hsa
        # For 2025, no inflation applied
        self.assertAlmostEqual(self.fed.totalDeductions(2025), base_total, places=2)

        # For 2026, no inflation applied since it's explicitly specified
        std_ded_2026 = 32200.00
        max_401k_2026 = 24000.00
        max_hsa_2026 = 8806.50
        expected_2026 = std_ded_2026 + max_401k_2026 + max_hsa_2026
        self.assertAlmostEqual(self.fed.totalDeductions(2026), expected_2026, places=2)

    def test_bracket_cache_years(self):
        # Should include 2025, 2026, 2027, 2028
        self.assertIn(2025, self.fed.brackets_by_year)
        self.assertIn(2026, self.fed.brackets_by_year)
        self.assertIn(2027, self.fed.brackets_by_year)
        self.assertIn(2028, self.fed.brackets_by_year)

    def test_tax_burden_base_year(self):
        # Test known values for 2025 (base year from JSON)
        # Bracket 1: up to 23850 @ 10%
        result1 = self.fed.taxBurden(10000, 2025)
        self.assertAlmostEqual(result1.totalFederalTax, 1000.0, places=2)
        # Bracket 2: up to 96950 @ 12%, base 2385
        result2 = self.fed.taxBurden(50000, 2025)
        self.assertAlmostEqual(result2.totalFederalTax, 2385 + (50000-23850)*0.12, places=2)

    def test_tax_burden_inflated_year(self):
        # For 2026, brackets should be inflated by 3% from 2025
        # Bracket 1 max: 23850 * 1.03
        bracket1_max_2027 = 24800 * 1.03
        # Bracket 2 base: 2385 * 1.03
        bracket2_base_2027 = 2480 * 1.03
        # Bracket 2 rate: 12%
        # Test income just above bracket 1
        income = bracket1_max_2027 + 1000
        expected = bracket2_base_2027 + (income - bracket1_max_2027) * 0.12
        result = self.fed.taxBurden(income, 2027)
        self.assertAlmostEqual(result.totalFederalTax, expected, places=2)

    def test_invalid_year(self):
        # Year before the first specified year should raise error
        with self.assertRaises(ValueError):
            self.fed.taxBurden(50000, 2024)

if __name__ == '__main__':
    unittest.main()
