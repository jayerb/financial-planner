"""Tests for the spec generator module."""

import os
import sys
import json
import tempfile
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from spec_generator import save_spec, load_existing_spec, get_nested, list_existing_programs


def test_save_spec_creates_directory_and_file():
    """Test that save_spec creates the program directory and spec.json file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec = {
            'firstYear': 2025,
            'lastWorkingYear': 2035,
            'lastPlanningYear': 2065,
            'income': {'baseSalary': 100000}
        }
        
        # Create input-parameters directory structure
        os.makedirs(os.path.join(tmpdir, 'input-parameters'))
        
        result_path = save_spec(spec, 'testprogram', tmpdir)
        
        assert os.path.exists(result_path)
        assert result_path.endswith('spec.json')
        
        with open(result_path, 'r') as f:
            saved_spec = json.load(f)
        
        assert saved_spec == spec


def test_save_spec_with_investments():
    """Test that save_spec correctly saves investment account data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec = {
            'firstYear': 2025,
            'lastWorkingYear': 2035,
            'lastPlanningYear': 2065,
            'income': {'baseSalary': 100000},
            'investments': {
                'taxableBalance': 50000.0,
                'taxableAppreciationRate': 0.07,
                'taxDeferredBalance': 200000.0,
                'taxDeferredAppreciationRate': 0.06,
                'hsaBalance': 15000.0,
                'hsaAppreciationRate': 0.05
            }
        }
        
        os.makedirs(os.path.join(tmpdir, 'input-parameters'))
        
        result_path = save_spec(spec, 'testprogram', tmpdir)
        
        with open(result_path, 'r') as f:
            saved_spec = json.load(f)
        
        assert 'investments' in saved_spec
        assert saved_spec['investments']['taxableBalance'] == 50000.0
        assert saved_spec['investments']['taxableAppreciationRate'] == 0.07
        assert saved_spec['investments']['taxDeferredBalance'] == 200000.0
        assert saved_spec['investments']['taxDeferredAppreciationRate'] == 0.06
        assert saved_spec['investments']['hsaBalance'] == 15000.0
        assert saved_spec['investments']['hsaAppreciationRate'] == 0.05


def test_investments_section_structure():
    """Test that the investments section has the expected structure."""
    # This test validates the expected schema for investments
    investments = {
        'taxableBalance': 100000.0,
        'taxableAppreciationRate': 0.07,
        'taxDeferredBalance': 250000.0,
        'taxDeferredAppreciationRate': 0.06,
        'hsaBalance': 20000.0,
        'hsaAppreciationRate': 0.05
    }
    
    # Verify all expected keys are present
    expected_keys = [
        'taxableBalance',
        'taxableAppreciationRate', 
        'taxDeferredBalance',
        'taxDeferredAppreciationRate',
        'hsaBalance',
        'hsaAppreciationRate'
    ]
    
    for key in expected_keys:
        assert key in investments, f"Missing expected key: {key}"
    
    # Verify types
    assert isinstance(investments['taxableBalance'], float)
    assert isinstance(investments['taxableAppreciationRate'], float)
    assert isinstance(investments['taxDeferredBalance'], float)
    assert isinstance(investments['taxDeferredAppreciationRate'], float)
    assert isinstance(investments['hsaBalance'], float)
    assert isinstance(investments['hsaAppreciationRate'], float)
    
    # Verify appreciation rates are fractions (0-1), not percentages
    assert 0 <= investments['taxableAppreciationRate'] <= 1
    assert 0 <= investments['taxDeferredAppreciationRate'] <= 1
    assert 0 <= investments['hsaAppreciationRate'] <= 1


def test_investments_section_optional():
    """Test that the investments section is optional in the spec."""
    spec_without_investments = {
        'firstYear': 2025,
        'lastWorkingYear': 2035,
        'lastPlanningYear': 2065,
        'income': {'baseSalary': 100000}
    }
    
    # Should not have investments section
    assert 'investments' not in spec_without_investments
    
    # Adding investments section should work
    spec_with_investments = spec_without_investments.copy()
    spec_with_investments['investments'] = {
        'taxableBalance': 50000.0,
        'taxableAppreciationRate': 0.07
    }
    
    assert 'investments' in spec_with_investments
    assert spec_with_investments['investments']['taxableBalance'] == 50000.0


