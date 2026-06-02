from mem0 import Memory, MemoryClient

from app.config import settings

_memory: Memory | MemoryClient | None = None


def get_memory() -> Memory | MemoryClient:
    global _memory
    if _memory is None:
        if settings.mem0_api_key:
            _memory = MemoryClient(api_key=settings.mem0_api_key)
        else:
            _memory = Memory.from_config(
                {
                    "llm": {
                        "provider": "anthropic",
                        "config": {"model": settings.llm_model, "api_key": settings.llm_api_key},
                    },
                    "embedder": {
                        "provider": "openai",
                        "config": {
                            "model": settings.embed_model,
                            "api_key": settings.embed_api_key,
                        },
                    },
                }
            )
    return _memory


def _to_list(results: list | dict) -> list[dict]:
    if isinstance(results, dict):
        return results.get("results", [])
    return results if isinstance(results, list) else []


def mem_add(text: str, user_id: str) -> None:
    mem = get_memory()
    if isinstance(mem, MemoryClient):
        mem.add(text, user_id=user_id)  # cloud: user_id is a direct param
    else:
        mem.add(text, filters={"user_id": user_id})  # local: must use filters


def mem_search(query: str, user_id: str, limit: int = 5) -> list[dict]:
    return _to_list(get_memory().search(query, filters={"user_id": user_id}, limit=limit))


def mem_get_all(user_id: str) -> list[dict]:
    return _to_list(get_memory().get_all(filters={"user_id": user_id}))
