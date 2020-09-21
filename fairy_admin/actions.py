import json

from collections import namedtuple
from flask import request, url_for, jsonify, abort, get_flashed_messages
from flask_admin import tools, expose
from flask_admin._compat import text_type
from flask_admin.helpers import get_redirect_target
from flask_admin.actions import ActionsMixin as _ActionsMixin
from flask_admin.babel import gettext

from .model.template import AjaxAction, AjaxModalAction, LinkAction
from .model.template import POSITION_HEAD, POSITION_ROW


Action = namedtuple('Action', ['func', 'text', 'form', 'confirmation'])

def action(name, text, form=None, confirmation=None, position=POSITION_HEAD):
    """
    Use this decorator to expose actions that span more than one
    entity (model, file, etc)

    :param name:
        Action name
    :param text:
        Action text
    :param form:
        Input form for action. If not rovided, action willm be executed
        directory.
    :param confirmation:
        Confirmation text. If not provided, action will be executed
        unconditionally.
    """
    def wrap(f):
        f._action = (name, text, position, form, confirmation)
        return f
    return wrap


class ActionsMixin(_ActionsMixin):
    actions = None
    """
    用于控制表头按钮显示顺序，如果为 None 按照默认顺序显示
    """
    row_actions = None
    """
    用于控制行内按钮显示顺序，如果为 None 则按照默认顺序显示
    """

    def init_actions(self):
        """
        Initialize list of actions for the current administrative view.
        Overwrite flask_admin.actions.ActionsMixin.init_actions
        """
        self._actions = []
        self._actions_data = {}

        if self.can_create:
            action_name = 'create'
            text = 'Create'
            self._actions.append(action_name)

            title = gettext(text)
            if self.create_modal:
                modal_title = gettext('Create New Record')
                action = AjaxModalAction(
                    action_name,
                    modal_title,
                    form=True,
                    position=POSITION_HEAD,
                    name=title,
                    endpoint='.create_view'
                )
            else:
                action = LinkAction(
                    action_name,
                    name=title,
                    position=POSITION_HEAD,
                    endpoint='.create_view'
                )
            self._actions_data[action_name] = action

        if self.can_view_details:
            action_name = 'view_details'
            title = gettext('Details')
            self._actions.append(action_name)

            if self.details_modal:
                modal_title = gettext('View Record')
                action = AjaxModalAction(
                    action_name,
                    modal_title,
                    position=POSITION_ROW,
                    form=False,
                    name=title,
                    endpoint='.details_view'
                )
            else:
                action = LinkAction(
                    action_name,
                    position=POSITION_ROW,
                    name=title,
                    endpoint='.details_view'
                )
            self._actions_data[action_name] = action

        if self.can_edit:
            action_name = 'edit'
            title = gettext('Edit')
            self._actions.append(action_name)

            if self.edit_modal:
                modal_title = gettext('Edit Record')
                action = AjaxModalAction(
                    action_name,
                    modal_title,
                    position=POSITION_ROW,
                    form=True,
                    name=title,
                    endpoint='.edit_view'
                )
            else:
                action = LinkAction(
                    action_name,
                    position=POSITION_ROW,
                    name=title,
                    endpoint='.edit_view'
                )
            self._actions_data[action_name] = action

        for p in dir(self):
            attr = tools.get_dict_attr(self, p)

            if not hasattr(attr, '_action'):
                continue

            # 兼容 flask_admin.action
            if len(attr._action) == 3:
                action_name, text, desc = attr._action
                form = None
                position = POSITION_HEAD
            else:
                action_name, text, position, form, desc = attr._action

            self._actions.append(action_name)

            title = text_type(text)
            klass = None
            if action_name == 'delete':
                klass = 'danger'
                position = POSITION_HEAD | POSITION_ROW
            if form is not None:
                action = AjaxModalAction(
                    action_name,
                    text_type(text),
                    form=form,
                    position=position,
                    name=text_type(text),
                    endpoint='.action_view'
                )
            else:
                action = AjaxAction(
                    action_name,
                    confirmation=text_type(desc),
                    position=position,
                    klass=klass,
                    name=text_type(title)
                )
            self._actions_data[action_name] = action

        if self.column_extra_row_actions:
            print('BaseModelView.column_extra_row_actions is deprecated')
            for action in self.column_extra_row_actions:
                self._actions.append(action.event)
                self._actions_data[action.event] = action

    def get_actions_list(self):
        """
        Return a list and a dictironary of allowed actions.
        Overwrite flask_admin.actions.ActionsMixin.get_actions_list
        """

        display_checkbox = False
        result_actions = []
        action_list = self.actions or self._actions
        for action_name in action_list:
            action = self._actions_data[action_name]
            if not (action.position & POSITION_HEAD):
                continue
            result_actions.append(action)
            if action_name != 'create':
                display_checkbox = True

        return display_checkbox, result_actions

    def _get_list_row_actions(self, item):
        """
        关于 action:
        a. 异步: 异步请求: ajax=True
          1. 区分是否弹框提示: confirmation
        b. 同步: 打开页面: ajax=False
          1. 弹框: modal=object
            i. 区分是否可编辑: form
          2. 跳转
        """
        pk = self.get_pk_value(item)

        action_names = []
        actions = {}

        action_list = self.row_actions or self._actions
        for action_name in action_list:
            action = self._actions_data[action_name]
            if not (action.position & POSITION_ROW):
                continue
            if action_name == 'view_details':
                if self.column_action_details and self.column_action_details:
                    action_names.append(action_name)
                    actions[action_name] = action
            elif action_name == 'edit':
                if self.model_can_edit(item) and self.column_action_edit:
                    action_names.append(action_name)
                    actions[action_name] = action
            elif action_name == 'delete':
                if self.model_can_delete(item) and self.column_action_delete:
                    action_names.append(action_name)
                    actions[action_name] = action
            elif self.model_check_extra_action(item, action_name):
                action_names.append(action_name)
                actions[action_name] = action

        result_actions = []
        action_list = self.row_actions or action_names
        for action_name in action_list:
            if self.model_check_extra_action(item, action_name):
                result_actions.append(actions[action_name])

        return result_actions

    @expose('/action/<string:action_name>/', methods=['POST'])
    def action_view(self, action_name):
        """
        获取 Action 表单
        """
        if action_name not in self._actions_data:
            abort(404)
        elif not self.is_action_allowed(action_name):
            abort(403)

        action = self._actions_data[action_name]

        if request.args.get('modal'):
            template = action.form.modal_template
        else:
            template = action.form.template

        return_url = get_redirect_target() or self.get_url('.index_view')

        action_url = url_for('.action_ajax_view', action_name=action_name)
        kwargs = {
            'form': action.form(),
            'form_opts': None,
            'action_url': action_url,
            'return_url': return_url
        }
        return self.render(template, **kwargs)

    @expose('/action/<string:action_name>/ajax/', methods=['POST'])
    def action_ajax_view(self, action_name):
        """
        异步执行 Action
        """
        if action_name not in self._actions_data:
            abort(404)
        elif not self.is_action_allowed(action_name):
            abort(403)

        func, text, Form, desc = self._actions_data.get(action_name)

        action_data = json.loads(request.form['_data'])
        ids = action_data['ids']

        form = None
        if Form is not None:
            form = Form(request.form)
            if not form.validate():
                result = dict(code=400, msg='Invalid form data.')
                return jsonify(result)

        try:
            if form is None:
                response = func(ids)
            else:
                response = func(ids, form=form)
        except Exception as e:
            result = dict(
                code=500,
                msg='Failed to perform action. {}'.format(e.message)
            )
        else:
            result = dict(code=0, msg='Success')
        get_flashed_messages()
        return jsonify(result) 