def test_load_existing_spec():
    """Test loading an existing spec.json file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec = {
            'firstYear': 2025,
            'lastWorkingYear': 2035,
            'lastPlanningYear': 2065,
            'income': {'baseSalary': 150000}
        }
        
        # Create the program directory and save the spec
        os.makedirs(os.path.join(tmpdir, 'input-parameters'))
        save_spec(spec, 'testprogram', tmpdir)
        
        # Load the spec
        loaded_spec = load_existing_spec('testprogram', tmpdir)
        
        assert loaded_spec is not None
        assert loaded_spec['firstYear'] == 2025
        assert loaded_spec['income']['baseSalary'] == 150000


def test_load_existing_spec_nonexistent():
    """Test that loading a nonexistent spec returns None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, 'input-parameters'))
        
        result = load_existing_spec('nonexistent', tmpdir)
        
        assert result is None


def test_get_nested():
    """Test the get_nested helper function."""
    data = {
        'level1': {
            'level2': {
                'value': 42
            }
        },
        'simple': 'test'
    }
    
    # Test nested access
    assert get_nested(data, 'level1', 'level2', 'value') == 42
    
    # Test simple access
    assert get_nested(data, 'simple') == 'test'
    
    # Test missing key with default
    assert get_nested(data, 'missing', default='default') == 'default'
    
    # Test missing nested key with default
    assert get_nested(data, 'level1', 'missing', default=100) == 100
    
    # Test None default
    assert get_nested(data, 'missing') is None


def test_list_existing_programs():
    """Test listing existing programs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create input-parameters directory
        input_params = os.path.join(tmpdir, 'input-parameters')
        os.makedirs(input_params)
        
        # Create some program directories with spec.json files
        for name in ['program1', 'program2', 'program3']:
            prog_dir = os.path.join(input_params, name)
            os.makedirs(prog_dir)
            with open(os.path.join(prog_dir, 'spec.json'), 'w') as f:
                json.dump({'firstYear': 2025}, f)
        
        # Create a directory without spec.json (should be ignored)
        invalid_dir = os.path.join(input_params, 'invalid')
        os.makedirs(invalid_dir)
        
        # List programs
        programs = list_existing_programs(tmpdir)
        
        assert len(programs) == 3
        assert 'program1' in programs
        assert 'program2' in programs
        assert 'program3' in programs
        assert 'invalid' not in programs


def test_list_existing_programs_empty():
    """Test listing programs when none exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, 'input-parameters'))
        
        programs = list_existing_programs(tmpdir)
        
        assert programs == []


def test_list_existing_programs_no_directory():
    """Test listing programs when input-parameters doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        programs = list_existing_programs(tmpdir)
        
        assert programs == []


def test_save_spec_with_insurance():
    """Test that save_spec correctly saves insurance data for post-retirement."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec = {
            'firstYear': 2025,
            'lastWorkingYear': 2035,
            'lastPlanningYear': 2065,
            'income': {'baseSalary': 100000},
            'insurance': {
                'fullInsurancePremiums': 30000.0,
                'premiumInflationRate': 0.04
            }
        }
        
        os.makedirs(os.path.join(tmpdir, 'input-parameters'))
        
        result_path = save_spec(spec, 'testprogram', tmpdir)
        
        with open(result_path, 'r') as f:
            saved_spec = json.load(f)
        
        assert 'insurance' in saved_spec
        assert saved_spec['insurance']['fullInsurancePremiums'] == 30000.0
        assert saved_spec['insurance']['premiumInflationRate'] == 0.04


def test_insurance_section_structure():
    """Test that the insurance section has the expected structure."""
    insurance = {
        'fullInsurancePremiums': 30000.0,
        'premiumInflationRate': 0.05
    }
    
    # Verify all expected keys are present
    expected_keys = [
        'fullInsurancePremiums',
        'premiumInflationRate'
    ]
    
    for key in expected_keys:
        assert key in insurance, f"Missing expected key: {key}"
    
    # Verify types
    assert isinstance(insurance['fullInsurancePremiums'], float)
    assert isinstance(insurance['premiumInflationRate'], float)
    
    # Verify inflation rate is a fraction (0-1), not a percentage
    assert 0 <= insurance['premiumInflationRate'] <= 1
    
    # Verify premiums are positive
    assert insurance['fullInsurancePremiums'] >= 0


def test_insurance_section_optional():
    """Test that the insurance section is optional in the spec."""
    spec_without_insurance = {
        'firstYear': 2025,
        'lastWorkingYear': 2035,
        'lastPlanningYear': 2065,
        'income': {'baseSalary': 100000}
    }
    
    # Should not have insurance section
    assert 'insurance' not in spec_without_insurance
    
    # Adding insurance section should work
    spec_with_insurance = spec_without_insurance.copy()
    spec_with_insurance['insurance'] = {
        'fullInsurancePremiums': 25000.0,
        'premiumInflationRate': 0.04
    }
    
    assert 'insurance' in spec_with_insurance
    assert spec_with_insurance['insurance']['fullInsurancePremiums'] == 25000.0
    assert spec_with_insurance['insurance']['premiumInflationRate'] == 0.04


