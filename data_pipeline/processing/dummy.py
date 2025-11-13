import asyncio
import random
import string

from ..models import Processor, Webpage, SubTheme


class DummyProcessor(Processor):
    """This class is for testing."""
    processor_type = "generator"

    def __init__(self, data_manager):
        super().__init__(data_manager, 2, 1)
        self.chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
    
    def _generate_title(self) -> str:
        return ''.join(random.choice(self.chars) for _ in range(6))
    
    async def _process(self, webpages: list[Webpage]) -> None:
        await asyncio.sleep(3)
        # unique title
        title = self._generate_title()
        # we can read sub_themes safely because n_processors = 1
        while title in self.data_manager.sub_themes:
            title = self._generate_title()
        await self.data_manager.update_sub_themes({
            title: SubTheme(title=title, content=f"Consumed {len(webpages)} webpages.")
        })
