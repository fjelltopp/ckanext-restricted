# encoding: utf-8
import ckan.tests.factories as factories
from ckan.lib.helpers import url_for
import pytest
import mock


@pytest.mark.usefixtures(u'clean_db')
@pytest.mark.usefixtures(u'clean_index')
@pytest.mark.ckan_config(u'ckan.plugins', u'restricted image_view recline_view')
@pytest.mark.usefixtures(u'with_plugins')
@pytest.mark.usefixtures(u'with_request_context')
class TestAccessRequest(object):

    @mock.patch('ckan.lib.mailer.mail_recipient')
    def test_request_access_all_admins_are_emailed(self, mocked_mail_recipient, app):

        admin_1 = factories.User(email='admin_1@example.com')
        admin_2 = factories.User(email='admin_2@example.com')
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
        stranger = factories.User(email='stranger@example.com')
        maintainer_email = 'maintainer_email@example.com'
        request_access_url = url_for(
            controller='ckanext.restricted.controller:RestrictedController',
            action='restricted_request_access_form',
            package_id=dataset['id'],
            resource_id=resource['id']
        )
        response = app.get(
            url=request_access_url,
            query_string={
                'package_name': dataset['name'],
                'resource_id': resource['id'],
                'message': 'aaaa',
                'maintainer_email': maintainer_email,
                'save': 1
            },
            extra_environ={'REMOTE_USER': stranger['name']}
        )
        assert response.status_code == 200

        mocked_mail_recipient.assert_called()
        email_recipients = [
            x[0][1]  # recipient_email
            for x in mocked_mail_recipient.call_args_list
        ]
        assert maintainer_email in email_recipients
        assert admin_1['email'] in email_recipients
        assert admin_2['email'] in email_recipients

    @mock.patch('ckan.lib.mailer.mail_recipient')
    def test_request_access_non_admins_are_not_emailed(self, mocked_mail_recipient, app):

        admin_1 = factories.User(email='admin_1@example.com')
        editor = factories.User(email='editor@example.com')
        member = factories.User(email='member@example.com')
        owner_org = factories.Organization(
            users=[
                {'name': admin_1['id'], 'capacity': 'admin'},
                {'name': editor['id'], 'capacity': 'editor'},
                {'name': member['id'], 'capacity': 'member'}
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
        stranger = factories.User(email='stranger@example.com')
        maintainer_email = 'maintainer_email@example.com'
        request_access_url = url_for(
            controller='ckanext.restricted.controller:RestrictedController',
            action='restricted_request_access_form',
            package_id=dataset['id'],
            resource_id=resource['id']
        )
        response = app.get(
            url=request_access_url,
            query_string={
                'package_name': dataset['name'],
                'resource_id': resource['id'],
                'message': 'aaaa',
                'maintainer_email': maintainer_email,
                'save': 1
            },
            extra_environ={'REMOTE_USER': stranger['name']}
        )
        assert response.status_code == 200

        mocked_mail_recipient.assert_called()
        email_recipients = [
            x[0][1]  # recipient_email
            for x in mocked_mail_recipient.call_args_list
        ]
        assert editor['email'] not in email_recipients, 'Only org admins should be emailed, not editors'
        assert member['email'] not in email_recipients, 'Only org admins should be emailed, not members'

    @mock.patch('ckan.lib.mailer.mail_recipient')
    def test_org_admin_is_emailed_if_no_maintaner_on_request_access(self, mocked_mail_recipient, app):

        admin = factories.User(email='admin_1@example.com')
        owner_org = factories.Organization(
            users=[
                {'name': admin['id'], 'capacity': 'admin'},
            ]
        )

        dataset = factories.Dataset(
            owner_org=owner_org['id'],
            name='name',
            private=False,
            user=admin
        )
        resource = factories.Resource(
            package_id=dataset['id'],
            name='name',
            restricted='{"level": "public"}'
        )

        # stranger requests access to dataset
        stranger = factories.User(email='stranger@example.com')
        request_access_url = url_for(
            controller='ckanext.restricted.controller:RestrictedController',
            action='restricted_request_access_form',
            package_id=dataset['id'],
            resource_id=resource['id']
        )
        response = app.get(
            url=request_access_url,
            query_string={
                'package_name': dataset['name'],
                'resource_id': resource['id'],
                'message': 'aaaa',
                'maintainer_email': '',
                'save': 1
            },
            extra_environ={'REMOTE_USER': stranger['name']}
        )
        assert response.status_code == 200

        mocked_mail_recipient.assert_called()
        email_recipients = [
            x[0][1]  # recipient_email
            for x in mocked_mail_recipient.call_args_list
        ]
        assert admin['email'] in email_recipients, 'Only org admins should be emailed, not members'
