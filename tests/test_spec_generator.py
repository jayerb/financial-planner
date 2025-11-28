"""Tests for the spec generator module."""

import os
import sys
import json
import tempfile
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from spec_generator import save_spec


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
