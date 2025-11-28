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
