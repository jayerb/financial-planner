"""Tests for the MCP server module."""

import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Add src and mcp-server to path for imports BEFORE importing mcp modules
MCP_SERVER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../mcp-server'))
SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src'))

if MCP_SERVER_PATH not in sys.path:
    sys.path.insert(0, MCP_SERVER_PATH)
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from mcp.types import Tool, TextContent

# Import server module - need to import from the mcp-server directory
import importlib.util
server_spec = importlib.util.spec_from_file_location("mcp_server", os.path.join(MCP_SERVER_PATH, "server.py"))
mcp_server = importlib.util.module_from_spec(server_spec)
server_spec.loader.exec_module(mcp_server)

tools_spec = importlib.util.spec_from_file_location("tools", os.path.join(MCP_SERVER_PATH, "tools.py"))
tools_module = importlib.util.module_from_spec(tools_spec)
tools_spec.loader.exec_module(tools_module)
MultiProgramTools = tools_module.MultiProgramTools


# Path to the test fixtures
BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))


class TestServerConfiguration:
    """Tests for server configuration and setup."""
    
    def test_server_name(self):
        """Test that server has correct name."""
        assert mcp_server.server.name == "financial-planner"
    
    def test_program_param_schema(self):
        """Test that PROGRAM_PARAM has correct schema."""
        assert mcp_server.PROGRAM_PARAM['type'] == 'string'
        assert 'description' in mcp_server.PROGRAM_PARAM


class TestGetTools:
    """Tests for get_tools function."""
    
    def setup_method(self):
        """Reset global tools before each test."""
        mcp_server.tools = None
    
    def teardown_method(self):
        """Reset global tools after each test."""
        mcp_server.tools = None
    
    def test_get_tools_initializes_on_first_call(self):
        """Test that get_tools initializes tools on first call."""
        tools = mcp_server.get_tools()
        
        assert tools is not None
        # Check by class name since we're using dynamic imports
        assert tools.__class__.__name__ == 'MultiProgramTools'
    
    def test_get_tools_returns_cached_instance(self):
        """Test that get_tools returns the same instance on subsequent calls."""
        tools1 = mcp_server.get_tools()
        tools2 = mcp_server.get_tools()
        
        assert tools1 is tools2
    
    @patch.dict(os.environ, {'FINANCIAL_PLANNER_PROGRAM': 'quickexample'})
    def test_get_tools_uses_env_default_program(self):
        """Test that FINANCIAL_PLANNER_PROGRAM env var sets default program."""
        mcp_server.tools = None  # Reset
        tools = mcp_server.get_tools()
        
        assert tools.default_program == 'quickexample'


class TestListTools:
    """Tests for list_tools function."""
    
    @pytest.mark.asyncio
    async def test_list_tools_returns_tools(self):
        """Test that list_tools returns a list of Tool objects."""
        tools = await mcp_server.list_tools()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        assert all(isinstance(t, Tool) for t in tools)
    
    @pytest.mark.asyncio
    async def test_list_tools_contains_expected_tools(self):
        """Test that list_tools contains all expected tool names."""
        tools = await mcp_server.list_tools()
        tool_names = [t.name for t in tools]
        
        expected_tools = [
            'list_programs',
            'get_program_overview',
            'list_available_years',
            'get_annual_summary',
            'get_tax_details',
            'get_income_breakdown',
            'get_deferred_comp_info',
            'get_retirement_balances',
            'get_investment_balances',
            'compare_years',
            'get_lifetime_totals',
            'search_financial_data'
        ]
        
        for expected in expected_tools:
            assert expected in tool_names
    
    @pytest.mark.asyncio
    async def test_tools_have_descriptions(self):
        """Test that all tools have descriptions."""
        tools = await mcp_server.list_tools()
        
        for tool in tools:
            assert tool.description is not None
            assert len(tool.description) > 0
    
    @pytest.mark.asyncio
    async def test_tools_have_input_schemas(self):
        """Test that all tools have input schemas."""
        tools = await mcp_server.list_tools()
        
        for tool in tools:
            assert tool.inputSchema is not None
            assert 'type' in tool.inputSchema
            assert tool.inputSchema['type'] == 'object'
    
    @pytest.mark.asyncio
    async def test_get_annual_summary_requires_year(self):
        """Test that get_annual_summary requires year parameter."""
        tools = await mcp_server.list_tools()
        annual_summary = next(t for t in tools if t.name == 'get_annual_summary')
        
        assert 'year' in annual_summary.inputSchema['required']
    
    @pytest.mark.asyncio
    async def test_compare_years_requires_both_years(self):
        """Test that compare_years requires both year1 and year2."""
        tools = await mcp_server.list_tools()
        compare = next(t for t in tools if t.name == 'compare_years')
        
        assert 'year1' in compare.inputSchema['required']
        assert 'year2' in compare.inputSchema['required']


