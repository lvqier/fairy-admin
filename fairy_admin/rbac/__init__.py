import click

from flask import Blueprint, request, url_for, render_template, jsonify, redirect
from flask_admin import AdminIndexView
from flask_admin.babel import gettext
from flask_admin.helpers import get_redirect_target
from flask_admin.model.helpers import prettify_name
from flask_security import Security, current_user, SQLAlchemyUserDatastore
from flask_security.utils import verify_password, login_user, logout_user
from flask_login import LoginManager

from .views import UserView, RoleView, PermissionView
from .mixins import UserMixin, RoleMixin, PermissionMixin


class RBAC(SQLAlchemyUserDatastore):

    LOGIN_TEMPLATE = 'rbac/login.html'

    def __init__(self, db, user_model=None, role_model=None, permission_model=None, name=None, description=None):
        self.db = db
        self.User = user_model
        self.Role = role_model
        self.Permission = permission_model
        self.name = name
        self.description = description
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
                db.Column('role_id', db.Integer, db.ForeignKey(self.Role.id)),
                db.Column('permission_id', db.Integer, db.ForeignKey(self.Permission.id))
            )
            self.Role.permissions = db.relationship(self.Permission, secondary=role_permission_table)
        if self.User is None:
            class User(db.Model, UserMixin):
                def __repr__(self):
                    return self.nickname
            self.User = User
        if not hasattr(self.User, 'roles'):
            user_role_table = db.Table('admin_user_role',
                db.Column('user_id', db.Integer, db.ForeignKey(self.User.id)),
                db.Column('role_id', db.Integer, db.ForeignKey(self.Role.id))
            )
            self.User.roles = db.relationship(self.Role, secondary=user_role_table)

        super(RBAC, self).__init__(db, self.User, self.Role)

    def init_app(self, app, endpoint='rbac', url='/rbac', index_endpoint='admin.index'):
        self.index_endpoint = index_endpoint

        # app.config['SECURITY_LOGIN_USER_TEMPLATE'] = self.LOGIN_TEMPLATE
        self.security.init_app(app, datastore=self)

        blueprint = Blueprint(endpoint, __name__, cli_group='rbac')
        blueprint.add_url_rule('/login', endpoint='login_view', view_func=self.login_view, methods=['GET'])
        blueprint.add_url_rule('/login', endpoint='ajax_login', view_func=self.ajax_login, methods=['POST'])
        blueprint.add_url_rule('/logout', endpoint='logout', view_func=self.logout, methods=['GET'])
        blueprint.cli.short_help = 'Commands for rbac shortcuts.'
        blueprint.cli.command('generate_permissions')(self.generate_permissions)
        blueprint.cli.command('user_change_username')(self.user_change_username)
        blueprint.cli.command('user_change_password')(self.user_change_password)
        blueprint.cli.command('create_user')(self.create_user)
        blueprint.cli.command('user_add_role')(self.user_add_role)
        blueprint.cli.command('active_user')(self.active_user)
        blueprint.cli.command('setup_admin')(self.setup_admin)
        app.register_blueprint(blueprint, url_prefix=url)

    def init_admin(self, admin):
        self.admin = admin

    def has_permission(self, permission_code):
        alt_permission_codes = [permission_code]
        items = permission_code.split('.')
        while items:
            items[-1] = '*'
            alt_permission_codes.append('.'.join(items))
            items = items[:-1]

        for role in current_user.roles:
            for permission in role.permissions:
                if permission.code in alt_permission_codes:
                    return True
        return False

    def login_view(self):
        next_url = request.args.get('next', '')
        ctx = {'rbac': self}
        if next_url:
            ctx.update(next_url=next_url)
        return render_template(self.LOGIN_TEMPLATE, **ctx)

    def logout(self):
        logout_user()
        next_url = request.args.get('next')
        return redirect(url_for('.login_view', next=next_url))

    def ajax_login(self):
        username = request.form['username']
        password = request.form['password']
        remember = request.form.get('remember')
        user = self.find_user(username=username)
        if user is None or not verify_password(password, user.password):
            return jsonify(dict(code=403, msg=gettext('用户名或者密码错误!')))
        if not user.active:
            return jsonify(dict(code=403, msg=gettext('用户未启用!')))
        login_user(user, bool(remember))
        return_url = get_redirect_target('next') or url_for(self.index_endpoint)
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

    def generate_permissions(self):
        permission_codes= []
        for tenant_admin, _ in self.admin._tenant_admins:
            permission_code = '{}.*'.format(tenant_admin.endpoint)
            permission_name = prettify_name('{}.all'.format(tenant_admin.endpoint))
            permission_codes.append((permission_code, permission_name))
            for view in tenant_admin._views:
                endpoint = view.endpoint
                if isinstance(view, AdminIndexView):
                    permission_code = '{}.index'.format(tenant_admin.endpoint)
                    permission_name = prettify_name(permission_code)
                    permission_codes.append((permission_code, permission_name))
                    continue

                permission_code = '{}.{}.list'.format(tenant_admin.endpoint, endpoint)
                permission_name = view._prettify_name(permission_code)
                permission_codes.append((permission_code, permission_name))

                for action in view._actions:
                    permission_code = '{}.{}.{}'.format(tenant_admin.endpoint, endpoint, action)
                    permission_name = view._prettify_name(permission_code)
                    permission_codes.append((permission_code, permission_name))

        permission_code = '*'
        permission_name = 'All'
        permission_codes.append((permission_code, permission_name))
        for view in self.admin._views:
            endpoint = view.endpoint
            if isinstance(view, AdminIndexView):
                permission_code = 'index'
                permission_name = prettify_name(permission_code)
                permission_codes.append((permission_code, permission_name))
                continue

            permission_code = '{}.list'.format(endpoint)
            permission_name = view._prettify_name(permission_code)
            permission_codes.append((permission_code, permission_name))

            for action in view._actions:
                permission_code = '{}.{}'.format(endpoint, action)
                permission_name = view._prettify_name(permission_code)
                permission_codes.append((permission_code, permission_name))

        for permission_code, permission_name in permission_codes:
            query = self.Permission.query.filter_by(code=permission_code)
            permission = query.one_or_none()
            if permission is None:
                permission = self.Permission(code=permission_code)
                self.db.session.add(permission)
            permission.name = permission_name

        to_delete_permissions = []
        permission_codes = [p[0] for p in permission_codes]
        for permission in self.Permission.query.all():
            if permission.code not in permission_codes:
                to_delete_permissions.append(permission)

        for permission in to_delete_permissions:
            self.db.session.delete(permission)

        self.db.session.commit()

    @click.argument('mobile')
    def user_change_username(self, mobile):
        username = input('Enter username: ')
        user = self.User.query.filter_by(mobile=mobile).one_or_none()
        if user is None:
            print('User of mobile {} does not exist.'.format(mobile))

        user.username = username
        self.db.session.commit()

    @click.argument('username')
    def user_change_password(self, username):
        user = self.User.query.filter_by(username=username).one_or_none()
        if user is None:
            print('User {} does not exist.'.format(username))
            return
        password = input('Enter password: ')
        user.password = password
        self.db.session.commit()

    def create_user(self):
        username = input('Enter username: ')
        mobile = input('Enter mobile: ')
        password = input('Enter password: ')
        user = self.User.query.filter_by(username=username).one_or_none()
        if user is not None:
            print('User {} already exists.'.format(username))
            return

        user = self.User(username=username, password=password)
        user.mobile = mobile
        self.db.session.add(user)
        self.db.session.commit()

    @click.argument('username')
    @click.argument('role')
    def user_add_role(self, username, role):
        user = self.User.query.filter_by(username=username).one_or_none()
        if user is None:
            print('User {} does not exist.'.format(username))
            return

        role = self.Role.query.filter_by(name=role).one_or_none()
        if role is None:
            print('Role {} does not exist.'.format(role))
            return

        user.roles.append(role)
        self.db.session.commit()

    @click.argument('username')
    def active_user(self, username):
        user = self.User.query.filter_by(username=username).one_or_none()
        if user is None:
            print('User {} does not exist.'.format(username))
            return

        user.active = True
        self.db.session.commit()

    def setup_admin(self):
        permission = self.Permission.query.filter_by(code='*').one_or_none()
        if permission is None:
            print('Please run generate_permissions first')
        role = self.Role.query.filter_by(name='admin').one_or_none()
        if role is None:
            role = self.Role(name='admin', code='admin')
            self.db.session.add(role)
        role.permissions.append(permission)
        self.db.session.commit()
