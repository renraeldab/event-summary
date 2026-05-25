# Event Summary — Coding Agent Guide

This document is designed for AI coding agents (Claude Code, Cursor, Copilot, etc.) who need to extend the project. It provides the exact integration contracts, file paths, and step-by-step templates so you can add new data sources or processors without reading the entire codebase.

## Overview

Event Summary is an async data pipeline that:
1. **Retrieves** webpages from multiple sources (search APIs, RSS, etc.).
2. **Processes** them with LLMs to extract structured entities and sub-themes.
3. **Renders** a static HTML report.

The core abstraction is a **producer-consumer** pattern with two independent consumer queues (entity extraction and sub-theme generation).

## Architecture at a Glance

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│ Retrievers  │────▶│ DataManager │────▶│  Processors     │
│ (producers) │     │ (dual queues│     │  (consumers)    │
│             │     │  + storage) │     │                 │
└─────────────┘     └─────────────┘     └─────────────────┘
     DDGS                                   BaselineExtractor
     Metaso                                 BaselineGenerator
     CurrentsAPI
     RSS (reference impl)
```

- **Retriever**: Fetches webpage metadata and content, then calls `data_manager.produce_webpage()`.
- **DataManager**: Holds `webpages`, `entities`, `sub_themes`. Manages two `asyncio.Queue`s (`_extractor_queue`, `_generator_queue`).
- **Processor**: Consumes webpages from its queue in batches, runs LLM inference, and overrides the global state via `override_entities()` / `override_sub_themes()`.

## Directory Layout

```
event-summary/
├── data_pipeline/
│   ├── __main__.py              # Entry point: wires retrievers + processors
│   ├── models.py                # DataManager, Retriever, Processor abstractions
│   ├── utils.py                 # OpenAICompatible LLM client wrapper
│   ├── crawling/
│   │   ├── __init__.py          # Exports retrievers; register new ones here
│   │   ├── utils.py             # timestamp_valid helper
│   │   ├── ddgs.py              # DuckDuckGo + Trafilatura
│   │   ├── metaso.py            # Metaso Chinese search API
│   │   ├── currents.py          # CurrentsAPI news
│   │   └── rss.py               # RSS/Atom feedparser (reference implementation)
│   └── processing/
│       ├── __init__.py          # Exports processors
│       └── base.py              # BaselineExtractor, BaselineGenerator
├── html_generator/
│   ├── __main__.py              # Renders data/*.json into HTML
│   └── template.html            # Jinja2 template
├── data/                        # JSON output directory
└── tests/                       # Async test, RSS test, LLM test
```

## How to Integrate a New Data Source (Retriever)

### Step 1: Create a new file in `data_pipeline/crawling/`

Implement the `Retriever` abstract base class from `data_pipeline.models`. You **must** implement `_get_entries` and `_fetch`. Optionally implement `_filter` and `_preprocess`.

**Contract**:

| Method | Sync/Async | Purpose | Requirements |
|--------|-----------|---------|--------------|
| `_get_entries(self)` | Sync | Populate `self.entries` with `Webpage` dicts. | Must not raise unhandled exceptions. |
| `_filter(self)` | Async | Prune `self.entries` before fetching. | Optional. Call `super()` if not needed. |
| `_fetch(self, client, webpage)` | Async | Download full content. | **Must catch ALL exceptions.** On failure, set `webpage['content'] = None` and still return it. |
| `_preprocess(self, webpage)` | Async | Transform HTML → clean text. | Optional. |

**Minimal Template** (copy-paste into `data_pipeline/crawling/<your_source>.py`):

```python
import httpx
from ..models import Retriever, DataManager, Webpage

class MySource(Retriever):
    name = "MySource"

    def __init__(self, api_key: str, query: str, data_manager: DataManager):
        super().__init__(query, data_manager, start=None, end=None, max_concurrent=3, wait_fixed=0.2)
        self.api_key = api_key

    def _get_entries(self) -> None:
        # Synchronous search / listing
        try:
            response = httpx.get(
                "https://api.example.com/search",
                params={"q": self.query, "key": self.api_key},
                timeout=30.0
            )
            response.raise_for_status()
        except Exception:
            return

        for item in response.json().get("results", []):
            self.entries.append(Webpage(
                title=item.get("title"),
                url=item.get("url"),
                timestamp=None,  # convert to float timestamp if available
                summary=item.get("snippet"),
                content=None     # fill in _fetch
            ))

    async def _fetch(self, client: httpx.AsyncClient, webpage: Webpage) -> Webpage:
        try:
            resp = await client.get(webpage["url"], timeout=10.0)
            resp.raise_for_status()
            webpage["content"] = resp.text
        except Exception:
            webpage["content"] = None
        return webpage

    async def _preprocess(self, webpage: Webpage) -> Webpage:
        # Optional: strip HTML, extract main text, etc.
        return webpage
