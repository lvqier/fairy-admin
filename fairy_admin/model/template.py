from flask import url_for
from flask_admin.babel import gettext


class BaseRowAction(object):
    def __init__(self, event, icon=None, klass=None, name=None, endpoint='.action_ajax_view'):
        self.event = event
        self.icon = icon
        self.klass = klass
        self.name = name
        self.endpoint = endpoint

    def convert(self):
        return {
            'event': self.event,
            'icon': self.icon,
            'class': self.klass,
            'name': self.name
        }

    @property
    def url(self):
        return url_for(self.endpoint, action_name=self.event)


class AjaxRowAction(BaseRowAction):
    def __init__(self, event, confirmation=None, **kwargs):
        super(AjaxRowAction, self).__init__(event, **kwargs)
        self.confirmation = confirmation

    def convert(self):
        result = super(AjaxRowAction, self).convert()
        result.update({
            'ajax': True,
            'data': {
                'confirmation': self.confirmation,
                'url': self.url
            }
        })
        return result


class ModalRowAction(BaseRowAction):
    def __init__(self, event, modal_title, form=True, btn=True, **kwargs):
        super(ModalRowAction, self).__init__(event, **kwargs)
        self.modal_title = modal_title
        self.form = form
        self.btn = btn

    def convert(self):
        result = super(ModalRowAction, self).convert()
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
                'url': self.url,
                'title': self.modal_title,
                'form': self.form,
                'btn': btn
            }
        })
        return result

    @property
    def url(self):
        return url_for(self.endpoint, action_name=self.event, modal=True)


class LinkRowAction(BaseRowAction):
    def __init__(self, event, **kwargs):
        super(LinkRowAction, self).__init__(event, **kwargs)

    def convert(self):
        result = super(LinkRowAction, self).convert()
        result.update({
            'ajax': False,
            'data': {
                'modal': False,
                'url': self.url
            }
        })
        return result
