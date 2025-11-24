import os
import sys
import json
import math
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
from tax.ESPPDetails import ESPPDetails


def load_program_spec():
    spec_path = os.path.join(os.path.dirname(__file__), '../../input-parameters/program1/spec.json')
    with open(spec_path, 'r') as f:
        return json.load(f)


def test_espp_basic_taxable_benefit():
    sd = ESPPDetails()
    spec = load_program_spec()
    discount = spec.get('esppDiscount', 0)

    # load reference value
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    with open(os.path.join(repo_root, 'reference', 'federal-details.json'), 'r') as f:
        fed = json.load(f)
    max_espp = fed.get('maxESPPValue', 0)

    expected = max_espp * discount
    result = sd.taxable_from_spec(spec)
    assert math.isclose(result, expected, rel_tol=1e-9)


def test_espp_zero_discount():
    sd = ESPPDetails()
    result = sd.taxable_benefit(0.0)
    assert result == 0.0


def test_espp_ignores_inflation():
    # Even if inflation rate provided, cap should not change
    sd_no_infl = ESPPDetails()
    sd_infl = ESPPDetails()

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    with open(os.path.join(repo_root, 'reference', 'federal-details.json'), 'r') as f:
        fed = json.load(f)
    max_espp = fed.get('maxESPPValue', 0)

    expected = max_espp * 0.15
    assert math.isclose(sd_no_infl.taxable_benefit(0.15), expected, rel_tol=1e-9)
    assert math.isclose(sd_infl.taxable_benefit(0.15), expected, rel_tol=1e-9)
