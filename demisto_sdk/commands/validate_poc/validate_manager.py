from typing import List

import toml
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.git_util import GitUtil

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.commands.validate_poc.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)


class ValidateManager:
    def __init__(
        self,
        use_git=False,
        validate_all=False,
        file_path=None,
    ):
        self.files_to_run = self.gather_files_to_run(file_path, use_git, validate_all)
        self.validation_codes, self.run_using_select = self.gather_validations_to_run(
            use_git, validate_all
        )
        self.config: dict = toml.load("validation_conf.toml")

    def run(self):
        results: List[ValidationResult] = []
        # gather validator from validate_poc package
        validators = BaseValidator.__subclasses__()

        for validator in validators:
            # if error in validation_codes the left = True if run_using_select = True then we get get True
            # if error in validation_codes the left = True if run_using_select = False then we get get False
            # if error in validation_codes the left = False if run_using_select = True then we get get False
            # if error in validation_codes the left = False if run_using_select = False then we get get True
            if (validator.error_code in self.validation_codes) == self.run_using_select:
                for object_ in self.files_to_run:
                    if isinstance(object_, Pack):
                        for content_item in object_.content_items:
                            if validator.should_run(content_item):
                                if validator.error_code not in content_item.ignored_errors:
                                    results.append(validator.is_valid(content_item))
                    if validator.error_code not in content_item.ignored_errors:
                        results.append(validator.is_valid(content_item))
        return self.post_results(results)

    def gather_files_to_run(self, file_paths, use_git, validate_all):
        content_objects_to_run = set()
        if use_git:
            file_paths = GitUtil()._get_all_changed_files()

        for file_path in file_paths:
            content_object = BaseContent.from_path(file_path)
            if content_object is None:
                raise Exception(f"no content found in {file_path}")
            content_objects_to_run.add(BaseContent.from_path(file_path))
        if validate_all:
            content_dto = ContentDTO.from_path(CONTENT_PATH)
            if not isinstance(content_dto, ContentDTO):
                raise Exception("no content found")
            content_objects_to_run = set(content_dto.packs)
        return content_objects_to_run
    

    def gather_validations_to_run(self, use_git, validate_all):
        flag = "use_git" if use_git else "validate_all"
        if select := self.config.get(flag, {}).get("select"):
            validation_codes, run_using_select = select, True
        else:
            validation_codes, run_using_select = (
                self.config.get(flag, {}).get("ignore"),
                False,
            )
        return validation_codes, run_using_select

    def post_results(self, results: List[ValidationResult] = []):
        only_throw_warning = self.config.get("throw_warnings", {}).get("warnings_list", [])
        is_valid = True
        for result in results:
            if not result.is_valid:
                if result.error_code in only_throw_warning:
                    logger.warning(f"[yellow]{result.format_message}[/yellow]")
                else:
                    logger.error(f"[red]{result.format_message}[/red]")
                    is_valid = False
        return is_valid

