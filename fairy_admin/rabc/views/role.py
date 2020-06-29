
from flask_admin.contrib.sqla import ModelView


class RoleView(ModelView):
    create_modal = True
    edit_modal = True

    column_list = ['name', 'code']
    form_columns = ['name', 'code', 'description', 'permissions']