```

**Important rules for `_fetch`**:
- Never let an exception escape. Always `try/except Exception`.
- On any failure, set `webpage["content"] = None` and return the dict.
- Use `await asyncio.sleep(...)` instead of `time.sleep(...)`.
- The semaphore (`self.max_concurrent`) is already handled by `Retriever.retrieve()`.

### Step 2: Register the retriever

Edit `data_pipeline/crawling/__init__.py`:

```python
from .my_source import MySource  # add this line
```

### Step 3: Wire it into the pipeline

Edit `data_pipeline/__main__.py`. Add your retriever instantiation inside the `if __name__ == "__main__"` block, following the same pattern as `Metaso` or `CurrentsAPI`:

```python
from data_pipeline.crawling import MySource  # add import

# ... inside main block ...
my_api_key = os.environ.get("MY_API_KEY")
if my_api_key:
    retrievers.append(MySource(my_api_key, query, data_manager))
```

### Step 4: Add environment variable (optional)

Add the key to `.env.example` so users know it exists:

```
MY_API_KEY=YOUR_KEY_HERE
```

## How to Integrate a New Processor

Processors consume webpages and produce either `Entity` or `SubTheme` objects. The pipeline already supports multiple processors running in parallel.

1. Subclass `Processor` from `data_pipeline.models`.
2. Set `processor_type = "extractor"` or `"generator"`.
3. Implement `async def _process(self, webpages: list[Webpage]) -> list[Entity | SubTheme]`.
4. Register in `data_pipeline/processing/__init__.py` and wire into `data_pipeline/__main__.py`.

The `_process` method **must** return the **full updated list** (not a delta), because `DataManager.override_*` replaces the entire collection.

## Integration Checklist

Before declaring a new source integration complete, verify:

- [ ] New retriever file created in `data_pipeline/crawling/`
- [ ] `_get_entries` populates `self.entries` with valid `Webpage` dicts
- [ ] `_fetch` catches all exceptions and returns the webpage dict even on failure
- [ ] `data_pipeline/crawling/__init__.py` exports the new class
- [ ] `data_pipeline/__main__.py` instantiates and appends it to `retrievers`
- [ ] `.env.example` updated if a new API key is required
- [ ] `pyproject.toml` updated if a new dependency is required (run `uv add <pkg>`)
- [ ] A quick manual test passes: `python -m data_pipeline "test query"`

## Testing & Validation

- **Async test**: `tests/async_test.py` — deterministic producer-consumer simulation. Useful for verifying concurrency logic without hitting APIs.
- **LLM test**: `tests/llm_test.py` — verifies the OpenAI-compatible client works.
- **RSS test**: `tests/simple_test_rss.py` — reference implementation test for a custom retriever.

When adding a new retriever, you can copy `tests/simple_test_rss.py` and adapt it to your source for a standalone integration test.

## Key Design Notes

1. **Dual queues**: `DataManager` maintains two independent queues. Every new webpage is pushed to both. The entity extractor and sub-theme generator run at their own pace.
2. **Override semantics**: Processors call `override_entities(entities, n_update)` or `override_sub_themes(sub_themes, n_update)`. This replaces the entire stored list, so `_process` should return the merged/updated full list.
3. **State locking**: `DataManager` uses `asyncio.Lock` for `webpages`, `entities`, and `sub_themes`. Processors are safe to read shared state, but writes go through the provided override methods.
4. **tqdm bars**: The `DataManager` dynamically updates tqdm progress bars. If you create new consumers, consider whether they need their own progress tracking.
5. **HTML generator**: Reads every `.json` file in `data/` and renders them in a sidebar-navigated report. No code changes are needed there unless you add new output fields.
