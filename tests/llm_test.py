import os
import sys
from pathlib import Path
import asyncio

from dotenv import load_dotenv

sys.path.append(str(Path(__file__).resolve().parent.parent))

from data_pipeline.utils import OpenAICompatible

load_dotenv()
api_key = os.environ.get("OPENAI_API_KEY")
base_url = os.environ.get("OPENAI_BASE_URL")
model = os.environ.get("OPENAI_MODEL")


async def main():
    if api_key is None and base_url is None:
        return
    client = OpenAICompatible(base_url, api_key, model, 2)
    completions = await asyncio.gather(
        client.chat_completions([{"role": "user", "content": "How to find a black hole?"}]),
        client.chat_completions([{"role": "user", "content": "Write a poem about pizzas."}])
    )
    for completion in completions:
        print('=' * 100)
        print(completion.choices[0].message.content)


if __name__ == "__main__":
    asyncio.run(main())
