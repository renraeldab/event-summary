"""Implement entity extractor and sub-theme generator based on simple LLM JSON output."""
from typing import Any
import json

from ..models import DataManager, Processor, Webpage, Entity, SubTheme
from ..utils import OpenAICompatible

EXTRACTOR_SYS_PROMPT = """# Task

Extract entities from the given document, and update the existing entities.
- Valid entity types and their schemas will be given.
- The existing entities will be given along with a new document and a query.
- You should output the complete entity list after updated.
- Significant events should be summarized and extracted.
- Your goal is to maintain the entity list so that:
    - All entities are important and relevant to the query.
    - The number of entities is under controll and there is no duplication.

# Entity Definition

```python
class Person(TypedDict):
    type: Literal["Person"]
    name: str
    description: str


class Creature(TypedDict):
    type: Literal["Creature"]
    name: str
    description: str


class Organization(TypedDict):
    type: Literal["Organization"]
    name: str
    description: str


class Location(TypedDict):
    type: Literal["Location"]
    name: str
    description: str


class Concept(TypedDict):
    type: Literal["Concept"]
    name: str
    description: str


class Method(TypedDict):
    type: Literal["Method"]
    name: str
    description: str


class Artifact(TypedDict):
    type: Literal["Artifact"]
    name: str
    description: str


class Event(TypedDict):
    type: Literal["Event"]
    name: str
    description: str
    time: str   # prefer YYYY-MM-DD if the event took place on a specific day
```"""
EXTRACTOR_USER_PROMPT = """ # Query

{query}

# Document

<DOCUMENT START>
{document}
<DOCUMENT END>

# Current Entities

```json
{entities_json}
```

Return the full updated entity list in JSON. DO NOT output anything else."""
generator_prompt = ""


class LLMProcessor(Processor):
    def __init__(
        self,
        query: str,
        data_manager: DataManager,
        client: OpenAICompatible,
        batch_size: int = 1,
        n_processors: int = 1
    ):
        super().__init__(query, data_manager, batch_size, n_processors)
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


def check_entity(entity: Any) -> None:
    assert isinstance(entity, dict), f"The entity should be dict instead of {type(entity)}."
    assert "type" in entity, "Missing field: type."
    assert "name" in entity, "Missing field: name."
    assert "description" in entity, "Missing field: description."
    entity_types = ("Person", "Creature", "Organization", "Location", "Event", "Concept", "Method", "Artifact")
    assert entity["type"] in entity_types, f"Invalid entity type: {entity['type']}. Valid types: {entity_types}."
    if entity["type"] == "Event":
        assert "time" in entity, f"Missing filed for event {entity['name']}: time."


class BaselineExtractor(LLMProcessor):
    """Simple solution, not scalable (can be really slow and expensive)."""

    processor_type = "extractor"

    def __init__(self, query: str, data_manager: DataManager, client: OpenAICompatible):
        super().__init__(query, data_manager, client)
    
    async def _update_entities(self, messages: list[dict]) -> tuple[list[Entity], list[dict] | None]:
        message = await self.get_message(messages)
        messages.append({"role": "assistant", "content": message.content})
        # remove markdown code block
        text = message.content.strip("```")
        if text.startswith("json"):
            text = text.lstrip("json")
        try:
            entities = json.loads(text)
        except json.JSONDecodeError as e:
            messages.append({"role": "user", "content": f"JSONDecodeError: {e} Try again."})
            return [], messages
        if not isinstance(entities, list):
            messages.append({"role": "user", "content": "The JSON object is not a list. Try again."})
            return [], messages
        for entity in entities:
            try:
                check_entity(entity)
            except AssertionError as e:
                messages.append({"role": "user", "content": f"{e} Try again."})
                return [], messages
        return entities, None
    
    async def _process(self, webpages: list[Webpage]) -> list[Entity]:
        retries = 0
        user_prompt = EXTRACTOR_USER_PROMPT.format(
            query=self.query,
            document=webpages[0]["content"],
            entities_json=json.dumps(list(self.data_manager.entities.values()), indent=4, ensure_ascii=False)
        )
        messages = [
            {"role": "system", "content": EXTRACTOR_SYS_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        while True:
            if retries >= 3:
                raise Exception("The LLM keeps failing to generate a valid output.")
            entities, messages = await self._update_entities(messages)
            if messages is not None:
                retries += 1
                continue
            break
        return entities


class BaselineGenerator(LLMProcessor):
    processor_type = "generator"

    def __init__(self, query, data_manager: DataManager, client: OpenAICompatible):
        super().__init__(query, data_manager, client)
    
    async def _process(self, webpages: list[Webpage]) -> list[SubTheme]:
        message = await self.get_message([{"role": "user", "content": ""}])
        raise NotImplementedError
