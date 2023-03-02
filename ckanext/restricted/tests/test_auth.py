from unittest.mock import patch, MagicMock

import pytest

from ckanext.restricted.auth import restricted_resource_show


@pytest.mark.usefixtures(u'clean_db')
@pytest.mark.usefixtures(u'clean_index')
@pytest.mark.ckan_config(u'ckan.plugins', u'restricted')
@pytest.mark.usefixtures(u'with_plugins')
@pytest.mark.usefixtures(u'with_request_context')
class TestAuth:
    @patch('ckanext.restricted.auth.authz')
    @patch('ckanext.restricted.auth.logic_auth')
    def test_user_can_check_access_for_resource_within_activity(self, logic_auth, authz):
        res = {'package_id': '42'}
        logic_auth.get_resource_object = MagicMock(return_value=res)
        authz.is_authorized = MagicMock(return_value={'success': True})
        context = {}
        data_dict = {'id': '14aeaaa7-730e-4197-9a90-18f4a8509ce3/984412af-c948-459c-815a-84ad3a635163'}

        expected_data_dict = {'id': '14aeaaa7-730e-4197-9a90-18f4a8509ce3'}

        assert restricted_resource_show(context, data_dict) == {'success': True}
        logic_auth.get_resource_object.assert_called_once_with(context, expected_data_dict)
        authz.is_authorized.assert_called_once_with('package_update', context, {'id': '42'})

    @patch('ckanext.restricted.auth.authz')
    @patch('ckanext.restricted.auth.logic_auth')
    def test_user_can_check_access_for_resource(self, logic_auth, authz):
        res = {'package_id': '42'}
        logic_auth.get_resource_object = MagicMock(return_value=res)
        authz.is_authorized = MagicMock(return_value={'success': True})
        context = {}
        data_dict = {'id': '14aeaaa7-730e-4197-9a90-18f4a8509ce3'}

        expected_data_dict = {'id': '14aeaaa7-730e-4197-9a90-18f4a8509ce3'}

        assert restricted_resource_show(context, data_dict) == {'success': True}
        logic_auth.get_resource_object.assert_called_once_with(context, expected_data_dict)
        authz.is_authorized.assert_called_once_with('package_update', context, {'id': '42'})
