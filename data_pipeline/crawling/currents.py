from datetime import datetime

import httpx

from ..models import Retriever, DataManager, Webpage
from .utils import timestamp_valid


def _parse_currents_date(date_str: str) -> float | None:
    """Convert Currents API date format to timestamp.

    Expected format: "2019-09-18 21:08:58 +0000"
    """
    try:
        # Parse the date string
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
        return dt.timestamp()
    except (ValueError, AttributeError):
        return None


def _timestamp_to_currents_date(timestamp: float) -> str:
    """Convert timestamp to Currents API date format.

    Returns format: "YYYY-MM-DD"
    """
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d")


class CurrentsAPI(Retriever):
    """Retriever using Currents API for news articles.

    Documentation: https://currentsapi.services/en/docs/

    Flow:
    - _get_entries(): use Currents API search endpoint to get articles
    - _filter(): filter by timestamp if start/end provided
    - _fetch(): no additional fetch needed (content provided by API)

    Output is stored into DataManager as Webpage objects.
    """

    BASE_URL = "https://api.currentsapi.services/v1"

    def __init__(
        self,
        api_key: str,
        query: str,
        data_manager: DataManager,
        start: float | None = None,
        end: float | None = None,
        language: str = "en",
        page_size: int = 20,
    ):
        super().__init__(query, data_manager, start, end)
        self.api_key = api_key
        self.language = language
        self.page_size = page_size

    def _get_entries(self) -> None:
        """Search with Currents API and populate self.entries."""
        params = {
            "apiKey": self.api_key,
            "keywords": self.query,
            "language": self.language,
            "page_size": str(self.page_size),
        }

        # Add date filters if provided
        if self.start:
            params["start_date"] = _timestamp_to_currents_date(self.start)
        if self.end:
            params["end_date"] = _timestamp_to_currents_date(self.end)

        try:
            response = httpx.get(
                f"{self.BASE_URL}/search",
                params=params,
                timeout=30.0
            )
            response.raise_for_status()
        except httpx.HTTPError:
            return

        data = response.json()

        # Check for API errors
        if data.get("status") != "ok":
            return

        # Parse articles
        for article in data.get("news", []):
            title = article.get("title")
            url = article.get("url")

            if not url or not title:
                continue

            # Parse timestamp
            published = article.get("published")
            timestamp = _parse_currents_date(published) if published else None

            # Use description as summary, full content if available
            description = article.get("description", "")

            self.entries.append(Webpage(
                title=title,
                url=url,
                timestamp=timestamp,
                summary=description,
                content=description  # Currents API provides description, not full content
            ))

    async def _filter(self) -> None:
        """Filter articles by timestamp if needed."""
        for i in reversed(range(len(self.entries))):
            if not timestamp_valid(self.entries[i]["timestamp"], self.start, self.end):
                self.entries.pop(i)

    async def _fetch(self, client: httpx.AsyncClient, webpage: Webpage) -> Webpage:
        """Content already provided by API, no additional fetch needed."""
        return webpage
