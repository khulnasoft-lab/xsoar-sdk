import builtins
import logging
import os
import shutil
from io import TextIOWrapper
from pathlib import Path
from typing import Callable, Tuple
from unittest.mock import patch

import demisto_client
import pytest
from urllib3.response import HTTPResponse

from demisto_sdk.commands.common.constants import (
    CONTENT_ENTITIES_DIRS,
    JOBS_DIR,
    LAYOUTS_DIR,
    LISTS_DIR,
    PRE_PROCESS_RULES_DIR,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.tests.tools_test import SENTENCE_WITH_UMLAUTS
from demisto_sdk.commands.download.downloader import *
from TestSuite.test_tools import str_in_call_args_list

TEST_DATA_FOLDER = Path.cwd() / "tests_data"


def ordered(obj: dict | list) -> dict | list:
    """
    Order a nested list / dict for comparison in tests

    Args:
        obj (dict | list): A nested list / dict to order.

    Returns:
        dict | list: The same nested list / dict, but ordered.
    """
    if isinstance(obj, dict):
        return {key: ordered(value) for key, value in obj.items()}

    if isinstance(obj, list):
        return sorted(obj, key=lambda x: str(x))


class Environment:
    """
    Environment is class designed to spin up a virtual, temporary content repo and build all objects related to
    the Downloader (such as pack content & custom content)
    """
    def __init__(self, tmp_path):
        self.tmp_path = Path(tmp_path)
        tests_path: Path = self.tmp_path / "tests"
        tests_env_path: Path = tests_path / "tests_env"
        tests_data_path: Path = tests_path / "tests_data"
        shutil.copytree(
            src=(Path.cwd() / "tests_env"), dst=str(tests_env_path)
        )
        shutil.copytree(
            src=(Path.cwd() / "tests_data"),
            dst=str(tests_data_path),
        )

        self.CONTENT_BASE_PATH = tests_path / "tests_env" / "content"
        self.CUSTOM_CONTENT_BASE_PATH = tests_path / "tests_data" / "custom_content"
        self.PACK_INSTANCE_PATH = self.CONTENT_BASE_PATH / "Packs" / "TestPack"
        self.INTEGRATION_INSTANCE_PATH = self.PACK_INSTANCE_PATH / "Integrations" / "TestIntegration"
        self.SCRIPT_INSTANCE_PATH = self.PACK_INSTANCE_PATH / "Scripts" / "TestScript"
        self.PLAYBOOK_INSTANCE_PATH = self.PACK_INSTANCE_PATH / "Playbooks" / "playbook-DummyPlaybook.yml"
        self.LAYOUT_INSTANCE_PATH = self.PACK_INSTANCE_PATH / "Layouts" / "layout-details-TestLayout.json"
        self.LAYOUTSCONTAINER_INSTANCE_PATH = self.PACK_INSTANCE_PATH / "Layouts" / "layoutscontainer-mytestlayout.json"
        self.PRE_PROCESS_RULES_INSTANCE_PATH = self.PACK_INSTANCE_PATH / "PreProcessRules/preprocessrule-dummy.json"
        self.LISTS_INSTANCE_PATH = self.PACK_INSTANCE_PATH / "Lists" / "list-dummy.json"
        self.JOBS_INSTANCE_PATH = self.PACK_INSTANCE_PATH / "Jobs" / "job-sample.json"
        self.CUSTOM_CONTENT_SCRIPT_PATH = self.CUSTOM_CONTENT_BASE_PATH / "automation-TestScript.yml"
        self.CUSTOM_CONTENT_INTEGRATION_PATH = self.CUSTOM_CONTENT_BASE_PATH / "integration-Test_Integration.yml"
        self.CUSTOM_CONTENT_LAYOUT_PATH = self.CUSTOM_CONTENT_BASE_PATH / "layout-details-TestLayout.json"
        self.CUSTOM_CONTENT_PLAYBOOK_PATH = self.CUSTOM_CONTENT_BASE_PATH / "playbook-DummyPlaybook.yml"
        self.CUSTOM_CONTENT_JS_INTEGRATION_PATH = self.CUSTOM_CONTENT_BASE_PATH/ "integration-DummyJSIntegration.yml"
        self.CUSTOM_API_RESPONSE = self.CUSTOM_CONTENT_BASE_PATH / "api-response"

        self.INTEGRATION_PACK_OBJECT = {
            "Test Integration": [
                {
                    "name": "Test Integration",
                    "id": "Test Integration",
                    "path": f"{self.INTEGRATION_INSTANCE_PATH}/TestIntegration.py",
                    "file_extension": "py",
                },
                {
                    "name": "Test Integration",
                    "id": "Test Integration",
                    "path": f"{self.INTEGRATION_INSTANCE_PATH}/TestIntegration_testt.py",
                    "file_extension": "py",
                },
                {
                    "name": "Test Integration",
                    "id": "Test Integration",
                    "path": f"{self.INTEGRATION_INSTANCE_PATH}/TestIntegration.yml",
                    "file_extension": "yml",
                },
                {
                    "name": "Test Integration",
                    "id": "Test Integration",
                    "path": f"{self.INTEGRATION_INSTANCE_PATH}/TestIntegration_image.png",
                    "file_extension": "png",
                },
                {
                    "name": "Test Integration",
                    "id": "Test Integration",
                    "path": f"{self.INTEGRATION_INSTANCE_PATH}/CHANGELOG.md",
                    "file_extension": "md",
                },
                {
                    "name": "Test Integration",
                    "id": "Test Integration",
                    "path": f"{self.INTEGRATION_INSTANCE_PATH}/TestIntegration_description.md",
                    "file_extension": "md",
                },
                {
                    "name": "Test Integration",
                    "id": "Test Integration",
                    "path": f"{self.INTEGRATION_INSTANCE_PATH}/README.md",
                    "file_extension": "md",
                },
            ]
        }
        self.SCRIPT_PACK_OBJECT = {
            "TestScript": [
                {
                    "name": "TestScript",
                    "id": "TestScript",
                    "path": f"{self.SCRIPT_INSTANCE_PATH}/TestScript.py",
                    "file_extension": "py",
                },
                {
                    "name": "TestScript",
                    "id": "TestScript",
                    "path": f"{self.SCRIPT_INSTANCE_PATH}/TestScript.yml",
                    "file_extension": "yml",
                },
                {
                    "name": "TestScript",
                    "id": "TestScript",
                    "path": f"{self.SCRIPT_INSTANCE_PATH}/CHANGELOG.md",
                    "file_extension": "md",
                },
                {
                    "name": "TestScript",
                    "id": "TestScript",
                    "path": f"{self.SCRIPT_INSTANCE_PATH}/README.md",
                    "file_extension": "md",
                },
            ]
        }
        self.PLAYBOOK_PACK_OBJECT = {
            "DummyPlaybook": [
                {
                    "name": "DummyPlaybook",
                    "id": "DummyPlaybook",
                    "path": str(self.PLAYBOOK_INSTANCE_PATH),
                    "file_extension": "yml",
                }
            ]
        }
        self.LAYOUT_PACK_OBJECT = {
            "Hello World Alert": [
                {
                    "name": "Hello World Alert",
                    "id": "Hello World Alert",
                    "path": str(self.LAYOUT_INSTANCE_PATH),
                    "file_extension": "json",
                }
            ]
        }
        self.LAYOUTSCONTAINER_PACK_OBJECT = {
            "mylayout": [
                {
                    "name": "mylayout",
                    "id": "mylayout",
                    "path": str(self.LAYOUTSCONTAINER_INSTANCE_PATH),
                    "file_extension": "json",
                }
            ]
        }
        self.PRE_PROCESS_RULES_PACK_OBJECT = {
            "DummyPreProcessRule": [
                {
                    "name": "DummyPreProcessRule",
                    "id": "DummyPreProcessRule",
                    "path": str(self.PRE_PROCESS_RULES_INSTANCE_PATH),
                    "file_extension": "json",
                }
            ]
        }
        self.LISTS_PACK_OBJECT = {
            "DummyList": [
                {
                    "name": "DummyList",
                    "id": "DummyList",
                    "path": str(self.LISTS_INSTANCE_PATH),
                    "file_extension": "json",
                }
            ]
        }
        self.JOBS_PACK_OBJECT = {
            "DummyJob": [
                {
                    "name": "DummyJob",
                    "id": "DummyJob",
                    "path": str(self.JOBS_INSTANCE_PATH),
                    "file_extension": "json",
                }
            ]
        }

        self.PACK_CONTENT = {
            INTEGRATIONS_DIR: self.INTEGRATION_PACK_OBJECT,
            SCRIPTS_DIR: self.SCRIPT_PACK_OBJECT,
            PLAYBOOKS_DIR: self.PLAYBOOK_PACK_OBJECT,
            LAYOUTS_DIR: self.LAYOUTSCONTAINER_PACK_OBJECT,
        }

        self.INTEGRATION_CUSTOM_CONTENT_OBJECT = {
            "id": "Test Integration",
            "file_name": "integration-Test_Integration.yml",
            "name": "Test Integration",
            "entity": "Integrations",
            "type": FileType.INTEGRATION,
            "file_extension": "yml",
            "code_lang": "python",
        }
        self.SCRIPT_CUSTOM_CONTENT_OBJECT = {
            "id": "f1e4c6e5-0d44-48a0-8020-a9711243e918",
            "file_name": "script-TestScript.yml",
            "name": "TestScript",
            "entity": "Scripts",
            "type": FileType.SCRIPT,
            "file_extension": "yml",
            "code_lang": "python",
        }
        self.PLAYBOOK_CUSTOM_CONTENT_OBJECT = {
            "id": "DummyPlaybook",
            "file_name": "DummyPlaybook.yml",
            "name": "DummyPlaybook",
            "entity": "Playbooks",
            "type": FileType.PLAYBOOK,
            "file_extension": "yml",
        }
        self.LAYOUT_CUSTOM_CONTENT_OBJECT = {
            "id": "Hello World Alert",
            "file_name": "layout-details-TestLayout.json",
            "name": "",
            "entity": "Layouts",
            "type": FileType.LAYOUT,
            "file_extension": "json",
        }
        self.FAKE_CUSTOM_CONTENT_OBJECT = {
            "id": "DEMISTO",
            "name": "DEMISTO",
            "entity": "Layouts",
            "type": FileType.LAYOUT,
            "file_extension": "json",
        }
        self.JS_INTEGRATION_CUSTOM_CONTENT_OBJECT = {
            "id": "SumoLogic",
            "name": "SumoLogic",
            "entity": "Integrations",
            "type": FileType.INTEGRATION,
            "file_extension": "yml",
            "code_lang": "javascript",
        }

        self.CUSTOM_CONTENT = [
            self.INTEGRATION_CUSTOM_CONTENT_OBJECT,
            self.SCRIPT_CUSTOM_CONTENT_OBJECT,
            self.PLAYBOOK_CUSTOM_CONTENT_OBJECT,
            self.LAYOUT_CUSTOM_CONTENT_OBJECT,
            self.JS_INTEGRATION_CUSTOM_CONTENT_OBJECT,
        ]


class TestHelperMethods:
    def test_get_custom_content_objects(self, tmp_path, mocker):
        env = Environment(tmp_path)
        downloader = Downloader()

        mock_bundle_data = (TEST_DATA_FOLDER / "custom_content" / "download_tar.tar.gz").read_bytes()
        mock_bundle_response = HTTPResponse(body=mock_bundle_data, status=200)
        mocker.patch.object(
            demisto_client,
            "generic_request_func",
            return_value=(mock_bundle_response, None, None),
        )

        downloader.custom_content_temp_dir = env.CUSTOM_CONTENT_BASE_PATH
        custom_content_data = downloader.download_custom_content()
        custom_content_objects = downloader.parse_custom_content_data(custom_content_data=custom_content_data)
        assert custom_content_objects == env.CUSTOM_CONTENT

    @pytest.mark.parametrize(
        "name, output",
        [
            ("test", "test"),
            ("automation-demisto", "script-demisto"),
            ("playbook-demisto", "demisto"),
        ],
    )
    def test_update_file_prefix(self, name, output):
        downloader = Downloader()
        assert downloader.update_file_prefix(name) == output
        assert not downloader.update_file_prefix(name).startswith("playbook-")

    @pytest.mark.parametrize(
        "name", ["GSM", "G S M", "G_S_M", "G-S-M", "G S_M", "G_S-M"]
    )
    def test_create_dir_name(self, name):
        downloader = Downloader()
        assert downloader.create_directory_name(name) == "GSM"


class TestFlags:
    def test_missing_output_flag(self, mocker):
        """
        Given: A downloader object
        When: The user tries to download a system items without specifying the output flag
        Then: Ensure downloader.verify_flags() returns False and logs the error
        """
        downloader = Downloader()
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")

        assert downloader.verify_flags() is False
        assert str_in_call_args_list(
            logger_info.call_args_list,
            "Error: Missing required parameter '-o' / '--output'.",
        )

    def test_missing_input_flag(self, mocker):
        """
        Given: A downloader object
        When: The user tries to download a system items without specifying any input flag
        Then: Ensure downloader.verify_flags() returns False and logs the error
        """
        downloader = Downloader(output="Output", input=tuple())
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")

        assert downloader.verify_flags() is False
        assert str_in_call_args_list(
            logger_info.call_args_list,
            "Error: No input parameter has been provided "
            "('-i' / '--input', '-r' / '--regex', '-a' / '--all)."
        )

    def test_missing_item_type(self, mocker):
        """
        Given: A downloader object
        When: The user tries to download a system item without specifying the item type
        Then: Ensure downloader.verify_flags() returns False and logs the error
        """
        downloader = Downloader(output="Output", input=("My Playbook",), system=True, item_type=None)
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")

        assert downloader.verify_flags() is False
        assert str_in_call_args_list(
            logger_info.call_args_list,
            "Error: Missing required parameter for downloading system items: '-it' / '--item-type'."
        )

    def test_all_flag(self, tmp_path, mocker):
        """
        Given: A downloader object
        When: The user tries to download all content items
        Then: Ensure all content items are downloaded
        """
        env = Environment(tmp_path)
        downloader = Downloader(all_custom_content=True, output=env.CONTENT_BASE_PATH)

        mock_bundle_data = (TEST_DATA_FOLDER / "custom_content" / "download_tar.tar.gz").read_bytes()
        mock_bundle_response = HTTPResponse(body=mock_bundle_data, status=200)
        mocker.patch.object(
            demisto_client,
            "generic_request_func",
            return_value=(mock_bundle_response, None, None),
        )

        custom_content_data = downloader.download_custom_content()
        custom_content_objects = downloader.parse_custom_content_data(custom_content_data=custom_content_data)
        filtered_custom_content_objects = downloader.filter_custom_content(
            custom_content_objects=custom_content_objects
        )

        # We subtract one since there is one JS script in the testing content bundle that is skipped during filtration.
        assert len(custom_content_data) - 1 == len(filtered_custom_content_objects)

    def test_init_flag(self, tmp_path, mocker):
        """
        Given: A downloader object
        When: The user uses the init flag in order to initialize a new pack
        Then: Ensure the pack is properly initialized
        """
        env = Environment(tmp_path)
        mock = mocker.patch.object(
            builtins, "input", side_effect=("test_pack_name", "n", "n")
        )

        downloader = Downloader(output=env.CONTENT_BASE_PATH, init=True)
        initialized_path = downloader.initialize_output_path(root_folder=env.CONTENT_BASE_PATH)

        assert mock.call_count == 3
        assert initialized_path == env.CONTENT_BASE_PATH / "Packs" / "test_pack_name"
        assert (initialized_path / "pack_metadata.json").exists()
        assert not (initialized_path / "Integrations").exists()
        for file in initialized_path.iterdir():
            assert not file.is_dir()


class TestBuildPackContent:
    def test_build_existing_pack_structure(self, tmp_path):
        env = Environment(tmp_path)
        test_path = Path(env.PACK_INSTANCE_PATH)
        downloader = Downloader(output=str(test_path))
        result = downloader.build_existing_pack_structure(existing_pack_path=test_path)
        expected_result = env.PACK_CONTENT
        assert ordered(result) == ordered(expected_result)

    def test_build_pack_content_object(self, tmp_path):
        env = Environment(tmp_path)
        parameters = [
            {
                "entity": INTEGRATIONS_DIR,
                "path": env.INTEGRATION_INSTANCE_PATH,
                "out": env.INTEGRATION_PACK_OBJECT,
            },
            {
                "entity": SCRIPTS_DIR,
                "path": env.SCRIPT_INSTANCE_PATH,
                "out": env.SCRIPT_PACK_OBJECT,
            },
            {
                "entity": PLAYBOOKS_DIR,
                "path": env.PLAYBOOK_INSTANCE_PATH,
                "out": env.PLAYBOOK_PACK_OBJECT,
            },
            {
                "entity": LAYOUTS_DIR,
                "path": env.LAYOUT_INSTANCE_PATH,
                "out": env.LAYOUT_PACK_OBJECT,
            },
            {
                "entity": LAYOUTS_DIR,
                "path": "demisto_sdk/commands/download/tests/downloader_test.py",
                "out": {},
            },
            {
                "entity": LAYOUTS_DIR,
                "path": env.LAYOUTSCONTAINER_INSTANCE_PATH,
                "out": env.LAYOUTSCONTAINER_PACK_OBJECT,
            },
            {
                "entity": PRE_PROCESS_RULES_DIR,
                "path": env.PRE_PROCESS_RULES_INSTANCE_PATH,
                "out": [],
            },
            {"entity": LISTS_DIR, "path": env.LISTS_INSTANCE_PATH, "out": []},
            {"entity": JOBS_DIR, "path": env.JOBS_INSTANCE_PATH, "out": []},
        ]
        downloader = Downloader()
        for param in parameters:
            file_name, pack_content_object = downloader.build_pack_content_object(
                param["entity"], param["path"]
            )
            assert {file_name: ordered(pack_content_object)} == ordered(param["out"])

    def test_get_main_file_details(self, tmp_path):
        env = Environment(tmp_path)
        parameters = [
            {
                "entity": INTEGRATIONS_DIR,
                "path": env.INTEGRATION_INSTANCE_PATH,
                "main_id": "Test Integration",
                "main_name": "Test Integration",
            },
            {
                "entity": LAYOUTS_DIR,
                "path": env.LAYOUT_INSTANCE_PATH,
                "main_id": "Hello World Alert",
                "main_name": "Hello World Alert",
            },
            {
                "entity": LAYOUTS_DIR,
                "path": "demisto_sdk/commands/download/tests/downloader_test.py",
                "main_id": "",
                "main_name": "",
            },
        ]
        downloader = Downloader()
        for param in parameters:
            op_id, op_name = downloader.get_metadata_file(
                param["entity"], os.path.abspath(param["path"])
            )
            assert op_id == param["main_id"]
            assert op_name == param["main_name"]


class TestBuildCustomContent:
    def test_build_custom_content_object(self, tmp_path):
        env = Environment(tmp_path)
        parameters = [
            {
                "path": env.CUSTOM_CONTENT_SCRIPT_PATH,
                "output_custom_content_object": env.SCRIPT_CUSTOM_CONTENT_OBJECT,
            },
            {
                "path": env.CUSTOM_CONTENT_INTEGRATION_PATH,
                "output_custom_content_object": env.INTEGRATION_CUSTOM_CONTENT_OBJECT,
            },
            {
                "path": env.CUSTOM_CONTENT_LAYOUT_PATH,
                "output_custom_content_object": env.LAYOUT_CUSTOM_CONTENT_OBJECT,
            },
            {
                "path": env.CUSTOM_CONTENT_PLAYBOOK_PATH,
                "output_custom_content_object": env.PLAYBOOK_CUSTOM_CONTENT_OBJECT,
            },
        ]
        downloader = Downloader()
        for param in parameters:
            with open(param["path"], "r") as file:
                loaded_file = create_stringio_object(file.read())

            result = downloader.create_content_item_object(
                file_name=param["path"].name, file_data=loaded_file)

            # Assure these keys exist, and skip testing them
            # ('file' is StringIO bytes representation, and 'data' is the parsed file in dictionary format)
            assert 'data' in result
            result.pop('data')
            assert 'file' in result
            result.pop('file')

            assert result == param["output_custom_content_object"]


class TestMergeExistingFile:
    def test_merge_and_extract_existing_file_corrupted_dir(self, tmp_path, mocker):
        """
        Given
            - The integration exist in output pack, the directory is corrupted
            (i.e. a file is missing, for example: the image file)

        When
            - An integration about to be downloaded

        Then
            - Ensure integration is downloaded successfully
        """
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
        env = Environment(tmp_path)
        mocker.patch.object(
            Downloader, "get_corresponding_pack_file_object", return_value={}
        )
        with patch.object(Downloader, "__init__", lambda a, b, c: None):
            downloader = Downloader()
            downloader.output_pack_path = env.PACK_INSTANCE_PATH
            downloader.pack_content = env.PACK_CONTENT
            downloader.run_format = False
            downloader.num_merged_files = 0
            downloader.num_added_files = 0
            downloader.download_unified_content(
                env.INTEGRATION_CUSTOM_CONTENT_OBJECT
            )
            assert str_in_call_args_list(logger_info.call_args_list, "Merged")

    def test_merge_and_extract_existing_file_js(self, tmp_path):
        with patch.object(Downloader, "__init__", lambda a, b, c: None):
            downloader = Downloader()
            downloader.num_merged_files = 0
            downloader.num_added_files = 0
            downloader.files_not_downloaded = []
            downloader.pack_content = {
                entity: list() for entity in CONTENT_ENTITIES_DIRS
            }
            js_custom_content_object = {
                "id": "SumoLogic",
                "name": "SumoLogic",
                "path": "demisto_sdk/commands/download/tests/tests_data/custom_content/integration-DummyJSIntegration"
                ".yml",
                "entity": "Integrations",
                "type": "integration",
                "file_extension": "yml",
                "exist_in_pack": True,
                "code_lang": "javascript",
            }
            downloader.download_unified_content(js_custom_content_object)

    def test_merge_and_extract_existing_file(self, tmp_path):
        env = Environment(tmp_path)
        downloader = Downloader()
        downloader.pack_content = env.PACK_CONTENT
        downloader.run_format = False
        downloader.num_merged_files = 0
        downloader.num_added_files = 0
        downloader.download_unified_content(
            env.INTEGRATION_CUSTOM_CONTENT_OBJECT
        )
        paths = [
            file["path"] for file in env.INTEGRATION_PACK_OBJECT["Test Integration"]
        ]
        for path in paths:
            assert Path(path).is_file()
        yml_data = get_yaml(
            env.INTEGRATION_PACK_OBJECT["Test Integration"][2]["path"]
        )
        for field in KEEP_EXISTING_YAML_FIELDS:
            obj = yml_data
            dotted_path_list = field.split(".")
            for path_part in dotted_path_list:
                if path_part != dotted_path_list[-1]:
                    obj = obj.get(path_part)
                else:
                    if obj.get(path_part):
                        assert True
                    else:
                        assert False
        with open(
            env.INTEGRATION_PACK_OBJECT["Test Integration"][5]["path"]
        ) as description_file:
            description_data = description_file.read()
        assert "Test Integration Long Description TEST" in description_data
        with open(
            env.INTEGRATION_PACK_OBJECT["Test Integration"][0]["path"]
        ) as code_file:
            code_data = code_file.read()
        assert "TEST" in code_data

    def test_merge_existing_file(self, tmp_path):
        env = Environment(tmp_path)
        parameters = [
            {
                "content_object": env.PLAYBOOK_CUSTOM_CONTENT_OBJECT,
                "ending": "yml",
                "method": get_yaml,
                "instance_path": env.PLAYBOOK_INSTANCE_PATH,
                "fields": ["fromversion", "toversion"],
            },
            {
                "content_object": env.LAYOUT_CUSTOM_CONTENT_OBJECT,
                "ending": "json",
                "method": get_json,
                "instance_path": env.LAYOUT_INSTANCE_PATH,
                "fields": ["fromVersion", "toVersion"],
            },
        ]

        with patch.object(Downloader, "__init__", lambda a, b, c: None):
            downloader = Downloader()
            downloader.pack_content = env.PACK_CONTENT
            downloader.run_format = False
            downloader.num_merged_files = 0
            downloader.num_added_files = 0
            for param in parameters:
                downloader.download_non_unified_content(
                    param["content_object"], param["ending"]
                )
                assert Path(param["instance_path"]).is_file()
                file_data = param["method"](param["instance_path"], cache_clear=True)
                for field in param["fields"]:
                    if file_data.get(field):
                        assert True
                    else:
                        assert False
                if param["ending"] == "yml":
                    task_4_name = file_data["tasks"]["4"]["task"]["name"]
                    assert task_4_name == "Done TEST"

    def test_get_corresponding_pack_content_object(self, tmp_path):
        env = Environment(tmp_path)
        parameters = [
            {
                "custom_content_obj": env.INTEGRATION_CUSTOM_CONTENT_OBJECT,
                "pack_content_obj": env.INTEGRATION_PACK_OBJECT,
            },
            {
                "custom_content_obj": env.SCRIPT_CUSTOM_CONTENT_OBJECT,
                "pack_content_obj": env.SCRIPT_PACK_OBJECT,
            },
            {
                "custom_content_obj": env.PLAYBOOK_CUSTOM_CONTENT_OBJECT,
                "pack_content_obj": env.PLAYBOOK_PACK_OBJECT,
            },
            {
                "custom_content_obj": env.LAYOUT_CUSTOM_CONTENT_OBJECT,
                "pack_content_obj": env.LAYOUT_PACK_OBJECT,
            },
            {
                "custom_content_obj": env.FAKE_CUSTOM_CONTENT_OBJECT,
                "pack_content_obj": {},
            },
        ]
        with patch.object(Downloader, "__init__", lambda a, b, c: None):
            downloader = Downloader("", "")
            downloader.pack_content = env.PACK_CONTENT
            for param in parameters:
                corr_obj = downloader.get_corresponding_pack_content_object(
                    param["custom_content_obj"]
                )
                assert corr_obj == param["pack_content_obj"]

    def test_update_data_yml(self, tmp_path):
        env = Environment(tmp_path)
        downloader = Downloader()
        downloader.update_data(
            file_to_update=env.CUSTOM_CONTENT_INTEGRATION_PATH,
            original_file=f"{env.INTEGRATION_INSTANCE_PATH}/TestIntegration.yml",
            is_yaml=True,
        )
        file_data = get_yaml(env.CUSTOM_CONTENT_INTEGRATION_PATH)

        for field in KEEP_EXISTING_YAML_FIELDS:
            nested_keys = field.split(".")

            if len(nested_keys) > 1:
                iterated_value = file_data.get(nested_keys[0])

                for key in nested_keys[1:]:
                    assert iterated_value.get(key)
                    iterated_value = file_data[key]

            else:
                assert file_data.get(field)

    def test_update_data_json(self, tmp_path):
        env = Environment(tmp_path)
        downloader = Downloader()
        downloader.update_data(
            file_to_update=env.CUSTOM_CONTENT_LAYOUT_PATH,
            original_file=str(env.LAYOUT_INSTANCE_PATH),
            is_yaml=False,
        )
        file_data: dict = get_json(env.CUSTOM_CONTENT_LAYOUT_PATH)

        for field in KEEP_EXISTING_JSON_FIELDS:
            nested_keys = field.split(".")

            if len(nested_keys) > 1:
                iterated_value = file_data.get(nested_keys[0])

                for key in nested_keys[1:]:
                    assert iterated_value.get(key)
                    iterated_value = file_data[key]

            else:
                assert file_data.get(field)


class TestMergeNewFile:
    def test_merge_and_extract_new_file(self, tmp_path):
        env = Environment(tmp_path)
        parameters = [
            {
                "content_object": env.INTEGRATION_CUSTOM_CONTENT_OBJECT,
                "raw_files": [
                    "odp/bn.py",
                    "odp/bn.yml",
                    "odp/bn_image.png",
                    "odp/bn_description.md",
                    "odp/README.md",
                ],
            },
            {
                "content_object": env.SCRIPT_CUSTOM_CONTENT_OBJECT,
                "raw_files": ["odp/bn.py", "odp/bn.yml", "odp/README.md"],
            },
        ]
        for param in parameters:
            temp_dir = env.tmp_path / f"temp_dir_{parameters.index(param)}"
            os.mkdir(temp_dir)
            entity = param["content_object"]["entity"]
            downloader = Downloader(output=str(temp_dir), input="", regex="")
            basename = downloader.create_directory_name(
                param["content_object"]["name"]
            )
            output_entity_dir_path = f"{temp_dir}/{entity}"
            os.mkdir(output_entity_dir_path)
            output_dir_path = f"{output_entity_dir_path}/{basename}"
            os.mkdir(output_dir_path)
            files = [
                file.replace("odp", output_dir_path).replace("bn", basename)
                for file in param["raw_files"]
            ]

            downloader.merge_and_extract_new_file(param["content_object"])
            output_files = get_child_files(output_dir_path)
            assert sorted(output_files) == sorted(files)

    def test_merge_new_file(self, tmp_path):
        env = Environment(tmp_path)
        parameters = [
            {"content_object": env.PLAYBOOK_CUSTOM_CONTENT_OBJECT},
            {"content_object": env.LAYOUT_CUSTOM_CONTENT_OBJECT},
        ]
        for param in parameters:
            temp_dir = env.tmp_path / f"temp_dir_{parameters.index(param)}"
            os.mkdir(temp_dir)
            entity = param["content_object"]["entity"]
            output_dir_path = f"{temp_dir}/{entity}"
            os.mkdir(output_dir_path)
            old_file_path = param["content_object"]["path"]
            new_file_path = f"{output_dir_path}/{Path(old_file_path).name}"
            downloader = Downloader(output=temp_dir, input="", regex="")
            downloader.merge_new_file(param["content_object"])
            assert Path(new_file_path).is_file()


class TestVerifyPackPath:
    @pytest.mark.parametrize(
        "output_path, expected_result",
        [
            ("Integrations", False),
            ("Packs/TestPack/", True),
            ("Demisto", False),
            ("Packs", False),
            ("Packs/TestPack", True),
        ],
    )
    def test_verify_output_path_is_pack(self, tmp_path, output_path, expected_result):
        env = Environment(tmp_path)
        output_path = Path(f"{env.CONTENT_BASE_PATH}/{output_path}")
        assert Downloader().verify_output_path(output_path=output_path) == expected_result


@pytest.mark.parametrize(
    "input_content, item_type, insecure, endpoint, req_type, req_body",
    [
        (
            ("PB1", "PB2"),
            "Playbook",
            False,
            "/playbook/search",
            "GET",
            {"query": "name:PB1 or PB2"},
        ),
        (
            ("Mapper1", "Mapper2"),
            "Mapper",
            True,
            "/classifier/search",
            "POST",
            {"query": "name:Mapper1 or Mapper2"},
        ),
        (("Field1", "Field2"), "Field", True, "/incidentfields", "GET", {}),
        (
            ("Classifier1", "Classifier2"),
            "Classifier",
            False,
            "/classifier/search",
            "POST",
            {"query": "name:Classifier1 or Classifier2"},
        ),
    ],
)
def test_build_req_params(
    input_content: tuple[str], item_type, insecure, endpoint, req_type, req_body, monkeypatch
):
    monkeypatch.setenv("DEMISTO_BASE_URL", "http://demisto.instance.com:8080/")
    monkeypatch.setenv("DEMISTO_API_KEY", "API_KEY")
    downloader = Downloader(input=input_content, system=True, item_type=item_type, insecure=insecure)
    res_endpoint, res_req_type, res_req_body = downloader.build_req_params()
    assert endpoint == res_endpoint
    assert req_type == res_req_type
    assert req_body == res_req_body


@pytest.mark.parametrize(
    "content_item, content_type, expected_result",
    [
        ({"name": "name 1"}, "Playbook", "name_1.yml"),
        ({"name": "name 1"}, "Field", "name_1.json"),
        ({"name": "name with / slash in it"}, "Playbook", "name_with_slash_in_it.yml"),
        ({"id": "id 1"}, "Field", "id_1.json"),
    ],
)
def test_build_file_name(content_item: dict, content_type: str, expected_result: str):
    downloader = Downloader()

    downloader.system_item_type = content_type
    file_name = downloader.generate_content_file_name(content_item=content_item, content_item_type=content_type)

    assert file_name == expected_result


@pytest.mark.parametrize("source_is_unicode", (True, False))
@pytest.mark.parametrize(
    "suffix,dumps_method,write_method,fields",
    (
        (
            ".json",
            json.dumps,
            lambda f, data: json.dump(data, f),
            ("fromVersion", "toVersion"),
        ),
        (
            ".yml",
            yaml.dumps,
            lambda f, data: yaml.dump(data, f),
            ("fromversion", "toversion"),
        ),
    ),
)
def test_safe_write_unicode_to_non_unicode(
    tmp_path: Path,
    suffix: str,
    dumps_method: Callable,
    write_method: Callable[[TextIOWrapper, dict], None],
    source_is_unicode: bool,
    fields: Tuple[
        str, str
    ],  # not all field names are merged, and they depend on the file type
) -> None:
    """
    Given: A format to check (yaml/json), with its writing method
    When: Calling Downloader.update_data
    Then:
        1. Make sure that downloading unicode content into a non-unicode file works (result should be all unicode)
        2. Make sure that downloading non-unicode content into a unicode file works (result should be all unicode)
    """
    from demisto_sdk.commands.download.downloader import Downloader

    non_unicode_path = (tmp_path / "non_unicode").with_suffix(suffix)
    with non_unicode_path.open("wb") as f:
        f.write(
            dumps_method({fields[0]: SENTENCE_WITH_UMLAUTS}).encode(
                "latin-1", "backslashreplace"
            )
        )
    assert "ü" in non_unicode_path.read_text(
        encoding="latin-1"
    )  # assert it was written as latin-1

    unicode_path = (tmp_path / "unicode").with_suffix(suffix)
    with open(unicode_path, "w") as f:
        write_method(f, {fields[1]: SENTENCE_WITH_UMLAUTS})
    assert "ü" in unicode_path.read_text(
        encoding="utf-8"
    )  # assert the content was written as unicode

    source, dest = (
        (unicode_path, non_unicode_path)
        if source_is_unicode
        else (
            non_unicode_path,
            unicode_path,
        )
    )

    Downloader.update_data(
        file_to_update=dest, original_file=str(source), is_yaml=(suffix == ".yml")
    )

    # make sure the two files were merged correctly
    result = get_file(dest)
    assert set(result.keys()) == set(fields)
    assert set(result.values()) == {SENTENCE_WITH_UMLAUTS}


def test_uuids_find_and_replacement_in_content_items(mocker):
    """
    Given:
        A mock tar file download_tar.tar
    When:
        calling create_uuid_to_name_mapping on the mock tar
    Then:
        Assure UUIDs are properly mapped and replaced.
    """
    expected_mapping = {
        "e4c2306d-5d4b-4b19-8320-6fdad94595d4": "custom_automation",
        "de57b1f7-b754-43d2-8a8c-379d12bdddcd": "custom_script",
        "84731e69-0e55-40f9-806a-6452f97a01a0": "Custom Layout",
        "4d45f0d7-5fdd-4a4b-8f1e-5f2502f90a61": "ExampleType",
        "a53a2f17-2f05-486d-867f-a36c9f5b88d4": "custom_playbook"
    }

    mock_bundle_data = (TEST_DATA_FOLDER / "custom_content" / "download_tar.tar.gz").read_bytes()
    mock_bundle_response = HTTPResponse(body=mock_bundle_data, status=200)
    mocker.patch.object(demisto_client, "generic_request_func", return_value=(mock_bundle_response, None, None))

    downloader = Downloader(
        all_custom_content=True,
    )

    all_custom_content_data = downloader.download_custom_content()
    all_custom_content_objects = downloader.parse_custom_content_data(
        custom_content_data=all_custom_content_data
    )

    uuid_mapping = downloader.create_uuid_to_name_mapping(custom_content_objects=all_custom_content_objects)
    assert uuid_mapping == expected_mapping

    changed_uuids_count = 0
    for file_object in all_custom_content_objects.values():
        if downloader.replace_uuid_ids(
            custom_content_object=file_object, uuid_mapping=uuid_mapping
        ):
            changed_uuids_count += 1

    assert changed_uuids_count == 7


def test_get_system_playbook(mocker):
    """
    Given:
        A name of a playbook to download.
    When:
        Using the download command.
    Then:
        Ensure the function works as expected and returns the playbook.
    """
    playbook_path = TEST_DATA_FOLDER / "playbook-DummyPlaybook2.yml"
    playbook_data = get_yaml(playbook_path)
    mocker.patch.object(
        demisto_client, "generic_request_func", return_value=[playbook_data]
    )

    downloader = Downloader(input=("test",), output="test")
    playbooks = downloader.get_system_playbook(content_items=["DummyPlaybook"])
    assert isinstance(playbooks, list)
    assert playbooks[0] == playbook_data
    assert len(playbooks) == 1


def test_get_system_playbook_item_does_not_exist_by_name(mocker):
    """
    Given:
        A name of a playbook to download using the API.
    When:
        Using the download command, but the API call returns "Item not found" error for the playbook.
    Then:
        Ensure that the function tries to retrieve the playbook its ID instead.
    """
    playbook_path = TEST_DATA_FOLDER / "playbook-DummyPlaybook2.yml"

    playbook = get_yaml(playbook_path)
    playbook["id"] = "dummy_-_playbook"
    mocker.patch.object(
        demisto_client,
        "generic_request_func",
        side_effect=(ApiException("Item not found"), [playbook]),
    )
    mocker.patch.object(
        Downloader, "get_playbook_id_by_playbook_name", return_value="test"
    )
    downloader = Downloader(input=("DummyPlaybook",), output="test")
    playbooks = downloader.get_system_playbook(content_items=["DummyPlaybook"])
    assert isinstance(playbooks, list)
    assert len(playbooks) == 1


@pytest.mark.parametrize(
    "exception, mock_value, expected_call",
    [(Exception, "test", 0), (ApiException, None, 1)],
)
def test_get_system_playbook_failure(mocker, exception, mock_value, expected_call):
    """
    Given: a mock exception
    When: calling get_system_playbook function.
    Then:
        - Ensure that when the API call throws a non-ApiException error,
          a second attempt is not made to retrieve the playbook by the ID.
        - Ensure that when the API call throws an ApiException error and the id extraction fails,
          the function raises the same error.
    """
    mocker.patch.object(demisto_client, "generic_request_func", side_effect=exception())
    get_id_by_name_mock = mocker.patch.object(
        Downloader, "get_playbook_id_by_playbook_name", return_value=mock_value
    )
    downloader = Downloader(input=("DummyPlaybook",), output="test")
    with pytest.raises(exception):
        downloader.get_system_playbook(content_items=["DummyPlaybook"])
    assert get_id_by_name_mock.call_count == expected_call


def test_list_files_flag(mocker):
    """
    Given:
        list_files flag (-lf / --list-files) is set to True (and only that. Other flags are not required)
    When:
        Running the Download command
    Then:
        Ensure the command list all files available for download properly.
    """
    downloader = Downloader(list_files=True)
    mock_bundle_data = (TEST_DATA_FOLDER / "custom_content" / "download_tar.tar.gz").read_bytes()
    mock_bundle_response = HTTPResponse(body=mock_bundle_data, status=200)

    mocker.patch.object(demisto_client, "generic_request_func", return_value=(mock_bundle_response, None, None))

    # Mock "create_custom_content_table" just for spying, to get its return value
    content_table_mock = mocker.spy(Downloader, "create_custom_content_table")
    assert downloader.download() == 0

    expected_table = ('CONTENT NAME                CONTENT TYPE\n'
                      '--------------------------  ----------------\n'
                      'CommonServerUserPowerShell  script\n'
                      'CommonServerUserPython      script\n'
                      'custom_automation           script\n'
                      'custom_script               script\n'
                      'custom_incident             incidentfield\n'
                      'Custom_Layout               incidenttype\n'
                      'custom_integration          integration\n'
                      'Custom Layout               layoutscontainer\n'
                      'ExampleType                 layoutscontainer\n'
                      'custom_playbook             playbook')

    assert content_table_mock.call_count == 1
    assert expected_table in content_table_mock.spy_return
