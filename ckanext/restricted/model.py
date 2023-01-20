from sqlalchemy import Column, types, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

from ckan.model.meta import metadata

Base = declarative_base(metadata=metadata)


class ResourceAccessControl(Base):
    """
    Represents the status of email communication of dataset transfers to organizations,
    each row is a user who has been emailed regarding a specific dataset transfer
    """

    __tablename__ = 'restricted_resource_access_control'

    resource_id = Column(types.Integer,
                         ForeignKey('resource.id', onupdate='CASCADE', ondelete='CASCADE'), primary_key=True)
    level = Column(types.UnicodeText, nullable=False)


class ResourceUserAccessControl(Base):
    """
    Represents access granted per resource to particular users
    """

    __tablename__ = 'restricted_resource_user_access_control'

    resource_id = Column(types.UnicodeText,
                         ForeignKey('resource.id', onupdate='CASCADE', ondelete='CASCADE'))

    user_id = Column(types.UnicodeText, ForeignKey('user.id', onupdate='CASCADE', ondelete='CASCADE'), nullable=False)


class ResourceOrgAccessControl(Base):
    """
    Represents access granted per resource to all users belonging to particular organizations
    """

    __tablename__ = 'restricted_resource_org_access_control'

    resource_id = Column(types.UnicodeText,
                         ForeignKey('resource.id', onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    org_id = Column(types.UnicodeText,
                    ForeignKey('group.id', onupdate='CASCADE', ondelete='CASCADE'), nullable=False)