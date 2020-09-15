class Base(object):
    pass

class BaseStruct(Base):
    @classmethod
    def encode(cls, dct, packer):
        for name, encoder, default in cls.__struct__:
            value = dct.get(name, default)
            if value is not None:
                encoder.encode(value, packer)

class BaseDataFormat(BaseStruct):
    pass

class BaseSampleFormat(BaseDataFormat):
    pass


class BaseCounterData(BaseDataFormat):
    pass


class BaseFlowData(BaseDataFormat):
    pass
