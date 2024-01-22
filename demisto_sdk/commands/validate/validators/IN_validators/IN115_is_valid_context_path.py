from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Command, Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsValidContextPathValidator(BaseValidator[ContentTypes]):
    error_code = "IN115"
    description = (
        "Validate that the contextPath field of each output is in the right format."
    )
    error_message = "The following commands include outputs with context path different from missing contextPath, please make sure to add: {0}."
    related_field = "contextPath"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    ", ".join(commands_missing_context_path)
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                commands_missing_context_path := [
                    command.name
                    for command in content_item.commands
                    if self.is_command_missing_context_path(command)
                ]
            )
        ]

    def is_command_missing_context_path(self, command: Command) -> bool:
        """Validate that all outputs entry has contextPath key for a given command.

        Args:
            command (Command): The command to run on

        Returns:
            (bool): True if the an output entry is missing a contextPath. Otherwise, return False.
        """
        for output in command.outputs:
            if not output.contextPath:
                return True
        return False
