import json
import os
import uuid

from datetime import datetime
from flask import request, jsonify, get_flashed_messages, abort
from flask_admin import expose
from flask_admin.helpers import get_redirect_target
from flask_admin.model import BaseModelView as _BaseModelView
from flask_admin.model.base import ViewArgs
from flask_admin.babel import gettext
from markupsafe import Markup
from math import ceil

from .fields import UnboundField
from .template import AjaxRowAction, ModalRowAction, LinkRowAction


class BaseModelViewMixin(object):
    can_export = True
    page_size = 10
    form_label_width = None
    '''
    form_label_width allows user to control width of label on the left side of form input
    '''
    column_display_numbers = False
    column_actions_width = 178
    column_action_details = True
    column_action_edit = True
    column_action_delete = True

    def __init__(self, *args, **kwargs):
        super(BaseModelViewMixin, self).__init__(*args, **kwargs)
        datetime_formatter = self.column_type_formatters.get(datetime)
        if datetime_formatter is None:
            self.column_type_formatters[datetime] = self._datetime_formatter
        self.column_type_formatters[bool] = self._bool_formatter

    def _datetime_formatter(self, view, value):
        datetime_format = getattr(self, 'datetime_format', '%Y-%m-%d %H:%M:%S')
        return value.strftime(datetime_format)

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

    def model_can_view_details(self, row):
        '''
        按行检查是否支持查看详情，用于控制行内“详情”按钮
        '''
        return self.can_view_details

    def model_can_edit(self, row):
        '''
        按行检查是否支持编辑，用于控制行内“编辑”按钮
        '''
        return self.can_edit

    def model_can_delete(self, row):
        '''
        按行检查是否支持编辑，用于控制行内“删除”按钮
        '''
        return self.can_delete

    def model_check_extra_action(self, row, action):
        '''
        按行检查是否支持额外动作，用于控制行内相应动作按钮
        '''
        return True

    def _get_list_row_actions(self, item):
        '''
        关于 action:
        a. 异步: 异步请求: ajax=True
          1. 区分是否弹框提示: confirmation
        b. 同步: 打开页面: ajax=False
          1. 弹框: modal=object
            i. 区分是否可编辑: form
          2. 跳转
        '''
        pk = self.get_pk_value(item)

        actions = []
        if self.model_can_view_details(item) and self.column_action_details:
            name = gettext('Details')
            if self.details_modal:
                modal_title = '{} #{}'.format(gettext('View Record'), pk)
                action = ModalRowAction('details', '.details_view', modal_title, form=False, name=name)
            else:
                action = LinkRowAction('details', '.details_view', name=name)
            actions.append(action)

        if self.model_can_edit(item) and self.column_action_edit:
            name = gettext('Edit')
            if self.edit_modal:
                modal_title = '{} #{}'.format(gettext('Edit Record'), pk)
                action = ModalRowAction('edit', '.edit_view', modal_title, form=True, name=name)
            else:
                url = self.get_url('.edit_view', id=pk)
                action = LinkRowAction('edit', '.edit_view', name=name)
            actions.append(action)

        if self.model_can_delete(item) and self.column_action_delete:
            name = gettext('Delete')
            confirmation = gettext('Are you sure you want to delete this record?')
            action = AjaxRowAction('delete', '.ajax_action_view', confirmation=confirmation, klass='danger', name=name)
            actions.append(action)

        if self.column_extra_row_actions:
            for extra_action in self.column_extra_row_actions:
                if self.model_check_extra_action(item, extra_action):
                    actions.append(extra_action)

        return actions

    def get_actions_list(self):
        actions = []
        if self.can_create:
            name = gettext('Create')
            if self.create_modal:
                modal_title = gettext('Create New Record')
                action = ModalRowAction('create', '.create_view', modal_title, form=True, name=name)
            else:
                action = LinkRowAction('create', '.create_view', name=name)
            actions.append(action)

        action_list, actions_confirmation = super(BaseModelViewMixin, self).get_actions_list()

        for action_name, title in action_list:
            confirmation=actions_confirmation.get(action_name)
            klass = None
            if action_name == 'delete':
                klass = 'danger'
            action = AjaxRowAction(action_name, '.ajax_action_view', confirmation=confirmation, klass=klass, name=title)
            actions.append(action)

        return bool(action_list), actions

    @expose('/ajax/config/')
    def ajax_config(self):
        '''
        LayUI 的数据表配置接口
        '''
        limits = [self.page_size]
        if self.can_set_page_size:
            limits = [20, 50, 100]
            if self.page_size not in limits:
                limits.insert(0, self.page_size)

        # return_url = get_redirect_target() or self.get_url('.index_view')

        display_checkbox, actions = self.get_actions_list()

        filter_groups = self._get_filter_groups()
        columns = []
        for c, name in self._list_columns:
            column = {
                'field': c,
                'sort': self.is_sortable(c),
                'title': name,
                'description': self.column_descriptions.get(c),
            }
            if filter_groups and name in filter_groups:
                column['filter'] = True

            columns.append(column)

        default_tool_bar = ['filter']
        if self.can_export:
            default_tool_bar.append('exports')
        default_tool_bar.append('print')

        result = {
            'url': self.get_url('.ajax'),
            'page': {
                'limit': self.page_size,
                'limits': limits,
                'prev': gettext('Prev'),
                'next': gettext('Next')
            },
            'actions': [action.convert() for action in actions],
            'cols': columns,
            'default_tool_bar': default_tool_bar,
            'column_display_numbers': self.column_display_numbers,
            'column_display_checkbox': display_checkbox,
            'column_display_actions': self.column_display_actions,
            'column_actions_width': self.column_actions_width,
            'can_edit': self.can_edit,
            'can_view_details': self.can_view_details,
            'can_delete': self.can_delete,
        }

        return jsonify(result)

    @expose('/ajax/')
    def ajax(self):
        '''
        LayUI 的数据表数据接口
        '''
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

        referer = request.headers.get('Referer')

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

    @expose('/ajax/action/', methods=['POST'])
    def ajax_action_view(self):
        '''
        动作执行接口，同时服务批量操作与按行操作
        '''
        data = request.json
        action = data['action']
        ids = data['ids']

        handler = self._actions_data.get(action)
        if handler and self.is_action_allowed(action):
            try:
                response = handler[0](ids)
            except Exception as e:
                result = dict(code=500, msg='Failed to perform action. {}'.format(e.message))
            else:
                result = dict(code=0, msg='Success')
        else:
            result = dict(code=403, msg='Action is not allowed.')
        get_flashed_messages()
        return jsonify(result)

    @expose('/ajax/new/', methods=['POST'])
    def ajax_create_view(self):
        '''
        异步创建接口
        '''
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
        '''
        异步保存编辑接口
        '''
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
        '''
        异步删除接口
        '''
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

    @expose('/ajax/upload/<string:field_name>', methods=['POST'])
    def ajax_upload(self, field_name):
        '''
        异步上传接口，服务文件上传字段
        '''
        form = self.get_form()
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
        url = self.get_url(endpoint, filename=relative_file)
        data = {
            'filename': file.filename,
            'title': field_name,
            'src': url,
            'path': relative_file
        }
        return jsonify(dict(code=0, msg='', data=data))

    def is_editable(self, item):
        return True

    def is_deletable(self, item):
        return True


class BaseModelView(BaseModelViewMixin, _BaseModelView):
    pass
