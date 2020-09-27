
from flask_admin.form import SecureForm


class ActionForm(SecureForm):
    modal_template = 'admin/model/modals/action_form.html'

    def on_prefill(self, ids):
        """
        Override to prefill form data
        """
        pass


class Form(ActionForm):
    def __init__(self, *args, **kwargs):
        print('fairy_admin.form.form.Form is deprecated, please use fairy_admin.form.ActionForm instead.')
        super(Form, self).__init__(*args, **kwargs)
