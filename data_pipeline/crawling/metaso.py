from datetime import datetime

import httpx

from ..models import Retriever, DataManager, Webpage
from .utils import timestamp_valid


def _chinese_date_to_timestamp(date_str: str) -> float | None:
    """Convert a Chinese-formatted date string (e.g., '2023年02月09日') to a timestamp."""
    try:
        return datetime.strptime(date_str, "%Y年%m月%d日").timestamp()
    except ValueError:
        return None


class Metaso(Retriever):
    """https://metaso.cn/search-api/playground"""

    def __init__(
        self,
        api_key: str,
        query: str,
        data_manager: DataManager,
        start: float | None = None,
        end: float | None = None,
        size: int = 20
    ):
        super().__init__(query, data_manager, start, end)
        self.api_key = api_key
        self.size = size
    
    def _get_entries(self) -> None:
        try:
            response = httpx.post(
                "https://metaso.cn/api/v1/search",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                json={
                    "q": self.query,
                    "scope": "webpage",
                    "size": f"{self.size}",
                    "includeRawContent": True   # fetch webpage content
                }
            )
            response.raise_for_status()
        except httpx.HTTPError:
            return
        data = response.json()
        for webpage in data.get("webpages", []):
            self.entries.append(Webpage(
                title=webpage["title"],
                url=webpage["link"],
                timestamp=_chinese_date_to_timestamp(webpage["date"]) if webpage.get("date") else None,
                summary=webpage["snippet"],
                content=webpage["content"]
            ))
    
    async def _filter(self) -> None:
        """Only filter timestamps."""
        for i in reversed(range(len(self.entries))):
            if not timestamp_valid(self.entries[i]["timestamp"], self.start, self.end):
                self.entries.pop(i)

    async def _fetch(self, client: httpx.AsyncClient, webpage: Webpage) -> Webpage:
        # already done by the API
        return webpage
