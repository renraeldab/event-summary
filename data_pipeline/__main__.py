import os
import argparse

from dotenv import load_dotenv


# read variables from .env
load_dotenv()
api_key = os.environ.get("API_KEY")


if __name__ == "__main__":
    # parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("query", type=str, help="A topic or an event.")
    parser.add_argument("--api_key", type=str, help="API key.")
    args = parser.parse_args()
    # overwrite .env
    if args.api_key:
        api_key = args.api_key
    # main
    print("Hello from data_pipeline!")
    print(api_key)
