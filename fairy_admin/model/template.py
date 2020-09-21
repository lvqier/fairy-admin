from flask import url_for
from flask_admin.babel import gettext


POSITION_HEAD = 0X01
POSITION_ROW = 0x02


class BaseAction(object):
    def __init__(self, event, position=POSITION_HEAD, icon=None, klass=None, name=None, endpoint='.action_ajax_view'):
        self.event = event
        self.position = position
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


class AjaxAction(BaseAction):
    def __init__(self, event, confirmation=None, **kwargs):
        super(AjaxAction, self).__init__(event, **kwargs)
        self.confirmation = confirmation

    def convert(self):
        result = super(AjaxAction, self).convert()
        result.update({
            'ajax': True,
            'data': {
                'confirmation': self.confirmation,
                'url': self.url
            }
        })
        return result


class AjaxRowAction(AjaxAction):
    def __init__(self, event, endpoint, **kwargs):
        super(AjaxRowAction, self).__init__(event, endpoint=endpoint, **kwargs)
        print('AjaxRowAction is deprecated, please use AjaxAction instead')


class AjaxModalAction(BaseAction):
    def __init__(self, event, modal_title, form=True, btn=True, **kwargs):
        super(AjaxModalAction, self).__init__(event, **kwargs)
        self.modal_title = modal_title
        self.form = form
        self.btn = btn

    def convert(self):
        result = super(AjaxModalAction, self).convert()
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
                'form': bool(self.form),
                'btn': btn
            }
        })
        return result

    @property
    def url(self):
        return url_for(self.endpoint, action_name=self.event, modal=True)


class ModalRowAction(AjaxModalAction):
    def __init__(self, event, endpoint, *args, **kwargs):
        super(ModalRowAction, self).__init__(event, *args, endpoint=endpoint, **kwargs)
        print('ModalRowAction is deprecated, please use ModalRowAction instead')


class LinkAction(BaseAction):
    def __init__(self, event, **kwargs):
        super(LinkAction, self).__init__(event, **kwargs)

    def convert(self):
        result = super(LinkAction, self).convert()
        result.update({
            'ajax': False,
            'data': {
                'modal': False,
                'url': self.url
            }
        })
        return result


class LinkRowAction(LinkAction):
    def __init__(self, event, endpoint, **kwargs):
        super(LinkRowAction, self).__init__(event, endpoint=endpoint, **kwargs)
        print('LinkRowAction is deprecated, please use LinkAction instead')
