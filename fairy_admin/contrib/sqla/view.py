
from flask import g, request, url_for
from flask_admin import expose
from flask_admin.contrib.sqla import ModelView as _ModelView
from flask_admin.model.helpers import get_mdict_item_or_list
from flask_admin.helpers import get_redirect_target
from flask_sqlalchemy import Model
from sqlalchemy import func
from sqlalchemy.orm.attributes import InstrumentedAttribute

from fairy_admin.model import BaseModelViewMixin

from .filters import SQLAlchemyFilter
from .form import AdminModelConverter


class Call(object):
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __call__(self, s):
        self.func(*self.args, **self.kwargs)


class ModelView(BaseModelViewMixin, _ModelView):
    create_modal = True
    edit_modal = True

    model_form_converter = AdminModelConverter
    model_relationship_views = []

    def __init__(self, ModelClass, session, *args, **kwargs):
        super(ModelView, self).__init__(ModelClass, session, *args, **kwargs)
        for key in self.model_relationship_views:
            field = getattr(self.model, key)
            if not isinstance(field, InstrumentedAttribute):
                field_name = '{}.{}'.format(ModelClass.__name__, key)
                print('Warning: lazy of relationship field {}.{} should be set to \'dynamic\''.format(field_name))
            relationship_model_view = self.model_relationship_views[key]
            relationship_model_view.setup_relationship(
                self.endpoint,
                key,
                session
            )

    def _repr(self, value):
        return repr(value) if isinstance(value, Model) else value

    def _apply_filters(self, query, count_query, joins, count_joins, filters):
        """
        适配LayUI表格扩展：soulTable的filter功能
        """
        if self.admin.template_mode == 'layui':
            sqla_filter = SQLAlchemyFilter(self.model, query=query)
            query = sqla_filter.apply(filters)
            count_query = query.with_entities(func.count('*'))
            return query, count_query, joins, count_joins
        return super(ModelView, self).apply_filters(
            query,
            count_query,
            joins,
            count_joins,
            filters
        )

    def create_blueprints(self, admin):
        blueprints = []
        for key in self.model_relationship_views:
            relationship_model_view = self.model_relationship_views[key]
            url = '{}/<int:model_id>/{}'.format(
                self.url,
                relationship_model_view.key
            )
            bp = relationship_model_view.create_blueprint(admin, url=url)

            bp.record_once(
                Call(
                    bp.url_value_preprocessor,
                    self._url_value_preprocessor
                )
            )
            bp.record(Call(bp.url_defaults, self._url_defaults))
            blueprints.append(bp)
        return blueprints

    def _url_value_preprocessor(self, endpoint, view_args):
        g.model_id = view_args.pop('model_id')
        g.model = self.get_query().filter_by(id=g.model_id).first()

    def _url_defaults(self, endpoint, view_args):
        if 'model_id' not in view_args:
            view_args['model_id'] = g.model_id

    @expose('/details/')
    def details_view(self):
        """
        Overwrite flask_admin.contrib.sqla.ModelView.details_view
        Add relationship data to template args
        """
        return_url = get_redirect_target() or self.get_url('.index_view')

        if not self.can_view_details:
            return redirect(return_url)

        id = get_mdict_item_or_list(request.args, 'id')
        if id is None:
            return redirect(return_url)

        model = self.get_one(id)

        if model is None:
            flash(gettext('Record does not exist.'), 'error')

        if self.details_modal and request.args.get('modal'):
            template = self.details_modal_template
        else:
            template = self.details_template

        relationship_views = []
        for relationship in self.model_relationship_views:
            relationship_view = self.model_relationship_views[relationship]
            bp = relationship_view.blueprint
            endpoint = '{}.ajax_config'.format(relationship_view.blueprint.name)
            data = {
                'field': relationship,
                'name': self._prettify_name(relationship_view.model.__name__),
                'config_url': self.get_url(endpoint, model_id=id)
            }
            relationship_views.append(data)

        return self.render(
            template,
            model=model,
            details_columns=self._details_columns,
            get_value=self.get_detail_value,
            relationship_views=relationship_views,
            return_url=return_url
        )
        return super(ModelView, self).details_view()


class ModelRelationshipView(ModelView):
    def __init__(self, ModelClass, **kwargs):
        super(ModelRelationshipView, self).__init__(ModelClass, None, **kwargs)

    def setup_relationship(self, endpoint, key, session):
        self.session = session
        self.endpoint = '{}_{}'.format(endpoint, key)
        self.key = key
        self._refresh_cache()

    def get_query(self):
        """
        默认取模型的relationship字段，可重载
        """
        return getattr(g.model, self.key)

    def get_count_query(self):
        return self.get_query().with_entities(func.count('*'))

    def on_model_change(self, form, model, is_create):
        """
        创建时默认添加到relationship集合。
        一般如果重载了get_query()，本方法也需要被重载
        """
        if is_create:
            self.get_query().append(model)

    def create_blueprint(self, admin, url=None, endpoint=None):
        self.url = url or self.url
        self.endpoint = endpoint or self.endpoint
        return super(ModelRelationshipView, self).create_blueprint(admin)
