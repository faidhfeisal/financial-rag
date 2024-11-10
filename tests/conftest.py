import pytest
import asyncio
import aiohttp
from typing import AsyncGenerator

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def http_session() -> AsyncGenerator[aiohttp.ClientSession, None]:
    """Fixture that creates a new aiohttp session for each test."""
    async with aiohttp.ClientSession() as session:
        yield session