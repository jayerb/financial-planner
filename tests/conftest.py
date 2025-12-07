"""Pytest configuration for the financial-planner test suite."""

# Configure pytest-asyncio to use auto mode so all async tests are automatically run
pytest_plugins = ('pytest_asyncio',)

# Set the default asyncio mode - this tells pytest-asyncio to automatically
# apply the asyncio mark to async test functions
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "asyncio: mark test as an async test"
    )
