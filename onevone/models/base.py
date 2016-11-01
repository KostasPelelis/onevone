class SerializedMixin(object):

    # Code taken from http://stackoverflow.com/a/9746249/2277088

    def serialize(self):
        cls = self.__class__
        ret = dict()
        for column in cls.__table__.columns:
            value = getattr(self, column.name)
            if value is not None:
                ret[column.name] = value
        return ret

    def serialize_only(self, fields=[]):
        cls = self.__class__
        ret = dict()
        columns = set([column.name for column in cls.__table__.columns])
        if not set(fields).issubset(columns):
            raise Exeption(
                'One or more fields are not part of table {0}'.format(str(cls.table)))
        for field in fields:
            ret[field] = getattr(self, field)
        return ret