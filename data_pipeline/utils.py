import asyncio
import openai


class OpenAICompatible:
    """
    A simple wrapper class for AsyncOpenAI that uses a semaphore to limit the number of concurrent requests.
    """

    def __init__(
        self,
        base_url: str | None,
        api_key: str | None,
        model: str | None = None,
        max_concurrent: int = 1
    ):
        self.client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.model = model

    async def chat_completions(self, messages: list[dict], model: str | None = None, **kwargs):
        if model is None and self.model is None:
            raise ValueError("Model is None.")
        async with self.semaphore:
            return await self.client.chat.completions.create(messages=messages, model=self.model, **kwargs)
