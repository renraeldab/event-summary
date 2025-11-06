from abc import ABC, abstractmethod
from typing import TypedDict, Literal, Union
import asyncio
import json
from pathlib import Path

import httpx


class Webpage(TypedDict):
    title: str
    url: str
    timestamp: float | None
    summary: str | None
    content: str | None


EntityType = Literal[
    "Person",
    "Creature",
    "Organization",
    "Location",
    "Event",
    "Concept",
    "Method",
    "Artifact"
]


class EntityBase(TypedDict):
    name: str
    description: str


class Person(EntityBase):
    type: Literal["Person"]


class Creature(EntityBase):
    type: Literal["Creature"]


class Organization(EntityBase):
    type: Literal["Organization"]


class Location(EntityBase):
    type: Literal["Location"]


class Concept(EntityBase):
    type: Literal["Concept"]


class Method(EntityBase):
    type: Literal["Method"]


class Artifact(EntityBase):
    type: Literal["Artifact"]


class Event(EntityBase):
    type: Literal["Event"]
    start_time: str
    end_time: str


Entity = Union[
    Person,
    Creature,
    Organization,
    Location,
    Event,
    Concept,
    Method,
    Artifact,
]


class SubTheme(TypedDict):
    title: str
    content: str


class DataManager:
    def __init__(self):
        self.webpages: dict[str, Webpage] = {}
        self.entities: dict[tuple[EntityType, str], Entity] = {}
        self.sub_themes: dict[str, SubTheme] = {}
        self._queue = asyncio.Queue()
        self._stop_event = asyncio.Event()
    
    async def produce_webpage(self, webpage: Webpage) -> None:
        if self._stop_event.is_set():
            raise ValueError("The crawling phase has finished.")
        # ignore existing urls
        if webpage["url"] not in self.webpages:
            self.webpages[webpage["url"]] = webpage
            await self._queue.put(webpage["url"])
    
    async def consume_webpage(self) -> Webpage | None:
        while not self._stop_event.is_set():
            try:
                url = await asyncio.wait_for(self._queue.get(), timeout=0.1)
                return self.webpages[url]
            except asyncio.TimeoutError:
                continue
        # make sure the queue is empty
        if not self._queue.empty():
            url = await self._queue.get()
            return self.webpages[url]
        else:
            self._queue.task_done()
            return None
    
    def finish_crawling(self) -> None:
        self._stop_event.set()
    
    def __str__(self) -> str:
        data = {
            "webpages": list(self.webpages.values()),
            "entities": list(self.entities.values()),
            "sub_themes": list(self.sub_themes.values()),
        }
        return json.dumps(data, indent=4, ensure_ascii=False)

    def to_file(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding="utf-8") as f:
            f.write(str(self))

    @classmethod
    def from_file(cls, path: str) -> "DataManager":
        with open(path, encoding="utf-8") as f:
            data = json.loads(f.read())
        instance = cls()
        for webpage in data.get("webpages", []):
            if not isinstance(webpage, dict):
                continue
            url = webpage.get("url")
            if not url:
                continue
            instance.webpages[url] = {
                "title": webpage.get("title", ""),
                "url": url,
                "timestamp": webpage.get("timestamp", None),
                "summary": webpage.get("summary", None),
                "content": webpage.get("content", None),
            }
        for entity in data.get("entities", []):
            if not isinstance(entity, dict):
                continue
            etype = entity.get("type")
            name = entity.get("name")
            if not etype or not name:
                continue
            ent: dict = {
                "type": etype,
                "name": name,
                "description": entity.get("description", ""),
            }
            if etype == "Event":
                ent["start_time"] = entity.get("start_time", "")
                ent["end_time"] = entity.get("end_time", "")
            instance.entities[(etype, name)] = ent
        for sub_theme in data.get("sub_themes", []):
            if not isinstance(sub_theme, dict):
                continue
            title = sub_theme.get("title")
            if not title:
                continue
            instance.sub_themes[title] = {
                "title": title,
                "content": sub_theme.get("content", ""),
            }
        return instance


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
        data_manager: DataManager,
        start: float | None = None,     # optional start timestamp
        end: float | None = None,       # optional end timestamp
        max_concurrent: int = 2,        # max requesets at the same time
        wait_fixed: float = 0.          # wait for some time between requests
    ):
        self.entries: list[Webpage] = []
        self.query = query
        self.data_manager = data_manager
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
                        await self.data_manager.produce_webpage(webpage)
                    await asyncio.sleep(self.wait_fixed)
            
            await asyncio.gather(*[task(entry) for entry in self.entries])
