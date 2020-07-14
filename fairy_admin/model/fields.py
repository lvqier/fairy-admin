from wtforms.fields import DateField, DateTimeField
from wtforms.fields.core import UnboundField
from flask_admin.model.fields import AjaxSelectMultipleField


DateField.control = 'date'
DateTimeField.control = 'datetime'


def _process_formdata(self, valuelist):
    # TODO 这里需要根据 template mode 区分处理方式
    if self.widget.multiple and self.widget.tag == 'xm-select':
        valuelist = valuelist[0].split(',')
    return self._old_process_formdata(valuelist)


AjaxSelectMultipleField._old_process_formdata = AjaxSelectMultipleField.process_formdata
AjaxSelectMultipleField.process_formdata = _process_formdata
