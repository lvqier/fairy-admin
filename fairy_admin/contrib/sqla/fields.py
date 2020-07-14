from flask_admin.contrib.sqla.fields import QuerySelectMultipleField
from wtforms.fields import Field

from fairy_admin.model.fields import _process_formdata


QuerySelectMultipleField._old_process_formdata = QuerySelectMultipleField.process_formdata
QuerySelectMultipleField.process_formdata = _process_formdata
