"""Create database model to store permissions in database instead of plugin_extras

Revision ID: 484275223bbe
Revises: 
Create Date: 2023-01-17 16:50:23.131955

"""
from alembic import op
from sqlalchemy import ForeignKey, Column, String



# revision identifiers, used by Alembic.
revision = '484275223bbe'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    update_schema()


def update_schema():
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
