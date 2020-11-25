"""Tests for plugin.py."""
# encoding: utf-8
from ckan.tests import helpers
import ckan.tests.factories as factories
import ckan.logic as logic
import logging
from ckan.lib.base import render_snippet
from ckan.lib.helpers import url_for
from pprint import pformat
import mock
import pytest

log = logging.getLogger(__name__)


@pytest.mark.usefixtures(u'clean_db')
@pytest.mark.usefixtures(u'clean_index')
@pytest.mark.ckan_config(u'ckan.plugins', u'restricted image_view recline_view')
@pytest.mark.usefixtures(u'with_plugins')
@pytest.mark.usefixtures(u'with_request_context')
class TestRestrictedPlugin(object):
    """Tests for the ckanext.example_iauthfunctions.plugin module.
    Specifically tests that overriding parent auth functions will cause
    child auth functions to use the overridden version.
    """

    def test_basic_access(self):
        """Normally organization admins can delete resources
        Our plugin prevents this by blocking delete organization.

        Ensure the delete button is not displayed (as only resource delete
        is checked for showing this)

        """

        owner = factories.User()
        access = factories.User()
        owner_org = factories.Organization(
            users=[{'name': owner['id'], 'capacity': 'admin'}]
        )
        dataset = factories.Dataset(owner_org=owner_org['id'], private=True)
        resource = factories.Resource(package_id=dataset['id'])

        assert logic.check_access('package_show', {'user': owner['name']}, {'id': dataset['id']})
        assert logic.check_access('resource_show', {'user': owner['name']}, {'id': resource['id']})
        with pytest.raises(logic.NotAuthorized):
            logic.check_access('package_show', {'user': access['name']}, {'id': dataset['id']})
        with pytest.raises(logic.NotAuthorized):
            logic.check_access('resource_show', {'user': access['name']}, {'id': resource['id']})

    def test_public_package_restricted_resource(self):
        """Normally organization admins can delete resources
        Our plugin prevents this by blocking delete organization.

        Ensure the delete button is not displayed (as only resource delete
        is checked for showing this)

        """

        owner = factories.User()
        org_user = factories.User()
        access = factories.User()
        owner_org = factories.Organization(
            users=[{'name': owner['id'], 'capacity': 'admin'},
                   {'name': org_user['id'], 'capacity': 'member'}]
        )
        dataset = factories.Dataset(owner_org=owner_org['id'], private=False)
        resource = factories.Resource(package_id=dataset['id'])

        assert logic.check_access('package_show', {'user': access['name']}, {'id': dataset['id']})
        assert logic.check_access('resource_show', {'user': org_user['name']}, {'id': resource['id']})

        with pytest.raises(logic.NotAuthorized):
            logic.check_access('resource_show', {'user': access['name']}, {'id': resource['id']})

    def test_public_resource(self):
        """Normally organization admins can delete resources
        Our plugin prevents this by blocking delete organization.

        Ensure the delete button is not displayed (as only resource delete
        is checked for showing this)

        """

        owner = factories.User()
        access = factories.User()
        owner_org = factories.Organization(
            users=[{'name': owner['id'], 'capacity': 'admin'}]

        )
        dataset = factories.Dataset(owner_org=owner_org['id'], private=False)
        resource = factories.Resource(package_id=dataset['id'],
                                      restricted='{"level": "public"}')

        assert logic.check_access('package_show', {'user': access['name']}, {'id': dataset['id']})
        assert logic.check_access('resource_show', {'user': access['name']}, {'id': resource['id']})

    def test_allow_users(self):
        """Normally organization admins can delete resources
        Our plugin prevents this by blocking delete organization.

        Ensure the delete button is not displayed (as only resource delete
        is checked for showing this)

        """

        owner = factories.User()
        access = factories.User()
        access2 = factories.User()
        owner_org = factories.Organization(
            users=[{'name': owner['id'], 'capacity': 'admin'}]

        )
        dataset = factories.Dataset(owner_org=owner_org['id'], private=False)
        restrict_string = '{"level": "restricted", "allowed_users":["%s"]}' % (access["name"],)
        resource = factories.Resource(package_id=dataset['id'],
                                      restricted=restrict_string)

        assert logic.check_access('resource_show', {'user': access['name']}, {'id': resource['id']})
        with pytest.raises(logic.NotAuthorized):
            logic.check_access('resource_show', {'user': access2['name']}, {'id': resource['id']})

    def test_allow_organizations(self):
        """Normally organization admins can delete resources
        Our plugin prevents this by blocking delete organization.

        Ensure the delete button is not displayed (as only resource delete
        is checked for showing this)

        """

        owner = factories.User()
        access = factories.User()
        access2 = factories.User()
        owner_org = factories.Organization(
            users=[{'name': owner['id'], 'capacity': 'admin'}]

        )
        access_org = factories.Organization(
            users=[{'name': access['id'], 'capacity': 'admin'}]
        )

        dataset = factories.Dataset(owner_org=owner_org['id'], private=False)
        restrict_string = '{"level": "restricted", "allowed_organizations":["%s"]}' % (access_org["name"],)
        resource = factories.Resource(package_id=dataset['id'],
                                      restricted=restrict_string)

        assert logic.check_access('resource_show', {'user': access['name']}, {'id': resource['id']})
        with pytest.raises(logic.NotAuthorized):
            logic.check_access('resource_show', {'user': access2['name']}, {'id': resource['id']})

    def _two_users_with_two_restricted_resources(self):
        restrict_string = '{{"level": "restricted", "allowed_organizations":["{!s}"]}}'
        user = factories.User()
        user_org = factories.Organization(
            users=[{'name': user['id'], 'capacity': 'admin'}]

        )
        user_dataset = factories.Dataset(user_org=user_org['id'], private=False)
        user_resource = factories.Resource(package_id=user_dataset['id'],
                                           name="user-resource",
                                           restricted=restrict_string.format(user_org["name"]))
        other = factories.User()
        other_org = factories.Organization(users=[{'name': other['id'], 'capacity': 'admin'}])
        other_dataset = factories.Dataset(other_org=other_org['id'], private=False)
        other_resource = factories.Resource(package_id=other_dataset['id'],
                                            name="other-resource",
                                            restricted=restrict_string.format(other_org["name"]))
        return user, user_resource, other, other_resource

    def test_user_can_search_only_accessible_resources(self):
        # given:
        user, user_resource, other, other_resource = self._two_users_with_two_restricted_resources()
        # when:
        context = {
            'ignore_auth': False,
            'user': other['name']
        }
        resource_search = helpers.call_action(
            'resource_search',
            context,
            query='name:resource',
            hide_inaccessible_resources=True
        )
        # then:
        assert resource_search['count'] == 1
        assert len(resource_search['results']) == 1
        assert resource_search['results'][0] == other_resource

    def test_user_can_search_all_resources(self):
        # given:
        user, user_resource, other, other_resource = self._two_users_with_two_restricted_resources()
        # when:
        context = {
            'ignore_auth': False,
            'user': other['name']
        }
        resource_search = helpers.call_action(
            'resource_search',
            context,
            query='name:resource'
        )
        # then:
        assert resource_search['count'] == 2
        for r in [user_resource, other_resource]:
            assert r in resource_search['results']

    def _two_users_one_package_two_resources_one_restricted(self):
        user = factories.User()
        other = factories.User()
        organisation = factories.Organization(
            users=[
                {'name': user['id'], 'capacity': 'admin'}
            ]

        )
        restrict_other = '{{"level": "restricted", "allowed_users":["{}"]}}'.format(other["name"])
        restrict_org = '{{"level": "restricted", "allowed_organisations":["{}"]}}'.format(organisation["name"])
        dataset = factories.Dataset(owner_org=organisation['id'], private=False)
        other_resource = factories.Resource(package_id=dataset['id'],
                                            name="other-resource",
                                            restricted=restrict_other)
        org_resource = factories.Resource(package_id=dataset['id'],
                                          name="org-resource",
                                          restricted=restrict_org)
        return dataset, other, other_resource, org_resource

    def test_user_can_see_only_accessible_resource_in_package_show(self):
        # given:
        dataset, other, other_resource, org_resource = self._two_users_one_package_two_resources_one_restricted()
        # when:
        context = {
            'ignore_auth': False,
            'user': other['name']
        }
        package_show = helpers.call_action(
            'package_show',
            context,
            id=dataset['id'],
            hide_inaccessible_resources=True
        )
        # then:
        assert package_show['num_resources'] == 1
        assert len(package_show['resources']) == 1
        assert package_show['resources'][0]['id'] == other_resource['id']

    def test_user_can_see_all_resource_in_package_show(self):
        # given:
        dataset, other, other_resource, org_resource = self._two_users_one_package_two_resources_one_restricted()
        # when:
        context = {
            'ignore_auth': False,
            'user': other['name']
        }
        package_show = helpers.call_action(
            'package_show',
            context,
            id=dataset['id']
        )
        # then:
        assert package_show['num_resources'] == 2
        assert len(package_show['resources']) == 2
        resources_ids = [x['id'] for x in package_show['resources']]
        for r in [org_resource['id'], other_resource['id']]:
            assert r in resources_ids

    def test_user_can_see_only_accessible_resource_in_package_search(self):
        # given:
        dataset, other, other_resource, org_resource = self._two_users_one_package_two_resources_one_restricted()
        # when:
        context = {
            'ignore_auth': False,
            'user': other['name']
        }
        package_search = helpers.call_action(
            'package_search',
            context,
            q=dataset['title'],
            hide_inaccessible_resources=True
        )
        # then:
        package = package_search['results'][0]
        assert package['num_resources'] == 1
        assert len(package['resources']) == 1
        assert package['resources'][0]['id'] == other_resource['id']

    @pytest.mark.ckan_config(u'ckan.auth.allow_dataset_collaborators', 'true')
    def test_collaborator_overrides_restricted_settings(self):
        dataset, other, other_resource, org_resource = self._two_users_one_package_two_resources_one_restricted()
        helpers.call_action(
            'package_collaborator_create',
            id=dataset['id'], user_id=other['name'], capacity='member'
        )
        context = {
            'ignore_auth': False,
            'user': other['name']
        }
        assert logic.check_access('resource_show', context, {'id': org_resource['id']})
        assert logic.check_access('resource_show', context, {'id': other_resource['id']})

    def test_org_member_see_only_accessible_resources_in_package_search(self):
        """
        A bug was flagged where the hide_inaccessible_resources param in
        the package_search action was causing resources only to be visible to
        organisation "editors" and "admins" .  Organisation "members" with read
        but not write privileges could not see the resources in a
        package_search action.  This test checks that org members can see their
        resources in a package_search action with
        hide_inaccessible_resources=True.
        """
        user = factories.User()
        org = factories.Organization(
            users=[{'name': user['id'], 'capacity': 'member'}]
        )
        restricted = '{{"level": "restricted", "allowed_organisations":[], "allowed_users":[]}}'
        dataset = factories.Dataset(owner_org=org['id'], private=False)
        resource = factories.Resource(
            package_id=dataset['id'],
            restricted=restricted
        )
        context = {
            'ignore_auth': False,
            'user': user['name']
        }
        package_search = helpers.call_action(
            'package_search',
            context,
            q=dataset['title'],
            hide_inaccessible_resources=True
        )
        package = package_search['results'][0]
        assert package['num_resources'] == 1
        assert len(package['resources']) == 1
        assert package['resources'][0]['id'] == resource['id']

    def test_restricted_string_snippet(self):
        """
        """
        sysadmin = factories.Sysadmin()
        org = factories.Organization(
            users=[{'name': sysadmin['id'], 'capacity': 'admin'}]
        )
        dataset = factories.Dataset(owner_org=org['id'])

        restricted1 = """{
            "level": "restricted",
            "allowed_organizations": "fjelltopp,unaids,fjelltopp",
            "allowed_users":""
        }"""
        resource1 = factories.Resource(
            package_id=dataset['id'],
            restricted=restricted1
        )

        restricted2 = """{
            "level": "restricted",
            "allowed_organizations": "",
            "allowed_users":"test_user_0,test_user_1"
        }"""
        resource2 = factories.Resource(
            package_id=dataset['id'],
            restricted=restricted2
        )

        restricted3 = """{
            "level": "restricted",
            "allowed_organizations": "fjelltopp,unaids,fjelltopp",
            "allowed_users":"test_user_0,test_user_1"
        }"""
        resource3 = factories.Resource(
            package_id=dataset['id'],
            restricted=restricted3
        )

        restricted4 = """{
            "level": "restricted",
            "allowed_organizations": "",
            "allowed_users":""
        }"""
        resource4 = factories.Resource(
            package_id=dataset['id'],
            restricted=restricted4
        )

        html1 = render_snippet(
            'restricted/restricted_string.html',
            res=resource1,
            pkg=dataset
        )
        log.debug(pformat(html1))
        expected = (
            "Access restricted to specific <a href='#' data-module"
            "='restricted_popup' data-module-title='Access granted to "
            "organizations' data-module-content='fjelltopp<br />unaids"
            "<br />" + org['name'] + "'>organizations</a>"
        )
        assert expected in html1

        html2 = render_snippet(
            'restricted/restricted_string.html',
            res=resource2,
            pkg=dataset
        )
        log.debug(pformat(html2))
        expected = (
            "Access restricted to specific <a href='#' "
            "data-module='restricted_popup' data-module-title='Access "
            "granted to users' data-module-content='test_user_0<br />"
            "test_user_1'>users</a>"
        )
        assert expected in html2

        html3 = render_snippet(
            'restricted/restricted_string.html',
            res=resource3,
            pkg=dataset
        )
        log.debug(pformat(html3))
        expected = (
            "Access restricted to specific <a href='#' "
            "data-module='restricted_popup' data-module-title='Access "
            "granted to organizations' data-module-content='fjelltopp<br />"
            "unaids<br />" + org['name'] + "'>organizations</a> and "
            "<a href='#' data-module='restricted_popup' "
            "data-module-title='Access granted to users' "
            "data-module-content='test_user_0<br />test_user_1'>users</a>."
        )
        assert expected in html3

        html4 = render_snippet(
            'restricted/restricted_string.html',
            res=resource4,
            pkg=dataset
        )
        log.debug(pformat(html4))
        expected = (
            'Access restricted to members of <a href="/organization/'
            '{}">{}</a>'.format(org['name'], org['title'])
        )
        assert expected in html4

    @mock.patch('ckan.lib.mailer.mail_recipient')
    def test_all_org_admins_are_emailed_on_request_access(self, mocked_mail_recipient, app):
        
        # create two admins and one regular member of an org
        user_1 = factories.User(email='user_1@example.com')
        user_2 = factories.User(email='user_2@example.com')
        user_3 = factories.User(email='user_3@example.com')
        owner_org = factories.Organization(
            users=[
                {'name': user_1['id'], 'capacity': 'admin'},
                {'name': user_2['id'], 'capacity': 'admin'},
                {'name': user_3['id'], 'capacity': 'member'}
            ]
        )

        # user_1 creates a dataset
        dataset = factories.Dataset(
            owner_org=owner_org['id'],
            name='name',
            private=False,
            user=user_1
        )
        resource = factories.Resource(
            package_id=dataset['id'],
            name='name',
            restricted='{"level": "public"}'
        )

        # user_4 requests access to dataset
        user_4 = factories.User(email='user_4@example.com')
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
                'package_name': dataset['id'],
                'resource': resource['id'],
                'message': 'aaaa',
                'maintainer_email': maintainer_email,
                'save': 1
            },
            extra_environ={'REMOTE_USER': user_3['name']}
        )
        assert response.status_code == 200

        mocked_mail_recipient.assert_called()
        email_recipients = [
            x[0][1] # recipient_email
            for x in mocked_mail_recipient.call_args_list
        ]
        assert maintainer_email in email_recipients
        assert user_1['email'] in email_recipients
        assert user_2['email'] in email_recipients
        assert user_3['email'] not in email_recipients, \
            'Only org admins should be emailed'