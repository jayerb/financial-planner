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
        deductions_2025 = self.fed.totalDeductions(2025)
        self.assertAlmostEqual(deductions_2025['standardDeduction'], std_ded, places=2)
        self.assertAlmostEqual(deductions_2025['max401k'], max_401k, places=2)
        self.assertAlmostEqual(deductions_2025['maxHSA'], max_hsa, places=2)
        self.assertAlmostEqual(deductions_2025['total'], base_total, places=2)

        # For 2026, no inflation applied since it's explicitly specified
        std_ded_2026 = 32200.00
        max_401k_2026 = 24000.00
        max_hsa_2026 = 8806.50
        expected_2026 = std_ded_2026 + max_401k_2026 + max_hsa_2026
        deductions_2026 = self.fed.totalDeductions(2026)
        self.assertAlmostEqual(deductions_2026['standardDeduction'], std_ded_2026, places=2)
        self.assertAlmostEqual(deductions_2026['max401k'], max_401k_2026, places=2)
        self.assertAlmostEqual(deductions_2026['maxHSA'], max_hsa_2026, places=2)
        self.assertAlmostEqual(deductions_2026['total'], expected_2026, places=2)

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

    def test_ltcg_brackets_loaded(self):
        # Verify LTCG brackets are loaded for base years
        self.assertIn(2025, self.fed.ltcg_brackets_by_year)
        self.assertIn(2026, self.fed.ltcg_brackets_by_year)
        # Verify inflated years also have LTCG brackets
        self.assertIn(2027, self.fed.ltcg_brackets_by_year)
        self.assertIn(2028, self.fed.ltcg_brackets_by_year)

    def test_ltcg_brackets_structure(self):
        # Verify LTCG brackets have correct structure
        brackets_2025 = self.fed.ltcg_brackets_by_year[2025]
        self.assertEqual(len(brackets_2025), 3)
        self.assertAlmostEqual(brackets_2025[0]["maxIncome"], 96700.00, places=2)
        self.assertAlmostEqual(brackets_2025[0]["rate"], 0.0, places=4)
        self.assertAlmostEqual(brackets_2025[1]["maxIncome"], 600050.00, places=2)
        self.assertAlmostEqual(brackets_2025[1]["rate"], 0.15, places=4)
        self.assertAlmostEqual(brackets_2025[2]["rate"], 0.20, places=4)

    def test_ltcg_brackets_inflated(self):
        # Verify LTCG brackets are inflated for future years
        brackets_2026 = self.fed.ltcg_brackets_by_year[2026]
        brackets_2027 = self.fed.ltcg_brackets_by_year[2027]
        # 2027 should be 2026 * (1 + 0.03)
        for i in range(len(brackets_2026)):
            expected_max = brackets_2026[i]["maxIncome"] * 1.03
            self.assertAlmostEqual(brackets_2027[i]["maxIncome"], expected_max, places=2)

    def test_ltcg_tax_zero_gains(self):
        # No LTCG means no LTCG tax
        tax = self.fed.longTermCapitalGainsTax(50000, 0, 2025)
        self.assertAlmostEqual(tax, 0.0, places=2)

    def test_ltcg_tax_in_zero_percent_bracket(self):
        # 2025: 0% bracket up to $96,700
        # If ordinary income is $50,000 and LTCG is $10,000, total is $60,000
        # All LTCG falls in 0% bracket
        tax = self.fed.longTermCapitalGainsTax(50000, 10000, 2025)
        self.assertAlmostEqual(tax, 0.0, places=2)

    def test_ltcg_tax_spans_zero_and_fifteen_percent_brackets(self):
        # 2025: 0% bracket up to $96,700, 15% up to $600,050
        # If ordinary income is $90,000 and LTCG is $20,000, total is $110,000
        # First $6,700 of LTCG is in 0% bracket, remaining $13,300 in 15% bracket
        tax = self.fed.longTermCapitalGainsTax(90000, 20000, 2025)
        expected = (6700 * 0.0) + (13300 * 0.15)
        self.assertAlmostEqual(tax, expected, places=2)

    def test_ltcg_tax_all_in_fifteen_percent_bracket(self):
        # 2025: 0% bracket up to $96,700, 15% up to $600,050
        # If ordinary income is $100,000 (already past 0% bracket)
        # and LTCG is $10,000, all LTCG is in 15% bracket
        tax = self.fed.longTermCapitalGainsTax(100000, 10000, 2025)
        expected = 10000 * 0.15
        self.assertAlmostEqual(tax, expected, places=2)

    def test_ltcg_tax_spans_fifteen_and_twenty_percent_brackets(self):
        # 2025: 15% bracket up to $600,050, 20% above
        # If ordinary income is $590,000 and LTCG is $20,000, total is $610,000
        # First $10,050 in 15% bracket, remaining $9,950 in 20% bracket
        tax = self.fed.longTermCapitalGainsTax(590000, 20000, 2025)
        expected = (10050 * 0.15) + (9950 * 0.20)
        self.assertAlmostEqual(tax, expected, places=2)

    def test_ltcg_tax_invalid_year(self):
        # Year before the first specified year should raise error
        with self.assertRaises(ValueError):
            self.fed.longTermCapitalGainsTax(50000, 10000, 2024)

if __name__ == '__main__':
    unittest.main()
