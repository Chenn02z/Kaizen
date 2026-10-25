from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import async_engine_args, settings

# NullPool: Supabase's pooler already pools server-side, and per-session connections
# avoid cross-event-loop issues in tests.
_url, _connect_args = async_engine_args(settings.database_url)
engine = create_async_engine(_url, poolclass=NullPool, connect_args=_connect_args)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
