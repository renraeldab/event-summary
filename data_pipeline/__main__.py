import os
import argparse
import asyncio

from dotenv import load_dotenv

from data_pipeline.models import DataManager, Retriever
from data_pipeline.crawling import Metaso


# read variables from .env
load_dotenv()
metaso_api_key = os.environ.get("METASO_API_KEY")


if __name__ == "__main__":
    # parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("query", type=str, help="A topic or an event.")
    parser.add_argument("--metaso_api_key", type=str, help="Metaso API key.")
    args = parser.parse_args()
    query = args.query
    # overwrite .env
    if args.metaso_api_key:
        metaso_api_key = args.metaso_api_key
    # main
    data_manager = DataManager()
    retrievers: list[Retriever] = []
    if metaso_api_key:
        retrievers.append(Metaso(metaso_api_key, query, data_manager))  # haven't include timestamp input yet
    
    async def retrieve_all():
        await asyncio.gather(*[retriever.retrieve() for retriever in retrievers])
    
    asyncio.run(retrieve_all())
    data_manager.to_file(f"data/{query}.json")
