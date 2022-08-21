from typing import Optional
from pydantic import Field

from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class GenericModule(ContentItem):
    description: str
    definition_id: Optional[str] = Field(alias='definitionId')