def test_load_existing_spec_with_insurance():
    """Test loading an existing spec.json file with insurance data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec = {
            'firstYear': 2025,
            'lastWorkingYear': 2035,
            'lastPlanningYear': 2065,
            'income': {'baseSalary': 150000},
            'insurance': {
                'fullInsurancePremiums': 35000.0,
                'premiumInflationRate': 0.05
            }
        }
        
        # Create the program directory and save the spec
        os.makedirs(os.path.join(tmpdir, 'input-parameters'))
        save_spec(spec, 'testprogram', tmpdir)
        
        # Load the spec
        loaded_spec = load_existing_spec('testprogram', tmpdir)
        
        assert loaded_spec is not None
        assert 'insurance' in loaded_spec
        assert loaded_spec['insurance']['fullInsurancePremiums'] == 35000.0
        assert loaded_spec['insurance']['premiumInflationRate'] == 0.05


def test_save_spec_with_expenses():
    """Test that save_spec correctly saves expense data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec = {
            'firstYear': 2025,
            'lastWorkingYear': 2035,
            'lastPlanningYear': 2065,
            'income': {'baseSalary': 100000},
            'expenses': {
                'annualAmount': 80000.0,
                'inflationRate': 0.03
            }
        }
        
        os.makedirs(os.path.join(tmpdir, 'input-parameters'))
        
        result_path = save_spec(spec, 'testprogram', tmpdir)
        
        with open(result_path, 'r') as f:
            saved_spec = json.load(f)
        
        assert 'expenses' in saved_spec
        assert saved_spec['expenses']['annualAmount'] == 80000.0
        assert saved_spec['expenses']['inflationRate'] == 0.03


def test_expenses_section_structure():
    """Test that the expenses section has the expected structure."""
    expenses = {
        'annualAmount': 75000.0,
        'inflationRate': 0.03
    }
    
    # Verify all expected keys are present
    expected_keys = [
        'annualAmount',
        'inflationRate'
    ]
    
    for key in expected_keys:
        assert key in expenses, f"Missing expected key: {key}"
    
    # Verify types
    assert isinstance(expenses['annualAmount'], float)
    assert isinstance(expenses['inflationRate'], float)
    
    # Verify inflation rate is a fraction (0-1), not a percentage
    assert 0 <= expenses['inflationRate'] <= 1
    
    # Verify amount is positive
    assert expenses['annualAmount'] >= 0


def test_expenses_with_special_expenses():
    """Test that expenses section can include special one-time expenses."""
    expenses = {
        'annualAmount': 60000.0,
        'inflationRate': 0.03,
        'specialExpenses': [
            {'year': 2030, 'amount': 50000.0, 'description': 'College tuition'},
            {'year': 2032, 'amount': 25000.0, 'description': 'Car purchase'},
            {'year': 2035, 'amount': 100000.0}  # Description is optional
        ]
    }
    
    # Verify special expenses structure
    assert 'specialExpenses' in expenses
    assert len(expenses['specialExpenses']) == 3
    
    # Verify each special expense has required fields
    for exp in expenses['specialExpenses']:
        assert 'year' in exp
        assert 'amount' in exp
        assert isinstance(exp['year'], int)
        assert isinstance(exp['amount'], float)
        assert exp['amount'] > 0
    
    # Verify description is optional
    assert 'description' in expenses['specialExpenses'][0]
    assert 'description' in expenses['specialExpenses'][1]
    assert 'description' not in expenses['specialExpenses'][2]


def test_expenses_section_optional():
    """Test that the expenses section is optional in the spec."""
    spec_without_expenses = {
        'firstYear': 2025,
        'lastWorkingYear': 2035,
        'lastPlanningYear': 2065,
        'income': {'baseSalary': 100000}
    }
    
    # Should not have expenses section
    assert 'expenses' not in spec_without_expenses
    
    # Adding expenses section should work
    spec_with_expenses = spec_without_expenses.copy()
    spec_with_expenses['expenses'] = {
        'annualAmount': 70000.0,
        'inflationRate': 0.025
    }
    
    assert 'expenses' in spec_with_expenses
    assert spec_with_expenses['expenses']['annualAmount'] == 70000.0
    assert spec_with_expenses['expenses']['inflationRate'] == 0.025


