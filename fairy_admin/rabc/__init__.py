from .views import UserView, RoleView, PermissionView
from .mixins import UserMixin, RoleMixin, PermissionMixin


class RABC(object):
    def __init__(self, user_model=None, role_model=None, permission_model=None):
        self.User = user_model
        self.Role = role_model
        self.Permission = permission_model
        self._model_views = {}

    def init_app(self, app, db):
        self.db = db
        if self.Permission is None:
            class Permission(db.Model, PermissionMixin):
                def __repr__(self):
                    return self.name
            self.Permission = Permission
        if self.Role is None:
            class Role(db.Model, RoleMixin):
                def __repr__(self):
                    return self.name

            self.Role = Role
        if not hasattr(self.Role, 'permissions'):
            role_permission_table = db.Table('role_permission',
                db.Column('role_id', db.Integer, db.ForeignKey('admin_role.id')),
                db.Column('permission_id', db.Integer, db.ForeignKey('admin_permission.id'))
            )
            self.Role.permissions = db.relationship(self.Permission, secondary=role_permission_table)
        if self.User is None:
            class User(db.Model, UserMixin):
                def __repr__(self):
                    return self.nickname
            self.User = User
        if not hasattr(self.User, 'roles'):
            user_role_table = db.Table('user_role',
                db.Column('user_id', db.Integer, db.ForeignKey('admin_user.id')),
                db.Column('role_id', db.Integer, db.ForeignKey('admin_role.id'))
            )
            self.User.roles = db.relationship(self.Role, secondary=user_role_table)
        for key, model in (('user', self.User), ('role', self.Role), ('permission', self.Permission)):
            if not key in self._model_views:
                continue
            admin = self._model_views[key]['admin']
            model_view = self._model_views[key]['model_view']
            kwargs = self._model_views[key]['kwargs']
            admin.add_view(model_view(model, db.session, **kwargs))

    def register_user_view(self, admin, model_view=None, **kwargs):
        self._model_views['user'] = {
            'admin': admin,
            'model_view': model_view or UserView,
            'kwargs': kwargs
        }
    
    def register_role_view(self, admin, model_view=None, **kwargs):
        self._model_views['role'] = {
            'admin': admin,
            'model_view': model_view or RoleView,
            'kwargs': kwargs
        }

    def register_permission_view(self, admin, model_view=None, **kwargs):
        self._model_views['permission'] = {
            'admin': admin,
            'model_view': model_view or PermissionView,
            'kwargs': kwargs
        }
