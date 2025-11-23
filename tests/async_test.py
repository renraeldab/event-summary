import sys
from pathlib import Path
import asyncio
import random
import string
import time

import httpx

sys.path.append(str(Path(__file__).resolve().parent.parent))

from data_pipeline.models import Retriever, Webpage, DataManager, Processor, SubTheme, Entity


class TestRetriever(Retriever):
    def __init__(self, query: str, data_manager: DataManager):
        super().__init__(query, data_manager, max_concurrent=1, wait_fixed=random.uniform(0., 0.5))
        self.name = query
    
    def _get_entries(self) -> None:
        count = random.randint(5, 20)
        chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
        for _ in range(count):
            self.entries.append(Webpage(
                title="",
                url=''.join(random.choice(chars) for _ in range(6)),
                timestamp=None,
                summary=None,
                content="xxx"
            ))
        time.sleep(random.uniform(0.1, 0.5))

    async def _filter(self) -> None:
        time.sleep(random.uniform(0.01, 0.1))
        for _ in self.entries:
            await asyncio.sleep(random.uniform(0.1, 0.2))

    async def _fetch(self, client: httpx.AsyncClient, webpage: Webpage) -> Webpage:
        await asyncio.sleep(1)
        return webpage

    async def _preprocess(self, webpage: Webpage) -> Webpage:
        await asyncio.sleep(0.5)
        return webpage


class TestGenerator(Processor):
    processor_type = "generator"

    def __init__(self, data_manager):
        super().__init__(data_manager, 2, 1)
        self.chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
    
    def _generate_sub_theme(self) -> SubTheme:
        title = ''.join(random.choice(self.chars) for _ in range(6))
        # we can read sub_themes safely because n_processors = 1
        while title in self.data_manager.sub_themes:
            title = ''.join(random.choice(self.chars) for _ in range(6))
        return SubTheme(title=title, content="")
    
    async def _process(self, webpages: list[Webpage]) -> list[SubTheme]:
        """Return one unique sub-theme."""
        await asyncio.sleep(3)
        sub_theme = self._generate_sub_theme()
        sub_theme["content"] = f"Consumed {len(webpages)} webpages."
        return [sub_theme]


class TestExtractor(Processor):
    processor_type = "extractor"

    def __init__(self, data_manager):
        super().__init__(data_manager, 2, 2)
        self.entity_types = [
            "Person",
            "Creature",
            "Organization",
            "Location",
            "Event",
            "Concept",
            "Method",
            "Artifact"
        ]
        self.chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
    
    def _generate_entity(self) -> Entity:
        entity_type = random.choice(self.entity_types)
        entity = {
            "name": ''.join(random.choice(self.chars) for _ in range(4)),
            "description": "xxx",
            "type": entity_type
        }
        if entity_type == "Event":
            entity["start_time"] = "xxx"
            entity["end_time"] = "xxx"
        return entity
    
    async def _process(self, webpages: list[Webpage]) -> list[Entity]:
        """Return three entities (may override existing entities)."""
        await asyncio.sleep(3)
        entities = []
        for _ in range(4):
            entity = self._generate_entity()
            entity["description"] = f"Consumed {len(webpages)} webpages."
            entities.append(entity)
        return entities


if __name__ == "__main__":
    data_manager = DataManager()
    retrievers = [TestRetriever(f"test {i}", data_manager) for i in range(4)]
    processors = [TestGenerator(data_manager), TestExtractor(data_manager)]

    async def retrieve_all():
        await asyncio.gather(*[retriever.retrieve() for retriever in retrievers])
        data_manager.finish_crawling()
    
    async def main():
        await asyncio.gather(retrieve_all(), *[processor.run() for processor in processors])
    
    asyncio.run(main())
