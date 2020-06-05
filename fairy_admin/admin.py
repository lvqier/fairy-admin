
import os
import json

from flask import Blueprint, request, abort, jsonify
from flask_admin import Admin, expose
from flask_admin.model.base import ViewArgs, BaseModelView
from math import ceil
from wtforms.widgets import TextArea


TextArea.tag = 'textarea'

CWD = os.path.dirname(os.path.abspath(__file__))


class FairyAdmin(Admin):

    def init_app(self, app, *args, **kwargs):
        super(FairyAdmin, self).init_app(app, *args, **kwargs)
        template_folder = os.path.join('templates', self.template_mode)
        blueprint = Blueprint('fairy_admin', __name__, template_folder=template_folder, static_folder='static')
        app.register_blueprint(blueprint, url_prefix='/admin/fairy')


def _ajax(self):
    view_args = ViewArgs(page=request.args.get('page', 1, type=int),
            page_size=request.args.get('limit', 0, type=int),
            sort=request.args.get('sort', None, type=int),
            sort_desc=request.args.get('desc', None, type=int),
            search=request.args.get('search', None),
            filters=self._get_list_filter_args(),
            extra_args=dict([
                (k, v) for k, v in request.args.items()
                if k not in ('page', 'page_size', 'sort', 'desc', 'search', ) and
                not k.startswith('flt')
            ]))

    sort_column = self._get_column_by_idx(view_args.sort)
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
        for list_column in list_columns:
            field = list_column[0]
            item[field] = getattr(row, field)
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

    form = self.delete_form()

    if not self.validate_form(form):
        return jsonify(dict(code=400, msg='Form validate failed'))

    id = form.id.data

    model = self.get_one(id)
    if model is None:
        return jsonify(dict(code=404, msg='Record does not exist.'))

    if not self.delete_model(model):
        return jsonify(dict(code=500, msg='Unknown error.'))
    return jsonify(dict(code=0, msg=''))


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
