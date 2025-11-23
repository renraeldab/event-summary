#!/usr/bin/env python3
"""
测试RSS爬虫的独立脚本
放置位置：与crawling文件夹同级
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_pipeline.models import DataManager
from data_pipeline.crawling.rss import RSS

# BBC RSS源列表
BBC_RSS_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.bbci.co.uk/news/uk/rss.xml",
    "https://feeds.bbci.co.uk/news/politics/rss.xml",
    "https://feeds.bbci.co.uk/news/health/rss.xml",
    "https://feeds.bbci.co.uk/news/education/rss.xml",
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"
]


async def test_rss_basic():
    """测试RSS爬虫基本功能"""
    print("🧪 开始测试RSS爬虫基本功能...")

    data_manager = DataManager()

    # 创建RSS爬虫实例
    rss_crawler = RSS(
        query="科技新闻",
        data_manager=data_manager,
        rss_urls=BBC_RSS_FEEDS[:2],  # 只使用前2个源进行测试
        keywords=["AI", "artificial intelligence"],
        max_concurrent=2,
        timeout=30
    )

    # 运行爬虫
    await rss_crawler.retrieve()

    # 输出结果统计
    print(f"📊 测试结果统计:")
    print(f"   - 获取的网页数量: {len(data_manager.webpages)}")
    print(f"   - 爬虫发现的条目数: {len(rss_crawler.entries)}")

    # 显示前几个结果
    print("\n📰 前3个结果预览:")
    for i, (url, webpage) in enumerate(list(data_manager.webpages.items())[:3]):
        print(f"  title{i + 1}. {webpage['title']}")
        print(f"     来源: {url}")
        print(f"     时间戳: {webpage['timestamp']}")
        print(f"     内容长度: {len(webpage['content']) if webpage['content'] else 0} 字符")
        print(f"     摘要: {webpage['summary'][:100]}..." if webpage['summary'] else "无摘要")
        print()


async def test_rss_with_content_extraction():
    """测试RSS爬虫的内容提取功能"""
    print("\n🧪 测试RSS爬虫内容提取功能...")

    data_manager = DataManager()

    # 使用更具体的查询和关键词
    rss_crawler = RSS(
        query="BBC科技新闻",
        data_manager=data_manager,
        rss_urls=["https://feeds.bbci.co.uk/news/technology/rss.xml"],  # 只使用科技频道
        keywords=["AI", "artificial intelligence"],
        max_concurrent=1,  # 降低并发数避免被封
        timeout=60
    )

    await rss_crawler.retrieve()

    # 分析内容提取质量
    total_pages = len(data_manager.webpages)
    pages_with_content = sum(1 for webpage in data_manager.webpages.values()
                             if webpage.get('content') and len(webpage['content']) > 100)

    print(f"📊 内容提取质量分析:")
    print(f"   - 总网页数: {total_pages}")
    print(f"   - 成功提取内容的网页数: {pages_with_content}")
    print(f"   - 内容提取成功率: {pages_with_content / total_pages * 100:.1f}%")

    # 显示内容提取示例
    print("\n🔍 内容提取示例:")
    for i, (url, webpage) in enumerate(list(data_manager.webpages.items())[:2]):
        if webpage.get('content'):
            print(f"  {i + 1}. {webpage['title']}")
            print(f"     内容预览: {webpage['content'][:200]}...")
            print()


async def test_rss_error_handling():
    """测试RSS爬虫的错误处理"""
    print("\n🧪 测试RSS爬虫错误处理...")

    data_manager = DataManager()

    # 使用无效的URL测试错误处理
    invalid_feeds = [
        "https://invalid-rss-url-that-does-not-exist.com/feed.xml",
        "https://feeds.bbci.co.uk/news/technology/rss.xml"  # 保留一个有效的用于对比
    ]

    rss_crawler = RSS(
        query="错误处理测试",
        data_manager=data_manager,
        rss_urls=invalid_feeds,
        keywords=["test"],
        max_concurrent=2,
        timeout=5  # 短超时以便快速测试
    )

    await rss_crawler.retrieve()

    print(f"✅ 错误处理测试完成")
    print(f"   - 从无效源中恢复，成功获取网页数: {len(data_manager.webpages)}")


async def main():
    """运行所有测试"""
    print("🚀 开始RSS爬虫测试套件")
    print("=" * 50)

    try:
        # 测试1: 基本功能
        await test_rss_basic()

        # 测试2: 内容提取
        await test_rss_with_content_extraction()

        # 测试3: 错误处理
        await test_rss_error_handling()

        print("=" * 50)
        print("🎉 所有测试完成！")

    except Exception as e:
        print(f"💥 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 设置日志级别，减少输出噪音
    import logging

    logging.getLogger().setLevel(logging.WARNING)

    # 运行测试
    asyncio.run(main())