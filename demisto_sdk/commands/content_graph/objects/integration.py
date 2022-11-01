from typing import TYPE_CHECKING, List

from demisto_sdk.commands.content_graph.objects.base_content import BaseContent

if TYPE_CHECKING:
    # avoid circular imports
    from demisto_sdk.commands.content_graph.objects.script import Script

from pydantic import Field, validator

from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.objects.integration_script import IntegrationScript


class Command(BaseContent, content_type=ContentType.COMMAND):  # type: ignore[call-arg]
    name: str

    # From HAS_COMMAND relationship
    deprecated: bool = False
    description: str = ""

    # missing attribute in DB
    node_id: str = ""
    object_id: str = Field("", alias="id")

    @validator("id", always=True)
    def validate_id(cls, value, values):
        if value:
            return value
        return values.get("name")

    @validator("node_id", always=True)
    def validate_node_id(cls, value, values):
        if value:
            return value
        return f"{ContentType.COMMAND}:{values.get('name')}"

    def dump(self, *args) -> None:
        raise NotImplementedError()


class Integration(IntegrationScript, content_type=ContentType.INTEGRATION):  # type: ignore[call-arg]
    is_fetch: bool = False
    is_fetch_events: bool = False
    is_feed: bool = False
    category: str
    commands: List[Command] = Field([], exclude=True)

    @property
    def imports(self) -> List["Script"]:
        return [
            r.content_item  # type: ignore[misc]
            for r in self.relationships_data
            if r.relationship_type == RelationshipType.IMPORTS and r.content_item == r.target
        ]

    def set_commands(self):
        commands = [
            Command(
                # the related to has to be a command
                name=r.content_item.name,  # type: ignore[union-attr]
                marketplaces=r.content_item.marketplaces,
                deprecated=r.deprecated,
                description=r.description,
            )
            for r in self.relationships_data
            if r.is_direct and r.relationship_type == RelationshipType.HAS_COMMAND
        ]
        self.commands = commands

    def metadata_fields(self):
        return {
            "name": True,
            "description": True,
            "category": True,
            "commands": {"name": True, "description": True},
        }