class TestCallTool:
    """Tests for call_tool function."""
    
    def setup_method(self):
        """Reset global tools before each test."""
        mcp_server.tools = None
    
    @pytest.mark.asyncio
    async def test_call_list_programs(self):
        """Test calling list_programs tool."""
        result = await mcp_server.call_tool('list_programs', {})
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        
        data = json.loads(result[0].text)
        assert 'available_programs' in data
    
    @pytest.mark.asyncio
    async def test_call_get_program_overview(self):
        """Test calling get_program_overview tool."""
        result = await mcp_server.call_tool('get_program_overview', {'program': 'quickexample'})
        
        assert isinstance(result, list)
        data = json.loads(result[0].text)
        assert 'planning_horizon' in data or 'error' in data
    
    @pytest.mark.asyncio
    async def test_call_list_available_years(self):
        """Test calling list_available_years tool."""
        result = await mcp_server.call_tool('list_available_years', {'program': 'quickexample'})
        
        data = json.loads(result[0].text)
        assert 'working_years' in data or 'error' in data
    
    @pytest.mark.asyncio
    async def test_call_get_annual_summary(self):
        """Test calling get_annual_summary tool."""
        result = await mcp_server.call_tool('get_annual_summary', {'year': 2025, 'program': 'quickexample'})
        
        data = json.loads(result[0].text)
        assert 'gross_income' in data or 'error' in data
    
    @pytest.mark.asyncio
    async def test_call_get_tax_details(self):
        """Test calling get_tax_details tool."""
        result = await mcp_server.call_tool('get_tax_details', {'year': 2025, 'program': 'quickexample'})
        
        data = json.loads(result[0].text)
        assert 'federal' in data or 'error' in data
    
    @pytest.mark.asyncio
    async def test_call_get_income_breakdown(self):
        """Test calling get_income_breakdown tool."""
        result = await mcp_server.call_tool('get_income_breakdown', {'year': 2025, 'program': 'quickexample'})
        
        data = json.loads(result[0].text)
        assert 'gross_income' in data or 'error' in data
    
    @pytest.mark.asyncio
    async def test_call_get_deferred_comp_info(self):
        """Test calling get_deferred_comp_info tool."""
        result = await mcp_server.call_tool('get_deferred_comp_info', {'year': 2025, 'program': 'quickexample'})
        
        data = json.loads(result[0].text)
        assert 'contribution' in data or 'error' in data
    
    @pytest.mark.asyncio
    async def test_call_get_retirement_balances(self):
        """Test calling get_retirement_balances tool."""
        result = await mcp_server.call_tool('get_retirement_balances', {'program': 'quickexample'})
        
        data = json.loads(result[0].text)
        assert 'final_balances' in data or 'yearly_balances' in data or 'error' in data
    
    @pytest.mark.asyncio
    async def test_call_get_investment_balances(self):
        """Test calling get_investment_balances tool."""
        result = await mcp_server.call_tool('get_investment_balances', {'program': 'quickexample'})
        
        data = json.loads(result[0].text)
        # quickexample may not have investments configured
        assert 'message' in data or 'initial_balances' in data or 'error' in data
    
    @pytest.mark.asyncio
    async def test_call_compare_years(self):
        """Test calling compare_years tool."""
        result = await mcp_server.call_tool('compare_years', {
            'year1': 2025, 
            'year2': 2030, 
            'program': 'quickexample'
        })
        
        data = json.loads(result[0].text)
        assert 'comparison' in data or 'error' in data
    
    @pytest.mark.asyncio
    async def test_call_get_lifetime_totals(self):
        """Test calling get_lifetime_totals tool."""
        result = await mcp_server.call_tool('get_lifetime_totals', {'program': 'quickexample'})
        
        data = json.loads(result[0].text)
        assert 'lifetime_totals' in data or 'error' in data
    
    @pytest.mark.asyncio
    async def test_call_search_financial_data(self):
        """Test calling search_financial_data tool."""
        result = await mcp_server.call_tool('search_financial_data', {
            'query': 'salary',
            'year': 2025,
            'program': 'quickexample'
        })
        
        data = json.loads(result[0].text)
        assert 'query' in data or 'error' in data
    
    @pytest.mark.asyncio
    async def test_call_compare_programs(self):
        """Test calling compare_programs tool."""
        result = await mcp_server.call_tool('compare_programs', {
            'program1': 'quickexample',
            'program2': 'myprogram'
        })
        
        data = json.loads(result[0].text)
        assert 'metrics' in data or 'error' in data
        if 'metrics' in data:
            assert 'summary' in data
            assert 'recommendation' in data
    
    @pytest.mark.asyncio
    async def test_call_compare_programs_with_metrics(self):
        """Test calling compare_programs tool with specific metrics."""
        result = await mcp_server.call_tool('compare_programs', {
            'program1': 'quickexample',
            'program2': 'myprogram',
            'metrics': ['lifetime_income', 'take_home']
        })
        
        data = json.loads(result[0].text)
        if 'metrics' in data:
            assert len(data['metrics']) == 2
    
    @pytest.mark.asyncio
    async def test_call_unknown_tool(self):
        """Test calling an unknown tool returns error."""
        result = await mcp_server.call_tool('unknown_tool', {})
        
        data = json.loads(result[0].text)
        assert 'error' in data
        assert 'Unknown tool' in data['error']
    
    @pytest.mark.asyncio
    async def test_call_tool_with_exception(self):
        """Test that exceptions are handled gracefully."""
        # Call with invalid year type to trigger an error
        result = await mcp_server.call_tool('get_annual_summary', {
            'year': 'not_a_year',  # This might cause an error depending on implementation
            'program': 'quickexample'
        })
        
        data = json.loads(result[0].text)
        # Should either work or return an error, but not crash
        assert isinstance(data, dict)


