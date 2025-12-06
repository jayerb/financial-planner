"""Pytest configuration for MCP server tests."""

import pytest

# Set the asyncio_mode to auto for all async tests in this directory
@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