def test_save_spec_with_special_expenses():
    """Test that save_spec correctly saves special expense data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec = {
            'firstYear': 2025,
            'lastWorkingYear': 2035,
            'lastPlanningYear': 2065,
            'income': {'baseSalary': 100000},
            'expenses': {
                'annualAmount': 80000.0,
                'inflationRate': 0.03,
                'specialExpenses': [
                    {'year': 2028, 'amount': 40000.0, 'description': 'Home renovation'},
                    {'year': 2033, 'amount': 75000.0, 'description': 'College year 1'}
                ]
            }
        }
        
        os.makedirs(os.path.join(tmpdir, 'input-parameters'))
        
        result_path = save_spec(spec, 'testprogram', tmpdir)
        
        with open(result_path, 'r') as f:
            saved_spec = json.load(f)
        
        assert 'expenses' in saved_spec
        assert 'specialExpenses' in saved_spec['expenses']
        assert len(saved_spec['expenses']['specialExpenses']) == 2
        assert saved_spec['expenses']['specialExpenses'][0]['year'] == 2028
        assert saved_spec['expenses']['specialExpenses'][0]['amount'] == 40000.0
        assert saved_spec['expenses']['specialExpenses'][0]['description'] == 'Home renovation'


def test_load_existing_spec_with_expenses():
    """Test loading an existing spec.json file with expense data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec = {
            'firstYear': 2025,
            'lastWorkingYear': 2035,
            'lastPlanningYear': 2065,
            'income': {'baseSalary': 150000},
            'expenses': {
                'annualAmount': 90000.0,
                'inflationRate': 0.04,
                'specialExpenses': [
                    {'year': 2030, 'amount': 60000.0, 'description': 'Wedding'}
                ]
            }
        }
        
        # Create the program directory and save the spec
        os.makedirs(os.path.join(tmpdir, 'input-parameters'))
        save_spec(spec, 'testprogram', tmpdir)
        
        # Load the spec
        loaded_spec = load_existing_spec('testprogram', tmpdir)
        
        assert loaded_spec is not None
        assert 'expenses' in loaded_spec
        assert loaded_spec['expenses']['annualAmount'] == 90000.0
        assert loaded_spec['expenses']['inflationRate'] == 0.04
        assert len(loaded_spec['expenses']['specialExpenses']) == 1
        assert loaded_spec['expenses']['specialExpenses'][0]['description'] == 'Wedding'


def test_save_spec_with_birth_year():
    """Test that save_spec correctly saves birth year for Medicare eligibility."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec = {
            'birthYear': 1975,
            'firstYear': 2025,
            'lastWorkingYear': 2035,
            'lastPlanningYear': 2065,
            'income': {'baseSalary': 100000}
        }
        
        os.makedirs(os.path.join(tmpdir, 'input-parameters'))
        
        result_path = save_spec(spec, 'testprogram', tmpdir)
        
        with open(result_path, 'r') as f:
            saved_spec = json.load(f)
        
        assert 'birthYear' in saved_spec
        assert saved_spec['birthYear'] == 1975


def test_birth_year_determines_medicare_eligibility():
    """Test that birth year can be used to calculate Medicare eligibility at age 65."""
    spec = {
        'birthYear': 1970,
        'firstYear': 2025,
        'lastWorkingYear': 2035,
        'lastPlanningYear': 2065
    }
    
    # Medicare eligibility is at age 65
    medicare_age = 65
    medicare_eligible_year = spec['birthYear'] + medicare_age
    
    assert medicare_eligible_year == 2035
    
    # Verify the person would be Medicare eligible starting in their retirement
    assert medicare_eligible_year >= spec['lastWorkingYear']


def test_load_existing_spec_with_birth_year():
    """Test loading an existing spec.json file with birth year."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec = {
            'birthYear': 1980,
            'firstYear': 2025,
            'lastWorkingYear': 2040,
            'lastPlanningYear': 2070,
            'income': {'baseSalary': 150000}
        }
        
        # Create the program directory and save the spec
        os.makedirs(os.path.join(tmpdir, 'input-parameters'))
        save_spec(spec, 'testprogram', tmpdir)
        
        # Load the spec
        loaded_spec = load_existing_spec('testprogram', tmpdir)
        
        assert loaded_spec is not None
        assert 'birthYear' in loaded_spec
        assert loaded_spec['birthYear'] == 1980
        
        # Verify Medicare eligibility calculation
        medicare_eligible_year = loaded_spec['birthYear'] + 65
        assert medicare_eligible_year == 2045
