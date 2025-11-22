"""
Standalone test script for CurrentsAPI retriever.
Run from project root: uv run python test_currents_standalone.py
"""

import asyncio
from datetime import datetime, timedelta

from data_pipeline.crawling.currents import CurrentsAPI
from data_pipeline.models import DataManager


# API Key
API_KEY = '' # Set your Currents API key here


async def test_get_entries():
    """Test retrieving entries from Currents API."""
    print("=" * 60)
    print("TEST 1: test_get_entries()")
    print("=" * 60)

    dm = DataManager()
    r = CurrentsAPI(API_KEY, "LLM", dm, page_size=5)

    # Get entries (synchronous part)
    r._get_entries()

    print(f"\nFound {len(r.entries)} entries")
    print("\nEntry details:")
    for i, entry in enumerate(r.entries, 1):
        print(f"\n{i}. Title: {entry['title']}")
        print(f"   URL: {entry['url']}")
        print(f"   Timestamp: {entry['timestamp']}")
        if entry['timestamp']:
            dt = datetime.fromtimestamp(entry['timestamp'])
            print(f"   Date: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Summary: {entry['summary'][:100]}..." if entry['summary'] else "   Summary: None")
        print(f"   Has content: {entry['content'] is not None}")


async def test_filter():
    """Test timestamp filtering."""
    print("\n" + "=" * 60)
    print("TEST 2: test_filter()")
    print("=" * 60)

    # Set date range (last 7 days)
    end = datetime.now().timestamp()
    start = (datetime.now() - timedelta(days=7)).timestamp()

    dm = DataManager()
    r = CurrentsAPI(API_KEY, "LLM", dm, start=start, end=end, page_size=10)

    r._get_entries()
    print(f"\nBefore filter: {len(r.entries)} entries")

    await r._filter()
    print(f"After filter: {len(r.entries)} entries")

    print("\nFiltered entries:")
    for i, entry in enumerate(r.entries, 1):
        if entry['timestamp']:
            dt = datetime.fromtimestamp(entry['timestamp'])
            print(f"{i}. {entry['title'][:50]}... - {dt.strftime('%Y-%m-%d')}")
        else:
            print(f"{i}. {entry['title'][:50]}... - No timestamp")


async def test_retrieve():
    """Test the full retrieve() pipeline."""
    print("\n" + "=" * 60)
    print("TEST 3: test_retrieve() - Full Pipeline")
    print("=" * 60)

    dm = DataManager()
    r = CurrentsAPI(API_KEY, "LLM", dm, page_size=5, language="en")

    # Run full pipeline
    await r.retrieve()

    print(f"\nFinal webpages in DataManager: {len(dm.webpages)}")
    print("\nWebpage details:")
    for i, (url, page) in enumerate(dm.webpages.items(), 1):
        print(f"\n{i}. Title: {page['title']}")
        print(f"   URL: {url}")
        if page['timestamp']:
            dt = datetime.fromtimestamp(page['timestamp'])
            print(f"   Published: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        if page['summary']:
            print(f"   Summary: {page['summary'][:100]}...")
        if page['content']:
            print(f"   Content length: {len(page['content'])} chars")
            print(f"   Content preview: {page['content'][:150]}...")


async def test_with_date_range():
    """Test with specific date range."""
    print("\n" + "=" * 60)
    print("TEST 4: test_with_date_range()")
    print("=" * 60)

    # Test with last 3 days
    end = datetime.now()
    start = end - timedelta(days=3)

    print(f"Date range: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")

    dm = DataManager()
    r = CurrentsAPI(
        API_KEY,
        "LLM",
        dm,
        start=start.timestamp(),
        end=end.timestamp(),
        page_size=10,
        language="en"
    )

    await r.retrieve()

    print(f"\nFound {len(dm.webpages)} articles in date range")
    for i, page in enumerate(dm.webpages.values(), 1):
        if page['timestamp']:
            dt = datetime.fromtimestamp(page['timestamp'])
            print(f"{i}. {page['title'][:60]}... ({dt.strftime('%Y-%m-%d')})")


async def run_all_tests():
    """Run all tests sequentially."""
    print("\n" + "=" * 60)
    print("CURRENTS API UNIT TESTS - Query: 'LLM'")
    print("=" * 60)

    await test_get_entries()
    await test_filter()
    await test_retrieve()
    await test_with_date_range()

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
