
from flask_admin.contrib.sqla.form import AdminModelConverter as _AdminModelConverter

from .fields import QuerySelectMultipleField


class AdminModelConverter(_AdminModelConverter):
    def __init__(self, *args):
        super(AdminModelConverter, self).__init__(*args)
