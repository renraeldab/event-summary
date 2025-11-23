import os
import argparse
import asyncio

from dotenv import load_dotenv

from data_pipeline.models import DataManager, Retriever, Processor
from data_pipeline.crawling import Metaso, DDGS, CurrentsAPI, RSS


# read variables from .env
load_dotenv()
metaso_api_key = os.environ.get("METASO_API_KEY")
currents_api_key = os.environ.get("CURRENTS_API_KEY")


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
    
    async def retrieve_all():
        await asyncio.gather(*[retriever.retrieve() for retriever in retrievers])
        data_manager.finish_crawling()
    
    async def main():
        await asyncio.gather(retrieve_all(), *[processor.run() for processor in processors])
    
    asyncio.run(main())
    data_manager.to_file(f"data/{query}.json")
