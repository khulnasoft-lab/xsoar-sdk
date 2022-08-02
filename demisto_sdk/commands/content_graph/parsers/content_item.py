from abc import abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, List, Union, Tuple

from demisto_sdk.commands.common.tools import (
    get_current_repo,
    get_files_in_dir,
    get_json, get_yaml,
    get_yml_paths_in_dir
)
from demisto_sdk.commands.content_graph.constants import ContentTypes, Rel, UNIFIED_FILES_SUFFIXES, MARKETPLACE_PROPERTIES
import demisto_sdk.commands.content_graph.parsers.base_content as base_content


class NotAContentItem(Exception):
    pass


class ContentItemParser(base_content.BaseContentParser):
    """ A class representation of a content item.

    Attributes:
        path (Path):
    """
    def __init__(self, path: Path) -> None:
        self.path: Path = path
        self.relationships: Dict[Tuple[ContentTypes, Rel, ContentTypes], List[Dict[str, Any]]] = {}

    @property
    @abstractmethod
    def content_item_id(self) -> str:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def content_type(self) -> ContentTypes:
        pass

    @property
    @abstractmethod
    def fromversion(self) -> str:
        pass

    @property
    @abstractmethod
    def toversion(self) -> str:
        pass

    def get_data(self) -> Dict[str, Any]:
        base_content_data: Dict[str, Any] = super().get_data()
        content_item_data: Dict[str, Any] = {
            'id': self.content_item_id,
            'name': self.name,
            'deprecated': self.deprecated,
            'fromversion': self.fromversion,
            'toversion': self.toversion,
            'source': list(get_current_repo()),
            'file_path': self.path.as_posix(),
        }

        return content_item_data | base_content_data

    @staticmethod
    def is_package(path: Path) -> bool:
        return path.is_dir()

    @staticmethod
    def is_unified_file(path: Path) -> bool:
        return path.suffix in UNIFIED_FILES_SUFFIXES

    @staticmethod
    def is_content_item(path: Path) -> bool:
        return ContentItemParser.is_package(path) or ContentItemParser.is_unified_file(path)

    def add_relationship(
        self,
        relationship: Rel,
        target_id: str,
        target_type: ContentTypes = None,
        **kwargs: Dict[str, Any],
    ) -> None:
        relationship_key: Tuple[ContentTypes, Rel, ContentTypes] = (self.content_type, relationship, target_type)
        relationship: Dict[str, Any] = {
            'source_id': self.content_item_id,
            'source_fromversion': self.fromversion,
            'source_marketplaces': self.marketplaces,
            'target_id': target_id,
        }
        relationship.update(kwargs)
        self.relationships.setdefault(relationship_key, []).append(relationship)

    def add_dependency(self, dependency_id: str, dependency_type: Optional[ContentTypes] = None, is_mandatory: bool = True) -> None:
        if dependency_type is None:
            if self.content_type == ContentTypes.SCRIPT:
                dependency_type = ContentTypes.COMMAND_OR_SCRIPT
            else:
                dependency_type = ContentTypes.BASE_CONTENT

        self.add_relationship(
            Rel.USES,
            target_id=dependency_id,
            target_type=dependency_type,
            mandatorily=is_mandatory,
        )


class YAMLContentItemParser(ContentItemParser):
    def __init__(self, path: Path, pack_marketplaces: List[str]) -> None:
        super().__init__(path)
        self.pack_marketplaces: List[str] = pack_marketplaces
        self.yml_data = self.get_yaml()

    @property
    def name(self) -> str:
        return self.yml_data.get('name')

    @property
    def deprecated(self) -> bool:
        return self.yml_data.get('deprecated', False)

    @property
    def fromversion(self) -> str:
        return self.yml_data.get('fromversion')

    @property
    def toversion(self) -> str:
        return self.yml_data.get('toversion')

    @property
    def marketplaces(self) -> List[str]:
        if not (marketplaces := self.yml_data.get('marketplaces', [])):
            return self.pack_marketplaces
        return marketplaces

    def connect_to_tests(self) -> None:
        tests_playbooks: List[str] =  self.yml_data.get('tests', [])
        for test_playbook_id in tests_playbooks:
            if 'no test' not in test_playbook_id.lower():
                self.add_relationship(
                    Rel.TESTED_BY,
                    target_id=test_playbook_id,
                    target_type=ContentTypes.TEST_PLAYBOOK,
                )

    def get_yaml(self) -> Dict[str, Union[str, List[str]]]:
        if not self.path.is_dir():
            yaml_path = self.path.as_posix()
        else:
            _, yaml_path = get_yml_paths_in_dir(self.path.as_posix())
        if not yaml_path:
            raise NotAContentItem

        return get_yaml(yaml_path)


class JSONContentItemParser(ContentItemParser):
    def __init__(self, path: Path, pack_marketplaces: List[str]) -> None:
        super().__init__(path)
        self.pack_marketplaces: List[str] = pack_marketplaces
        self.json_data: Dict[str, Any] = self.get_json()

    @property
    def content_item_id(self) -> str:
        return self.json_data.get('id')

    @property
    def name(self) -> str:
        return self.json_data.get('name')

    @property
    def deprecated(self) -> bool:
        return self.json_data.get('deprecated', False)

    @property
    def fromversion(self) -> str:
        return self.json_data.get('fromVersion')

    @property
    def toversion(self) -> str:
        return self.json_data.get('toVersion', '')

    @property
    def marketplaces(self) -> List[str]:
        if not (marketplaces := self.json_data.get('marketplaces', [])):
            return self.pack_marketplaces
        return marketplaces
    
    def get_json(self) -> Dict[str, Any]:
        if self.path.is_dir():
            json_files_in_dir = get_files_in_dir(self.path.as_posix(), ['json'], False)
            if len(json_files_in_dir) != 1:
                raise NotAContentItem(f'Directory {self.path} must have a single JSON file.')
            self.path = Path(json_files_in_dir[0])
        return get_json(self.path.as_posix())
