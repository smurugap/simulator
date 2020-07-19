from sflow.base import Base, BaseStruct, BaseSampleFormat
from sflow.base import BaseCounterData, BaseFlowData
from sflow.types import Address, Array, DataFormat, UInt
from sflow.flows.inmon import SampledHeader
from sflow.constants import SAMPLING_RATE
from random import randint

class FlowRecord(BaseStruct):
    @staticmethod
    def encode(value, packer):
        DataFormat.encode((0, 1), packer)
        record_length = len(value['header']) + 16
        UInt.encode(record_length, packer)
        SampledHeader.encode(value, packer)

class FlowSample(BaseSampleFormat):
    __format__ = (0, 1)
    __struct__ = [
        ('sequence_number', UInt, randint(100, 999)),
        ('source_id', UInt, None),
        ('sampling_rate', UInt, SAMPLING_RATE),
        ('sample_pool', UInt, randint(10000, 100000)),
        ('drops', UInt, randint(1, 10)),
        ('input', UInt, None),
        ('output', UInt, 0),
        ('flow_records', Array(FlowRecord), None),
    ]


class SampleRecord(Base):
    @staticmethod
    def encode(value, packer):
        sample_length = len(value['flow_records'][0]['header']) + 58
        DataFormat.encode((0, 1), packer)
        UInt.encode(sample_length, packer)
        FlowSample.encode(value, packer)

class Datagram(BaseStruct):
    __struct__ = [
        ('version', UInt, 5),
        ('agent_address', Address, None),
        ('sub_agent_id', UInt, 0),
        ('sequence_number', UInt, randint(100, 999)),
        ('uptime', UInt, randint(10000, 100000)),
        ('samples', Array(SampleRecord), None),
    ]
