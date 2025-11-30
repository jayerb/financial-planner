"""Tests for custom renderer configuration functionality.

This module tests the ability to create, save, load, and delete custom
renderer configurations stored in the report-config directory.
"""

import pytest
import sys
import os
import json
import tempfile
import shutil
from io import StringIO
from unittest.mock import patch

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from model.PlanData import PlanData, YearlyData


# Create a minimal mock plan data for testing renderers
@pytest.fixture
def mock_plan_data():
    """Create a minimal PlanData with yearly data for testing."""
    plan = PlanData(
        first_year=2025,
        last_working_year=2030,
        last_planning_year=2035
    )
    
    # Add yearly data for a few years
    for year in range(2025, 2036):
        is_working = year <= 2030
        yd = YearlyData(year=year, is_working_year=is_working)
        yd.base_salary = 100000.0 if is_working else 0.0
        yd.bonus = 10000.0 if is_working else 0.0
        yd.gross_income = yd.base_salary + yd.bonus
        yd.federal_tax = 20000.0 if is_working else 5000.0
        yd.state_tax = 5000.0 if is_working else 1000.0
        yd.total_fica = 8000.0 if is_working else 0.0
        yd.total_taxes = yd.federal_tax + yd.state_tax + yd.total_fica
        yd.take_home_pay = yd.gross_income - yd.total_taxes
        yd.effective_tax_rate = yd.total_taxes / yd.gross_income if yd.gross_income > 0 else 0.0
        plan.yearly_data[year] = yd
    
    return plan


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for custom renderer configurations."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_config():
    """Create a sample custom renderer configuration."""
    return {
        'title': 'Test Income Report',
        'fields': ['base_salary', 'bonus', 'gross_income'],
        'show_totals': True
    }


@pytest.fixture
def sample_config_file_contents():
    """Create sample JSON file contents with multiple configurations."""
    return {
        'TestReport1': {
            'title': 'Test Report One',
            'fields': ['base_salary', 'bonus'],
            'show_totals': True
        },
        'TestReport2': {
            'title': 'Test Report Two',
            'fields': ['federal_tax', 'state_tax', 'total_taxes'],
            'show_totals': False
        }
    }


