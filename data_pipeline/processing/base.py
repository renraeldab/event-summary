"""Implement entity extractor and sub-theme generator based on simple LLM JSON output."""
from ..models import DataManager, Processor, Webpage, Entity, SubTheme
from ..utils import OpenAICompatible

extractor_prompt = ""
generator_prompt = ""


class LLMProcessor(Processor):
    def __init__(
        self,
        data_manager: DataManager,
        client: OpenAICompatible,
        batch_size: int = 1,
        n_processors: int = 1
    ):
        super().__init__(data_manager, batch_size, n_processors)
        self.client = client
        self.total_tokens = 0
    
    async def get_message(self, messages: list[dict], **kwargs):
        completion = await self.client.chat_completions(messages=messages, **kwargs)
        message = completion.choices[0].message
        if message.content is None and message.tool_calls is None:
            raise ValueError(f"Unexpected message: {message}")
        if completion.usage:
            self.total_tokens += completion.usage.total_tokens
        return message


class BaseExtractor(LLMProcessor):
    processor_type = "extractor"

    def __init__(self, data_manager: DataManager, client: OpenAICompatible):
        super().__init__(data_manager, client)
    
    async def _process(self, webpages: list[Webpage]) -> list[Entity]:
        message = await self.get_message([{"role": "user", "content": ""}])
        raise NotImplementedError


class BaseGenerator(Processor):
    processor_type = "generator"

    def __init__(self, data_manager: DataManager, client: OpenAICompatible):
        super().__init__(data_manager, client)
    
    async def _process(self, webpages: list[Webpage]) -> list[SubTheme]:
        message = await self.get_message([{"role": "user", "content": ""}])
        raise NotImplementedError
