from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship


class UserMixin(object):
    __tablename__ = 'admin_user'

    id = Column(Integer, primary_key=True)
    nickname = Column(String(16))
    username = Column(String(16), nullable=False)
    password = Column(String(256))
    mobile = Column(String(16))
    email = Column(String(32))
    status = Column(String(16))
    create_at = Column(DateTime, default=datetime.now)
    update_at = Column(DateTime, onupdate=datetime.now)


class RoleMixin(object):
    __tablename__ = 'admin_role'

    id = Column(Integer, primary_key=True)
    name = Column(String(16))
    code = Column(String(32))
    description = Column(String(1024))
    create_at = Column(DateTime, default=datetime.now)
    update_at = Column(DateTime, onupdate=datetime.now)


class PermissionMixin(object):
    __tablename__ = 'admin_permission'

    id = Column(Integer, primary_key=True)
    name = Column(String(16))
    code = Column(String(32))
    description = Column(String(1024))
    create_at = Column(DateTime, default=datetime.now)
    update_at = Column(DateTime, onupdate=datetime.now)
