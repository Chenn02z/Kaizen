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
        await session.execute(
            text(
                "TRUNCATE TABLE logs, extracted_facts, user_progress, habit_progress,"
                " habit_plans, habit_categories"
                " RESTART IDENTITY CASCADE"
            )
        )
        # corpus_chunks may not exist yet if the migration hasn't been applied
        await session.execute(
            text(
                "DO $$ BEGIN"
                " IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'corpus_chunks')"
                " THEN TRUNCATE TABLE corpus_chunks RESTART IDENTITY CASCADE; END IF;"
                " END $$"
            )
        )
        await session.execute(
            text(
                "DO $$ BEGIN"
                " IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'interventions')"
                " THEN TRUNCATE TABLE interventions RESTART IDENTITY CASCADE; END IF;"
                " END $$"
            )
        )
        await session.commit()
        yield session


@pytest_asyncio.fixture
async def client():
    """In-process ASGI test client."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
