import os
import sys
import json
import math
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
from tax.ESPPDetails import ESPPDetails


def test_espp_basic_taxable_benefit():
    max_espp = 25000.0
    discount = 0.15
    sd = ESPPDetails(max_espp)

    expected = max_espp * discount
    spec = {'esppDiscount': discount}
    result = sd.taxable_from_spec(spec)
    assert math.isclose(result, expected, rel_tol=1e-9)


def test_espp_zero_discount():
    sd = ESPPDetails(25000.00)
    spec = {'esppDiscount': 0.0}
    result = sd.taxable_from_spec(spec)
    assert result == 0.0


