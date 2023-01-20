"""Create database model to store permissions in database instead of plugin_extras

Revision ID: 484275223bbe
Revises: 
Create Date: 2023-01-17 16:50:23.131955

"""
from alembic import op
from ckan import model
from sqlalchemy import ForeignKey, Column, String

# revision identifiers, used by Alembic.
from ckan.model import Resource
from ckan.plugins import toolkit
from ckanext.restricted import logic

revision = '484275223bbe'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    update_schema()
    migrate_restricted_schema()


def update_schema():
    # TODO: Might require adding additional index on restricted_resource_user_access_control.user_id and
    #  restricted_resource_org_access_control.org_id. These columns are part of a composite primary key. On Oracle
    #  in such case when a query was against these columns (not the whole key) primary key index wasn't used, since
    #  this column was first one. Need to check psql EXPLAIN to be sure about query plan.

    # TODO: Using user_name and org_name as keys in table could be also used - would improve readability,
    #  but I'm not sure if we can trust it. I prefer ids instead.

    op.create_table(
        'restricted_resource_access_control',
        Column('resource_id', String,
               ForeignKey('resource.id', onupdate='CASCADE', ondelete='CASCADE'),
               primary_key=True),
        Column('level', String, nullable=False)
    )
    op.create_table(
        'restricted_resource_user_access_control',
        Column('resource_id', String,
               ForeignKey('resource.id', onupdate='CASCADE', ondelete='CASCADE')),
        Column('user_id', String, ForeignKey('user.id', onupdate='CASCADE', ondelete='CASCADE'))
    )
    op.create_primary_key(
        'restricted_resource_user_access_control_pk', 'restricted_resource_user_access_control',
        ['resource_id', 'user_id']
    )
    op.create_table(
        'restricted_resource_org_access_control',
        Column('resource_id', String,
               ForeignKey('resource.id', onupdate='CASCADE', ondelete='CASCADE')),
        Column('org_id', String, ForeignKey('group.id', onupdate='CASCADE', ondelete='CASCADE'))
    )
    op.create_primary_key(
        'restricted_resource_org_access_control_pk', 'restricted_resource_org_access_control',
        ['resource_id', 'org_id']
    )


def downgrade():
    op.drop_table('restricted_resource_access_control')
    op.drop_table('restricted_resource_user_access_control')
    op.drop_table('restricted_resource_org_access_control')
    pass


def migrate_restricted_schema():
    # TODO: Acutally this code didn't work well in my env, because I couldn't run 'adx demodata'
    #  due to some weird errors with dependencies.
    #  Since I didn't have 'unaids' organization my migration was breaking.
    #  When I specifically not migrated 'unaids' it worked ok though.

    all_resources = model.Session.query(Resource).all()

    for resource in all_resources:
        resource_dict = resource.as_dict()
        restricted_data = logic.restricted_get_restricted_dict(resource_dict)

        if resource_has_defined_restrictions(restricted_data):
            migrate_resource_information(resource_dict, restricted_data)

    model.repo.commit()


def migrate_resource_information(resource_dict, restricted_data):
    from ckanext.restricted.model import ResourceAccessControl

    rac = ResourceAccessControl(resource_id=resource_dict['id'], level='restricted')

    model.Session.add(rac)

    add_user_level_access_if_present(resource_dict, restricted_data)
    add_org_level_access_if_present(resource_dict, restricted_data)

    model.repo.commit()


def add_user_level_access_if_present(resource_dict, restricted_data):
    from ckanext.restricted.model import ResourceUserAccessControl

    context = {
        'ignore_auth': True
    }
    if restricted_data['allowed_users']:
        for user in restricted_data['allowed_users']:
            if user:
                user_id = toolkit.get_action('user_show')(context, {'id': user})['id']
                model.Session.add(ResourceUserAccessControl(resource_id=resource_dict['id'], user_id=user_id))


def add_org_level_access_if_present(resource_dict, restricted_data):
    from ckanext.restricted.model import ResourceOrgAccessControl

    if restricted_data['allowed_organizations']:
        for org in restricted_data['allowed_organizations']:
            if org:
                org_id = toolkit.get_action('user_show')({'ignore_auth': True}, {'id': org})['id']
                model.Session.add(ResourceOrgAccessControl(resource_id=resource_dict['id'], org_id=org_id))


def resource_has_defined_restrictions(restricted_data):
    return restricted_data and restricted_data['level'] and restricted_data['level'] == 'restricted'
