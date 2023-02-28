# coding: utf8

from __future__ import unicode_literals
import ckan.authz as authz
import ckan.logic.auth as logic_auth
import ckan.plugins.toolkit as toolkit
from ckanext.restricted import logic

from logging import getLogger
log = getLogger(__name__)


@toolkit.auth_allow_anonymous_access
def restricted_resource_show(context, data_dict=None):
    # Ensure user who can edit the package can see the resource
    resource = data_dict.get('resource', context.get('resource', {}))
    if not resource:
        extract_id_from_id_contactenated_with_activity_id(data_dict)
        resource = logic_auth.get_resource_object(context, data_dict)
    if type(resource) is not dict:
        resource = resource.as_dict()

    if authz.is_authorized(
            'package_update', context,
            {'id': resource.get('package_id')}).get('success'):
        return ({'success': True})

    user_name = logic.restricted_get_username_from_context(context)

    package = data_dict.get('package', {})
    if not package:
        model = context['model']
        package = model.Package.get(resource.get('package_id'))
        package = package.as_dict()

    return (logic.restricted_check_user_resource_access(
        user_name, resource, package))


def extract_id_from_id_contactenated_with_activity_id(data_dict):
    if 'id' in data_dict and '/' in data_dict['id']:
        data_dict['id'] = data_dict['id'].split('/')[0]


def logged_in(context, data_dict=None):
    log.warning(context['user'])
    if context['user']:
        return {'success': True, 'msg': 'No one is allowed to create groups'}
    else:
        return {'success': False, 'msg': 'You must be logged in to see this'}
