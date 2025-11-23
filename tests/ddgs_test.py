import sys
from pathlib import Path
import asyncio

sys.path.append(str(Path(__file__).resolve().parent.parent))

from data_pipeline.crawling.ddgs import DDGS
from data_pipeline.models import DataManager


async def test_retrieve():
    dm = DataManager()
    r = DDGS("中国经济", dm, max_results=5)

    await r.retrieve()

    print("Final webpages in DataManager:")
    for url, page in dm.webpages.items():
        print("Title:", page["title"])
        print("Content preview:", page["content"][:200], "\n")

if __name__ == "__main__":
    asyncio.run(test_retrieve())
