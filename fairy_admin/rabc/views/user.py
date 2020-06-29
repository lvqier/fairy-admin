from flask_admin.contrib.sqla import ModelView


class UserView(ModelView):
    create_modal = True
    edit_modal = True

    column_list = ['nickname', 'username', 'mobile', 'email', 'status']
    form_columns = ['nickname', 'username', 'password', 'mobile', 'email', 'roles', 'status']
    form_choices = {
        'status': (('enabled', '启用'), ('disabled', '禁用'))
    }
