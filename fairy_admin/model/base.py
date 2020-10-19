import json
import os
import uuid

from datetime import datetime, date
from flask import request, jsonify, get_flashed_messages, abort, send_from_directory, redirect
from flask_admin import tools, expose
from flask_admin.helpers import get_redirect_target
from flask_admin.model import BaseModelView as _BaseModelView
from flask_admin.model.base import ViewArgs as _ViewArgs
from flask_admin.model.filters import BaseFilter
from flask_admin.babel import gettext
from fairy_admin.tenant import TenantAdmin
from markupsafe import Markup
from math import ceil
from wtforms import form

from fairy_admin.actions import ActionsMixin

from .fields import UnboundField


class ViewArgs(_ViewArgs):
    def __init__(self, *args, **kwargs):
        super(ViewArgs, self).__init__(*args, **kwargs)
        self.sort_desc = kwargs.get('sort_desc') == 'desc'


class BaseModelViewMixin(ActionsMixin):
    can_export = True
    export_types = ['csv', 'xlsx']

    page_size = 10
    form_label_width = None
    """
    form_label_width controls width of label on the left side of form input
    """
    column_list_reload = False
    """
    control display of reload button on table of model list
    """
    column_display_numbers = False
    """
    enable column_display_numbers to show row number on table of model list
    """
    column_actions_width = 178
    """
    control display width of actions column on table of model list
    """
    column_display_actions = True
    """
    control display of actions column on table of model list
    """

    def __init__(self, *args, **kwargs):
        super(BaseModelViewMixin, self).__init__(*args, **kwargs)
        datetime_formatter = self.column_type_formatters.get(datetime)
        if datetime_formatter is None:
            self.column_type_formatters[datetime] = self._datetime_formatter
        date_formatter = self.column_type_formatters.get(date)
        if date_formatter is None:
            self.column_type_formatters[date] = self._date_formatter
        self.column_type_formatters[bool] = self._bool_formatter

    def _datetime_formatter(self, view, value):
        datetime_format = getattr(self, 'datetime_format', '%Y-%m-%d %H:%M:%S')
        return value.strftime(datetime_format)

    def _date_formatter(self, view, value):
        date_format = getattr(self, 'date_format', '%Y-%m-%d')
        return value.strftime(date_format)

    def _bool_formatter(self, view, value):
        icon = 'ok' if value else 'close'
        return Markup('<i class="layui-icon layui-icon-{}"></i>'.format(icon))

    def _get_list_filter_args(self):
        if self.admin.template_mode == 'layui':
            filter_sos = request.args.get('filterSos', None)
            return json.loads(filter_sos) if filter_sos is not None else None
        return super(BaseModelViewMixin, self)._get_list_filter_args()

    def _repr(self, value):
        return value

    def _refresh_filters_cache(self):
        self._filters = self.get_filters()

    def _get_filter_groups(self):
        return None

    def get_filters(self):
        filters = {}
        if self.column_filters:
            for n in self.column_filters:
                if isinstance(n, BaseFilter):
                    filters[n.name] = n
                else:
                    filters[n] = True
        return filters

    def render(self, template, **kwargs):
        """
        Overwride flask_admin.base.BaseView.render

        Changes: 
        * add get_label function for column name to work with get_value
        """
        kwargs['get_label'] = self.get_column_name
        return super(BaseModelViewMixin, self).render(template, **kwargs)

    @expose('/ajax/config/')
    def ajax_config(self):
        """
        LayUI 的数据表配置接口
        """
        limits = [self.page_size]
        if self.can_set_page_size:
            limits = [20, 50, 100]
            if self.page_size not in limits:
                limits.insert(0, self.page_size)

        # return_url = get_redirect_target() or self.get_url('.index_view')

        display_checkbox, actions = self.get_actions_list()

        columns = []
        for c, name in self._list_columns:
            column = {
                'field': c,
                'sort': self.is_sortable(c),
                'title': name,
                'description': self.column_descriptions.get(c),
            }
            if self._filters and c in self._filters:
                column['filter'] = True
                flt = self._filters[c]
                if isinstance(flt, BaseFilter):
                    column['options'] = flt.get_options(self)

            columns.append(column)

        default_tool_bar = []
        if not hasattr(self, 'can_filter_columns') or self.can_filter_columns:
            default_tool_bar.append('filter')
        if self.can_export:
            default_tool_bar.append('exports')
        if hasattr(self, 'can_print') and self.can_print:
            default_tool_bar.append('print')

        actions = [action.convert() for action in actions]
        display_actions = self.column_display_actions and actions

        result = {
            'url': self.get_url('.ajax'),
            'page': {
                'limit': self.page_size,
                'limits': limits,
                'prev': gettext('Prev'),
                'next': gettext('Next')
            },
            'actions': actions,
            'reload': self.column_list_reload,
            'cols': columns,
            'default_tool_bar': default_tool_bar,
            'column_display_numbers': self.column_display_numbers,
            'column_display_checkbox': display_checkbox,
            'column_display_actions': display_actions,
            'column_actions_width': self.column_actions_width,
        }
        if self.can_export:
            result['export_url'] = self.get_url('.export', export_type='<export_type>')

        return jsonify(result)

    def is_accessible(self):
        if self.admin.rbac is None:
            return True

        if isinstance(self.admin, TenantAdmin):
            permission_code = '{}.{}.list'.format(self.admin.endpoint, self.endpoint)
        else:
            permission_code = '{}.list'.format(self.endpoint)

        return self.admin.rbac.has_permission(permission_code)

    def inaccessible_callback(self, name, **kwargs):
        return redirect(self.get_url('rbac.login_view', next=request.url))

    def _get_list_extra_args(self):
        extra_args = {}
        for k, v in request.args.items():
            if k in ('page', 'limit', 'field', 'desc', 'search', 'filterSos'):
                continue
            if k.startswith('flt'):
                continue
            extra_args[k] = v

        view_args = ViewArgs(
            page=request.args.get('page', 1, type=int),
            page_size=request.args.get('limit', 0, type=int),
            sort=request.args.get('field', None, type=str),
            sort_desc=request.args.get('order', None, type=str),
            search=request.args.get('search', None),
            filters=self._get_list_filter_args(),
            extra_args=extra_args
        )
        sort_column = view_args.sort
        view_args.sort = None
        for idx in range(len(self._list_columns)):
            item = self._list_columns[idx]
            if item[0] == sort_column:
                view_args.sort = idx
                break
        return view_args

    @expose('/ajax/', methods=['GET'])
    def ajax(self):
        """
        LayUI 的数据表数据接口
        """

        view_args = self._get_list_extra_args()

        sort_column = self._get_column_by_idx(view_args.sort)
        if sort_column is not None:
            sort_column = sort_column[0]

        page_size = view_args.page_size or self.page_size

        count, data = self.get_list(
            view_args.page - 1,
            sort_column,
            view_args.sort_desc,
            view_args.search,
            view_args.filters,
            page_size=page_size
        )

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
                item[c] = self._repr(self.get_list_value(None, row, c))

            pk = self.get_pk_value(row)

            if self.column_display_actions:
                row_actions = self._get_list_row_actions(row)
                item['_actions'] = [action.convert() for action in row_actions]
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

    @expose('/ajax/', methods=['POST'])
    def ajax_post(self):
        """
        表头数据接口
        """
        columns = request.form['columns']
        # tableFilterType = request.form.get('tableFilterType')
        columns = json.loads(columns)
        result = {}
        for column in columns:
            if column in self._filters:
                flt = self._filters[column]
                if isinstance(flt, BaseFilter):
                    result[column] = [o[0] for o in flt.get_options(self)]

        return jsonify(result)

    @expose('/ajax/new/', methods=['POST'])
    def ajax_create_view(self):
        """
        异步创建接口
        """
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

    @expose('/ajax/edit/', methods=['POST'])
    def ajax_edit_view(self):
        """
        异步保存编辑接口
        """
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

    @expose('/ajax/delete/', methods=['POST'])
    def ajax_delete_view(self):
        """
        异步删除接口
        """
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

    def get_form(self, form_name=None):
        """
        Get form class.

        If ``self.rom`` is set, will return it and will call
        ``self.scaffold_form`` otherwise.

        Override to implement customized behavior.
        """
        if form_name is None:
            return super(BaseModelViewMixin, self).get_form()

        # TODO use cache for forms
        for p in dir(self):
            attr = tools.get_dict_attr(self, p)
            if isinstance(attr, form.Form) or issubclass(attr, form.Form):
                print(form_name, attr)
                if hasattr(attr, '__formname__'):
                    if attr.__formname__ == form_name:
                        return attr
        return None

    @expose('/ajax/upload/<string:field_name>', methods=['POST'])
    def ajax_upload(self, field_name):
        """
        异步上传接口，服务文件上传字段
        """
        items = field_name.split('.')
        if len(items) == 1:
            _field_name = items[0]
            form = self.get_form()
        else:
            _field_name = items[1]
            form = self.get_form(items[0])

        field = getattr(form, _field_name)
        if isinstance(field, UnboundField):
            base_path = field.kwargs['base_path']
            relative_path = field.kwargs['relative_path']
            endpoint = field.kwargs.get('endpoint', '.download')
        else:
            base_path = field.base_path
            relative_path = field.relative_path
            endpoint = field.endpoint

        if base_path is None or relative_path is None:
            result = dict(
                code=500,
                msg='upload folder is not properly configured'
            )
            return jsonify(result)

        if callable(base_path):
            base_path = base_path()

        file = request.files['file']
        ext = os.path.splitext(file.filename)[1]
        filename = '{}{}'.format(uuid.uuid4().hex[:8], ext)
        # relative_path = os.path.join(relative_path, 'upload')
        abs_path = os.path.join(base_path, relative_path)
        if not os.path.exists(abs_path):
            os.makedirs(abs_path)
        relative_file = os.path.join(relative_path, filename)
        abs_file = os.path.join(abs_path, filename)
        file.save(abs_file)
        url = self.get_url(endpoint, field_name=field_name, filename=relative_file)
        data = {
            'filename': file.filename,
            'title': _field_name,
            'src': url,
            'path': relative_file
        }
        return jsonify(dict(code=0, msg='', data=data))

    @expose('/download/<string:field_name>/<path:filename>')
    def download(self, field_name, filename):
        items = field_name.split('.')
        if len(items) == 1:
            field_name = items[0]
            form = self.get_form()
        else:
            field_name = items[1]
            form = self.get_form(items[0])

        field = getattr(form, field_name)
        if isinstance(field, UnboundField):
            base_path = field.kwargs['base_path']
        else:
            base_path = field.base_path

        if base_path is None:
            abort(500)

        if callable(base_path):
            base_path = base_path()

        as_attachment = bool(request.args.get('attachment'))
        return send_from_directory(base_path, filename, as_attachment=as_attachment)


class BaseModelView(BaseModelViewMixin, _BaseModelView):
    pass
