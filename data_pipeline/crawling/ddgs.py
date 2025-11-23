import asyncio

from ddgs import DDGS as DDGSSearch
import httpx
import trafilatura

from ..models import Retriever, DataManager, Webpage


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
        max_results: int = 10
    ):
        super().__init__(query, data_manager, None, None, 5, 0.1)
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
    # 2. 异步 fetch：下载 HTML（不解析）
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
    # 3. preprocess 阶段（异步）：用 trafilatura 提取纯文本正文
    # ------------------------------------------------------------
    async def _preprocess(self, webpage: Webpage) -> Webpage:
        """
        Extract main content using trafilatura.
        If html extraction fails, fallback to summary.
        """
        html = webpage.get("content")

        if html:
            try:
                extracted = await asyncio.to_thread(trafilatura.extract, html)
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
