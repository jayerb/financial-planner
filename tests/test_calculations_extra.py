import os
import sys
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from calc.take_home import calculate_take_home


def load_spec():
    spec_path = os.path.join(os.path.dirname(__file__), '../input-parameters/program1/spec.json')
    with open(spec_path, 'r') as f:
        return json.load(f)


def test_medicare_surcharge_applies():
    spec = load_spec()
    # make income high to trigger surcharge
    spec['income']['baseSalary'] = 300000
    spec['income']['bonusFraction'] = 0
    spec['income']['otherIncome'] = 0
    results = calculate_take_home(spec, tax_year=2026)

    gross_income = results['gross_income']
    # load surcharge info
    medicare_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../reference/flat-tax-details.json'))
    with open(medicare_path, 'r') as f:
        medicare_details = json.load(f)
    surcharge_threshold = medicare_details.get('surchargeThreshold')
    surcharge_rate = medicare_details.get('surchargeRate')

    assert results['medicare_surcharge'] == (gross_income - surcharge_threshold) * surcharge_rate


def test_social_security_cap_applies():
    spec = load_spec()
    # raise income above max taxed income
    spec['income']['baseSalary'] = 200000
    spec['income']['bonusFraction'] = 0
    spec['income']['otherIncome'] = 0
    results = calculate_take_home(spec, tax_year=2026)

    # load social security reference
    ss_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../reference/social-security.json'))
    with open(ss_path, 'r') as f:
        ss = json.load(f)
    max_taxed = ss.get('maximumTaxedIncome')
    emp = ss.get('employeePortion')
    ma = ss.get('maPFML')

    assert round(results['total_social_security'], 2) == round(max_taxed * (emp + ma), 2)
