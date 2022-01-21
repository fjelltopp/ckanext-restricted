# encoding: utf-8
from ckanext.restricted.logic import restricted_allowed_user_mail_body
import ckan.tests.factories as factories
import ckan.plugins.toolkit as toolkit
import pytest


@pytest.mark.usefixtures(u'clean_db')
@pytest.mark.usefixtures(u'clean_index')
@pytest.mark.ckan_config(u'ckan.plugins', u'restricted')
@pytest.mark.usefixtures(u'with_plugins')
@pytest.mark.usefixtures(u'with_request_context')
class TestAllowedUserEmail(object):

    def test_restricted_allowed_user_mail_body(self):
        admin = factories.User(name='admin')
        owner_org = factories.Organization(
            users=[{'name': admin['id'], 'capacity': 'admin'}]
        )
        dataset = factories.Dataset(
            owner_org=owner_org['id'],
            name='dataset-name',
            private=False,
            user=admin
        )
        resource = factories.Resource(
            package_id=dataset['id'],
            name='resource-name',
            restricted='{"level": "public"}'
        )
        stranger = factories.User(email='stranger@example.com')
        result = restricted_allowed_user_mail_body(stranger, resource)
        expected_resource_link = "{}/dataset/{}/resource/{}".format(
            toolkit.config.get('ckan.site_url'),
            dataset['id'],
            resource['id']
        )
        assert stranger['fullname'] in result
        assert expected_resource_link in result
