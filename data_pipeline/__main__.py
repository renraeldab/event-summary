import os
import argparse
import asyncio

from dotenv import load_dotenv

from data_pipeline.models import DataManager, Retriever, Processor
from data_pipeline.crawling import Metaso,  RSS
from data_pipeline.processing import DummyProcessor

# read variables from .env
load_dotenv()
metaso_api_key = os.environ.get("METASO_API_KEY")

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

if __name__ == "__main__":
    # parse args
    parser = argparse.ArgumentParser(description="数据爬取和处理管道")
    parser.add_argument("query", type=str, help="搜索主题或事件")
    parser.add_argument("--metaso_api_key", type=str, help="Metaso API密钥")
    parser.add_argument("--use_rss", action="store_true", help="启用RSS爬虫")
    parser.add_argument("--rss_keywords", type=str, nargs="+", help="RSS关键词过滤", default=["China", "Chinese"])
    parser.add_argument("--rss_feeds", type=str, nargs="+", help="自定义RSS源", default=BBC_RSS_FEEDS)
    parser.add_argument("--max_concurrent", type=int, default=5, help="最大并发数")

    args = parser.parse_args()
    query = args.query

    # 覆盖.env配置
    if args.metaso_api_key:
        metaso_api_key = args.metaso_api_key

    # 初始化数据管理器
    data_manager = DataManager()
    retrievers: list[Retriever] = []
    processors: list[Processor] = [DummyProcessor(data_manager)]

    # 添加DDGS爬虫
    retrievers.append(DDGS(
        query,
        data_manager,
        max_concurrent=args.max_concurrent
    ))

    # 添加Metaso爬虫（如果提供了API密钥）
    if metaso_api_key:
        retrievers.append(Metaso(
            metaso_api_key,
            query,
            data_manager,
            max_concurrent=args.max_concurrent
        ))

    # 添加RSS爬虫（如果启用）
    if args.use_rss:
        retrievers.append(RSS(
            query=query,
            data_manager=data_manager,
            rss_urls=args.rss_feeds,
            keywords=args.rss_keywords,
            max_concurrent=args.max_concurrent
        ))
        print(f"✅ RSS爬虫已启用，使用关键词: {args.rss_keywords}")


    async def retrieve_all():
        """并发执行所有爬虫"""
        await asyncio.gather(*[retriever.retrieve() for retriever in retrievers])
        data_manager.finish_crawling()
        print("✅ 所有爬虫任务完成")


    async def main():
        """主异步函数"""
        await asyncio.gather(
            retrieve_all(),
            *[processor.run() for processor in processors]
        )


    # 运行主程序
    print(f"🚀 开始处理查询: {query}")
    print(f"📊 使用爬虫: {[type(r).__name__ for r in retrievers]}")

    asyncio.run(main())

    # 保存结果
    output_file = f"data/{query.replace(' ', '_')}.json"
    data_manager.to_file(output_file)
    print(f"💾 结果已保存至: {output_file}")

    # 输出统计信息
    print(f"📈 统计信息:")
    print(f"   - 网页数量: {len(data_manager.webpages)}")
    print(f"   - 实体数量: {len(data_manager.entities)}")
    print(f"   - 子主题数量: {len(data_manager.sub_themes)}")