from pathlib import Path

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import JSONContentItemParser


class GenericTypeParser(JSONContentItemParser, content_type=ContentTypes.GENERIC_TYPE):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.definition_id = self.json_data.get('definitionId')

        self.connect_to_dependencies()

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.GENERIC_TYPE

    def connect_to_dependencies(self) -> None:
        if layout := self.json_data.get('layout'):
            self.add_dependency(layout, ContentTypes.LAYOUT)
