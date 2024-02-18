import os

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.git_util import GitUtil
from pathlib import Path
from demisto_sdk.commands.common.constants import PACKS_DIR, FileType_ALLOWED_TO_DELETE, TESTS_DIR, UTILS_DIR
from demisto_sdk.commands.common.tools import find_type
from demisto_sdk.commands.common.files.file import File
from demisto_sdk.commands.common.files.errors import FileReadError
from demisto_sdk.commands.common.constants import DEMISTO_GIT_PRIMARY_BRANCH


GIT_UTIL = GitUtil.from_content_path()


def is_file_allowed_allowed_to_be_deleted_(file_path: Path) -> bool:
    file_path = str(file_path)

    try:
        file_content = File.read_from_git_path(file_path)
    except FileReadError as error:
        logger.warning(
            f'Could not read file {file_path} from git, error: {error}\ntrying to read {file_path} from github'
        )
        file_content = File.read_from_github_api(file_path, verify_ssl=True if os.getenv("CI") else False)

    if file_type := find_type(file_path, file_content):
        return file_type in FileType_ALLOWED_TO_DELETE

    return True


def is_file_allowed_to_be_deleted(file_path: Path) -> bool:
    """
    Args:
        file_path: The file path.

    Returns: True if the file allowed to be deleted, else False.

    """
    if not set(file_path.absolute().parts).intersection({PACKS_DIR, TESTS_DIR, UTILS_DIR}):
        # if the file is not under Packs/Tests/Utils folder, allow to delete it
        return True

    return is_file_allowed_allowed_to_be_deleted_(file_path)


def validate_deleted_files():
    deleted_files = GIT_UTIL.deleted_files(DEMISTO_GIT_PRIMARY_BRANCH)

    invalid_deleted_files = [
        str(file_path) for file_path in deleted_files if not is_file_allowed_to_be_deleted(file_path)
    ]
    if invalid_deleted_files:
        logger.error(f'The following files cannot be deleted: {", ".join(invalid_deleted_files)}, restore them')
        return 1
    return 0


def main():
    try:
        return validate_deleted_files()
    except Exception as error:
        logger.error(f'Unexpected error occurred while validating deleted files {error}')
        raise


if __name__ == "__main__":
    SystemExit(main())