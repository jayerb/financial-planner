import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/tax')))
from FederalBrackets import FederalBrackets

class TestFederalBrackets(unittest.TestCase):
    def setUp(self):
        # Use 3% inflation, test up to 2028
        self.inflation = 0.03
        self.final_year = 2028
        self.fed = FederalBrackets(self.inflation, self.final_year)

    def test_bracket_cache_years(self):
        # Should include 2026, 2027, 2028
        self.assertIn(2026, self.fed.brackets_by_year)
        self.assertIn(2027, self.fed.brackets_by_year)
        self.assertIn(2028, self.fed.brackets_by_year)

    def test_tax_burden_base_year(self):
        # Test known values for 2026
        # Bracket 1: up to 24800 @ 10%
        self.assertAlmostEqual(self.fed.taxBurden(10000, 2026), 1000.0, places=2)
        # Bracket 2: up to 100800 @ 12%, base 2480
        self.assertAlmostEqual(self.fed.taxBurden(50000, 2026), 2480 + (50000-24800)*0.12, places=2)
        # Bracket 7: very high income
        self.assertAlmostEqual(self.fed.taxBurden(1_000_000, 2026), 206582.25 + (1_000_000-768700)*0.37, places=2)

    def test_tax_burden_inflated_year(self):
        # For 2027, brackets should be inflated by 3%
        # Bracket 1 max: 24800 * 1.03
        bracket1_max_2027 = 24800 * 1.03
        # Bracket 2 base: 2480 * 1.03
        bracket2_base_2027 = 2480 * 1.03
        # Bracket 2 rate: 12%
        # Test income just above bracket 1
        income = bracket1_max_2027 + 1000
        expected = bracket2_base_2027 + (income - bracket1_max_2027) * 0.12
        self.assertAlmostEqual(self.fed.taxBurden(income, 2027), expected, places=2)

    def test_invalid_year(self):
        with self.assertRaises(ValueError):
            self.fed.taxBurden(50000, 2025)

if __name__ == '__main__':
    unittest.main()
