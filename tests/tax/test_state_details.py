import os
import sys
import json
import math
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
from tax.StateDetails import StateDetails


def load_program_spec():
    spec_path = os.path.join(os.path.dirname(__file__), '../../input-parameters/program1/spec.json')
    with open(spec_path, 'r') as f:
        return json.load(f)


def test_state_tax_basic_matches_program_logic():
    # Use zero inflation so values equal reference
    sd = StateDetails(inflation_rate=0.0, final_year=2026)

    spec = load_program_spec()
    income = spec['income']
    gross_income = income['baseSalary'] + income['baseSalary'] * income['bonusFraction'] + income['otherIncome']
    medical = spec.get('deductions', {}).get('medicalDentalVision', 0)
    # include ESPP contribution benefit
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    espp_discount = spec.get('esppDiscount', 0)
    with open(os.path.join(repo_root, 'reference', 'federal-details.json'), 'r') as f:
        fed_ref = json.load(f)
    max_espp = fed_ref.get('maxESPPValue', 0)
    espp_income = max_espp * espp_discount
    gross_income = gross_income + espp_income

    # load reference values
    with open(os.path.join(repo_root, 'reference', 'flat-tax-details.json'), 'r') as f:
        flat = json.load(f)
    with open(os.path.join(repo_root, 'reference', 'federal-details.json'), 'r') as f:
        fed = json.load(f)

    state = flat.get('state', {})
    state_rate = state.get('rate', 0)
    state_sd = state.get('standardDeduction', 0)
    c401k = fed.get('maxContributions', {}).get('401k', 0)
    hsa = fed.get('maxContributions', {}).get('HSA', 0)

    expected_state_tax = max(0.0, gross_income - (c401k + hsa) - medical - state_sd) * state_rate

    result = sd.taxBurden(gross_income, medical, year=2026)
    assert math.isclose(result, expected_state_tax, rel_tol=1e-9, abs_tol=1e-9)


def test_state_tax_zero_for_low_income():
    sd = StateDetails(inflation_rate=0.0, final_year=2026)
    # low income that should be below taxable after deductions
    gross = 20000
    medical = 0
    result = sd.taxBurden(gross, medical, year=2026)
    assert result == 0.0


def test_state_tax_inflation_applies_over_years():
    # Use 2% inflation and compute tax for two years after base (2028)
    inflation = 0.02
    sd = StateDetails(inflation_rate=inflation, final_year=2028)

    # simple income that will be taxable
    gross = 100000
    medical = 2000

    # load reference base values
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    with open(os.path.join(repo_root, 'reference', 'flat-tax-details.json'), 'r') as f:
        flat = json.load(f)
    with open(os.path.join(repo_root, 'reference', 'federal-details.json'), 'r') as f:
        fed = json.load(f)

    state = flat.get('state', {})
    state_rate = state.get('rate', 0)
    state_sd = state.get('standardDeduction', 0)
    c401k = fed.get('maxContributions', {}).get('401k', 0)
    hsa = fed.get('maxContributions', {}).get('HSA', 0)

    # base year in federal-details.json is 2026; we are computing for 2028 -> 2 years
    years = 2028 - fed.get('taxYear', 2026)
    inflator = (1.0 + inflation) ** years

    c401k_infl = c401k * inflator
    hsa_infl = hsa * inflator
    state_sd_infl = state_sd * inflator

    expected = max(0.0, gross - (c401k_infl + hsa_infl) - medical - state_sd_infl) * state_rate

    result = sd.taxBurden(gross, medical, year=2028)
    assert math.isclose(result, expected, rel_tol=1e-9, abs_tol=1e-9)