class TestCallToolWithOptionalParams:
    """Tests for call_tool with optional parameters."""
    
    def setup_method(self):
        """Reset global tools before each test."""
        mcp_server.tools = None
    
    @pytest.mark.asyncio
    async def test_get_retirement_balances_with_year(self):
        """Test get_retirement_balances with optional year parameter."""
        result = await mcp_server.call_tool('get_retirement_balances', {
            'year': 2030,
            'program': 'quickexample'
        })
        
        data = json.loads(result[0].text)
        if 'error' not in data:
            assert data.get('year') == 2030 or 'balances' in data
    
    @pytest.mark.asyncio
    async def test_get_investment_balances_with_year(self):
        """Test get_investment_balances with optional year parameter."""
        result = await mcp_server.call_tool('get_investment_balances', {
            'year': 2030,
            'program': 'quickexample'
        })
        
        data = json.loads(result[0].text)
        # Should have a valid response
        assert isinstance(data, dict)
    
    @pytest.mark.asyncio
    async def test_search_without_year(self):
        """Test search_financial_data without year parameter."""
        result = await mcp_server.call_tool('search_financial_data', {
            'query': 'federal tax',
            'program': 'quickexample'
        })
        
        data = json.loads(result[0].text)
        assert 'query' in data or 'error' in data


class TestResponseFormat:
    """Tests for response format consistency."""
    
    def setup_method(self):
        """Reset global tools before each test."""
        mcp_server.tools = None
    
    @pytest.mark.asyncio
    async def test_response_is_text_content(self):
        """Test that all responses are TextContent objects."""
        result = await mcp_server.call_tool('list_programs', {})
        
        assert all(isinstance(r, TextContent) for r in result)
        assert all(r.type == 'text' for r in result)
    
    @pytest.mark.asyncio
    async def test_response_is_valid_json(self):
        """Test that all responses are valid JSON."""
        tools = await mcp_server.list_tools()
        
        for tool in tools:
            # Build minimal arguments
            args = {'program': 'quickexample'}
            if 'year' in tool.inputSchema.get('required', []):
                args['year'] = 2025
            if 'year1' in tool.inputSchema.get('required', []):
                args['year1'] = 2025
                args['year2'] = 2030
            if 'query' in tool.inputSchema.get('required', []):
                args['query'] = 'salary'
            
            result = await mcp_server.call_tool(tool.name, args)
            
            # Should be parseable as JSON
            data = json.loads(result[0].text)
            assert isinstance(data, dict)
    
    @pytest.mark.asyncio
    async def test_program_included_in_response(self):
        """Test that program name is included in responses where applicable."""
        result = await mcp_server.call_tool('get_annual_summary', {
            'year': 2025,
            'program': 'quickexample'
        })
        
        data = json.loads(result[0].text)
        if 'error' not in data:
            assert 'program' in data
            assert data['program'] == 'quickexample'
