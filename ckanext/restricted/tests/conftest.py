import pytest
import mock


@pytest.fixture(autouse=True)
def restricted_action_mail():
    with mock.patch('ckanext.restricted.action.mail_recipient'):
        yield
