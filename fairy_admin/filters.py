import datetime


class SQLAlchemyFilter(object):
    def __init__(self, model, query=None):
        self.model = model
        self.query = query or model.query

    def apply(self, filter_sos):
        conditions = self.build_children(filter_sos)
        return self.query.filter(conditions)

    def build_children(self, children):
        conditions = None
        for filter_so in children:
            prefix, condition = self.build_filter_so(filter_so)
            if condition is None:
                continue
            if conditions is None:
                conditions = condition
            elif prefix == 'and':
                conditions = conditions & condition
            elif prefix == 'or':
                conditions = conditions | condition
            else:
                assert False, 'Invalid prefix {}'.format(prefix)
        return conditions

    def build_filter_so(self, filter_so):
        prefix = filter_so['prefix']
        mode = filter_so['mode']
        if mode == 'condition':
            return prefix, self.build_filter_so_condition(filter_so)
        elif mode == 'group':
            return prefix, self.build_filter_so_children(filter_so)
        elif mode == 'in':
            return prefix, self.build_filter_so_in(filter_so)
        elif mode == 'date':
            return prefix, self.build_filter_so_date(filter_so)
        else:
            assert False, 'Unsupported mode {}'.format(mode)

    def build_filter_so_condition(self, filter_so):
        field_name = filter_so['field']
        field = self.get_field(field_name)
        type = filter_so['type']
        value = filter_so['value']
        if type == 'eq':
            condition = field == value
        elif type == 'ne':
            condition = field != value
        elif type == 'gt':
            condition = field > value
        elif type == 'ge':
            condition = field >= value
        elif type == 'lt':
            condition = field < value
        elif type == 'le':
            condition = field <= value
        elif type == 'contain':
            value = '%{}%'.format(value)
            condition = field.like(value)
        elif type == 'notContain':
            value = '%{}%'.format(value)
            condition = ~field.like(value)
        elif type == 'start':
            value = '{}%'.format(value)
            condition = field.like(value)
        elif type == 'end':
            value = '%{}'.format(value)
            condition = field.like(value)
        elif type == 'null':
            condition = field is None
        elif type == 'notNull':
            condition = field is not None
        else:
            assert False, 'Unsupported condition type {}'.format(type)
        return condition

    def build_filter_so_children(self, filter_so):
        children = filter_so['children']
        return self.build_children(children)

    def build_filter_so_in(self, filter_so):
        field_name = filter_so['field']
        field = self.get_field(field_name)
        values = filter_so['values']
        return field.in_(values)

    def build_filter_so_date(self, filter_so):
        field_name = filter_so['field']
        field = self.get_field(field_name)
        type = filter_so['type']
        value = filter_so['value']
        if type == 'yesterday':
            now = datetime.datetime.now()
            today = datetime.datetime(now.year, now.month, now.day)
            yestoday = today - datetime.timedelta(days=1)
            return field >= yestoday & field < today
        elif type == 'thisWeek':
            now = datetime.datetime.now()
            today = datetime.datetime(now.year, now.month, now.day)
            sunday = today - datetime.timedelta(days=dt.weekday())
            next_sunday = sunday + datetime.timedelta(days=7)
            return field >= sunday & field < next_sunday
        elif type == 'lastWeek':
            now = datetime.datetime.now()
            today = datetime.datetime(now.year, now.month, now.day)
            sunday = today - datetime.timedelta(days=dt.weekday())
            prev_sunday = sunday - datetime.timedelta(days=7)
            return field >= prev_sunday & field < sunday
        elif type == 'thisMonth':
            now = datetime.datetime.now()
            month_1st = datetime.datetime(now.year, now.month, 1)
            next_month_1st = datetime.datetime(now.year + int(now.month / 12), now.month % 12 + 1, 1)
            print(month_1st, next_month_1st)
            return field >= month_1st & field < next_month_1st
        elif type == 'thisYear':
            now = datetime.datetime.now()
            year_1st = datetime.datetime(now.year, 1, 1)
            next_year_1st = datetime.datetime(now.year + 1, 1, 1)
            return field >= year_1st & field < next_year_1st
        elif type == 'specific':
            value = filter_so['value']
            # TODO finish fmt
            value = datetime.datetime.strptime(value, 'fmt')
            date = datetime.datetime(value.year, value.month, value.day)
            tomorrow = date + datetime.timedelta(days=1)
            return field >= date & field < tomorrow
        elif type == 'all':
            return None
        else:
            assert False, 'Unsupported date type {}'.format(type)

    def get_field(self, field_name):
        return getattr(self.model, field_name)
