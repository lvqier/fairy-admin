import json

from flask_admin.form.widgets import Select2Widget, DateTimePickerWidget, DatePickerWidget
from markupsafe import Markup
from wtforms.widgets import TextArea, html_params


def replace_call_method(cls, new_call):
    cls.__old_call__ = cls.__call__
    cls.__call__ = new_call

TextArea.tag = 'textarea'
DateTimePickerWidget.tag = 'datetime'
DatePickerWidget.tag = 'date'

Select2Widget.__old_call__ = Select2Widget.__call__


def _repr(value):
    return str(value)


def _xm_select_call(self, field, options=None, **kwargs):
    if not self.multiple:
        return self.__old_call__(field, **kwargs)
    options = []
    for val, label, selected in field.iter_choices():
        options.append(dict(name=str(label), value=val, selected=selected))
    params = {
        'class': 'xm-select',
        'data-name': field.name,
        'data-options': json.dumps(options)
    }
    return Markup('<div %s></div>' % html_params(**params))

Select2Widget.tag = 'xm-select'
replace_call_method(Select2Widget, _xm_select_call)

