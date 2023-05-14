import logging
import shutil
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Iterable, List
from zipfile import ZipFile

from pydantic import DirectoryPath

from demisto_sdk.commands.common.constants import (
    MarketplaceVersions,
)
from demisto_sdk.commands.common.tools import parse_marketplace_kwargs
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.utils.utils import check_configuration_file

logger = logging.getLogger("demisto-sdk")

MULTIPLE_ZIPPED_PACKS_FILE_NAME = "uploadable_packs.zip"


def upload_content_entity(**kwargs):
    from demisto_sdk.commands.upload.uploader import ConfigFileParser, Uploader

    keep_zip = kwargs.pop("keep_zip", None)

    marketplace: MarketplaceVersions = parse_marketplace_kwargs(kwargs)

    if config_file_path := kwargs.pop("input_config_file", None):
        logger.info("Uploading files from config file")
        if input_ := kwargs.get("input"):
            logger.warning(f"[orange]The input ({input_}) will NOT be used[/orange]")

        output_zip_path = keep_zip or tempfile.mkdtemp()

        zip_multiple_packs(
            paths=ConfigFileParser(Path(config_file_path)).custom_packs_paths,
            marketplace=marketplace,
            dir=Path(output_zip_path),
        )
        kwargs["detached_files"] = True
        kwargs["input"] = Path(output_zip_path, MULTIPLE_ZIPPED_PACKS_FILE_NAME)

    check_configuration_file("upload", kwargs)

    # Here the magic happens
    upload_result = Uploader(marketplace=marketplace, **kwargs).upload()

    # Clean up
    if config_file_path and not keep_zip:
        shutil.rmtree(output_zip_path, ignore_errors=True)

    return upload_result


def zip_multiple_packs(
    paths: Iterable[Path],
    marketplace: MarketplaceVersions,
    dir: DirectoryPath,
):
    packs = []
    were_zipped: List[Path] = []

    for path in paths:
        if not path.exists():
            logger.error(f"[red]{path} does not exist, skipping[/red]")
            continue

        if path.is_file() and path.suffix == ".zip":
            were_zipped.append(path)
            continue

        pack = None
        with suppress(Exception):
            pack = BaseContent.from_path(path)
        if (pack is None) or (not isinstance(pack, Pack)):
            logger.error(f"[red]could not parse pack from {path}, skipping[/red]")
            continue
        packs.append(pack)

    result_zip_path = dir / "content_packs.zip"
    ContentDTO(packs=packs).dump(dir / "result", marketplace=marketplace, zip=True)

    with ZipFile(result_zip_path, "a") as zip_file:
        # copy files that were already zipped into the result
        for was_zipped in were_zipped:
            zip_file.write(was_zipped, was_zipped.name)

    shutil.move(  # rename
        str(result_zip_path), result_zip_path.with_name(MULTIPLE_ZIPPED_PACKS_FILE_NAME)
    )
