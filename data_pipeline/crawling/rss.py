import asyncio
import httpx
import logging
from typing import List, Dict, Optional
import feedparser
from datetime import datetime
import time
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse

from ..models import Retriever, DataManager, Webpage

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RSS(Retriever):
    """
    Retriever using RSS feeds + BeautifulSoup for content extraction.
    Inherits from models.Retriever for consistent interface.
    """

    def __init__(
            self,
            query: str,
            data_manager: DataManager,
            rss_urls: List[str],
            keywords: Optional[List[str]] = None,
            max_concurrent: int = 5,
            wait_fixed: float = 0.5,
            timeout: int = 30,
            max_retries: int = 3
    ):
        super().__init__(query, data_manager, None, None, max_concurrent, wait_fixed)
        self.rss_urls = rss_urls
        self.keywords = keywords or []
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = None

    def _get_entries(self) -> None:
        """Synchronously fetch RSS feeds and populate self.entries."""
        logger.info(f"📥 开始同步获取RSS源: {len(self.rss_urls)}个源")

        all_entries = []
        for rss_url in self.rss_urls:
            try:
                entries = self._fetch_rss_feed(rss_url)
                all_entries.extend(entries)
                logger.info(f"✅ 成功获取 {len(entries)} 条条目来自 {rss_url}")
            except Exception as e:
                logger.error(f"❌ 获取RSS源失败 {rss_url}: {str(e)}")
                continue

        # 去重
        unique_entries = self._remove_duplicates(all_entries)
        logger.info(f"📊 总共获取 {len(unique_entries)} 条唯一条目")

        self.entries = unique_entries

    def _fetch_rss_feed(self, rss_url: str) -> List[Webpage]:
        """同步获取并解析单个RSS源"""
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    time.sleep(2 ** attempt)  # 指数退避

                # 使用httpx同步客户端获取RSS
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(rss_url)
                    response.raise_for_status()

                feed = feedparser.parse(response.content)
                entries = []

                for entry in feed.entries:
                    # 转换为Webpage格式
                    webpage = self._parse_rss_entry(entry, rss_url)
                    if self._filter_by_keywords(webpage):
                        entries.append(webpage)

                return entries

            except Exception as e:
                logger.warning(f"⚠️ 尝试 {attempt + 1}/{self.max_retries} 失败: {rss_url} - {str(e)}")
                if attempt == self.max_retries - 1:
                    raise e

        return []

    def _parse_rss_entry(self, entry, source_url: str) -> Webpage:
        """解析RSS条目为Webpage格式"""
        # 处理发布时间
        timestamp = None
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            timestamp = time.mktime(entry.published_parsed)
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            timestamp = time.mktime(entry.updated_parsed)

        return Webpage(
            title=getattr(entry, 'title', '无标题'),
            url=getattr(entry, 'link', ''),
            timestamp=timestamp,
            summary=getattr(entry, 'description', ''),
            content=None  # 将在_fetch中填充
        )

    def _filter_by_keywords(self, webpage: Webpage) -> bool:
        """根据关键词过滤条目"""
        if not self.keywords:
            return True

        content = f"{webpage['title']} {webpage['summary']}".lower()
        return any(keyword.lower() in content for keyword in self.keywords)

    def _remove_duplicates(self, entries: List[Webpage]) -> List[Webpage]:
        """基于标题和URL去重"""
        seen = set()
        unique_entries = []

        for entry in entries:
            identifier = f"{entry['title'][:50]}_{entry['url']}"
            if identifier not in seen:
                seen.add(identifier)
                unique_entries.append(entry)

        return unique_entries

    async def _fetch(self, client: httpx.AsyncClient, webpage: Webpage) -> Webpage:
        """异步获取网页内容并提取正文"""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        }

        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    await asyncio.sleep(1 * attempt)

                logger.debug(f"🔍 尝试 {attempt + 1}/{self.max_retries} 提取内容: {webpage['url']}")

                response = await client.get(webpage["url"], headers=headers, timeout=self.timeout)
                response.raise_for_status()

                # 使用BeautifulSoup提取正文
                content = await self._extract_article_content(response.text)
                webpage["content"] = content
                return webpage

            except httpx.TimeoutException:
                logger.warning(f"⏰ 内容提取超时: {webpage['url']}")
            except Exception as e:
                logger.error(f"❌ 内容提取失败: {webpage['url']} - {str(e)}")

        # 所有尝试都失败，使用摘要作为fallback
        webpage["content"] = webpage.get("summary", "")
        return webpage

    async def _extract_article_content(self, html: str) -> str:
        """提取文章正文内容"""
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # 方法1: 查找BBC特定的数据属性
            text_blocks = soup.find_all('div', {'data-component': 'text-block'})
            paragraphs = []
            for block in text_blocks:
                for p in block.find_all('p'):
                    text = p.get_text(strip=True)
                    if text and len(text) > 10:
                        paragraphs.append(text)

            if paragraphs:
                return '\n'.join(paragraphs)

            # 方法2: 查找article body
            article_body = soup.find('article') or soup.find('div', class_=re.compile(r'story-body|article-body'))
            if article_body:
                paragraphs = []
                for p in article_body.find_all('p'):
                    text = p.get_text(strip=True)
                    if text and len(text) > 10:
                        paragraphs.append(text)
                if paragraphs:
                    return '\n'.join(paragraphs)

            # 方法3: 备用内容提取
            return self._extract_fallback_content(soup)

        except Exception as e:
            logger.error(f"❌ 内容解析失败: {str(e)}")
            return ""

    def _extract_fallback_content(self, soup) -> str:
        """备用内容提取方法"""
        main_content = soup.find('main') or soup.find('div', id=re.compile(r'content|main'))
        paragraphs = []

        search_area = main_content if main_content else soup

        for p in search_area.find_all('p'):
            text = p.get_text(strip=True)
            if (len(text) > 50 and
                    not any(tag in p.parent.get('class', []) for tag in ['nav', 'footer', 'sidebar', 'ad']) and
                    not any(tag in p.get('class', []) for tag in ['caption', 'credit', 'byline'])):
                paragraphs.append(text)

        return '\n'.join(paragraphs) if paragraphs else ""

    def _preprocess(self, webpage: Webpage) -> Webpage:
        """预处理网页内容（如果需要进一步处理可以在这里实现）"""
        # 这里可以添加额外的预处理逻辑
        # 例如：清理文本、提取关键信息等
        return webpage