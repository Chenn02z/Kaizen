from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings

# NullPool: each connection is returned to the DB immediately after use.
# This keeps things simple for M1 and avoids cross-event-loop issues in tests.
engine = create_async_engine(settings.database_url, poolclass=NullPool)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
