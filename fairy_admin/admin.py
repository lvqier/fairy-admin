
import os
import json
import uuid

from datetime import datetime

from flask import Blueprint, request, url_for, abort, jsonify, send_from_directory
from flask_admin import BaseView, Admin, expose, consts as admin_consts
from flask_admin.helpers import get_url
from flask_admin.model.base import ViewArgs, BaseModelView
from flask_admin.form.widgets import Select2Widget, DateTimePickerWidget, DatePickerWidget
from flask_admin.model.fields import AjaxSelectMultipleField
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.fields import QuerySelectMultipleField
from flask_sqlalchemy import Model
from math import ceil
from wtforms.widgets import TextArea, html_params
from wtforms.fields import DateTimeField, DateField
from wtforms.fields.core import UnboundField
from markupsafe import escape, Markup

from .filters import SQLAlchemyFilter


CWD = os.path.dirname(os.path.abspath(__file__))

TextArea.tag = 'textarea'
Select2Widget.tag = 'xm-select'
DateTimePickerWidget.tag = 'datetime'
DateTimeField.control = 'datetime'
DatePickerWidget.tag = 'date'
DateField.control = 'date'

admin_consts.ICON_TYPE_LAYUI = 'layui'


class FairyAdmin(Admin):
    def __init__(self, *args, **kwargs):
        super(FairyAdmin, self).__init__(*args, **kwargs)

    def init_app(self, app, *args, index_view=None, **kwargs):
        if index_view is None:
            index_view = self.index_view

        if index_view.menu_icon_value is None:
            index_view.menu_icon_type = admin_consts.ICON_TYPE_LAYUI
            index_view.menu_icon_value = 'layui-icon-home'

        super(FairyAdmin, self).init_app(app, *args, index_view=index_view, **kwargs)

        template_folder = os.path.join('templates', self.template_mode)
        blueprint = Blueprint('fairy_admin', __name__, template_folder=template_folder, static_folder='static')
        app.register_blueprint(blueprint, url_prefix='/admin/fairy')

    def add_view(self, view):
        super(FairyAdmin, self).add_view(view)
        if isinstance(view, BaseModelView):
            formatter = view.column_type_formatters.get(datetime)
            if formatter is None:
                view.column_type_formatters[datetime] = self.datetime_formatter

    def datetime_formatter(self, view, value):
        datetime_format = getattr(view, 'datetime_format', '%Y-%m-%d %H:%M:%S')
        return value.strftime(datetime_format)


def _repr(value):
    if isinstance(value, Model):
        return repr(value)
    return value


def _apply_filters(self, query, count_query, joins, count_joins, filters):
    if self.admin.template_mode == 'layui':
        sqla_filter = SQLAlchemyFilter(self.model, query=query)
        query = sqla_filter.apply(filters)
        return query, count_query, joins, count_joins
    else:
        return self._old_apply_filters(query, count_query, joins, count_joins, filters)


def _get_list_filter_args(self):
    if self.admin.template_mode == 'layui':
        filter_sos = request.args.get('filterSos', None)
        if filter_sos is None:
            return None
        return json.loads(filter_sos)
    else:
        return self._old_get_list_filter_args()


def _ajax(self):
    view_args = ViewArgs(page=request.args.get('page', 1, type=int),
            page_size=request.args.get('limit', 0, type=int),
            sort=request.args.get('field', None, type=str),
            sort_desc=request.args.get('desc', None, type=int),
            search=request.args.get('search', None),
            filters=self._get_list_filter_args(),
            extra_args=dict([
                (k, v) for k, v in request.args.items()
                if k not in ('page', 'limit', 'field', 'desc', 'search', 'filterSos') and
                not k.startswith('flt')
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


def _ajax_upload(self, field):
    form = self.get_form()
    field_name = field
    field = getattr(form, field_name)
    if isinstance(field, UnboundField):
        base_path = field.kwargs['base_path']
        relative_path = field.kwargs['relative_path']
        endpoint = field.kwargs['endpoint']
    else:
        base_path = field.base_path
        relative_path = field.relative_path
        endpoint = field.endpoint

    if base_path is None or relative_path is None:
        return jsonify(dict(code=500, msg='upload folder is not properly configured'))

    if callable(base_path):
        base_path = base_path()

    file = request.files['file']
    ext = os.path.splitext(file.filename)[1]
    filename = '{}{}'.format(uuid.uuid4().hex[:8], ext)
    relative_path = os.path.join(relative_path, 'upload')
    abs_path = os.path.join(base_path, relative_path)
    if not os.path.exists(abs_path):
        os.makedirs(abs_path)
    relative_file = os.path.join(relative_path, filename)
    abs_file = os.path.join(abs_path, filename)
    file.save(abs_file)
    url = get_url(endpoint, filename=relative_file)
    # url = url_for('.static', field=field_name, filename=relative_file, _external=True)
    data = {
        'filename': file.filename,
        'title': field_name,
        'src': url,
        'path': relative_file
    }
    return jsonify(dict(code=0, msg='', data=data))


def _static(self, field, filename):
    form = self.get_form()
    field = getattr(form, field)
    if isinstance(field, UnboundField):
        base_path = field.kwargs['base_path']
        relative_path = field.kwargs['relative_path']
    else:
        base_path = field.base_path
        relative_path = field.relative_path

    if base_path is None or relative_path is None:
        return jsonify(dict(code=500, msg='upload folder is not properly configured'))

    if callable(base_path):
        base_path = base_path()
    return send_from_directory(base_path, filename)


def _is_editable(self, item):
    return True

def _is_deletable(self, item):
    return True


ModelView._old_apply_filters = ModelView._apply_filters
ModelView._apply_filters = _apply_filters
BaseModelView._old_get_list_filter_args = BaseModelView._get_list_filter_args
BaseModelView._get_list_filter_args = _get_list_filter_args
BaseModelView.ajax = _ajax
BaseModelView.ajax_create_view = _ajax_new
BaseModelView.ajax_edit_view = _ajax_edit
BaseModelView.ajax_delete_view = _ajax_delete
BaseModelView.ajax_upload = _ajax_upload
BaseModelView.static = _static
BaseModelView.is_editable = _is_editable
BaseModelView.is_deletable = _is_deletable

expose('/ajax/')(BaseModelView.ajax)
expose('/ajax/new/', methods=['POST'])(BaseModelView.ajax_create_view)
expose('/ajax/edit/', methods=['POST'])(BaseModelView.ajax_edit_view)
expose('/ajax/delete/', methods=['POST'])(BaseModelView.ajax_delete_view)
expose('/ajax/upload/<string:field>', methods=['POST'])(BaseModelView.ajax_upload)

BaseModelView.can_export = True
BaseModelView.page_size = 10
BaseModelView.form_label_width = None
'''
form_label_width allows user to control width of label on the left side of form input
'''


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


# 适配 xm-select 采用','分割的字段提交方式
_multi_select_fields = [AjaxSelectMultipleField, QuerySelectMultipleField]

def _patched_process_formdata(self, valuelist):
    if self.widget.multiple and self.widget.tag == 'xm-select':
        valuelist = valuelist[0].split(',')
    return self._old_process_formdata(valuelist)

for field in _multi_select_fields:
    field._old_process_formdata = field.process_formdata
    field.process_formdata = _patched_process_formdata
