from app.config import async_engine_args, sync_database_url

SUPABASE_URL = (
    "postgresql://postgres.ref:p%40ss@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres"
    "?sslmode=require"
)


def test_async_engine_args_moves_sslmode_into_connect_args() -> None:
    url, connect_args = async_engine_args(SUPABASE_URL)
    assert url.drivername == "postgresql+asyncpg"
    assert "sslmode" not in url.query
    assert url.password == "p@ss"
    assert connect_args == {"ssl": "require"}


def test_async_engine_args_without_ssl_for_local_db() -> None:
    url, connect_args = async_engine_args(
        "postgresql+asyncpg://kaizen:kaizen@localhost:5432/kaizen"
    )
    assert url.drivername == "postgresql+asyncpg"
    assert connect_args == {}


def test_sync_database_url_keeps_sslmode_and_password() -> None:
    assert sync_database_url(SUPABASE_URL) == SUPABASE_URL


def test_sync_database_url_accepts_legacy_postgres_scheme() -> None:
    assert sync_database_url("postgres://u:p@host:5432/db") == "postgresql://u:p@host:5432/db"
