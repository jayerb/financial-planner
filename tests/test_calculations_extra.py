import os
import sys
from unittest.mock import Mock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from calc.take_home import TakeHomeCalculator


def create_mock_federal():
    """Create a mock FederalDetails with sensible defaults."""
    mock = Mock()
    mock.totalDeductions.return_value = {
        'standardDeduction': 10000,
        'max401k': 3000,
        'maxHSA': 2000,
        'total': 15000
    }
    federal_result = Mock()
    federal_result.totalFederalTax = 50000
    federal_result.marginalBracket = 0.24
    federal_result.longTermCapitalGainsTax = 0
    mock.taxBurden.return_value = federal_result
    mock.longTermCapitalGainsTax.return_value = 0
    return mock


def create_mock_state():
    """Create a mock StateDetails with sensible defaults."""
    mock = Mock()
    mock.taxBurden.return_value = 10000
    mock.shortTermCapitalGainsTax.return_value = 0
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

    def total_contribution(gross_income, year):
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
    # The RSU calculator now uses a dictionary keyed by year
    mock.vested_value = {2026: vested_value}
    return mock


def create_spec(base_salary, bonus_fraction=0, other_income=0, medical_dental_vision=0):
    """Create a minimal spec dictionary for testing."""
    return {
        'lastPlanningYear': 2030,
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
    mock_social_security.total_contribution.assert_called_once_with(200000, 2026)


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


def test_espp_income_from_spec_used_when_provided():
    """Test that esppIncome from spec is used only for first year."""
    mock_federal = create_mock_federal()
    mock_state = create_mock_state()
    mock_espp = create_mock_espp()
    mock_social_security = create_mock_social_security()
    mock_medicare = create_mock_medicare()
    mock_rsu = create_mock_rsu_calculator()

    # Set up ESPP mock to return a different value - this should be used for non-first years
    mock_espp.taxable_from_spec.return_value = 5000

    calculator = TakeHomeCalculator(
        federal=mock_federal,
        state=mock_state,
        espp=mock_espp,
        social_security=mock_social_security,
        medicare=mock_medicare,
        rsu_calculator=mock_rsu
    )

    base_salary = 100000
    espp_income_from_spec = 3750  # This value should be used for first year
    spec = create_spec(base_salary=base_salary)
    spec['firstYear'] = 2026
    spec['lastWorkingYear'] = 2030
    spec['income']['esppIncome'] = espp_income_from_spec

    # Test first year - should use esppIncome from spec
    results = calculator.calculate(spec, tax_year=2026)
    expected_gross = base_salary + espp_income_from_spec
    assert results['gross_income'] == expected_gross
    assert results['espp_income'] == espp_income_from_spec


def test_espp_income_calculated_for_non_first_year():
    """Test that ESPP income is calculated for years after the first year."""
    mock_federal = create_mock_federal()
    mock_state = create_mock_state()
    mock_espp = create_mock_espp()
    mock_social_security = create_mock_social_security()
    mock_medicare = create_mock_medicare()
    mock_rsu = create_mock_rsu_calculator()

    # Set up ESPP mock to return a calculated value
    calculated_espp_income = 5000
    mock_espp.taxable_from_spec.return_value = calculated_espp_income

    calculator = TakeHomeCalculator(
        federal=mock_federal,
        state=mock_state,
        espp=mock_espp,
        social_security=mock_social_security,
        medicare=mock_medicare,
        rsu_calculator=mock_rsu
    )

    base_salary = 100000
    espp_income_from_spec = 3750  # This should NOT be used for year 2027
    spec = create_spec(base_salary=base_salary)
    spec['firstYear'] = 2026
    spec['lastWorkingYear'] = 2030
    spec['income']['esppIncome'] = espp_income_from_spec

    # Test second year - should use calculated ESPP income, not spec value
    mock_rsu.vested_value = {2027: 0}  # Update RSU mock for year 2027
    results = calculator.calculate(spec, tax_year=2027)

    expected_gross = base_salary + calculated_espp_income
    assert results['gross_income'] == expected_gross
    assert results['espp_income'] == calculated_espp_income
    mock_espp.taxable_from_spec.assert_called_with(spec)


def test_espp_income_calculated_when_not_in_spec():
    """Test that ESPP income is calculated when esppIncome not provided in spec."""
    mock_federal = create_mock_federal()
    mock_state = create_mock_state()
    mock_espp = create_mock_espp()
    mock_social_security = create_mock_social_security()
    mock_medicare = create_mock_medicare()
    mock_rsu = create_mock_rsu_calculator()

    # Set up ESPP mock to return a calculated value
    calculated_espp_income = 4500
    mock_espp.taxable_from_spec.return_value = calculated_espp_income

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
    spec['firstYear'] = 2026
    spec['lastWorkingYear'] = 2030
    # Do NOT set spec['income']['esppIncome'] - it should be calculated even for first year

    results = calculator.calculate(spec, tax_year=2026)

    # Gross income should include the calculated ESPP income
    expected_gross = base_salary + calculated_espp_income
    assert results['gross_income'] == expected_gross
    assert results['espp_income'] == calculated_espp_income

    # The ESPP mock's taxable_from_spec should have been called
    mock_espp.taxable_from_spec.assert_called_once_with(spec)


def test_short_term_capital_gains_added_to_gross_income():
    """Test that short-term capital gains are added to gross income."""
    mock_federal = create_mock_federal()
    mock_state = create_mock_state()
    mock_espp = create_mock_espp()
    mock_social_security = create_mock_social_security()
    mock_medicare = create_mock_medicare()
    mock_rsu = create_mock_rsu_calculator()

    calculator = TakeHomeCalculator(
        federal=mock_federal,
        state=mock_state,
        espp=mock_espp,
        social_security=mock_social_security,
        medicare=mock_medicare,
        rsu_calculator=mock_rsu
    )

    base_salary = 100000
    short_term_gains = 5000
    spec = create_spec(base_salary=base_salary)
    spec['income']['shortTermCapitalGains'] = short_term_gains

    results = calculator.calculate(spec, tax_year=2026)

    # Gross income should include short-term capital gains
    expected_gross = base_salary + short_term_gains
    assert results['gross_income'] == expected_gross
    assert results['short_term_capital_gains'] == short_term_gains


def test_long_term_capital_gains_tax_calculated():
    """Test that long-term capital gains tax is calculated using LTCG brackets."""
    mock_federal = create_mock_federal()
    mock_state = create_mock_state()
    mock_espp = create_mock_espp()
    mock_social_security = create_mock_social_security()
    mock_medicare = create_mock_medicare()
    mock_rsu = create_mock_rsu_calculator()

    # Configure LTCG tax calculation
    ltcg_tax = 1500
    mock_federal.longTermCapitalGainsTax.return_value = ltcg_tax

    calculator = TakeHomeCalculator(
        federal=mock_federal,
        state=mock_state,
        espp=mock_espp,
        social_security=mock_social_security,
        medicare=mock_medicare,
        rsu_calculator=mock_rsu
    )

    base_salary = 100000
    long_term_gains = 10000
    spec = create_spec(base_salary=base_salary)
    spec['income']['longTermCapitalGains'] = long_term_gains

    results = calculator.calculate(spec, tax_year=2026)

    # LTCG tax should be calculated and included
    assert results['long_term_capital_gains_tax'] == ltcg_tax
    assert results['long_term_capital_gains'] == long_term_gains
    
    # longTermCapitalGainsTax should have been called with AGI and LTCG amount
    mock_federal.longTermCapitalGainsTax.assert_called_once()
    call_args = mock_federal.longTermCapitalGainsTax.call_args
    assert call_args[0][1] == long_term_gains  # Second arg is LTCG amount
    assert call_args[0][2] == 2026  # Third arg is year


def test_federal_tax_includes_ltcg_tax():
    """Test that total federal tax includes both ordinary income tax and LTCG tax."""
    mock_federal = create_mock_federal()
    mock_state = create_mock_state()
    mock_espp = create_mock_espp()
    mock_social_security = create_mock_social_security()
    mock_medicare = create_mock_medicare()
    mock_rsu = create_mock_rsu_calculator()

    # Configure ordinary income tax and LTCG tax
    ordinary_tax = 50000
    ltcg_tax = 2000
    federal_result = Mock()
    federal_result.totalFederalTax = ordinary_tax
    federal_result.marginalBracket = 0.24
    federal_result.longTermCapitalGainsTax = 0
    mock_federal.taxBurden.return_value = federal_result
    mock_federal.longTermCapitalGainsTax.return_value = ltcg_tax

    calculator = TakeHomeCalculator(
        federal=mock_federal,
        state=mock_state,
        espp=mock_espp,
        social_security=mock_social_security,
        medicare=mock_medicare,
        rsu_calculator=mock_rsu
    )

    base_salary = 200000
    long_term_gains = 15000
    spec = create_spec(base_salary=base_salary)
    spec['income']['longTermCapitalGains'] = long_term_gains

    results = calculator.calculate(spec, tax_year=2026)

    # Total federal tax should be ordinary + LTCG
    expected_total_federal = ordinary_tax + ltcg_tax
    assert results['federal_tax'] == expected_total_federal
    assert results['ordinary_income_tax'] == ordinary_tax
    assert results['long_term_capital_gains_tax'] == ltcg_tax


def test_capital_gains_default_to_zero():
    """Test that capital gains default to zero if not specified."""
    mock_federal = create_mock_federal()
    mock_state = create_mock_state()
    mock_espp = create_mock_espp()
    mock_social_security = create_mock_social_security()
    mock_medicare = create_mock_medicare()
    mock_rsu = create_mock_rsu_calculator()

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
    # Do NOT set capital gains in spec

    results = calculator.calculate(spec, tax_year=2026)

    # Capital gains should default to 0
    assert results['short_term_capital_gains'] == 0
    assert results['long_term_capital_gains'] == 0
    assert results['long_term_capital_gains_tax'] == 0
    # Gross income should just be base salary
    assert results['gross_income'] == base_salary
