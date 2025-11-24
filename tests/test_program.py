import os
import sys
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from calc.take_home import calculate_take_home


def test_calculate_take_home_program1():
    spec_path = os.path.join(os.path.dirname(__file__), '../input-parameters/program1/spec.json')
    with open(spec_path, 'r') as f:
        spec = json.load(f)
    results = calculate_take_home(spec, tax_year=2026)

    # Expected calculations (as done in the program):
    # include ESPP taxable benefit
    base = 85000 + 85000*0.1 + 5000
    # ESPP max is fixed; do not inflate
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    with open(os.path.join(repo_root, 'reference', 'federal-details.json'), 'r') as f:
        fed_ref = json.load(f)
    max_espp = fed_ref.get('maxESPPValue', 0)
    espp_income = max_espp * spec.get('esppDiscount', 0)
    gross_income = base + espp_income
    assert results['gross_income'] == gross_income

    # total deductions from reference/federal-details.json: 32200 + 24000 + 8300 = 64500
    assert results['total_deductions'] == 32200 + 24000 + 8300

    # adjusted gross income = gross - deductions - medicalDentalVision(10800)
    expected_agi = gross_income - (32200 + 24000 + 8300) - 10800
    assert results['adjusted_gross_income'] == expected_agi

    # Federal tax for AGI (falls into bracket1 10%) => tax = AGI * 0.10
    # Compute expected federal tax using the same FederalDetails logic
    from tax.FederalDetails import FederalDetails
    fed_details = FederalDetails(spec.get('federalBracketInflation', 0), spec.get('lastYear'))
    fed_result = fed_details.taxBurden(expected_agi, 2026)
    assert round(results['federal_tax'], 2) == round(fed_result.totalFederalTax, 2)

    # Social security (employee + maPFML) = gross_income * (0.062 + 0.046)
    assert round(results['total_social_security'], 2) == round(gross_income * (0.062 + 0.046), 2)

    # Medicare charge = (gross - medicalDeduct + life_premium) * 0.0145
    life_premium = spec.get('companyProvidedLifeInsurance', {}).get('annualPremium', 0)
    medicare_charge_expected = (gross_income - 10800 + life_premium) * 0.0145
    assert round(results['medicare_charge'], 2) == round(medicare_charge_expected, 2)

    # Take home pay approx
    total_social_security = results['total_social_security']
    total_medicare = results['medicare_charge'] + results['medicare_surcharge']
    # State tax should consider 401k and HSA contributions (not the federal standard deduction)
    # Load state and federal contribution details to compute expected state tax
    flat_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../reference/flat-tax-details.json'))
    with open(flat_path, 'r') as f:
        flat = json.load(f)
    state_details = flat.get('state', {})
    state_rate = state_details.get('rate', 0)
    state_sd = state_details.get('standardDeduction', 0)

    fed_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../reference/federal-details.json'))
    with open(fed_path, 'r') as f:
        fed = json.load(f)
    max_contrib = fed.get('maxContributions', {})
    c401k = max_contrib.get('401k', 0)
    hsa = max_contrib.get('HSA', 0)

    expected_state_tax = max(0.0, gross_income - (c401k + hsa) - 10800 - state_sd) * state_rate
    assert round(results['state_tax'], 2) == round(expected_state_tax, 2)

    # Take home pay approx (subtract state tax)
    expected_take_home = gross_income - results['federal_tax'] - total_social_security - total_medicare - expected_state_tax
    assert round(results['take_home_pay'], 2) == round(expected_take_home, 2)
