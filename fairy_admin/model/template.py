from flask import url_for
from flask_admin.babel import gettext


class BaseRowAction(object):
    def __init__(self, event, icon=None, klass=None, name=None):
        self.event = event
        self.icon = icon
        self.klass = klass
        self.name = name

    def convert(self):
        return {
            'event': self.event,
            'icon': self.icon,
            'class': self.klass,
            'name': self.name
        }


class AjaxRowAction(BaseRowAction):
    def __init__(self, event, endpoint, confirmation=None, **kwargs):
        super(AjaxRowAction, self).__init__(event, **kwargs)
        self.endpoint = endpoint
        self.confirmation = confirmation

    def convert(self):
        result = super(AjaxRowAction, self).convert()
        url = url_for(self.endpoint)
        result.update({
            'ajax': True,
            'data': {
                'confirmation': self.confirmation,
                'url': url
            }
        })
        return result


class ModalRowAction(BaseRowAction):
    def __init__(self, event, endpoint, modal_title, form=True, btn=True, **kwargs):
        super(ModalRowAction, self).__init__(event, **kwargs)
        self.endpoint = endpoint
        self.modal_title = modal_title
        self.form = form
        self.btn = btn

    def convert(self):
        result = super(ModalRowAction, self).convert()
        url = url_for(self.endpoint, modal=True)
        btn = self.btn
        if self.btn is True:
            if self.form:
                btn = [gettext('Save'), gettext('Cancel')]
            else:
                btn = [gettext('Done')]

        result.update({
            'ajax': False,
            'data': {
                'modal': True,
                'url': url,
                'title': self.modal_title,
                'form': self.form,
                'btn': btn
            }
        })
        return result


class LinkRowAction(BaseRowAction):
    def __init__(self, event, endpoint, **kwargs):
        super(LinkRowAction, self).__init__(event, **kwargs)
        self.endpoint = endpoint

    def convert(self):
        result = super(LinkRowAction, self).convert()
        url = url_for(self.endpoint)
        result.update({
            'ajax': False,
            'data': {
                'modal': False,
                'url': url
            }
        })
        return result
