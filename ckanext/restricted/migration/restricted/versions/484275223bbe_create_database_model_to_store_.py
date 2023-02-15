"""Create database model to store permissions in database instead of plugin_extras

Revision ID: 484275223bbe
Revises: 
Create Date: 2023-01-17 16:50:23.131955

"""
import logging

from alembic import op
from sqlalchemy import orm

# revision identifiers, used by Alembic.
from ckan.model import Resource
from ckan.plugins import toolkit
from ckanext.restricted import logic

revision = '484275223bbe'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    update_schema(bind)
    migrate_restricted_schema(session)


def update_schema(bind):
    from ckanext.restricted.model import ResourceAccessControl, ResourceOrgAccessControl, ResourceUserAccessControl
    # TODO: Might require adding additional index on restricted_resource_user_access_control.user_id and
    #  restricted_resource_org_access_control.org_id. These columns are part of a composite primary key. On Oracle
    #  in such case when a query was against these columns (not the whole key) primary key index wasn't used, since
    #  this column was first one. Need to check psql EXPLAIN to be sure about query plan.

    # TODO: Using user_name and org_name as keys in table could be also used - would improve readability,
    #  but I'm not sure if we can trust it. I prefer ids instead.

    ResourceAccessControl.__table__.create(bind)
    ResourceOrgAccessControl.__table__.create(bind)
    ResourceUserAccessControl.__table__.create(bind)


def downgrade():
    op.drop_table('restricted_resource_access_control')
    op.drop_table('restricted_resource_user_access_control')
    op.drop_table('restricted_resource_org_access_control')


def migrate_restricted_schema(session):
    all_resources = session.query(Resource).all()

    for resource in all_resources:
        resource_dict = resource.as_dict()
        restricted_data = extract_restricted_data(resource_dict)

        if resource_has_defined_restrictions(restricted_data):
            migrate_resource_information(resource_dict, restricted_data, session)

    session.commit()


def convert_from_demodata(resource_dict):
    restricted_dict = {'level': 'public'}

    if resource_dict['restricted_allowed_orgs'] or resource_dict['restricted_allowed_users']:
        restricted_dict = {'level': 'restricted',
                           'allowed_organizations': resource_dict['restricted_allowed_orgs'].split(','),
                           'allowed_users': resource_dict['restricted_allowed_users'].split(',')}

    return restricted_dict


def extract_restricted_data(resource_dict):
    restricted_dict = {'level': 'public'}

    if resource_dict:
        if 'restricted_allowed_orgs' in resource_dict or 'restricted_allowed_users' in resource_dict:
            restricted_dict = convert_from_demodata(resource_dict)
        elif ('extras' in resource_dict and 'restricted' in resource_dict['extras']) or 'restricted' in resource_dict:
            restricted_dict = logic.restricted_get_restricted_dict(resource_dict)

    return restricted_dict


def migrate_resource_information(resource_dict, restricted_data, session):
    from ckanext.restricted.model import ResourceAccessControl

    session.add(ResourceAccessControl(resource_id=resource_dict['id'], level='restricted'))

    add_user_level_access_if_present(resource_dict, restricted_data, session)
    add_org_level_access_if_present(resource_dict, restricted_data, session)


def add_user_level_access_if_present(resource_dict, restricted_data, session):
    from ckanext.restricted.model import ResourceUserAccessControl

    context = {
        'ignore_auth': True
    }

    if 'allowed_users' in restricted_data:
        for user in restricted_data['allowed_users']:
            if user:
                user_data = toolkit.get_action('user_show')(context, {'id': user})

                if not user_data:
                    raise Exception(f"Cannot find user {user} defined as having access via restricted plugin")

                user_id = user_data['id']
                session.add(ResourceUserAccessControl(resource_id=(resource_dict['id']), user_id=user_id))


def add_org_level_access_if_present(resource_dict, restricted_data, session):
    from ckanext.restricted.model import ResourceOrgAccessControl

    if 'allowed_organizations' in restricted_data:
        for org in restricted_data['allowed_organizations']:
            if org:
                org_data = toolkit.get_action('organization_show')({'ignore_auth': True}, {'id': org})

                if not org_data:
                    raise Exception(f"Cannot find organization {org} defined as having access via restricted plugin")

                org_id = org_data['id']
                session.add(ResourceOrgAccessControl(resource_id=resource_dict['id'], org_id=org_id))


def resource_has_defined_restrictions(restricted_data):
    return restricted_data['level'] == 'restricted'
