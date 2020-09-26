
from wtforms import form


class Form(form.Form):
    modal_template = 'admin/model/modals/action_form.html'

    def on_prefill(self, ids):
        """
        Override to prefill form data
        """
        pass
