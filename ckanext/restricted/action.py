# coding: utf8

from __future__ import unicode_literals
import ckan.authz as authz
import ckan.logic.auth as logic_auth
from ckan import model
from ckan.common import _

from ckan.lib.base import render_jinja2
from ckan.lib.mailer import mail_recipient
from ckan.lib.mailer import MailerException
import ckan.logic
import ckan.plugins as p
from ckan.logic.action.create import user_create
from ckan.logic.action.get import package_search
from ckan.logic.action.get import package_show
from ckan.logic.action.get import resource_search
from ckan.plugins import toolkit

from ckanext.restricted import auth
from ckanext.restricted import logic
import json

try:
    # CKAN 2.7 and later
    from ckan.common import config
except ImportError:
    # CKAN 2.6 and earlier
    from pylons import config

from logging import getLogger

log = getLogger(__name__)
debug_log = getLogger('debug')

_get_or_bust = ckan.logic.get_or_bust

NotFound = ckan.logic.NotFound


def restricted_user_create_and_notify(context, data_dict):

    def body_from_user_dict(user_dict):
        body = ''
        for key, value in user_dict.items():
            body += '* {0}: {1}\n'.format(
                key.upper(), value if isinstance(value, str) else str(value))
        return body

    user_dict = user_create(context, data_dict)

    # Send your email, check ckan.lib.mailer for params
    try:
        name = _('CKAN System Administrator')
        email = config.get('email_to')
        if not email:
            raise MailerException('Missing "email-to" in config')

        subject = _('New Registration: {0} ({1})').format(
            user_dict.get('name', _(u'new user')), user_dict.get('email'))

        extra_vars = {
            'site_title': config.get('ckan.site_title'),
            'site_url': config.get('ckan.site_url'),
            'user_info': body_from_user_dict(user_dict)}

        body = render_jinja2(
            'restricted/emails/restricted_user_registered.txt', extra_vars)

        mail_recipient(name, email, subject, body)

    except MailerException as mailer_exception:
        log.error('Cannot send mail after registration')
        log.error(mailer_exception)

    return (user_dict)

@toolkit.chained_action
@toolkit.side_effect_free
def resource_view_list(resource_view_list, context, data_dict):
    try:
        return resource_view_list(context, data_dict)
    except toolkit.NotAuthorized:
        return []


@toolkit.side_effect_free
def restricted_package_show(context, data_dict, package_metadata=None):

    hide_inaccessible_resources = p.toolkit.asbool(data_dict.get('hide_inaccessible_resources', False))
    debug_logging = p.toolkit.asbool(data_dict.pop('debug_logging', False))
    debug_request_id = data_dict.pop('debug_request_id', "")

    if not package_metadata:
        package_metadata = package_show(context, data_dict)
    else:
        # context['package'] needs to be set for ckan package auth functions to work
        # this is set by package_show
        # if package_show not called, context['package'] needs to be set manually
        pkg = model.Package.get(package_metadata['id'])
        if not pkg:
            raise toolkit.ObjectNotFound(toolkit._('Dataset not found'))
        context['package'] = pkg

    if debug_logging:
        debug_log.debug(u"{} restricted_package_show for package {}".format(
            debug_request_id,
            package_metadata.get('name')
        ))

    # Ensure user who can edit can see the resource
    if authz.is_authorized(
            'package_update', context, package_metadata).get('success', False):

        if debug_logging:
            debug_log.debug(
                u"{} restricted_package_show granted - user authorised to edit dataset".format(
                    debug_request_id
                )
            )

            package = logic_auth.get_package_object(context, package_metadata)
            user = context.get('user')
            user_obj = context['model'].User.get(user)
            if package.owner_org:
                owner_org_editor = authz.has_user_permission_for_group_or_org(
                    package.owner_org, user, 'update_dataset'
                )
                collaborator = authz.user_is_collaborator_on_dataset(
                    user_obj.id, package.id, ['admin', 'editor']
                )
                if owner_org_editor:
                    debug_log.debug(
                        u"{} restricted_package_show user is an editor of owner org".format(
                            debug_request_id
                        )
                    )
                elif collaborator:
                    debug_log.debug(
                        u"{} restricted_package_show user is an editor collaborator of dataset".format(
                            debug_request_id
                        )
                    )
                else:
                    debug_log.debug(
                        u"{} restricted_package_show user is not a collaborator or editor of owner_org".format(
                            debug_request_id
                        )
                    )

            debug_log.debug(context)

        return package_metadata

    # Custom authorization
    if isinstance(package_metadata, dict):
        restricted_package_metadata = dict(package_metadata)
    else:
        restricted_package_metadata = dict(package_metadata.for_json())

    # restricted_package_metadata['resources'] = _restricted_resource_list_url(
    #     context, restricted_package_metadata.get('resources', []))
    resources = restricted_package_metadata.get('resources', [])

    if hide_inaccessible_resources:

        if debug_logging:
            debug_log.debug("{} restricted_package_show hiding inaccessible resources".format(
                debug_request_id
            ))

        resources = _restricted_resource_list_accessible_by_user(
            context,
            resources,
            package_dict=package_metadata,
            debug_logging=debug_logging,
            debug_request_id=debug_request_id
        )
        restricted_package_metadata['num_resources'] = len(resources)
    resources = _restricted_resource_list_hide_fields(context, resources)
    restricted_package_metadata['resources'] = resources

    return (restricted_package_metadata)


