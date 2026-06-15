import json
import logging

from pydantic import BaseModel
from sqlalchemy import select

from app.db.models import CorpusChunk
from app.db.session import AsyncSessionLocal
from app.llm.client import complete, embed

logger = logging.getLogger(__name__)


class _RerankScore(BaseModel):
    index: int
    score: float


async def retrieve(
    query: str, top_k: int = 5, top_n: int = 3, rerank: bool = True
) -> list[CorpusChunk]:
    """Embed query, cosine search top_k, optionally rerank to top_n."""
    query_vec = (await embed([query]))[0]

    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            select(CorpusChunk)
            .where(CorpusChunk.embedding.isnot(None))
            .order_by(CorpusChunk.embedding.cosine_distance(query_vec))
            .limit(top_k)
        )
        candidates = list(rows.scalars().all())

    if not candidates:
        return []

    if not rerank:
        return candidates[:top_n]

    return await _rerank(query, candidates, top_n)


async def _rerank(query: str, candidates: list[CorpusChunk], top_n: int) -> list[CorpusChunk]:
    """LLM-based reranker: score each candidate 1-10 for relevance to query."""
    snippets = "\n\n".join(f"[{i}] {c.content[:300]}" for i, c in enumerate(candidates))
    system = (
        "You are a relevance scorer. Given a user query and candidate passages, "
        "return a JSON array of {index, score} objects where score is 1-10. "
        "Return only valid JSON, no explanation."
    )
    user = f"Query: {query}\n\nCandidates:\n{snippets}"

    response = await complete(
        messages=[{"role": "user", "content": user}],
        system=system,
        max_tokens=256,
    )

    try:
        text_content = next(b.text for b in response.content if b.type == "text")
        # The model may wrap the array in a markdown fence or prose; extract it.
        start, end = text_content.find("["), text_content.rfind("]")
        if start == -1 or end <= start:
            raise ValueError("no JSON array in reranker output")
        scores = [
            _RerankScore.model_validate(item)
            for item in json.loads(text_content[start : end + 1])
        ]
        indexed = {s.index: s.score for s in scores}
        pos = {id(c): i for i, c in enumerate(candidates)}
        sorted_candidates = sorted(
            candidates,
            key=lambda c: indexed.get(pos[id(c)], 0.0),
            reverse=True,
        )
        return sorted_candidates[:top_n]
    except Exception:
        logger.warning("reranker output unparseable; falling back to cosine order", exc_info=True)
        return candidates[:top_n]
