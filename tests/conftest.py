# Strategy: truncate the `logs` table before each test so row-count assertions
# are meaningful without requiring savepoint/rollback machinery.

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.main import app


@pytest_asyncio.fixture
async def db_session():
    """Yield an open session; truncate logs before handing it to the test."""
    async with AsyncSessionLocal() as session:
        await session.execute(text("TRUNCATE TABLE logs RESTART IDENTITY"))
        await session.commit()
        yield session


@pytest_asyncio.fixture
async def client():
    """In-process ASGI test client."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