def _restricted_resource_list_accessible_by_user(context, resource_list, package_dict=None, debug_logging=False, debug_request_id=""):
    restricted_resources_list = []
    user_name = logic.restricted_get_username_from_context(context)
    user_obj = context.get('auth_user_obj')

    if debug_logging:
        debug_log.debug("{} _restricted_resource_list_accessible_by_user user_name {}".format(
            debug_request_id,
            user_name
        ))

    for resource in resource_list:
        resource_dict = dict(resource)
        if not package_dict:
            package_dict = package_show(context, {'id': resource_dict['package_id']})
        user_has_resource_access = logic.restricted_check_user_resource_access(
            user_name,
            resource_dict,
            package_dict,
            user_obj=user_obj,
            check_access_package_show=False,
            user_organization_dict=logic.get_organization_dict(user_name),
            debug_logging=debug_logging,
            debug_request_id=debug_request_id
        ).get('success', False)

        if user_has_resource_access:
            restricted_resources_list.append(resource_dict)
    return restricted_resources_list


@toolkit.side_effect_free
def restricted_resource_search(context, data_dict):
    hide_inaccessible_resources = p.toolkit.asbool(data_dict.get('hide_inaccessible_resources', False))

    resource_search_result = resource_search(context, data_dict)
    results = resource_search_result['results']
    if hide_inaccessible_resources:
        results = _restricted_resource_list_accessible_by_user(context, results)
    results = _restricted_resource_list_hide_fields(context, results)
    count = len(results)

    resource_search_result.update({'count': count, 'results': results})
    return resource_search_result


@toolkit.side_effect_free
def restricted_package_search(context, data_dict):
    # pop the param as ckan package search action doesn't support any extra parameters
    hide_inaccessible_resources = p.toolkit.asbool(data_dict.pop('hide_inaccessible_resources', False))

    debug_logging = p.toolkit.asbool(data_dict.pop('debug_logging', False))
    debug_request_id = data_dict.pop('debug_request_id', "")

    if debug_logging:
        debug_log.debug("{} restricted_package_search data_dict {}".format(
            debug_request_id,
            data_dict
        ))
        debug_log.debug("{} restricted_package_search hide_inaccessible_resources {}".format(
            debug_request_id,
            hide_inaccessible_resources
        ))
        debug_log.debug("{} restricted_package_search context {}".format(
            debug_request_id,
            context
        ))


    package_search_result = package_search(context, data_dict)

    if debug_logging:
        debug_log.debug("{} restricted_package_search context after package search {}".format(
            debug_request_id,
            context
        ))

    restricted_package_search_result = {}

    for key, value in package_search_result.items():
        if key == 'results':
            restricted_package_search_result_list = []
            for package in value:
                restricted_package_search_result_list.append(
                    restricted_package_show(
                        context,
                        {
                            'id': package.get('id'),
                            'hide_inaccessible_resources': hide_inaccessible_resources,
                            'debug_logging': debug_logging,
                            'debug_request_id': debug_request_id
                        },
                        package_metadata=package
                    )
                )
            restricted_package_search_result[key] = \
                restricted_package_search_result_list
        else:
            restricted_package_search_result[key] = value

    return restricted_package_search_result


@toolkit.side_effect_free
def restricted_check_access(context, data_dict):

    package_id = data_dict.get('package_id', False)
    resource_id = data_dict.get('resource_id', False)

    user_name = logic.restricted_get_username_from_context(context)

    if not package_id:
        raise ckan.logic.ValidationError('Missing package_id')
    if not resource_id:
        raise ckan.logic.ValidationError('Missing resource_id')

    log.debug("action.restricted_check_access: user_name = " + str(user_name))

    log.debug("checking package " + str(package_id))
    package_dict = ckan.logic.get_action('package_show')(dict(context, return_type='dict'), {'id': package_id})
    log.debug("checking resource")
    resource_dict = ckan.logic.get_action('resource_show')(dict(context, return_type='dict'), {'id': resource_id})

    return logic.restricted_check_user_resource_access(user_name, resource_dict, package_dict)

# def _restricted_resource_list_url(context, resource_list):
#     restricted_resources_list = []
#     for resource in resource_list:
#         authorized = auth.restricted_resource_show(
#             context, {'id': resource.get('id'), 'resource': resource}).get('success', False)
#         restricted_resource = dict(resource)
#         if not authorized:
#             restricted_resource['url'] = _('Not Authorized')
#         restricted_resources_list += [restricted_resource]
#     return restricted_resources_list


def _restricted_resource_list_hide_fields(context, resource_list):
    restricted_resources_list = []
    for resource in resource_list:
        # copy original resource
        restricted_resource = dict(resource)

        # get the restricted fields
        restricted_dict = logic.restricted_get_restricted_dict(restricted_resource)

        # hide other fields in restricted to everyone but dataset owner(s)
        if not authz.is_authorized(
                'package_update', context, {'id': resource.get('package_id')}
                ).get('success'):

            user_name = logic.restricted_get_username_from_context(context)

            # hide partially other allowed user_names (keep own)
            allowed_users = []
            for user in restricted_dict.get('allowed_users'):
                if len(user.strip()) > 0:
                    if user_name == user:
                        allowed_users.append(user_name)
                    else:
                        allowed_users.append(user[0:3] + '*****' + user[-2:])

            allowed_orgs = []
            for org in restricted_dict.get('allowed_organizations', []):
                if len(org.strip()) > 0:
                    allowed_orgs.append(org)

            new_restricted = json.dumps({
                'level': restricted_dict.get("level"),
                'allowed_users': ','.join(allowed_users),
                'allowed_organizations': ','.join(allowed_orgs)
            })
            extras_restricted = resource.get('extras', {}).get('restricted', {})
            if (extras_restricted):
                restricted_resource['extras']['restricted'] = new_restricted

            field_restricted_field = resource.get('restricted', {})
            if (field_restricted_field):
                restricted_resource['restricted'] = new_restricted

        restricted_resources_list += [restricted_resource]
    return restricted_resources_list
