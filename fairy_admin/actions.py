import json

from collections import namedtuple
from flask import request, url_for, jsonify, abort, get_flashed_messages
from flask_admin import tools, expose
from flask_admin._compat import text_type
from flask_admin.helpers import get_redirect_target
from flask_admin.actions import ActionsMixin as _ActionsMixin
from flask_admin.babel import gettext

from .model.template import AjaxAction, AjaxModalAction, LinkAction


Action = namedtuple('Action', ['func', 'text', 'form', 'confirmation'])

def action(name, text, form=None, confirmation=None):
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
        f._action = (name, text, form, confirmation)
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
        TODO: treat create, delete, edit, view_details as action
        """
        self._actions = []
        self._actions_data = {}

        for p in dir(self):
            attr = tools.get_dict_attr(self, p)

            if hasattr(attr, '_action'):
                # 兼容 flask_admin.action
                if len(attr._action) == 3:
                    name, text, desc = attr._action
                    form = None
                else:
                    name, text, form, desc = attr._action
                func = getattr(self, p)
                self._actions.append((name, text))
                self._actions_data[name] = Action(func, text, form, desc)

    def get_actions_list(self):
        """
        Return a list and a dictironary of allowed actions.
        Overwrite flask_admin.actions.ActionsMixin.get_actions_list
        """
        all_actions = []
        actions = {}
        if self.can_create:
            action_name = 'create'
            title = gettext('Create')
            if self.create_modal:
                modal_title = gettext('Create New Record')
                action = AjaxModalAction(
                    action_name,
                    modal_title,
                    form=True,
                    name=title,
                    endpoint='.create_view'
                )
            else:
                action = LinkAction(
                    action_name,
                    name=title,
                    endpoint='.create_view'
                )
            actions[action_name] = action
            all_actions.append(action_name)

        action_list = []
        actions_confirmation = {}
        for act in self._actions:
            name, text = act

            if self.is_action_allowed(name):
                action_list.append((name, text_type(text)))

                confirmation = self._actions_data[name].confirmation
                if confirmation:
                    actions_confirmation[name] = text_type(confirmation)

        for action_name, title in action_list:
            confirmation = actions_confirmation.get(action_name)
            klass = None
            if action_name == 'delete':
                klass = 'danger'
            form = self._actions_data[action_name].form
            if form is not None:
                action = AjaxModalAction(
                    action_name,
                    title,
                    form=True,
                    name=title,
                    endpoint='.action_view'
                )
            else:
                action = AjaxAction(
                    action_name,
                    confirmation=confirmation,
                    klass=klass,
                    name=title
                )
            actions[action_name] = action
            all_actions.append(action_name)

        display_checkbox = False
        result_actions = []
        action_list = self.actions or all_actions
        for action_name in action_list:
            result_actions.append(actions[action_name])
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

        all_actions = []
        actions = {}
        if self.model_can_view_details(item) and self.column_action_details:
            action_name = 'details'
            title = gettext('Details')
            if self.details_modal:
                modal_title = '{} #{}'.format(gettext('View Record'), pk)
                action = AjaxModalAction(
                    action_name,
                    modal_title,
                    form=False,
                    name=title,
                    endpoint='.details_view'
                )
            else:
                action = LinkAction(
                    action_name,
                    name=title,
                    endpoint='.details_view'
                )
            all_actions.append(action_name)
            actions[action_name] = action

        if self.model_can_edit(item) and self.column_action_edit:
            action_name = 'edit'
            title = gettext('Edit')
            if self.edit_modal:
                modal_title = '{} #{}'.format(gettext('Edit Record'), pk)
                action = AjaxModalAction(
                    action_name,
                    modal_title,
                    form=True,
                    name=title,
                    endpoint='.edit_view'
                )
            else:
                action = LinkAction(
                    action_name,
                    name=title,
                    endpoint='.edit_view'
                )
            all_actions.append(action_name)
            actions[action_name] = action

        if self.model_can_delete(item) and self.column_action_delete:
            title = gettext('Delete')
            action_name = 'delete'
            confirmation = gettext('Are you sure you want to delete this record?')
            action = AjaxAction(
                action_name,
                confirmation=confirmation,
                klass='danger',
                name=title
            )
            all_actions.append(action_name)
            actions[action_name] = action

        if self.column_extra_row_actions:
            for extra_action in self.column_extra_row_actions:
                if self.model_check_extra_action(item, extra_action):
                    all_actions.append(extra_action.event)
                    actions.append(extra_action)

        result_actions = []
        action_list = self.row_actions or all_actions
        for action_name in action_list:
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

        func, text, Form, desc = self._actions_data.get(action_name)

        if request.args.get('modal'):
            template = Form.modal_template
        else:
            template = Form.template

        return_url = get_redirect_target() or self.get_url('.index_view')

        action_url = url_for('.action_ajax_view', action_name=action_name)
        kwargs = {
            'form': Form(),
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
