from functools import cached_property
from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import PARSING_RULES_DIR, MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.yaml_content_item import (
    YAMLContentItemParser,
)


class ParsingRuleParser(YAMLContentItemParser, content_type=ContentType.PARSING_RULE):
    def __init__(
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        git_sha: Optional[str] = None,
    ) -> None:
        super().__init__(path, pack_marketplaces, git_sha=git_sha)

    @cached_property
    def field_mapping(self):
        super().field_mapping.update({"object_id": "id"})
        return super().field_mapping

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.MarketplaceV2}

    @staticmethod
    def match(_dict: dict, path: str) -> bool:
        return (
            YAMLContentItemParser.match(_dict, path)
            and "rules" in _dict
            and "samples" in _dict
            and PARSING_RULES_DIR in Path(path).parts
        )
