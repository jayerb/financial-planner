import sys
import os
import json
from calc.take_home import calculate_take_home

def main():
    if len(sys.argv) < 2:
        print("Usage: python src/Program.py <program_name>")
        sys.exit(1)
    program_name = sys.argv[1]
    # Build path to spec.json
    spec_path = os.path.join(os.path.dirname(__file__), '../input-parameters', program_name, 'spec.json')
    if not os.path.exists(spec_path):
        print(f"Spec file not found: {spec_path}")
        sys.exit(1)
    with open(spec_path, 'r') as f:
        spec = json.load(f)
    # Delegate calculation to helper so it can be unit tested
    tax_year = 2026
    results = calculate_take_home(spec, tax_year)

    print(f"Federal tax burden for {tax_year} on adjusted gross income ${results['adjusted_gross_income']:,.2f} (gross income ${results['gross_income']:,.2f}, total deductions ${results['total_deductions']:,.2f}): ${results['federal_tax']:,.2f}")
    print(f"Marginal federal bracket: {results['marginal_bracket']:.2%}")
    print(f"Total Social Security + MA PFML: ${results['total_social_security']:,.2f}")
    print(f"Medicare: ${results['medicare_charge']:,.2f}")
    print(f"Medicare Surcharge: ${results['medicare_surcharge']:,.2f}")
    print(f"State tax: ${results.get('state_tax', 0):,.2f}")
    print(f"Take home pay: ${results['take_home_pay']:,.2f}")

    # calculation moved to `src/calc/take_home.py`

if __name__ == "__main__":
    main()
