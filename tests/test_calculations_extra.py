import os
import sys
from unittest.mock import Mock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from calc.take_home import TakeHomeCalculator


def create_mock_federal():
    """Create a mock FederalDetails with sensible defaults."""
    mock = Mock()
    mock.totalDeductions.return_value = 15000
    federal_result = Mock()
    federal_result.totalFederalTax = 50000
    federal_result.marginalBracket = 0.24
    mock.taxBurden.return_value = federal_result
    return mock


def create_mock_state():
    """Create a mock StateDetails with sensible defaults."""
    mock = Mock()
    mock.taxBurden.return_value = 10000
    return mock


def create_mock_espp():
    """Create a mock ESPPDetails with sensible defaults."""
    mock = Mock()
    mock.taxable_from_spec.return_value = 0
    return mock


def create_mock_social_security(max_taxed_income=168600, employee_portion=0.062, ma_pfml=0.0063):
    """Create a mock SocialSecurityDetails."""
    mock = Mock()
    mock.maximum_taxed_income = max_taxed_income
    mock.employee_portion = employee_portion
    mock.ma_pfml = ma_pfml

    def total_contribution(gross_income):
        taxable = min(gross_income, max_taxed_income)
        return taxable * (employee_portion + ma_pfml)

    mock.total_contribution.side_effect = total_contribution
    return mock


def create_mock_medicare(medicare_rate=0.0145, surcharge_threshold=250000, surcharge_rate=0.009):
    """Create a mock MedicareDetails."""
    mock = Mock()
    mock.medicare_rate = medicare_rate
    mock.surcharge_threshold = surcharge_threshold
    mock.surcharge_rate = surcharge_rate

    def base_contribution(medicare_base):
        return medicare_base * medicare_rate

    def surcharge(gross_income):
        if gross_income > surcharge_threshold:
            return (gross_income - surcharge_threshold) * surcharge_rate
        return 0

    mock.base_contribution.side_effect = base_contribution
    mock.surcharge.side_effect = surcharge
    return mock


def create_mock_rsu_calculator(vested_value=0, vested_shares=0, stock_price=100.0):
    """Create a mock RSUCalculator with sensible defaults."""
    mock = Mock()
    mock.calculate_vested_value.return_value = {
        'vested_value': vested_value,
        'vested_shares': vested_shares,
        'stock_price': stock_price,
        'target_year': 2026,
        'vesting_breakdown': []
    }
    return mock


def create_spec(base_salary, bonus_fraction=0, other_income=0, medical_dental_vision=0):
    """Create a minimal spec dictionary for testing."""
    return {
        'lastYear': 2030,
        'federalBracketInflation': 0.02,
        'income': {
            'baseSalary': base_salary,
            'bonusFraction': bonus_fraction,
            'otherIncome': other_income
        },
        'deductions': {
            'medicalDentalVision': medical_dental_vision
        },
        'companyProvidedLifeInsurance': {
            'annualPremium': 0
        }
    }


def test_medicare_surcharge_applies():
    # Configure mocks
    mock_federal = create_mock_federal()
    mock_state = create_mock_state()
    mock_espp = create_mock_espp()
    mock_social_security = create_mock_social_security()
    mock_rsu = create_mock_rsu_calculator()

    # Medicare mock with specific surcharge values
    surcharge_threshold = 250000
    surcharge_rate = 0.009
    mock_medicare = create_mock_medicare(
        surcharge_threshold=surcharge_threshold,
        surcharge_rate=surcharge_rate
    )

    calculator = TakeHomeCalculator(
        federal=mock_federal,
        state=mock_state,
        espp=mock_espp,
        social_security=mock_social_security,
        medicare=mock_medicare,
        rsu_calculator=mock_rsu
    )

    # High income to trigger surcharge
    spec = create_spec(base_salary=300000)
    results = calculator.calculate(spec, tax_year=2026)

    gross_income = results['gross_income']
    expected_surcharge = (gross_income - surcharge_threshold) * surcharge_rate

    assert results['medicare_surcharge'] == expected_surcharge
    mock_medicare.surcharge.assert_called_once_with(gross_income)


def test_social_security_cap_applies():
    # Configure mocks
    mock_federal = create_mock_federal()
    mock_state = create_mock_state()
    mock_espp = create_mock_espp()
    mock_rsu = create_mock_rsu_calculator()

    # Social security mock with specific cap values
    max_taxed_income = 168600
    employee_portion = 0.062
    ma_pfml = 0.0063
    mock_social_security = create_mock_social_security(
        max_taxed_income=max_taxed_income,
        employee_portion=employee_portion,
        ma_pfml=ma_pfml
    )
    mock_medicare = create_mock_medicare()

    calculator = TakeHomeCalculator(
        federal=mock_federal,
        state=mock_state,
        espp=mock_espp,
        social_security=mock_social_security,
        medicare=mock_medicare,
        rsu_calculator=mock_rsu
    )

    # Income above max taxed income
    spec = create_spec(base_salary=200000)
    results = calculator.calculate(spec, tax_year=2026)

    # Should be capped at max_taxed_income
    expected_ss = max_taxed_income * (employee_portion + ma_pfml)
    assert round(results['total_social_security'], 2) == round(expected_ss, 2)
    mock_social_security.total_contribution.assert_called_once_with(200000)


def test_no_medicare_surcharge_below_threshold():
    mock_federal = create_mock_federal()
    mock_state = create_mock_state()
    mock_espp = create_mock_espp()
    mock_social_security = create_mock_social_security()
    mock_medicare = create_mock_medicare(surcharge_threshold=250000)
    mock_rsu = create_mock_rsu_calculator()

    calculator = TakeHomeCalculator(
        federal=mock_federal,
        state=mock_state,
        espp=mock_espp,
        social_security=mock_social_security,
        medicare=mock_medicare,
        rsu_calculator=mock_rsu
    )

    # Income below surcharge threshold
    spec = create_spec(base_salary=150000)
    results = calculator.calculate(spec, tax_year=2026)

    assert results['medicare_surcharge'] == 0


def test_rsu_vested_value_added_to_gross_income():
    """Test that RSU vested value is added to gross income."""
    mock_federal = create_mock_federal()
    mock_state = create_mock_state()
    mock_espp = create_mock_espp()
    mock_social_security = create_mock_social_security()
    mock_medicare = create_mock_medicare()

    # RSU mock with specific vested value
    rsu_vested_value = 25000
    mock_rsu = create_mock_rsu_calculator(
        vested_value=rsu_vested_value,
        vested_shares=100,
        stock_price=250.0
    )

    calculator = TakeHomeCalculator(
        federal=mock_federal,
        state=mock_state,
        espp=mock_espp,
        social_security=mock_social_security,
        medicare=mock_medicare,
        rsu_calculator=mock_rsu
    )

    base_salary = 100000
    spec = create_spec(base_salary=base_salary)
    results = calculator.calculate(spec, tax_year=2026)

    # Gross income should include RSU vested value
    expected_gross = base_salary + rsu_vested_value
    assert results['gross_income'] == expected_gross
    assert results['rsu_vested_value'] == rsu_vested_value
    assert results['rsu_vested_shares'] == 100
    assert results['rsu_stock_price'] == 250.0
