import re
import copy
import logging
from typing import Any


from demisto_sdk.commands.common.constants import MarketplaceVersions

logger = logging.getLogger("demisto-sdk")

NOT_WRAPPED_RE_MAPPING = {
    rf"(?<!<-){key}(?!->)": value
    for key, value in {
        "incident": "alert",
        "Incident": "Alert",
        "incidents": "alerts",
        "Incidents": "Alerts",
        "INCIDENT": "ALERT",
        "INCIDENTS": "ALERTS",
    }.items()
}

WRAPPED_MAPPING = {
    rf"<-{key}->": key
    for key in (
        "incident",
        "incidents",
        "Incident",
        "Incidents",
        "INCIDENT",
        "INCIDENTS",
    )
}

WRAPPER_SCRIPT = {
    'python': "register_module_line('script_name', 'start', __line__())\n\n"
              "return_results(demisto.executeCommand('<original_script_name>', demisto.args()))\n\n"
              "register_module_line('script_name', 'end', __line__())",
    'javascript': "return executeCommand('<original_script_name>', args)\n"
}


"""
PLAYBOOK HELPER FUNCTIONS
"""


def prepare_descriptions_and_names_helper(
    name_or_description_content: str, replace_incident_to_alert: bool
):
    if replace_incident_to_alert:
        name_or_description_content = edit_names_and_descriptions_for_playbook(
            name_or_description_content, replace_incident_to_alert
        )
    return edit_names_and_descriptions_for_playbook(
        name_or_description_content, False
    )  # Here remove the wrapper


def prepare_descriptions_and_names(
    data: dict, marketplace: MarketplaceVersions
) -> dict:
    # Replace incidents to alerts only for XSIAM
    replace_incident_to_alert = marketplace == MarketplaceVersions.MarketplaceV2

    # Descriptions and names for all tasks
    for task_key, task_value in data.get("tasks", {}).items():

        if description := task_value.get("task", {}).get("description", ""):
            # Since it is a server key, we do not want to change it
            if description != "commands.local.cmd.set.incident":
                data["tasks"][task_key]["task"][
                    "description"
                ] = prepare_descriptions_and_names_helper(
                    description, replace_incident_to_alert
                )

        if name := task_value.get("task", {}).get("name", ""):
            data["tasks"][task_key]["task"][
                "name"
            ] = prepare_descriptions_and_names_helper(name, replace_incident_to_alert)

    # The external playbook's description
    if description := data.get("description"):
        data["description"] = prepare_descriptions_and_names_helper(
            description, replace_incident_to_alert
        )

    # The external playbook's name
    if name := data.get("name"):
        data["name"] = prepare_descriptions_and_names_helper(
            name, replace_incident_to_alert
        )

    return data


def edit_names_and_descriptions_for_playbook(
    name_or_description_field_content: str, replace_incident_to_alert: bool
) -> str:
    if replace_incident_to_alert:
        replacements = NOT_WRAPPED_RE_MAPPING
    else:
        replacements = WRAPPED_MAPPING

    new_content = name_or_description_field_content

    for pattern, replace_with in replacements.items():
        new_content = re.sub(pattern, replace_with, new_content)

    return new_content


def replace_playbook_access_fields_recursively(datum: Any) -> Any:

    if isinstance(datum, list):
        return [replace_playbook_access_fields_recursively(item) for item in datum]

    elif isinstance(datum, dict):
        for key, val in datum.items():
            if isinstance(val, str):
                if key in {"root", "simple"} and "incident" in val:
                    val = re.sub(
                        r"(?<!\.)\bincident\b", "alert", val
                    )  # values like 'X.incident' should not be replaced

                if key == "script" and val == "Builtin|||setIncident":
                    val = val.replace("setIncident", "setAlert")

                datum[key] = val

            else:
                datum[key] = replace_playbook_access_fields_recursively(val)

    return datum


def prepare_playbook_access_fields(data: dict) -> dict:
    data = replace_playbook_access_fields_recursively(data)
    return data


"""
SCRIPT HELPER FUNCTIONS
"""


def edit_ids_names_and_descriptions_for_script(data: str, incident_to_alert: bool = False):
    if incident_to_alert:
        for pattern, replace_with in NOT_WRAPPED_RE_MAPPING.items():
            data = re.sub(pattern, replace_with, data)

    for pattern, replace_with in WRAPPED_MAPPING.items():
        data = re.sub(pattern, replace_with, data)
    return data


def create_wrapper_script(data: dict) -> dict:

    copy_data = copy.deepcopy(data)
    try:
        copy_data['script'] = WRAPPER_SCRIPT[copy_data['type']].replace(
            '<original_script_name>',
            edit_ids_names_and_descriptions_for_script(copy_data['name'], True)).replace(
                'script_name',
                copy_data['name'])
    except Exception as e:
        logger.error(f'Failed to create the wrapper script: {e}')

    copy_data = set_deprecated_for_scripts(copy_data, old_script=True)
    logger.debug(f"Created {copy_data['name']} script wrapper to {data['name']} script")

    return replace_script_access_fields_recursively(copy_data)


def replace_script_access_fields_recursively(data: Any, incident_to_alert: bool = False) -> Any:
    if isinstance(data, list):
        return [replace_script_access_fields_recursively(item, incident_to_alert) for item in data]
    if isinstance(data, dict):
        for key in tuple(
            data.keys()
        ):
            value = data[key]
            if isinstance(value, str):
                if key in ('name', 'id', 'comment', 'description'):
                    data[key] = edit_ids_names_and_descriptions_for_script(value, incident_to_alert)
            else:
                data[key] = replace_script_access_fields_recursively(value, incident_to_alert)
        return data
    else:
        return data


def replace_register_module_line_for_script(data: dict):
    new_name = edit_ids_names_and_descriptions_for_script(
        data['name'],
        incident_to_alert=True
    )
    for state in ('start', 'end'):
        data['script'] = data['script'].replace(
            f"register_module_line('{data['name']}', '{state}', __line__())",
            f"register_module_line('{new_name}', '{state}', __line__())")

    return data


def set_deprecated_for_scripts(data: dict, old_script: bool):
    if old_script:
        data['deprecated'] = True
    elif 'deprecated' not in data:
        data['deprecated'] = False
    return data


def prepare_script_access_fields(data: dict, incident_to_alert: bool) -> dict:
    if incident_to_alert:
        data = replace_register_module_line_for_script(data)
        data = set_deprecated_for_scripts(data, old_script=False)
    return replace_script_access_fields_recursively(data, incident_to_alert)
