"""
Unit tests for CurrentsAPI retriever.

Usage:
    1. Set API_KEY variable directly in this file (line ~30)
    2. Or use environment variable: CURRENTS_API_KEY in .env
    3. Or pass as command line argument: python currents_test.py YOUR_API_KEY

Requirements:
    - Valid Currents API key
"""

import os
import sys
import asyncio
from datetime import datetime, timedelta

from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from data_pipeline.crawling.currents import CurrentsAPI
from data_pipeline.models import DataManager


# ============================================================================
# CONFIGURATION: Set your API key here for testing
# ============================================================================
API_KEY = ''  # Set your Currents API key here, e.g., "your_api_key_here"
# ============================================================================


def get_api_key():
    """Get API key from multiple sources in order of priority."""
    # 1. Check hardcoded API_KEY in this file
    if API_KEY:
        return API_KEY

    # 2. Check command line argument
    if len(sys.argv) > 1:
        return sys.argv[1]

    # 3. Check environment variable
    load_dotenv()
    return os.environ.get("CURRENTS_API_KEY")


async def test_get_entries():
    """Test retrieving entries from Currents API."""
    print("=" * 60)
    print("TEST 1: test_get_entries()")
    print("=" * 60)

    # Get API key
    api_key = get_api_key()

    if not api_key:
        print("ERROR: API key not found. Please set API_KEY in the script, environment, or pass as argument.")
        return

    dm = DataManager()
    r = CurrentsAPI(api_key, "LLM", dm, page_size=5)

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

    api_key = get_api_key()

    if not api_key:
        print("ERROR: API key not found. Please set API_KEY in the script, environment, or pass as argument.")
        return

    # Set date range (last 7 days)
    end = datetime.now().timestamp()
    start = (datetime.now() - timedelta(days=7)).timestamp()

    dm = DataManager()
    r = CurrentsAPI(api_key, "LLM", dm, start=start, end=end, page_size=10)

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


async def test_fetch():
    """Test the fetch method (should be no-op for CurrentsAPI)."""
    print("\n" + "=" * 60)
    print("TEST 3: test_fetch()")
    print("=" * 60)

    api_key = get_api_key()

    if not api_key:
        print("ERROR: API key not found. Please set API_KEY in the script, environment, or pass as argument.")
        return

    dm = DataManager()
    r = CurrentsAPI(api_key, "LLM", dm, page_size=3)
    r._get_entries()

    import httpx
    async with httpx.AsyncClient() as client:
        for entry in r.entries[:2]:  # Test first 2
            page = await r._fetch(client, entry)
            print(f"\nURL: {entry['url']}")
            print(f"Content exists: {page['content'] is not None}")
            if page['content']:
                print(f"Content length: {len(page['content'])} chars")
                print(f"Content preview: {page['content'][:150]}...")


async def test_retrieve():
    """Test the full retrieve() pipeline."""
    print("\n" + "=" * 60)
    print("TEST 4: test_retrieve() - Full Pipeline")
    print("=" * 60)

    api_key = get_api_key()

    if not api_key:
        print("ERROR: API key not found. Please set API_KEY in the script, environment, or pass as argument.")
        return

    dm = DataManager()
    r = CurrentsAPI(api_key, "LLM", dm, page_size=5, language="en")

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
    print("TEST 5: test_with_date_range()")
    print("=" * 60)

    api_key = get_api_key()

    if not api_key:
        print("ERROR: API key not found. Please set API_KEY in the script, environment, or pass as argument.")
        return

    # Test with last 3 days
    end = datetime.now()
    start = end - timedelta(days=3)

    print(f"Date range: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")

    dm = DataManager()
    r = CurrentsAPI(
        api_key,
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
    await test_fetch()
    await test_retrieve()
    await test_with_date_range()

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    # Run all tests
    asyncio.run(run_all_tests())

    # Or run individual tests by uncommenting:
    # asyncio.run(test_get_entries())
    # asyncio.run(test_filter())
    # asyncio.run(test_fetch())
    # asyncio.run(test_retrieve())
    # asyncio.run(test_with_date_range())
