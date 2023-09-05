import os
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import List, Optional
from time import time

import typer

from demisto_sdk.commands.common.constants import (
    MarketplaceVersions,
)
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.logger import (
    logger,
    logging_setup,
)
from demisto_sdk.commands.common.tools import download_content_graph, is_external_repository, merge_graph_zips
from demisto_sdk.commands.content_graph.commands.common import recover_if_fails
from demisto_sdk.commands.content_graph.commands.create import (
    create,
    create_content_graph,
)
from demisto_sdk.commands.content_graph.common import (
    NEO4J_DATABASE_HTTP,
    NEO4J_PASSWORD,
    NEO4J_USERNAME,
)
from demisto_sdk.commands.content_graph.content_graph_builder import (
    ContentGraphBuilder,
)
from demisto_sdk.commands.content_graph.interface import ContentGraphInterface

app = typer.Typer()


@recover_if_fails
def update_content_graph(
    content_graph_interface: ContentGraphInterface,
    marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
    use_git: bool = False,
    imported_path: Optional[Path] = None,
    use_current: bool = False,
    packs_to_update: Optional[List[str]] = None,
    dependencies: bool = True,
    output_path: Optional[Path] = None,
) -> None:
    """This function updates a new content graph database in neo4j from the content path
    Args:
        content_graph_interface (ContentGraphInterface): The content graph interface.
        marketplace (MarketplaceVersions): The marketplace to update.
        use_git (bool): Whether to use git to get the packs to update.
        imported_path (Path): The path to the imported graph.
        use_current (bool): Whether to use the current graph.
        packs_to_update (List[str]): The packs to update.
        dependencies (bool): Whether to create the dependencies.
        output_path (Path): The path to export the graph zip to.
    """
    packs_to_update = list(packs_to_update) if packs_to_update else []
    builder = ContentGraphBuilder(content_graph_interface)
    if not use_current:
        content_graph_interface.clean_import_dir()
        if not imported_path:
            # getting the graph from remote, so we need to clean the import dir
            try:
                extract_remote_import_files(content_graph_interface)
            except RuntimeError as e:
                logger.warning(
                    "Failed to download the content graph, recreating it instead"
                )
                logger.debug(f"Runtime Error: {e}", exc_info=True)
                create_content_graph(
                    content_graph_interface, marketplace, dependencies, output_path
                )
                return
    if imported_path and not content_graph_interface.import_graph(imported_path):
        logger.warning("Failed to import the content graph, will create a new graph")
        create_content_graph(
            content_graph_interface, marketplace, dependencies, output_path
        )
        return

    if use_git and (commit := content_graph_interface.commit):
        packs_to_update.extend(GitUtil().get_all_changed_pack_ids(commit))

    # If we're running from an external/private repository
    # we want to merge the graph in storage with the 
    # private repo graph as some resources in the private repo
    # might be dependent on core packs or other packs in the marketplace
    if not imported_path and is_external_repository():
        logger.info("Running from external repository, need to merge graphs...")
        with TemporaryDirectory() as storage_dir, TemporaryDirectory() as local_dir, TemporaryDirectory() as target_dir:

            # We need to export both the local repo graph and the one from storage
            # into 1 zip which we use to import into the current content graph.

            create_content_graph(content_graph_interface, marketplace, dependencies, Path(local_dir))
            logger.info(f"Downloading storage content graph to {storage_dir}...")
            storage_zip = download_content_graph(output_path=Path(storage_dir), marketplace=MarketplaceVersions.XSOAR)
            logger.info(f"Finished downloading the content graph from storage to {storage_zip}")

            target_zip = os.path.join(target_dir, "merged.zip")
            local_zip = os.path.join(local_dir, f"{marketplace}.zip")

            logger.info(f"Merging graph zips {storage_zip} and {local_zip} and saving to '{target_zip}'...")
            merge_start_time = time()
            merge_graph_zips(local_zip, storage_zip, target_zip)
            # Attempt to import the merged graph
            # If the importing the merged graph fails, we import the local repo graph instead
            if content_graph_interface.import_graph(imported_path=Path(target_zip)):
                logger.info(f"Successfully merged storage graph with local repo graph, took {int(time() - merge_start_time)}s")
            else:
                logger.info(f"Failed to merge storage graph with local repo graph, took {int(time() - merge_start_time)}s. Falling-back to local graph...")
                content_graph_interface.import_graph(imported_path=Path(local_dir))
            return

    if packs_to_update:
        packs_str = "\n".join([f"- {p}" for p in packs_to_update])
        logger.info(f"Updating the following packs:\n{packs_str}")
        builder.update_graph(packs_to_update)

    if dependencies:
        content_graph_interface.create_pack_dependencies()
    if output_path:
        output_path = output_path / marketplace.value
    content_graph_interface.export_graph(output_path)
    logger.info(
        f"Successfully updated the content graph. UI representation is available at {NEO4J_DATABASE_HTTP} "
        f"(username: {NEO4J_USERNAME}, password: {NEO4J_PASSWORD})"
    )


