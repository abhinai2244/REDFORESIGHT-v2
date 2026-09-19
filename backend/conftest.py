"""Pytest configuration for RedForesight backend tests."""
import pytest

@pytest.fixture(scope="session")
def event_loop_policy():
    """Use the asyncio event loop policy for tests."""
    import asyncio
    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    return asyncio.get_event_loop_policy()
