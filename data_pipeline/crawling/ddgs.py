from typing import Optional
from datetime import datetime

from ddgs import DDGS as DDGSSearch
import httpx
import trafilatura

from ..models import Retriever, DataManager, Webpage
from .utils import timestamp_valid


class DDGS(Retriever):
    """
    Retriever using DuckDuckGo Search (ddgs) + Trafilatura for HTML extraction.

    Flow:
    - _get_entries(): use ddgs to search webpage URLs (title, snippet, link)
    - _fetch(): async request each webpage, download HTML
    - _preprocess(): extract clean text using trafilatura

    Output is stored into DataManager as Webpage objects.
    """

    def __init__(
        self,
        query: str,
        data_manager: DataManager,
        start: float | None = None,
        end: float | None = None,
        max_results: int = 10,
        max_concurrent: int = 2,
        wait_fixed: float = 0.5,
    ):
        super().__init__(query, data_manager, start, end, max_concurrent, wait_fixed)
        self.max_results = max_results

    # ------------------------------------------------------------
    # 1. 搜索阶段：同步执行
    # ------------------------------------------------------------
    def _get_entries(self) -> None:
        """Search with ddgs and populate self.entries (no HTML fetched yet)."""
        try:
            results = DDGSSearch().text(self.query, max_results=self.max_results)
        except Exception:
            return

        for r in results:
            title = r.get("title")
            url = r.get("href")
            summary = r.get("body", "")

            if not url:
                continue

            # 初步填入网页记录（content 暂时留空）
            self.entries.append(Webpage(
                title=title,
                url=url,
                timestamp=None,     # ddgs 不提供时间
                summary=summary,
                content=None        # 等 _fetch() → _preprocess()
            ))

    # ------------------------------------------------------------
    # 2. 时间过滤阶段：异步执行
    # ------------------------------------------------------------
    async def _filter(self):
        """Filter entries by timestamp range. For ddgs usually timestamp=None → keep all."""
        for i in reversed(range(len(self.entries))):
            if not timestamp_valid(self.entries[i]["timestamp"], self.start, self.end):
                self.entries.pop(i)

    # ------------------------------------------------------------
    # 3. 异步 fetch：下载 HTML（不解析）
    # ------------------------------------------------------------
    # async def _fetch(self, client: httpx.AsyncClient, webpage: Webpage) -> Webpage:
    #     """
    #     Download webpage HTML.
    #     - Must not throw errors
    #     - If fail, set webpage['content'] = None and return
    #     """
    #     try:
    #         resp = await client.get(webpage["url"], timeout=10.0)
    #         resp.raise_for_status()
    #         webpage["content"] = resp.text     # raw HTML
    #     except Exception:
    #         webpage["content"] = None
    #     return webpage
    async def _fetch(self, client: httpx.AsyncClient, webpage: Webpage) -> Webpage:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        }

        try:
            resp = await client.get(webpage["url"], headers=headers, timeout=10.0)
            resp.raise_for_status()
            webpage["content"] = resp.text
        except Exception:
            webpage["content"] = None

        return webpage
    # ------------------------------------------------------------
    # 4. preprocess 阶段（同步）：用 trafilatura 提取纯文本正文
    # ------------------------------------------------------------
    def _preprocess(self, webpage: Webpage) -> Webpage:
        """
        Extract main content using trafilatura.
        If html extraction fails, fallback to summary.
        """
        html = webpage.get("content")

        if html:
            try:
                extracted = trafilatura.extract(html)
                if extracted:
                    webpage["content"] = extracted.strip()
                    return webpage
            except Exception:
                pass

        # fallback to snippet
        if webpage.get("summary"):
            webpage["content"] = webpage["summary"]
        else:
            webpage["content"] = None

        return webpage
