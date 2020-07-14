from datetime import datetime
from flask_security import RoleMixin as _RoleMixin, UserMixin as _UserMixin
from sqlalchemy import Column, Boolean, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship


class UserMixin(_UserMixin):
    __tablename__ = 'admin_user'

    id = Column(Integer, primary_key=True)
    nickname = Column(String(16))
    username = Column(String(16), nullable=False)
    password = Column(String(256))
    mobile = Column(String(16))
    email = Column(String(32))
    active = Column(Boolean, default=True)
    create_at = Column(DateTime, default=datetime.now)
    update_at = Column(DateTime, onupdate=datetime.now)


class RoleMixin(_RoleMixin):
    __tablename__ = 'admin_role'

    id = Column(Integer, primary_key=True)
    name = Column(String(16))
    code = Column(String(32))
    description = Column(String(1024))
    create_at = Column(DateTime, default=datetime.now)
    update_at = Column(DateTime, onupdate=datetime.now)

    def __eq__(self, other):
        '''
        使用 code 来判断是否相同
        '''
        return (self.code == other or
                self.code == getattr(other, 'code', None))

    def __hash__(self):
        return hash(self.code)


class PermissionMixin(object):
    __tablename__ = 'admin_permission'

    id = Column(Integer, primary_key=True)
    name = Column(String(16))
    code = Column(String(32))
    description = Column(String(1024))
    create_at = Column(DateTime, default=datetime.now)
    update_at = Column(DateTime, onupdate=datetime.now)
