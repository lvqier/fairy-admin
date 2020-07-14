from flask import Blueprint, request, url_for, render_template, jsonify, redirect
from flask_admin.babel import gettext
from flask_admin.helpers import get_redirect_target
from flask_security import Security, current_user, SQLAlchemyUserDatastore
from flask_security.utils import verify_password, login_user, logout_user
from flask_login import LoginManager


from .views import UserView, RoleView, PermissionView
from .mixins import UserMixin, RoleMixin, PermissionMixin


class RABC(SQLAlchemyUserDatastore):
    def __init__(self, db, user_model=None, role_model=None, permission_model=None):
        self.db = db
        self.User = user_model
        self.Role = role_model
        self.Permission = permission_model
        self.security = Security(register_blueprint=False)

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
            role_permission_table = db.Table('admin_role_permission',
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

        super(RABC, self).__init__(db, self.User, self.Role)

    def init_app(self, app, endpoint='rabc', url='/rabc', index_endpoint='admin.index'):
        self.index_endpoint = index_endpoint

        app.config['SECURITY_LOGIN_USER_TEMPLATE'] = 'rabc/login.html'
        self.security.init_app(app, datastore=self)

        blueprint = Blueprint(endpoint, __name__)
        blueprint.add_url_rule('/login', endpoint='login_view', view_func=self.login_view, methods=['GET'])
        blueprint.add_url_rule('/login', endpoint='ajax_login', view_func=self.ajax_login, methods=['POST'])
        blueprint.add_url_rule('/logout', endpoint='logout', view_func=self.logout, methods=['GET'])
        app.register_blueprint(blueprint, url_prefix=url)

    def login_view(self):
        return render_template('rabc/login.html')

    def logout(self):
        logout_user()
        return_url = get_redirect_target() or url_for(self.index_endpoint)
        return redirect(return_url)

    def ajax_login(self):
        username = request.form['username']
        password = request.form['password']
        remember = request.form.get('remember')
        user = self.find_user(username=username)
        if user is None or not verify_password(password, user.password):
            return jsonify(dict(code=403, msg=gettext('Incorrect username or password!')))
        if not user.active:
            return jsonify(dict(code=403, msg=gettext('User is not activated!')))
        login_user(user, bool(remember))
        return_url = get_redirect_target() or url_for(self.index_endpoint)
        return jsonify(dict(code=0, data={'url': return_url}))

    def create_user_view(self, session, model_view=None, **kwargs):
        ModelView = model_view or UserView
        return ModelView(self.User, session, **kwargs)
    
    def create_role_view(self, session, model_view=None, **kwargs):
        ModelView = model_view or RoleView
        return ModelView(self.Role, session, **kwargs)

    def create_permission_view(self, session, model_view=None, **kwargs):
        ModelView = model_view or PermissionView
        return ModelView(self.Permission, session, **kwargs)
