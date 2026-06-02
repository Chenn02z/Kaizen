import asyncio

from app.rag.embed import upsert_corpus

if __name__ == "__main__":
    count = asyncio.run(upsert_corpus())
    print(f"Embedded {count} new/updated chunks.")
