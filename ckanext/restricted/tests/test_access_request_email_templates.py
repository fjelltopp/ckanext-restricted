# encoding: utf-8
import ckan.tests.factories as factories
from ckan.lib.helpers import url_for
import ckan.plugins.toolkit as toolkit
import pytest
import mock


@pytest.mark.usefixtures(u'clean_db')
@pytest.mark.usefixtures(u'clean_index')
@pytest.mark.ckan_config(u'ckan.plugins', u'restricted image_view recline_view')
@pytest.mark.usefixtures(u'with_plugins')
@pytest.mark.usefixtures(u'with_request_context')
class TestAccessRequestEmailTemplate(object):

    @mock.patch('ckan.lib.mailer.mail_recipient')
    def test_restricted_access_request_template_vars(self, mocked_mail_recipient, app):

        admin_1 = factories.User()
        admin_2 = factories.User()
        owner_org = factories.Organization(
            users=[
                {'name': admin_1['id'], 'capacity': 'admin'},
                {'name': admin_2['id'], 'capacity': 'admin'},
            ]
        )

        # admin_1 creates a dataset
        dataset = factories.Dataset(
            owner_org=owner_org['id'],
            name='dataset-name',
            private=False,
            user=admin_1
        )
        resource = factories.Resource(
            package_id=dataset['id'],
            name='resource-name',
            restricted='{"level": "public"}'
        )

        # stranger requests access to dataset
        stranger = factories.User()

        request_access_url = url_for(
            controller='ckanext.restricted.controller:RestrictedController',
            action='restricted_request_access_form',
            package_id=dataset['name'],
            resource_id=resource['id']
        )
        response = app.get(
            url=request_access_url,
            query_string={
                'message': 'give me access!',
                'maintainer_email': '',
                'save': 1
            },
            extra_environ={'REMOTE_USER': stranger['name']}
        )
        assert response.status_code == 200
        mocked_mail_recipient.assert_called()
        first_email = mocked_mail_recipient.call_args_list[0]
        email_body = first_email[0][3]

        resource_edit_link = toolkit.url_for(
            '{}_resource.edit'.format(dataset['type']),
            id=dataset['name'],
            resource_id=resource['id'])
        assert resource_edit_link in email_body

    @mock.patch('ckan.lib.mailer.mail_recipient')
    def test_restricted_access_request_template_encoding(self, mocked_mail_recipient, app):

        admin_1 = factories.User()
        admin_2 = factories.User()
        owner_org = factories.Organization(
            users=[
                {'name': admin_1['id'], 'capacity': 'admin'},
                {'name': admin_2['id'], 'capacity': 'admin'},
            ]
        )

        # admin_1 creates a dataset
        dataset = factories.Dataset(
            owner_org=owner_org['id'],
            name='name',
            private=False,
            user=admin_1
        )
        resource = factories.Resource(
            package_id=dataset['id'],
            name='name',
            restricted='{"level": "public"}'
        )

        # stranger requests access to dataset
        stranger = factories.User()
        request_access_url = url_for(
            controller='ckanext.restricted.controller:RestrictedController',
            action='restricted_request_access_form',
            package_id=dataset['id'],
            resource_id=resource['id']
        )
        response = app.get(
            url=request_access_url,
            query_string={
                'package_name': dataset['id'],
                'resource': resource['id'],
                'message': 'aaaa',
                'maintainer_email': '',
                'save': 1
            },
            extra_environ={'REMOTE_USER': stranger['name']}
        )
        assert response.status_code == 200

        mocked_mail_recipient.assert_called()
        first_email = mocked_mail_recipient.call_args_list[0]
        email_body = first_email[0][3]
        assert '&amp;' not in email_body
