import hashlib
from pathlib import Path

from sqlalchemy import select

from app.db.models import CorpusChunk
from app.db.session import AsyncSessionLocal
from app.llm.client import embed

CORPUS_DIR = Path(__file__).parent.parent.parent / "corpus"


async def upsert_corpus() -> int:
    """Embed and upsert all corpus chunks. Returns count of newly embedded chunks."""
    paths = sorted(CORPUS_DIR.glob("*.md"))
    newly_embedded = 0

    async with AsyncSessionLocal() as session:
        for path in paths:
            content = path.read_text()
            content_hash = hashlib.sha256(content.encode()).hexdigest()

            result = await session.execute(
                select(CorpusChunk).where(CorpusChunk.filename == path.name)
            )
            existing = result.scalar_one_or_none()

            if existing and existing.content_hash == content_hash:
                continue  # already embedded, skip

            vectors = await embed([content])
            vector = vectors[0]

            if existing:
                existing.content = content
                existing.content_hash = content_hash
                existing.embedding = vector
            else:
                session.add(
                    CorpusChunk(
                        filename=path.name,
                        content=content,
                        content_hash=content_hash,
                        embedding=vector,
                    )
                )
            newly_embedded += 1

        await session.commit()
    return newly_embedded
