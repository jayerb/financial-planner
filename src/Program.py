import sys
import os
import json
from tax.FederalBrackets import FederalBrackets

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
    # Extract required parameters
    final_year = spec.get('lastYear')
    inflation_rate = spec.get('federalBracketInflation')
    if final_year is None or inflation_rate is None:
        print("spec.json must contain 'lastYear' and 'federalBracketInflation' fields.")
        sys.exit(1)
    # Construct FederalBrackets instance
    fed_brackets = FederalBrackets(inflation_rate, final_year)
    print(f"FederalBrackets instance created for years up to {final_year} with inflation rate {inflation_rate}")
    # Placeholder for future income/tax calculations
    # Example: print(fed_brackets.taxBurden(100000, final_year))

if __name__ == "__main__":
    main()
