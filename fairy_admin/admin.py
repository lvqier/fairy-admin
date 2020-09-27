
import os

from flask import Blueprint
from flask_admin import Admin

from .tenant import AdminMixin, AdminIndexView


class FairyAdmin(AdminMixin, Admin):
    def __init__(self, *args, rbac=None, index_view=None, url=None, endpoint=None, **kwargs):
        index_view = index_view or AdminIndexView(endpoint=endpoint, url=url)
        kwargs.update({
            'index_view': index_view,
            'url': url,
            'endpoint': endpoint
        })
        super(FairyAdmin, self).__init__(*args, **kwargs)
        self._tenant_admins = []
        self.rbac = rbac

    def init_app(self, app, *args, index_view=None, rbac=None, **kwargs):
        kwargs.update({
            'index_view': index_view
        })
        super(FairyAdmin, self).init_app(app, *args, **kwargs)

        self.rbac = rbac or self.rbac
        if 'fairy_admin' not in app.blueprints:
            template_folder = os.path.join('templates', self.template_mode)
            blueprint = Blueprint(
                'fairy_admin',
                __name__,
                template_folder=template_folder,
                static_folder='static'
            )
            app.register_blueprint(blueprint, url_prefix='/admin/fairy')

        for tenant_admin, _kwargs in self._tenant_admins:
            tenant_admin.init_app(app, self, **_kwargs)

        for view in self._views:
            self._add_blueprints(view)

        if self.rbac is not None:
            self.rbac.init_admin(self)

    def add_tenant_admin(self, tenant_admin, **kwargs):
        self._tenant_admins.append((tenant_admin, kwargs))

        if self.app is not None:
            tenant_admin.init_app(self.app, self, **kwargs)
