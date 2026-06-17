from app.config import normalize_async_database_url


def test_normalize_async_database_url_keeps_asyncpg_url() -> None:
    url = "postgresql+asyncpg://kaizen:kaizen@localhost:5432/kaizen"
    assert normalize_async_database_url(url) == url


def test_normalize_async_database_url_accepts_managed_postgres_url() -> None:
    url = "postgresql://kaizen:secret@host:5432/kaizen"
    assert (
        normalize_async_database_url(url)
        == "postgresql+asyncpg://kaizen:secret@host:5432/kaizen"
    )


def test_normalize_async_database_url_accepts_legacy_postgres_scheme() -> None:
    url = "postgres://kaizen:secret@host:5432/kaizen"
    assert (
        normalize_async_database_url(url)
        == "postgresql+asyncpg://kaizen:secret@host:5432/kaizen"
    )
