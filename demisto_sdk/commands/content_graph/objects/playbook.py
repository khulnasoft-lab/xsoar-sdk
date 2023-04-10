from typing import Callable, Optional, Set

import demisto_client

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Playbook(ContentItem, content_type=ContentType.PLAYBOOK):  # type: ignore[call-arg]
    def metadata_fields(self) -> Set[str]:
        return {"name", "description"}

    def _client_upload_method(self, client: demisto_client) -> Optional[Callable]:
        return client.import_playbook
