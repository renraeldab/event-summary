from abc import ABC, abstractmethod
from typing import TypedDict
import asyncio

import httpx


class Webpage(TypedDict):
    title: str
    url: str
    timestamp: float | None
    content: str | None


class Retriever(ABC):
    """
    Abstract base for retrieval implementations.

    Subclasses should implement:
    - _get_entries: populate self.entries with Webpage dicts
    - _fetch: asynchronously fetch for a single entry
    Optionally override:
    - _filter: filter step to prune/modify self.entries
    - _preprocess: transformation of a fetched webpage
    """

    def __init__(
        self,
        query: str,
        queue: asyncio.Queue,           # output queue
        start: float | None = None,     # optional start timestamp
        end: float | None = None,       # optional end timestamp
        max_concurrent: int = 2,        # max requesets at the same time
        wait_fixed: float = 0.          # wait for some time between requests
    ):
        self.entries: list[Webpage] = []
        self.query = query
        self.queue = queue
        self.start = start
        self.end = end
        self.max_concurrent = max_concurrent
        self.wait_fixed = wait_fixed
    
    @abstractmethod
    def _get_entries(self) -> None:
        """Populate self.entries synchronously."""
        raise NotImplementedError
    
    async def _filter(self) -> None:
        """Optional async filtering step."""
        pass

    @abstractmethod
    async def _fetch(self, client: httpx.AsyncClient, webpage: Webpage) -> Webpage:
        """Fetch and fill in 'content' for a single entry. If this step is not needed, just return webpage.
        
        **Error Handling**:
        - The implementation MUST catch all expected and unexpected exceptions (e.g., network timeouts, HTTP errors).
        - On any failure, the method MUST NOT raise an exception that escapes to the caller. Instead:
            - Leave `webpage['content'] = None` (or explicitly set it to `None`),
            - Still return the `webpage` dict.
        - If errors are too often, optimize `max_concurrent`, `wait_fixed`, and request parameters, like headers.

        **Retry Logic**:
        - Retry is optional.
        - Any desired retry behavior (e.g., limited attempts) should be implemented inside this method.

        **Performance**:
        - Avoid blocking calls (e.g., `time.sleep()`); use `await asyncio.sleep()` if needed.

        **Example (minimal safe implementation)**:
        ```python
        async def _fetch(self, client, webpage):
            try:
                response = await client.get(webpage["url"], timeout=10.0)
                response.raise_for_status()
                webpage["content"] = response.text
            except Exception as e:
                webpage["content"] = None
            return webpage
        ```
        """
        raise NotImplementedError

    def _preprocess(self, webpage: Webpage) -> Webpage:
        """Optional sync transformation for a single webpage's content (e.g., extracting text from html)."""
        return webpage

    async def retrieve(self) -> None:
        """Public method."""
        self._get_entries()
        await self._filter()
        if not self.entries:
            return
        semaphore = asyncio.Semaphore(self.max_concurrent)
        async with httpx.AsyncClient() as client:
            async def task(entry: Webpage) -> None:
                async with semaphore:
                    webpage = await self._fetch(client, entry)
                    webpage = self._preprocess(webpage)
                    if webpage["content"] is not None:
                        await self.queue.put(webpage)
                    await asyncio.sleep(self.wait_fixed)
            
            await asyncio.gather(*[task(entry) for entry in self.entries])
