#!/usr/bin/env python3
"""
简化版RSS爬虫测试
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_pipeline.models import DataManager
from data_pipeline.crawling.rss import RSS


async def simple_test():
    """最简单的RSS测试"""
    data_manager = DataManager()

    rss = RSS(
        query="科技新闻",
        data_manager=data_manager,
        rss_urls=["https://feeds.bbci.co.uk/news/technology/rss.xml"],
        keywords=["AI", "technology"],
        max_concurrent=2
    )

    print("开始RSS爬取...")
    await rss.retrieve()
    print(f"完成！获取了 {len(data_manager.webpages)} 个网页")

    # 保存结果
    data_manager.to_file("test_rss_output.json")
    print("结果已保存到 test_rss_output.json")


if __name__ == "__main__":
    asyncio.run(simple_test())