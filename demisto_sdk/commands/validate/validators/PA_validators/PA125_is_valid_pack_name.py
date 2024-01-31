from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import (
    INCORRECT_PACK_NAME_WORDS,
)
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class IsValidPackNameValidator(BaseValidator[ContentTypes]):
    error_code = "PA125"
    description = "Validate that the pack name is valid."
    error_message = "Invalid pack name ({0}), pack name should be at least 3 characters long, start with a capital letter, must not contain the words: {1}."
    related_field = "name"

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.name, ", ".join(INCORRECT_PACK_NAME_WORDS)
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if len(content_item.name) < 3
            or content_item.name[0].islower()
            or any(
                excluded_word.lower() in content_item.name.lower()
                for excluded_word in INCORRECT_PACK_NAME_WORDS
            )
        ]
