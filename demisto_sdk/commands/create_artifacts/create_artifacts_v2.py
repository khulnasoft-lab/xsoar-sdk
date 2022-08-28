from pathlib import Path
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.content_graph_commands import (create_content_graph,
                                                                       load_content_graph,
                                                                       marshal_content_graph,
                                                                       )
from demisto_sdk.commands.content_graph.objects.repository import Repository


class ContentArtifactManager:

    def __init__(self,
                 marketplace: MarketplaceVersions,
                 output: Path) -> None:
        self.marketplace = marketplace
        self.output = output

    def create_artifacts(self) -> None:
        repo: Repository = marshal_content_graph(marketplace=self.marketplace)
        repo.dump(self.output, self.marketplace)
