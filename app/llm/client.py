import anthropic
import openai as _openai
from langfuse import observe
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings

_client = anthropic.AsyncAnthropic(api_key=settings.llm_api_key)
_embed_client = _openai.AsyncOpenAI(api_key=settings.embed_api_key)

# Retry only on transient server-side errors; 4xx client errors must not be retried.
_RETRYABLE = (anthropic.RateLimitError, anthropic.InternalServerError)


@observe(as_type="generation")
@retry(
    retry=retry_if_exception_type(_RETRYABLE),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(3),
    reraise=True,
)
async def complete(
    messages: list[dict],
    *,
    system: str | None = None,
    tools: list[dict] | None = None,
    max_tokens: int = 1024,
) -> anthropic.types.Message:
    kwargs: dict = {
        "model": settings.llm_model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = {"type": "any"}
    return await _client.messages.create(**kwargs)


async def embed(texts: list[str]) -> list[list[float]]:
    """Embed a list of strings using the configured embedding model."""
    response = await _embed_client.embeddings.create(
        model=settings.embed_model,
        input=texts,
    )
    return [item.embedding for item in response.data]
