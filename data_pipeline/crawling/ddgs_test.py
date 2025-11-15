from data_pipeline.crawling.ddgs import DDGS
from data_pipeline.models import DataManager
import asyncio

async def test_get_entries():
    dm = DataManager()
    r = DDGS("猫咪 睡觉", dm, max_results=5)
    r._get_entries()

    print("Entries:", len(r.entries))
    for e in r.entries:
        print(e["title"], e["url"])

async def test_fetch():
    dm = DataManager()
    r = DDGS("猫咪", dm, max_results=3)
    r._get_entries()

    import httpx
    async with httpx.AsyncClient() as client:
        for entry in r.entries:
            page = await r._fetch(client, entry)
            print("URL:", entry["url"])
            print("Has HTML?", page["content"] is not None)

async def test_preprocess():
    dm = DataManager()
    r = DDGS("猫咪", dm, max_results=3)
    
    # step 1
    r._get_entries()

    import httpx
    async with httpx.AsyncClient() as client:
        for entry in r.entries:
            page = await r._fetch(client, entry)
            page = r._preprocess(page)
            print("Content:\n", page["content"][:200], "\n")

async def test_retrieve():
    dm = DataManager()
    r = DDGS("中国经济", dm, max_results=5, max_concurrent=2)

    await r.retrieve()

    print("Final webpages in DataManager:")
    for url, page in dm.webpages.items():
        print("Title:", page["title"])
        print("Content preview:", page["content"][:200], "\n")


# asyncio.run(test_get_entries())
# asyncio.run(test_fetch())
# asyncio.run(test_preprocess())
asyncio.run(test_retrieve())