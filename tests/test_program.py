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
    gross_income = 85000 + 85000*0.1 + 5000
    assert results['gross_income'] == gross_income

    # total deductions from reference/federal-details.json: 32200 + 24000 + 8300 = 64500
    assert results['total_deductions'] == 32200 + 24000 + 8300

    # adjusted gross income = gross - deductions - medicalDentalVision(10800)
    expected_agi = gross_income - (32200 + 24000 + 8300) - 10800
    assert results['adjusted_gross_income'] == expected_agi

    # Federal tax for AGI (falls into bracket1 10%) => tax = AGI * 0.10
    assert round(results['federal_tax'], 2) == round(expected_agi * 0.10, 2)

    # Social security (employee + maPFML) = gross_income * (0.062 + 0.046)
    assert round(results['total_social_security'], 2) == round(gross_income * (0.062 + 0.046), 2)

    # Medicare charge = (gross - medicalDeduct + life_premium) * 0.0145
    life_premium = spec.get('companyProvidedLifeInsurance', {}).get('annualPremium', 0)
    medicare_charge_expected = (gross_income - 10800 + life_premium) * 0.0145
    assert round(results['medicare_charge'], 2) == round(medicare_charge_expected, 2)

    # Take home pay approx
    total_social_security = results['total_social_security']
    total_medicare = results['medicare_charge'] + results['medicare_surcharge']
    expected_take_home = gross_income - results['federal_tax'] - total_social_security - total_medicare
    assert round(results['take_home_pay'], 2) == round(expected_take_home, 2)