@app.command(
    no_args_is_help=True,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def update(
    ctx: typer.Context,
    use_git: bool = typer.Option(
        False,
        "-g",
        "--use-git",
        is_flag=True,
        help="If true, uses git to determine the packs to update.",
    ),
    marketplace: MarketplaceVersions = typer.Option(
        MarketplaceVersions.XSOAR,
        "-mp",
        "--marketplace",
        help="The marketplace to generate the graph for.",
    ),
    use_current: bool = typer.Option(
        False,
        "-uc",
        "--use-current",
        is_flag=True,
        help="Whether to use the current content graph to update.",
    ),
    imported_path: Path = typer.Option(
        None,
        "-i",
        "--imported-path",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
        help="Path to content graph zip file to import.",
    ),
    packs_to_update: Optional[List[str]] = typer.Option(
        None,
        "-p",
        "--packs",
        help="A comma-separated list of packs to update.",
    ),
    no_dependencies: bool = typer.Option(
        False,
        "-nd",
        "--no-dependencies",
        is_flag=True,
        help="Whether or not to include dependencies in the graph.",
    ),
    output_path: Path = typer.Option(
        None,
        exists=True,
        dir_okay=True,
        file_okay=False,
        resolve_path=True,
        help="Output folder to locate the zip file of the graph exported file.",
    ),
    console_log_threshold: str = typer.Option(
        "INFO",
        "-clt",
        "--console-log-threshold",
        help=("Minimum logging threshold for the console logger."),
    ),
    file_log_threshold: str = typer.Option(
        "DEBUG",
        "-flt",
        "--file-log-threshold",
        help=("Minimum logging threshold for the file logger."),
    ),
    log_file_path: str = typer.Option(
        "demisto_sdk_debug.log",
        "-lp",
        "--log-file-path",
        help=("Path to the log file. Default: ./demisto_sdk_debug.log."),
    ),
) -> None:
    """
    Downloads the official content graph, imports it locally,
    and updates it with the changes in the given repository
    or by an argument of packs to update with.
    """
    if os.getenv("DEMISTO_SDK_GRAPH_FORCE_CREATE"):
        logger.info("DEMISTO_SDK_GRAPH_FORCE_CREATE is set. Will create a new graph")
        ctx.invoke(
            create,
            ctx,
            marketplace=marketplace,
            no_dependencies=no_dependencies,
            output_path=output_path,
            console_log_threshold=console_log_threshold,
            file_log_threshold=file_log_threshold,
            log_file_path=log_file_path,
        )
        return
    logging_setup(
        console_log_threshold=console_log_threshold,
        file_log_threshold=file_log_threshold,
        log_file_path=log_file_path,
    )
    with ContentGraphInterface() as content_graph_interface:
        update_content_graph(
            content_graph_interface,
            marketplace=marketplace,
            use_git=use_git,
            imported_path=imported_path,
            use_current=use_current,
            packs_to_update=list(packs_to_update) if packs_to_update else [],
            dependencies=not no_dependencies,
            output_path=output_path,
        )


def extract_remote_import_files(
    content_graph_interface: ContentGraphInterface,
) -> None:
    """Get or create a content graph.
    If the graph is not in the bucket or there are network issues,
    it will create a new one.

    Args:
        content_graph_interface (ContentGraphInterface)
        builder (ContentGraphBuilder)

    """
    try:
        with NamedTemporaryFile() as temp_file:
            official_content_graph = download_content_graph(
                Path(temp_file.name),
            )
            content_graph_interface.move_to_import_dir(official_content_graph)
    except Exception as e:
        raise RuntimeError("Failed to download the content graph") from e
