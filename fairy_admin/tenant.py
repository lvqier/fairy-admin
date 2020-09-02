import warnings

from datetime import datetime
from flask import g, request
from flask_admin import Admin, AdminIndexView as _AdminIndexView
from flask_admin.menu import MenuLink, MenuView
from flask_admin.model.base import BaseModelView
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user

from .consts import ICON_TYPE_LAYUI


class AdminIndexView(_AdminIndexView):
    def __init__(self, *args, menu_icon_type=ICON_TYPE_LAYUI, menu_icon_value='layui-icon-home', **kwargs):
        super(AdminIndexView, self).__init__(*args, menu_icon_type=menu_icon_type, menu_icon_value=menu_icon_value, **kwargs)


class AdminMixin(object):
    def add_view(self, view, menu=True):
        self._views.append(view)

        if self.app is not None:
            self.app.register_blueprint(view.create_blueprint(self))
            self._add_blueprints(view)

        if menu:
            self._add_view_to_menu(view)

    def _add_blueprints(self, view):
        if self.app is not None and hasattr(view, 'create_blueprints'):
            for blueprint in view.create_blueprints(self):
                blueprint.url_value_preprocessor(self._url_value_preprocessor)
                blueprint.url_defaults(self._url_defaults)
                self.app.register_blueprint(blueprint)

    def _url_value_preprocessor(self, endpoint, view_args):
        pass

    def _url_defaults(self, endpoint, view_args):
        pass


class TenantAdmin(AdminMixin, Admin):
    def __init__(self, index_view=None, url=None, endpoint=None, return_name=None, return_endpoint=None, return_url=None, return_icon_type=None, return_icon_value=None, **kwargs):
        '''
        return_* 相关参数用于控制“返回链接”
        '''
        index_view = index_view or AdminIndexView(url=url, endpoint=endpoint)
        kwargs['app'] = None
        super(TenantAdmin, self).__init__(index_view=index_view, url=url, endpoint=endpoint, **kwargs)
        self.rabc = None
        self._add_return_link(return_name, endpoint=return_endpoint, url=return_url, icon_type=return_icon_type, icon_value=return_icon_value)

    def _add_return_link(self, name, endpoint=None, url=None, icon_type=None, icon_value=None):
        icon_type = icon_type or ICON_TYPE_LAYUI
        icon_value = icon_value or 'layui-icon-return'
        menu_link = None
        if endpoint or url:
            menu_link = MenuLink(name, endpoint=endpoint, url=url, icon_type=icon_type, icon_value=icon_value)
        self.return_menu_link = menu_link

    def init_app(self, app, admin, index_view=None, endpoint=None, url=None):
        url = url or self.url
        url = self._get_admin_url(admin, url)
        self.index_view.url = url
        endpoint = endpoint or self.endpoint
        self.index_view.endpoint = endpoint
        index_view = index_view or self.index_view
        self._set_admin_index_view(index_view=index_view, endpoint=endpoint, url=url)

        # 用户拥有 admin 角色才会显示返回按钮
        if self.return_menu_link:
            self._menu.insert(0, self.return_menu_link)

        self.app = app
        self.admin = admin
        self.template_mode = admin.template_mode
        self.rabc = admin.rabc
        for view in self._views:
            blueprint = view.create_blueprint(self)
            blueprint.url_value_preprocessor(self._url_value_preprocessor)
            blueprint.url_defaults(self._url_defaults)
            app.register_blueprint(blueprint)

            self._add_blueprints(view)

    def _init_extension(self):
        pass

    def _url_defaults(self, endpoint, view_args):
        if 'tenant_id' not in view_args:
            view_args['tenant_id'] = g.tenant_id

    def _url_value_preprocessor(self, endpoint, view_args):
        g.tenant_id = view_args.pop('tenant_id')

    def _get_admin_url(self, admin, url):
        if not url.startswith('/'):
            url = '%s/%s' % (admin.url, url)
        else:
            url = '%s%s' % (admin.url, url)

        return url

    def _add_view_to_menu(self, view):
        self.add_menu_item(MenuView(view.name, view, cache=False), view.category)

    def _set_admin_index_view(self, index_view=None, endpoint=None, url=None):
        super(TenantAdmin, self)._set_admin_index_view(index_view=index_view, endpoint=endpoint, url=url)
        self._menu[0]._cache = False
