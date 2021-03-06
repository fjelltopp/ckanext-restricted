# coding: utf8

from __future__ import unicode_literals
from ckan.common import _
from ckan.common import request
import ckan.lib.base as base
from ckan.lib.base import render_jinja2
import ckan.lib.captcha as captcha
import ckan.lib.helpers as h
import ckan.lib.mailer as mailer
import ckan.lib.navl.dictization_functions as dictization_functions
import ckan.logic as logic
import ckan.model as model
import ckan.plugins.toolkit as toolkit

try:
    # CKAN 2.7 and later
    from ckan.common import config
except ImportError:
    # CKAN 2.6 and earlier
    from pylons import config

import simplejson as json

from logging import getLogger

log = getLogger(__name__)

DataError = dictization_functions.DataError
unflatten = dictization_functions.unflatten

render = base.render

SEND_SUCCESS = True
SEND_FAILED = False


class RestrictedController(toolkit.BaseController):

    def __before__(self, action, **env):
        base.BaseController.__before__(self, action, **env)
        try:
            context = {'model': base.model,
                       'user': base.c.user or base.c.author,
                       'auth_user_obj': base.c.userobj}
            logic.check_access('site_read', context)
        except logic.NotAuthorized:
            base.abort(401, _('Not authorized to see this page'))

    def _send_request_mail(self, data):
        try:
            dataset_name = data['package_name']
            resource_id = data['resource_id']
            context = {
                'model': model,
                'session': model.Session,
                'ignore_auth': True
            }
            dataset = toolkit.get_action('package_show')(
                context, {'id': dataset_name}
            )

            resource_link = toolkit.url_for(
                '{}_resource.read'.format(dataset['type']),
                id=dataset_name,
                resource_id=resource_id)
            resource_edit_link = toolkit.url_for(
                '{}_resource.edit'.format(dataset['type']),
                id=dataset_name,
                resource_id=resource_id)

            extra_vars = {
                'site_title': config.get('ckan.site_title'),
                'site_url': config.get('ckan.site_url'),
                'maintainer_name': data.get('maintainer_name', 'Maintainer'),
                'user_id': data.get('user_id', 'the user id'),
                'user_name': data.get('user_name', ''),
                'user_email': data.get('user_email', ''),
                'resource_name': data.get('resource_name', ''),
                'resource_link': config.get('ckan.site_url') + resource_link,
                'resource_edit_link': config.get('ckan.site_url') + resource_edit_link,
                'package_name': data.get('resource_name', ''),
                'message': data.get('message', ''),
                'admin_email_to': config.get('email_to', 'email_to_undefined')}

            body = render_jinja2('restricted/emails/restricted_access_request.txt', extra_vars)
            subject = \
                _('Access Request to resource {0} ({1}) from {2}').format(
                    data.get('resource_name', ''),
                    data.get('package_name', ''),
                    data.get('user_name', ''))

            email_dict = {
                data.get('maintainer_email'): extra_vars.get('maintainer_name'),
                extra_vars.get('admin_email_to'): '{} Admin'.format(extra_vars.get('site_title'))}

            dataset_org = toolkit.get_action('organization_show')(
                context, {
                    'id': dataset['owner_org'],
                    'include_users': True
                }
            )
            dataset_org_admin_ids = [
                user['id']
                for user in dataset_org['users']
                if user['capacity'] == 'admin'
            ]
            # fetch users directly from db to get non-hashed emails
            dataset_org_admins = model.Session.query(model.User).filter(
                model.User.id.in_(dataset_org_admin_ids),
                model.User.email.isnot(None)
            ).all()
            email_dict.update({
                user.email: user.name
                for user in dataset_org_admins
            })

            headers = {
                'CC': ",".join(email_dict.keys()),
                'reply-to': data.get('user_email')}

            # CC doesn't work and mailer cannot send to multiple addresses
            for email, name in email_dict.iteritems():
                mailer.mail_recipient(name, email, subject, body, headers=headers)

            # Special copy for the user (no links)
            email = data.get('user_email')
            name = data.get('user_name', 'User')

            extra_vars['resource_link'] = '[...]'
            extra_vars['resource_edit_link'] = '[...]'
            body = render_jinja2(
                'restricted/emails/restricted_access_request.txt', extra_vars)

            body_user = _(
                'Please find below a copy of the access '
                'request mail sent. \n\n >> {}'
            ).format(body.replace("\n", "\n >> "))

            mailer.mail_recipient(
                name, email, 'Fwd: ' + subject, body_user, headers=headers)
            return SEND_SUCCESS
        except mailer.MailerException as mailer_exception:
            log.error('Can not access request mail after registration.')
            log.error(mailer_exception)
        except Exception as e:
            log.exception("Failed to prepare the request email.", e)

        return SEND_FAILED

    def _send_request(self, context):

        try:
            data_dict = logic.clean_dict(unflatten(
                logic.tuplize_dict(logic.parse_params(request.params))))

            captcha.check_recaptcha(request)

        except logic.NotAuthorized:
            toolkit.abort(401, _('Not authorized to see this page'))
        except captcha.CaptchaError:
            error_msg = _('Bad Captcha. Please try again.')
            h.flash_error(error_msg)
            return self.restricted_request_access_form(
                package_id=data_dict.get('package_name'),
                resource_id=data_dict.get('resource'),
                data=data_dict)

        try:
            pkg = toolkit.get_action('package_show')(
                context, {'id': data_dict.get('package_name')})
            data_dict['pkg_dict'] = pkg
        except toolkit.ObjectNotFound:
            toolkit.abort(404, _('Dataset not found'))
        except Exception:
            toolkit.abort(404, _('Exception retrieving dataset to send mail'))

        # Validation
        errors = {}
        error_summary = {}

        if (data_dict['message'] == ''):
            msg = _('Missing Value')
            errors['message'] = [msg]
            error_summary['message'] = msg

        if len(errors) > 0:
            return self.restricted_request_access_form(
                data=data_dict,
                errors=errors,
                error_summary=error_summary,
                package_id=data_dict.get('package-name'),
                resource_id=data_dict.get('resource'))

        success = self._send_request_mail(data_dict)

        return render(
            'restricted/restricted_request_access_result.html',
            extra_vars={'data': data_dict, 'pkg_dict': pkg, 'success': success})

    def restricted_request_access_form(
            self, package_id, resource_id,
            data=None, errors=None, error_summary=None):
        """Redirects to form."""
        user_id = toolkit.c.user
        if not user_id:
            toolkit.abort(401, _('Access request form is available to logged in users only.'))

        context = {'model': model,
                   'session': model.Session,
                   'user': user_id,
                   'save': 'save' in request.params}

        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}

        if (context['save']) and not data and not errors:
            return self._send_request(context)

        if not data:
            data['package_id'] = package_id
            data['resource_id'] = resource_id

            try:
                user = toolkit.get_action('user_show')(context, {'id': user_id})
                data['user_id'] = user_id
                data['user_name'] = user.get('display_name', user_id)
                data['user_email'] = user.get('email', '')

                resource_name = ''

                pkg = toolkit.get_action('package_show')(context, {'id': package_id})
                data['package_name'] = pkg.get('name')
                resources = pkg.get('resources', [])
                for resource in resources:
                    if resource['id'] == resource_id:
                        resource_name = resource['name']
                        break
                else:
                    toolkit.abort(404, 'Dataset resource not found')
                # get mail
                contact_details = self._get_contact_details(pkg)
            except toolkit.ObjectNotFound:
                toolkit.abort(404, _('Dataset not found'))
            except Exception as e:
                log.warn('Exception Request Form: ' + repr(e))
                toolkit.abort(404, _(u'Exception retrieving dataset for the form ({})').format(str(e)))
            except Exception:
                toolkit.abort(404, _('Unknown exception retrieving dataset for the form'))

            data['resource_name'] = resource_name
            data['maintainer_email'] = contact_details.get('contact_email', '')
            data['maintainer_name'] = contact_details.get('contact_name', '')
        else:
            pkg = data.get('pkg_dict', {})

        extra_vars = {
            'pkg_dict': pkg, 'data': data,
            'errors': errors, 'error_summary': error_summary}
        return render(
            'restricted/restricted_request_access_form.html',
            extra_vars=extra_vars)

    def _send_organization_request(self, context):

        try:
            data_dict = logic.clean_dict(unflatten(
                logic.tuplize_dict(logic.parse_params(request.params))))

            captcha.check_recaptcha(request)

        except logic.NotAuthorized:
            toolkit.abort(401, _('Not authorized to see this page'))
        except captcha.CaptchaError:
            error_msg = _('Bad Captcha. Please try again.')
            h.flash_error(error_msg)
            return self.restricted_request_organization_form(
                data=data_dict
            )

        # Validation
        errors = {}
        error_summary = {}

        text_fields = [
            "organization_name",
            "organization_web",
            "organization_description",
            "reason",
        ]

        for field in text_fields:
            if data_dict.get(field, '') == '':
                msg = _('Missing Value')
                errors[field] = [msg]
                error_summary[field] = msg

        if len(errors) > 0:
            return self.restricted_request_organization_form(
                data=data_dict,
                errors=errors,
                error_summary=error_summary
            )

        success = self._send_organization_request_mail(data_dict)

        return render(
            'restricted/restricted_request_organization_result.html',
            extra_vars={'data': data_dict, 'pkg_dict': {}, 'success': success}
        )

    def _send_organization_request_mail(self, data):
        success = False
        try:

            extra_vars = {
                'site_title': config.get('ckan.site_title'),
                'site_url': config.get('ckan.site_url'),
                'user_id': data.get('user_id', 'the user id'),
                'user_name': data.get('user_name', ''),
                'user_email': data.get('user_email', ''),
                'organization_name': data.get('organization_name', ''),
                'organization_description': data.get('organization_description', ''),
                'organization_web': data.get('organization_web', ''),
                'reason': data.get('reason', ''),
                'admin_email_to': config.get('email_to', 'email_to_undefined')
            }

            body = render_jinja2(
                'restricted/emails/restricted_organization_request.txt',
                extra_vars
            )
            subject = _('Request to create new organisation {0}').format(
                data.get('organization_name', '')
            )
            email_dict = {
                extra_vars.get('admin_email_to'): '{} Admin'.format(
                    extra_vars.get('site_title')
                )
            }
            headers = {
                'CC': ",".join(email_dict.keys()),
                'reply-to': data.get('user_email')
            }

            # CC doesn't work and mailer cannot send to multiple addresses
            for email, name in email_dict.iteritems():
                mailer.mail_recipient(name, email, subject, body, headers=headers)

            # Special copy for the user (no links)
            email = data.get('user_email')
            name = data.get('user_name', 'User')

            body = render_jinja2(
                'restricted/emails/restricted_organization_request.txt', extra_vars)

            body_user = _(
                'Please find below a copy of the new organization request '
                'sent to the system administrators. \n\n >> {}'
            ).format(body.replace("\n", "\n >> "))

            mailer.mail_recipient(
                name, email, 'Fwd: ' + subject, body_user, headers=headers)
            success = True

        except mailer.MailerException as mailer_exception:
            log.error('Can not access request mail after registration.')
            log.error(mailer_exception)

        return success

    def restricted_request_organization_form(self, data=None, errors=None,
                                             error_summary=None):
        """Redirects to form."""
        user_id = toolkit.c.user
        if not user_id:
            toolkit.abort(
                401,
                _('Request organization form is available to logged in users only.')
            )

        context = {'model': model,
                   'session': model.Session,
                   'user': user_id,
                   'save': 'save' in request.params}

        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}

        if (context['save']) and not data and not errors:
            log.warning(data)
            return self._send_organization_request(data)

        user = toolkit.get_action('user_show')(context, {'id': user_id})
        data['user_id'] = user_id
        data['user_name'] = user.get('display_name', user_id)
        data['user_email'] = user.get('email', '')

        extra_vars = {
            'data': data, 'group_type': "organization",
            'errors': errors, 'error_summary': error_summary
        }
        return render(
            'restricted/restricted_request_organization_form.html',
            extra_vars=extra_vars
        )

    def _get_contact_details(self, pkg_dict):
        contact_email = ""
        contact_name = ""
        # Maintainer as Composite field
        try:
            contact_email = json.loads(
                pkg_dict.get('maintainer', '{}')).get('email', '')
            contact_name = json.loads(
                pkg_dict.get('maintainer', '{}')).get('name', 'Dataset Maintainer')
        except Exception:
            pass
        # Maintainer Directly defined
        if not contact_email:
            contact_email = pkg_dict.get('maintainer_email', '')
            contact_name = pkg_dict.get('maintainer', 'Dataset Maintainer')
        # 1st Author Directly defined
        if not contact_email:
            contact_email = pkg_dict.get('author_email', '')
            contact_name = pkg_dict.get('author', '')
        # First Author from Composite Repeating
        if not contact_email:
            try:
                author = json.loads(pkg_dict.get('author'))[0]
                contact_email = author.get('email', '')
                contact_name = author.get('name', 'Dataset Maintainer')
            except Exception:
                pass
        # CKAN instance Admin
        if not contact_email:
            contact_email = config.get('email_to', 'email_to_undefined')
            contact_name = 'CKAN Admin'
        return {'contact_email': contact_email, 'contact_name': contact_name}
