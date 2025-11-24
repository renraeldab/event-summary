import os
import argparse
import asyncio

from dotenv import load_dotenv

from data_pipeline.models import DataManager, Retriever, Processor
from data_pipeline.crawling import Metaso, DDGS, CurrentsAPI
from data_pipeline.processing import BaselineExtractor
from data_pipeline.utils import OpenAICompatible

# read variables from .env
load_dotenv()
metaso_api_key = os.environ.get("METASO_API_KEY")
currents_api_key = os.environ.get("CURRENTS_API_KEY")
openai_api_key = os.environ.get("OPENAI_API_KEY")
openai_base_url = os.environ.get("OPENAI_BASE_URL")
openai_model = os.environ.get("OPENAI_MODEL")

if __name__ == "__main__":
    # parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("query", type=str, help="A topic or an event.")
    parser.add_argument("--metaso_api_key", type=str, help="Metaso API key.")
    parser.add_argument("--currents_api_key", type=str, help="Currents API key.")
    args = parser.parse_args()
    query = args.query
    # overwrite .env
    if args.metaso_api_key:
        metaso_api_key = args.metaso_api_key
    if args.currents_api_key:
        currents_api_key = args.currents_api_key
    # main
    data_manager = DataManager()
    retrievers: list[Retriever] = []
    processors: list[Processor] = []
    retrievers.append(DDGS(query, data_manager))
    if metaso_api_key:
        retrievers.append(Metaso(metaso_api_key, query, data_manager))  # haven't include timestamp input yet
    if currents_api_key:
        retrievers.append(CurrentsAPI(currents_api_key, query, data_manager))
    if openai_model and (openai_base_url is not None or openai_api_key is not None):
        client = OpenAICompatible(openai_base_url, openai_api_key, openai_model, 2)
        processors.append(BaselineExtractor(query, data_manager, client))
    
    async def retrieve_all():
        await asyncio.gather(*[retriever.retrieve() for retriever in retrievers])
        data_manager.finish_crawling()
    
    async def main():
        await asyncio.gather(retrieve_all(), *[processor.run() for processor in processors])
    
    asyncio.run(main())
    data_manager.to_file(f"data/{query}.json")
