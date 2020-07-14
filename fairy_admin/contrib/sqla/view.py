
from flask import g
from flask_admin import expose
from flask_admin.contrib.sqla import ModelView as _ModelView
from flask_sqlalchemy import Model

from fairy_admin.model import BaseModelViewMixin

from .filters import SQLAlchemyFilter
from .form import AdminModelConverter


class ModelView(BaseModelViewMixin, _ModelView):
    create_modal = True
    edit_modal = True

    model_form_converter = AdminModelConverter
    model_relationship_views = []

    def __init__(self, ModelClass, session, *args, **kwargs):
        super(ModelView, self).__init__(ModelClass, session, *args, **kwargs)
        for key in self.model_relationship_views:
            relationship_model_view = self.model_relationship_views[key]
            relationship_model_view.setup_relationship(self.endpoint, key, session)

    def _repr(self, value):
        return repr(value) if isinstance(value, Model) else value
        
    def apply_filters(self):
        '''
        适配LayUI表格扩展：soulTable的filter功能
        '''
        if self.admin.template_mode == 'layui':
            sqla_filter = SQLAlchemyFilter(self.model, query=query)
            query = sqla_filter.apply(filters)
            return query, count_query, joins, count_joins
        return super(ModelView, self).apply_filters(query, count_query, joins, count_joins, filters)

    def create_blueprints(self, admin):
        blueprints = []
        for key in self.model_relationship_views:
            relationship_model_view = self.model_relationship_views[key]
            url = '{}/<int:model_id>/{}'.format(self.url, relationship_model_view.key)
            bp = relationship_model_view.create_blueprint(admin, url=url)
            bp.url_value_preprocessor(self._url_value_preprocessor)
            bp.url_defaults(self._url_defaults)
            blueprints.append(bp)
        return blueprints

    def _url_value_preprocessor(self, endpoint, view_args):
        g.model_id = view_args.pop('model_id')
        g.model = self.get_query().get(g.model_id)

    def _url_defaults(self, endpoint, view_args):
        if 'model_id' not in view_args:
            view_args['model_id'] = g.model_id


class ModelRelationshipView(ModelView):
    def __init__(self, ModelClass, **kwargs):
        super(ModelRelationshipView, self).__init__(ModelClass, None, **kwargs)

    def setup_relationship(self, endpoint, key, session):
        self.session = session
        self.endpoint = '{}_{}'.format(endpoint, key)
        self.key = key
        self._refresh_cache()

    def get_query(self):
        '''
        默认取模型的relationship字段，可重载
        '''
        return getattr(g.model, self.key)

    def get_query_count(self):
        return self.get_query().count()

    def on_model_change(self, form, model, is_create):
        '''
        创建时默认添加到relationship集合。一般如果重载了get_query()，本方法也需要被重载
        '''
        if is_create:
            self.get_query().append(model)

    def create_blueprint(self, admin, url=None, endpoint=None):
        self.url = url or self.url
        self.endpoint = endpoint or self.endpoint
        return super(ModelRelationshipView, self).create_blueprint(admin)
