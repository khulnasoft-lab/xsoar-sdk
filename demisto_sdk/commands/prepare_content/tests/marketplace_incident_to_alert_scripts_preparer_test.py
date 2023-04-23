import pytest

from TestSuite.script import Script
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.prepare_content.preparers.marketplace_incident_to_alert_scripts_prepare import (
    MarketplaceIncidentToAlertScriptsPreparer,
)

COMMENT_INCIDENT_CONSTANT = (
        'Post Processing Script that will close linked '
        'Incidents when the Incident is closed. '
        'Will set the same close code as the parent, '
        'and add closing notes from the parent. '
    )
COMMENT_ALERT_CONSTANT = (
        'Post Processing Script that will close linked '
        'Alerts when the Alert is closed. '
        'Will set the same close code as the parent, '
        'and add closing notes from the parent. '
    )
GIT_ROOT = git_path()


def create_script_for_test(tmp_path, repo):

    script = Script(
        tmpdir=tmp_path,
        name='script_incident_to_alert',
        repo=repo,
        create_unified=True
        )
    script.create_default_script(name='setIncident')
    data = script.yml.read_dict()
    data['comment'] = COMMENT_INCIDENT_CONSTANT
    return data


@pytest.mark.parametrize(
    'incident_to_alert,'
    'expected_names, '
    'expected_comments',
    [
        (
            True,
            ((0, 'setIncident'), (1, 'setAlert')),
            (
                (
                    0,
                    COMMENT_INCIDENT_CONSTANT
                ),
                (
                    1,
                    COMMENT_ALERT_CONSTANT
                )
            )
        ),
        (
            False,
            ((0, 'setIncident'),),
            (
                (
                    0,
                    COMMENT_INCIDENT_CONSTANT
                ),
            )
        ),
    ]
)
def test_marketplace_incident_to_alert_scripts_preparer(
        tmp_path,
        repo,
        incident_to_alert,
        expected_names,
        expected_comments,
        ):
    """
    Given:
        - A script that includes the word incident in its name
          with a comment that also includes the words incident and incidents.
    When:
        - MarketplaceIncidentToAlertScriptsPreparer.prepare() command is executed
    Then:
        - Ensure that a script is created with a new name when the word incident is replaced by the word alert.
        - Ensure that a wrapper script is created for the new script with the old name that includes the word incident.
        - Ensure that which returns a tuple from the function.
    """

    data = create_script_for_test(tmp_path, repo)

    data = MarketplaceIncidentToAlertScriptsPreparer.prepare(
        data,
        current_marketplace=MarketplaceVersions.MarketplaceV2,
        incident_to_alert=incident_to_alert,
    )

    assert isinstance(data, tuple)

    for i, script_name in expected_names:
        assert (
            data[i].get('name') == script_name
        )

    for i, comment in expected_comments:
        assert (
            data[i]['comment'] == comment
        )