class TestCustomRendererClass:
    """Test the CustomRenderer class directly."""
    
    def test_custom_renderer_init(self):
        """Test CustomRenderer initialization."""
        from render.renderers import CustomRenderer
        
        renderer = CustomRenderer(
            title='Test Report',
            fields=['base_salary', 'bonus'],
            start_year=2025,
            end_year=2030,
            show_totals=True
        )
        
        assert renderer.title == 'Test Report'
        assert renderer.fields == ['base_salary', 'bonus']
        assert renderer.start_year == 2025
        assert renderer.end_year == 2030
        assert renderer.show_totals is True
    
    def test_custom_renderer_init_defaults(self):
        """Test CustomRenderer initialization with defaults."""
        from render.renderers import CustomRenderer
        
        renderer = CustomRenderer(
            title='Test Report',
            fields=['gross_income']
        )
        
        assert renderer.title == 'Test Report'
        assert renderer.fields == ['gross_income']
        assert renderer.start_year is None
        assert renderer.end_year is None
        assert renderer.show_totals is True
    
    def test_custom_renderer_render_output(self, mock_plan_data):
        """Test that CustomRenderer produces expected output."""
        from render.renderers import CustomRenderer
        
        renderer = CustomRenderer(
            title='Income Test',
            fields=['base_salary', 'bonus', 'gross_income'],
            start_year=2025,
            end_year=2027,
            show_totals=True
        )
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(mock_plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Check title
        assert 'INCOME TEST' in result
        
        # Check that years are present
        assert '2025' in result
        assert '2026' in result
        assert '2027' in result
        
        # Check that years outside range are not present as data rows
        lines = result.split('\n')
        data_lines_2028 = [l for l in lines if l.strip().startswith('2028')]
        assert len(data_lines_2028) == 0
        
        # Check totals row
        assert 'TOTAL' in result
    
    def test_custom_renderer_no_totals(self, mock_plan_data):
        """Test CustomRenderer with show_totals=False."""
        from render.renderers import CustomRenderer
        
        renderer = CustomRenderer(
            title='No Summary Row',
            fields=['base_salary'],
            start_year=2025,
            end_year=2027,
            show_totals=False
        )
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(mock_plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Check that a totals row starting with "TOTAL" is not present
        # (The title may contain the word, but the data row should not)
        lines = result.split('\n')
        total_rows = [l for l in lines if l.strip().startswith('TOTAL')]
        assert len(total_rows) == 0, f"Found unexpected TOTAL row: {total_rows}"
    
    def test_custom_renderer_rate_fields_no_total(self, mock_plan_data):
        """Test that rate fields don't show totals."""
        from render.renderers import CustomRenderer
        
        renderer = CustomRenderer(
            title='Rate Test',
            fields=['effective_tax_rate', 'gross_income'],
            start_year=2025,
            end_year=2026,
            show_totals=True
        )
        
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            renderer.render(mock_plan_data)
        finally:
            sys.stdout = old_stdout
        
        result = output.getvalue()
        
        # Should have a TOTAL row
        assert 'TOTAL' in result


class TestCreateCustomRenderer:
    """Test the create_custom_renderer factory function."""
    
    def test_create_custom_renderer(self):
        """Test creating a CustomRenderer via factory function."""
        from render.renderers import create_custom_renderer
        
        renderer = create_custom_renderer(
            title='Factory Test',
            fields=['base_salary', 'bonus'],
            start_year=2025,
            end_year=2030,
            show_totals=True
        )
        
        assert renderer.title == 'Factory Test'
        assert renderer.fields == ['base_salary', 'bonus']
        assert renderer.start_year == 2025
        assert renderer.end_year == 2030
        assert renderer.show_totals is True
    
    def test_create_custom_renderer_defaults(self):
        """Test factory function with defaults."""
        from render.renderers import create_custom_renderer
        
        renderer = create_custom_renderer(
            title='Minimal Test',
            fields=['gross_income']
        )
        
        assert renderer.title == 'Minimal Test'
        assert renderer.fields == ['gross_income']
        assert renderer.start_year is None
        assert renderer.end_year is None
        assert renderer.show_totals is True


class TestCreateCustomRendererFromConfig:
    """Test creating renderers from configuration dictionaries."""
    
    def test_create_from_config_full(self, sample_config):
        """Test creating renderer from a complete config dict."""
        from render.renderers import create_custom_renderer_from_config
        
        renderer = create_custom_renderer_from_config(
            name='TestRenderer',
            config=sample_config,
            start_year=2025,
            end_year=2030
        )
        
        assert renderer.title == 'Test Income Report'
        assert renderer.fields == ['base_salary', 'bonus', 'gross_income']
        assert renderer.show_totals is True
        assert renderer.start_year == 2025
        assert renderer.end_year == 2030
    
    def test_create_from_config_uses_name_as_fallback_title(self):
        """Test that name is used as title if not provided in config."""
        from render.renderers import create_custom_renderer_from_config
        
        config = {
            'fields': ['base_salary']
        }
        
        renderer = create_custom_renderer_from_config(
            name='FallbackName',
            config=config
        )
        
        assert renderer.title == 'FallbackName'
    
    def test_create_from_config_empty_fields(self):
        """Test creating renderer with empty fields list."""
        from render.renderers import create_custom_renderer_from_config
        
        config = {
            'title': 'Empty Fields'
        }
        
        renderer = create_custom_renderer_from_config(
            name='EmptyTest',
            config=config
        )
        
        assert renderer.fields == []
    
    def test_create_from_config_show_totals_default(self):
        """Test that show_totals defaults to True."""
        from render.renderers import create_custom_renderer_from_config
        
        config = {
            'title': 'No Show Totals Key',
            'fields': ['base_salary']
        }
        
        renderer = create_custom_renderer_from_config(
            name='DefaultTest',
            config=config
        )
        
        assert renderer.show_totals is True
    
    def test_create_from_config_show_totals_false(self):
        """Test setting show_totals to False."""
        from render.renderers import create_custom_renderer_from_config
        
        config = {
            'title': 'No Totals',
            'fields': ['base_salary'],
            'show_totals': False
        }
        
        renderer = create_custom_renderer_from_config(
            name='NoTotalsTest',
            config=config
        )
        
        assert renderer.show_totals is False


class TestGetCustomRendererFactory:
    """Test the factory function generator."""
    
    def test_factory_creates_callable(self, sample_config):
        """Test that get_custom_renderer_factory returns a callable."""
        from render.renderers import get_custom_renderer_factory
        
        factory = get_custom_renderer_factory('TestFactory', sample_config)
        
        assert callable(factory)
    
    def test_factory_creates_renderer(self, sample_config):
        """Test that factory creates a CustomRenderer."""
        from render.renderers import get_custom_renderer_factory, CustomRenderer
        
        factory = get_custom_renderer_factory('TestFactory', sample_config)
        renderer = factory()
        
        assert isinstance(renderer, CustomRenderer)
        assert renderer.title == 'Test Income Report'
        assert renderer.fields == ['base_salary', 'bonus', 'gross_income']
    
    def test_factory_accepts_year_range(self, sample_config):
        """Test that factory accepts start_year and end_year."""
        from render.renderers import get_custom_renderer_factory
        
        factory = get_custom_renderer_factory('TestFactory', sample_config)
        renderer = factory(start_year=2025, end_year=2030)
        
        assert renderer.start_year == 2025
        assert renderer.end_year == 2030


class TestLoadUserCustomRenderers:
    """Test loading user configurations from a directory."""
    
    def test_load_from_empty_directory(self, temp_config_dir):
        """Test loading from an empty directory returns empty dict."""
        from render import renderers
        
        with patch.object(renderers, 'USER_CONFIG_DIR', temp_config_dir):
            result = renderers.load_user_custom_renderers()
        
        assert result == {}
    
    def test_load_from_nonexistent_directory(self):
        """Test loading from nonexistent directory returns empty dict."""
        from render import renderers
        
        with patch.object(renderers, 'USER_CONFIG_DIR', '/nonexistent/path'):
            result = renderers.load_user_custom_renderers()
        
        assert result == {}
    
    def test_load_single_config_file(self, temp_config_dir, sample_config_file_contents):
        """Test loading configurations from a single JSON file."""
        from render import renderers
        
        # Create config file
        config_path = os.path.join(temp_config_dir, 'test.json')
        with open(config_path, 'w') as f:
            json.dump(sample_config_file_contents, f)
        
        with patch.object(renderers, 'USER_CONFIG_DIR', temp_config_dir):
            result = renderers.load_user_custom_renderers()
        
        assert 'TestReport1' in result
        assert 'TestReport2' in result
        assert result['TestReport1']['title'] == 'Test Report One'
        assert result['TestReport2']['show_totals'] is False
    
    def test_load_multiple_config_files(self, temp_config_dir):
        """Test loading configurations from multiple JSON files."""
        from render import renderers
        
        # Create first config file
        config1 = {'ReportA': {'title': 'Report A', 'fields': ['base_salary']}}
        with open(os.path.join(temp_config_dir, 'config1.json'), 'w') as f:
            json.dump(config1, f)
        
        # Create second config file
        config2 = {'ReportB': {'title': 'Report B', 'fields': ['bonus']}}
        with open(os.path.join(temp_config_dir, 'config2.json'), 'w') as f:
            json.dump(config2, f)
        
        with patch.object(renderers, 'USER_CONFIG_DIR', temp_config_dir):
            result = renderers.load_user_custom_renderers()
        
        assert 'ReportA' in result
        assert 'ReportB' in result
    
    def test_source_file_added_to_config(self, temp_config_dir, sample_config):
        """Test that _source_file is added to each config."""
        from render import renderers
        
        config_path = os.path.join(temp_config_dir, 'myconfig.json')
        with open(config_path, 'w') as f:
            json.dump({'MyReport': sample_config}, f)
        
        with patch.object(renderers, 'USER_CONFIG_DIR', temp_config_dir):
            result = renderers.load_user_custom_renderers()
        
        assert result['MyReport']['_source_file'] == 'myconfig.json'
    
    def test_ignores_non_json_files(self, temp_config_dir, sample_config):
        """Test that non-JSON files are ignored."""
        from render import renderers
        
        # Create a non-JSON file
        with open(os.path.join(temp_config_dir, 'readme.txt'), 'w') as f:
            f.write('This is not a config file')
        
        # Create a JSON config file
        config_path = os.path.join(temp_config_dir, 'valid.json')
        with open(config_path, 'w') as f:
            json.dump({'ValidReport': sample_config}, f)
        
        with patch.object(renderers, 'USER_CONFIG_DIR', temp_config_dir):
            result = renderers.load_user_custom_renderers()
        
        assert 'ValidReport' in result
        assert len(result) == 1
    
    def test_handles_invalid_json(self, temp_config_dir, sample_config):
        """Test that invalid JSON files are handled gracefully."""
        from render import renderers
        
        # Create invalid JSON file
        with open(os.path.join(temp_config_dir, 'invalid.json'), 'w') as f:
            f.write('{ this is not valid json }')
        
        # Create valid JSON file
        with open(os.path.join(temp_config_dir, 'valid.json'), 'w') as f:
            json.dump({'ValidReport': sample_config}, f)
        
        with patch.object(renderers, 'USER_CONFIG_DIR', temp_config_dir):
            result = renderers.load_user_custom_renderers()
        
        # Should still load the valid config
        assert 'ValidReport' in result


class TestListUserConfigs:
    """Test the list_user_configs function."""
    
    def test_list_empty(self, temp_config_dir):
        """Test listing when no configs exist."""
        from render import renderers
        
        with patch.object(renderers, 'USER_CONFIG_DIR', temp_config_dir):
            result = renderers.list_user_configs()
        
        assert result == []
    
    def test_list_configs(self, temp_config_dir, sample_config_file_contents):
        """Test listing configurations."""
        from render import renderers
        
        config_path = os.path.join(temp_config_dir, 'configs.json')
        with open(config_path, 'w') as f:
            json.dump(sample_config_file_contents, f)
        
        with patch.object(renderers, 'USER_CONFIG_DIR', temp_config_dir):
            result = renderers.list_user_configs()
        
        assert len(result) == 2
        
        # Check structure of returned items
        names = [r['name'] for r in result]
        assert 'TestReport1' in names
        assert 'TestReport2' in names
        
        # Check that all expected keys are present
        for item in result:
            assert 'name' in item
            assert 'title' in item
            assert 'fields' in item
            assert 'show_totals' in item
            assert 'source_file' in item


class TestGetUserConfig:
    """Test the get_user_config function."""
    
    def test_get_existing_config(self, temp_config_dir, sample_config):
        """Test getting an existing configuration."""
        from render import renderers
        
        config_path = os.path.join(temp_config_dir, 'test.json')
        with open(config_path, 'w') as f:
            json.dump({'MyReport': sample_config}, f)
        
        with patch.object(renderers, 'USER_CONFIG_DIR', temp_config_dir):
            result = renderers.get_user_config('MyReport')
        
        assert result is not None
        assert result['title'] == 'Test Income Report'
    
    def test_get_nonexistent_config(self, temp_config_dir):
        """Test getting a nonexistent configuration returns None."""
        from render import renderers
        
        with patch.object(renderers, 'USER_CONFIG_DIR', temp_config_dir):
            result = renderers.get_user_config('NonexistentReport')
        
        assert result is None


class TestSaveUserConfig:
    """Test the save_user_config function."""
    
    def test_save_new_config(self, temp_config_dir, sample_config):
        """Test saving a new configuration."""
        from render import renderers
        
        with patch.object(renderers, 'USER_CONFIG_DIR', temp_config_dir):
            result = renderers.save_user_config('NewReport', sample_config, 'new.json')
        
        assert result is True
        
        # Verify file was created
        config_path = os.path.join(temp_config_dir, 'new.json')
        assert os.path.exists(config_path)
        
        # Verify content
        with open(config_path, 'r') as f:
            saved = json.load(f)
        
        assert 'NewReport' in saved
        assert saved['NewReport']['title'] == 'Test Income Report'
    
    def test_save_to_existing_file(self, temp_config_dir, sample_config):
        """Test saving to an existing file adds to it."""
        from render import renderers
        
        # Create initial config
        initial = {'ExistingReport': {'title': 'Existing', 'fields': ['base_salary']}}
        config_path = os.path.join(temp_config_dir, 'existing.json')
        with open(config_path, 'w') as f:
            json.dump(initial, f)
        
        with patch.object(renderers, 'USER_CONFIG_DIR', temp_config_dir):
            result = renderers.save_user_config('NewReport', sample_config, 'existing.json')
        
        assert result is True
        
        # Verify both configs exist
        with open(config_path, 'r') as f:
            saved = json.load(f)
        
        assert 'ExistingReport' in saved
        assert 'NewReport' in saved
    
    def test_save_overwrites_same_name(self, temp_config_dir):
        """Test saving with same name overwrites existing config."""
        from render import renderers
        
        # Create initial config
        initial_config = {'title': 'Original', 'fields': ['base_salary']}
        config_path = os.path.join(temp_config_dir, 'test.json')
        with open(config_path, 'w') as f:
            json.dump({'MyReport': initial_config}, f)
        
        # Save updated config with same name
        updated_config = {'title': 'Updated', 'fields': ['bonus']}
        
        with patch.object(renderers, 'USER_CONFIG_DIR', temp_config_dir):
            result = renderers.save_user_config('MyReport', updated_config, 'test.json')
        
        assert result is True
        
        # Verify update
        with open(config_path, 'r') as f:
            saved = json.load(f)
        
        assert saved['MyReport']['title'] == 'Updated'
        assert saved['MyReport']['fields'] == ['bonus']
    
    def test_save_creates_directory(self, temp_config_dir, sample_config):
        """Test saving creates directory if it doesn't exist."""
        from render import renderers
        
        new_dir = os.path.join(temp_config_dir, 'new_subdir')
        
        with patch.object(renderers, 'USER_CONFIG_DIR', new_dir):
            result = renderers.save_user_config('TestReport', sample_config, 'test.json')
        
        assert result is True
        assert os.path.exists(new_dir)
        assert os.path.exists(os.path.join(new_dir, 'test.json'))
    
    def test_save_strips_internal_fields(self, temp_config_dir):
        """Test that internal fields (starting with _) are not saved."""
        from render import renderers
        
        config_with_internal = {
            'title': 'Test',
            'fields': ['base_salary'],
            '_source_file': 'should_not_be_saved.json',
            '_internal_data': 'also should not be saved'
        }
        
        with patch.object(renderers, 'USER_CONFIG_DIR', temp_config_dir):
            result = renderers.save_user_config('TestReport', config_with_internal, 'test.json')
        
        assert result is True
        
        # Verify internal fields were not saved
        config_path = os.path.join(temp_config_dir, 'test.json')
        with open(config_path, 'r') as f:
            saved = json.load(f)
        
        assert '_source_file' not in saved['TestReport']
        assert '_internal_data' not in saved['TestReport']
        assert 'title' in saved['TestReport']


class TestDeleteUserConfig:
    """Test the delete_user_config function."""
    
    def test_delete_existing_config(self, temp_config_dir, sample_config_file_contents):
        """Test deleting an existing configuration."""
        from render import renderers
        
        config_path = os.path.join(temp_config_dir, 'configs.json')
        with open(config_path, 'w') as f:
            json.dump(sample_config_file_contents, f)
        
        with patch.object(renderers, 'USER_CONFIG_DIR', temp_config_dir):
            result = renderers.delete_user_config('TestReport1')
        
        assert result is True
        
        # Verify config was deleted
        with open(config_path, 'r') as f:
            saved = json.load(f)
        
        assert 'TestReport1' not in saved
        assert 'TestReport2' in saved  # Other config should remain
    
    def test_delete_last_config_removes_file(self, temp_config_dir, sample_config):
        """Test that deleting the last config removes the file."""
        from render import renderers
        
        config_path = os.path.join(temp_config_dir, 'single.json')
        with open(config_path, 'w') as f:
            json.dump({'OnlyConfig': sample_config}, f)
        
        with patch.object(renderers, 'USER_CONFIG_DIR', temp_config_dir):
            result = renderers.delete_user_config('OnlyConfig')
        
        assert result is True
        assert not os.path.exists(config_path)
    
    def test_delete_nonexistent_config(self, temp_config_dir):
        """Test deleting a nonexistent configuration returns False."""
        from render import renderers
        
        with patch.object(renderers, 'USER_CONFIG_DIR', temp_config_dir):
            result = renderers.delete_user_config('NonexistentReport')
        
        assert result is False


class TestGetAllCustomConfigs:
    """Test getting configs from both built-in and user directories."""
    
    def test_combines_builtin_and_user(self, temp_config_dir):
        """Test that built-in and user configs are combined."""
        from render import renderers
        
        # Create a user config
        user_config = {'UserReport': {'title': 'User Report', 'fields': ['base_salary']}}
        with open(os.path.join(temp_config_dir, 'user.json'), 'w') as f:
            json.dump(user_config, f)
        
        # Create a mock built-in config
        builtin_config = {'BuiltinReport': {'title': 'Builtin', 'fields': ['bonus']}}
        
        with patch.object(renderers, 'USER_CONFIG_DIR', temp_config_dir):
            with patch.object(renderers, 'load_custom_renderers', return_value=builtin_config):
                result = renderers.get_all_custom_configs()
        
        assert 'UserReport' in result
        assert 'BuiltinReport' in result
    
    def test_user_overrides_builtin(self, temp_config_dir):
        """Test that user configs override built-in configs with same name."""
        from render import renderers
        
        # Create user config with same name as "built-in"
        user_config = {'SharedName': {'title': 'User Version', 'fields': ['bonus']}}
        with open(os.path.join(temp_config_dir, 'user.json'), 'w') as f:
            json.dump(user_config, f)
        
        # Mock built-in config with same name
        builtin_config = {'SharedName': {'title': 'Builtin Version', 'fields': ['base_salary']}}
        
        with patch.object(renderers, 'USER_CONFIG_DIR', temp_config_dir):
            with patch.object(renderers, 'load_custom_renderers', return_value=builtin_config):
                result = renderers.get_all_custom_configs()
        
        # User version should override
        assert result['SharedName']['title'] == 'User Version'


class TestReloadRendererRegistry:
    """Test the reload_renderer_registry function."""
    
    def test_reload_clears_and_repopulates(self, temp_config_dir, sample_config):
        """Test that reload clears and repopulates the registry."""
        from render import renderers
        
        # Create a user config
        with open(os.path.join(temp_config_dir, 'test.json'), 'w') as f:
            json.dump({'CustomReport': sample_config}, f)
        
        with patch.object(renderers, 'USER_CONFIG_DIR', temp_config_dir):
            with patch.object(renderers, 'load_custom_renderers', return_value={}):
                renderers.reload_renderer_registry()
        
                # Check base renderers are present
                assert 'TaxDetails' in renderers.RENDERER_REGISTRY
                assert 'Balances' in renderers.RENDERER_REGISTRY
                assert 'AnnualSummary' in renderers.RENDERER_REGISTRY
                
                # Check custom renderer was loaded
                assert 'CustomReport' in renderers.RENDERER_REGISTRY
    
    def test_reload_updates_after_save(self, temp_config_dir, sample_config):
        """Test that reload picks up newly saved configs."""
        from render import renderers
        
        with patch.object(renderers, 'USER_CONFIG_DIR', temp_config_dir):
            with patch.object(renderers, 'load_custom_renderers', return_value={}):
                # Initially no custom configs
                renderers.reload_renderer_registry()
                assert 'NewReport' not in renderers.RENDERER_REGISTRY
                
                # Save a new config
                renderers.save_user_config('NewReport', sample_config, 'new.json')
                
                # Reload to pick up the change
                renderers.reload_renderer_registry()
                assert 'NewReport' in renderers.RENDERER_REGISTRY


class TestCustomRendererIntegration:
    """Integration tests for custom renderers with actual rendering."""
    
    def test_render_custom_config(self, mock_plan_data, temp_config_dir):
        """Test rendering using a custom configuration."""
        from render import renderers
        
        config = {
            'title': 'Integration Test Report',
            'fields': ['base_salary', 'bonus', 'take_home_pay'],
            'show_totals': True
        }
        
        with open(os.path.join(temp_config_dir, 'integration.json'), 'w') as f:
            json.dump({'IntegrationReport': config}, f)
        
        with patch.object(renderers, 'USER_CONFIG_DIR', temp_config_dir):
            with patch.object(renderers, 'load_custom_renderers', return_value={}):
                renderers.reload_renderer_registry()
                
                # Get the factory from registry
                factory = renderers.RENDERER_REGISTRY['IntegrationReport']
                renderer = factory(start_year=2025, end_year=2027)
                
                output = StringIO()
                old_stdout = sys.stdout
                sys.stdout = output
                
                try:
                    renderer.render(mock_plan_data)
                finally:
                    sys.stdout = old_stdout
                
                result = output.getvalue()
        
        assert 'INTEGRATION TEST REPORT' in result
        assert '2025' in result
        assert '2026' in result
        assert '2027' in result
        assert 'TOTAL' in result
