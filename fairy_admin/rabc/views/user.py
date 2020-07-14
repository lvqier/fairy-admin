from fairy_admin.contrib.sqla import ModelView


class UserView(ModelView):
    create_modal = True
    edit_modal = True

    column_list = ['nickname', 'username', 'mobile', 'email', 'active']
    form_columns = ['nickname', 'username', 'password', 'mobile', 'email', 'roles', 'active']
