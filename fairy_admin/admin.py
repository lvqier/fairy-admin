
import os
import json

from flask import Blueprint, request, abort, jsonify
from flask_admin import Admin, expose, consts as admin_consts
from flask_admin.model.base import ViewArgs, BaseModelView
from flask_admin.form.widgets import Select2Widget
from flask_admin.model.fields import AjaxSelectMultipleField
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.fields import QuerySelectMultipleField
from flask_sqlalchemy import Model
from math import ceil
from wtforms.widgets import TextArea, html_params
from markupsafe import escape, Markup

from .filters import SQLAlchemyFilter


TextArea.tag = 'textarea'
admin_consts.ICON_TYPE_LAYUI = 'layui'

CWD = os.path.dirname(os.path.abspath(__file__))


class FairyAdmin(Admin):
    def __init__(self, *args, **kwargs):
        super(FairyAdmin, self).__init__(*args, **kwargs)
        self.index_view.menu_icon_type = admin_consts.ICON_TYPE_LAYUI
        self.index_view.menu_icon_value = 'layui-icon-home'

    def init_app(self, app, *args, index_view=None, **kwargs):
        if index_view is None:
            index_view = self.index_view

        super(FairyAdmin, self).init_app(app, *args, index_view=index_view, **kwargs)

        template_folder = os.path.join('templates', self.template_mode)
        blueprint = Blueprint('fairy_admin', __name__, template_folder=template_folder, static_folder='static')
        app.register_blueprint(blueprint, url_prefix='/admin/fairy')


def _repr(value):
    if isinstance(value, Model):
        return repr(value)
    return value


def _apply_filters(self, query, count_query, joins, count_joins, filters):
    sqla_filter = SQLAlchemyFilter(self.model, query=query)
    query = sqla_filter.apply(filters)
    return query, count_query, joins, count_joins


def _get_list_filter_args(self):
    filter_sos = request.args.get('filterSos', None)
    if filter_sos is None:
        return None
    return json.loads(filter_sos)


def _ajax(self):
    view_args = ViewArgs(page=request.args.get('page', 1, type=int),
            page_size=request.args.get('limit', 0, type=int),
            sort=request.args.get('field', None, type=str),
            sort_desc=request.args.get('desc', None, type=int),
            search=request.args.get('search', None),
            filters=self._get_list_filter_args(),
            extra_args=dict([
                (k, v) for k, v in request.args.items()
                if k not in ('page', 'limit', 'field', 'desc', 'search', ) and
                not k.startswith('filterSos')
            ]))

    sort_column = view_args.sort
    if sort_column is not None:
        sort_column = sort_column[0]

    page_size = view_args.page_size or self.page_size

    count, data = self.get_list(view_args.page - 1, sort_column, view_args.sort_desc,
            view_args.search, view_args.filters, page_size=page_size)

    if count is not None and page_size:
        num_pages = int(ceil(count / float(page_size)))
    elif not page_size:
        num_pages = 0
    else:
        num_pages = None

    list_columns = self._list_columns
    page = []
    for row in data:
        item = {
            '_id': self.get_pk_value(row)
        }
        for c, name in list_columns:
            item[c] = _repr(self.get_list_value(None, row, c))
        page.append(item)

    result = {
        'code': 0,
        'msg': '',
        'count': count,
        'num_pages': num_pages,
        'page_size': page_size,
        'page': view_args.page,
        'data': page,
    }

    return jsonify(result)


def _ajax_new(self):
    if not self.can_create:
        return jsonify(dict(code=403, msg='Can not create'))

    form = self.create_form()
    if not hasattr(form, '_validated_ruleset') or not form._validated_ruleset:
        self._validate_form_instance(ruleset=self._form_create_rules, form=form)

    if not self.validate_form(form):
        fields = {}
        for f in form:
            fields[f.name] = f.label.text
        errors = []
        for field in form.errors:
            errors.append({
                'name': field,
                'label': fields[field],
                'errors': form.errors[field]
            })
        return jsonify(dict(code=400, msg='Form validate failed', errors=errors))

    model = self.create_model(form)
    return jsonify(dict(code=0, msg=''))


def _ajax_edit(self):
    if not self.can_edit:
        return jsonify(dict(code=403, msg='Can not edit'))

    id = request.args.get('id')
    if id is None:
        abort(400)

    model = self.get_one(id)

    if model is None:
        return jsonify(dict(code=404, msg='Record does not exist.'))

    form = self.edit_form(obj=model)
    if not hasattr(form, '_validated_ruleset') or not form._validated_ruleset:
        self._validate_form_instance(ruleset=self._form_edit_rules, form=form)

    if not self.validate_form(form):
        fields = {}
        for f in form:
            fields[f.name] = f.label.text
        errors = []
        for field in form.errors:
            errors.append({
                'name': field,
                'label': fields[field],
                'errors': form.errors[field]
            })
        return jsonify(dict(code=400, msg='Form validate failed', errors=errors))

    if not self.update_model(form, model):
        return jsonify(dict(code=500, msg='Unknown error'))
    return jsonify(dict(code=0, msg=''))


def _ajax_delete(self):
    if not self.can_delete:
        return jsonify(dict(code=403, msg='Can not edit'))

    data = request.json

    for id in data.get('ids', []):
        model = self.get_one(id)
        if model is None:
            continue
        if not self.delete_model(model):
            return jsonify(dict(code=500, msg='Unknown error.'))

    return jsonify(dict(code=0, msg=''))


ModelView._apply_filters = _apply_filters
BaseModelView._get_list_filter_args = _get_list_filter_args
BaseModelView.ajax = _ajax
BaseModelView.ajax_create_view = _ajax_new
BaseModelView.ajax_edit_view = _ajax_edit
BaseModelView.ajax_delete_view = _ajax_delete

expose('/ajax/')(BaseModelView.ajax)
expose('/ajax/new/', methods=['POST'])(BaseModelView.ajax_create_view)
expose('/ajax/edit/', methods=['POST'])(BaseModelView.ajax_edit_view)
expose('/ajax/delete/', methods=['POST'])(BaseModelView.ajax_delete_view)

BaseModelView.can_export = True
BaseModelView.page_size = 10


# 将 select2 组件更换成 xm-select
_select2_widget_call = Select2Widget.__call__

def _render_xm_select(self, field, options=None, **kwargs):
    if not self.multiple:
        return _select2_widget_call(self, field, **kwargs)
    options = []
    for val, label, selected in field.iter_choices():
        options.append(dict(name=_repr(label), value=val, selected=selected))
    params = {
        'class': 'xm-select',
        'data-name': field.name,
        'data-options': json.dumps(options)
    }
    return Markup('<div %s></div>' % html_params(**params))

Select2Widget.__call__ = _render_xm_select
Select2Widget.tag = 'xm-select'


# 适配 xm-select 采用','分割的字段提交方式
_multi_select_fields = [AjaxSelectMultipleField, QuerySelectMultipleField]

def _patched_process_formdata(self, valuelist):
    if self.widget.multiple and self.widget.tag == 'xm-select':
        valuelist = valuelist[0].split(',')
    return self._old_process_formdata(valuelist)

for field in _multi_select_fields:
    field._old_process_formdata = field.process_formdata
    field.process_formdata = _patched_process_formdata
