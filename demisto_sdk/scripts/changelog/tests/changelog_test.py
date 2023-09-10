from pathlib import Path

import pytest

from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.scripts.changelog import changelog
from demisto_sdk.scripts.changelog.changelog import (
    Changelog,
    clear_changelogs_folder,
    get_all_logs,
    get_new_log_entries,
    is_log_folder_empty,
    is_log_yml_exist,
    is_release,
)
from demisto_sdk.scripts.changelog.changelog_obj import LogType

yaml = YAML_Handler()


LOG_FILE_1 = {
        "logs": [{"description": "fixed an issue where test", "type": "fix"}],
        "pr_number": "12345",
    }
LOG_FILE_2 = {
        "logs": [
            {"description": "added a feature that test", "type": "feature"},
            {"description": "breaking changes: test", "type": "breaking"},
        ],
        "pr_number": "43524",
    }
LOG_FILE_3 = {
    "logs": [
            {"description": "added a feature that test", "type": "fix"},
            {"description": "breaking changes: test", "type": "internal"},
        ],
        "pr_number": "43524",
    }


@pytest.fixture
def changelog_mock():
    return Changelog(pr_name="test", pr_number="12345")

@pytest.fixture
def changelog_folder_mock(tmpdir, mocker):
    folder_path = Path(tmpdir / ".changelog")
    folder_path.mkdir()
    mocker.patch.object(changelog, "CHANGELOG_FOLDER", folder_path)
    return folder_path


@pytest.mark.parametrize(
    "pr_name, expected_result", [("", False), ("test", False), ("v1.10.2", True)]
)
def test_is_release(pr_name: str, expected_result: bool):
    """
    Given:
        - Changelog obj with some different `pr_name`
    When:
        - run the is_release method
    Then:
        - Ensure return True only if pr_name is in vX.X.X format
    """
    assert is_release(pr_name) == expected_result


def test_is_log_folder_empty(changelog_folder_mock: Path):
    """
    Given:
        - Changelog obj and a temporary path with a .changelog folder
    When:
        - run the is_log_folder_empty method
    Then:
        - Ensure return True only if there is a file in the .changelog folder
    """
    assert is_log_folder_empty()
    (changelog_folder_mock / "12345.yml").write_text("test: test")
    assert not is_log_folder_empty()


@pytest.mark.parametrize("pr_name", ("", "12345"))
def test_is_log_yml_exist(changelog_folder_mock: Path, pr_name: str):
    """
    Given:
        - Changelog obj and a temporary path with a .changelog folder
    When:
        - run the is_log_yml_exist method
    Then:
        - Ensure return True only if there is a yml file
          with the same name as pr_number in the .changelog folder
    """
    if pr_name:
        with (changelog_folder_mock / f"{pr_name}.yml").open("w") as f:
            f.write("test: test")
    assert is_log_yml_exist(pr_name) == int(bool(pr_name))


def test_get_all_logs(changelog_folder_mock: Path):
    """
    Given:
        - Tow log files
    When:
        - run `get_all_logs` function
    Then:
        - Ensure all log files are return
        - Ensure that if there are two entries in the log file
          it is returned as two entries within an `LogFileObject` object
    """
    with (changelog_folder_mock / "12345.yml").open("w") as f:
        yaml.dump(LOG_FILE_1, f)
    with (changelog_folder_mock / "43524.yml").open("w") as f:
        yaml.dump(LOG_FILE_2, f)
    log_files = get_all_logs()
    assert len(log_files) == 2
    assert len(log_files[0].logs) == 2


@pytest.mark.parametrize("pr_name", ["v2.2.2", ""])
def test_validate(mocker, changelog_mock: Changelog, pr_name: str):
    mock_validate_release = mocker.patch.object(changelog, "_validate_release")
    mock_validate_branch = mocker.patch.object(changelog, "_validate_branch")
    changelog_mock.pr_name = pr_name
    changelog_mock.validate()

    assert mock_validate_branch.call_count == int(not bool(pr_name))
    assert mock_validate_release.call_count == int(bool(pr_name))


def test_clear_changelogs_folder(changelog_folder_mock: Path):
    """
    Given:
        - A .changelog folder with a file
    When:
        - run `clear_changelogs_folder` function
    Then:
        - Ensure the .changelog folder is empty
    """
    with (changelog_folder_mock / "12345.yml").open("w") as f:
            f.write("test: test")
    clear_changelogs_folder()
    assert not any(changelog_folder_mock.iterdir())


def test_get_new_log_entries(changelog_folder_mock: Path):
    """
    Given:
        - list of LogFileObject with all types
    When:
        - run `get_new_log_entries` function
    Then:
        - Ensure a dictionary with all `LogType`s is returned
    """
    for i, log_file in enumerate((LOG_FILE_1, LOG_FILE_2, LOG_FILE_3)):
        with (changelog_folder_mock / f"{i}.yml").open("w") as f:
            yaml.dump(log_file, f)
    logs = get_all_logs()
    results = get_new_log_entries(logs)
    for type_ in LogType._member_names_[:-1]:  # exclude `initial` type
        assert type_ in results
