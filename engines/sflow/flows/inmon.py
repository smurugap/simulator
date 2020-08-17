from engines.sflow.base import BaseFlowData
from engines.sflow.types import UInt, HexOpaque
from engines.sflow.constants import PAYLOAD_SIZE

class SampledHeader(BaseFlowData):
    __format__ = (0, 1)
    __struct__ = [
        ('protocol', UInt, 1),
        ('frame_length', UInt, PAYLOAD_SIZE),
        ('stripped', UInt, 4),
        ('header', HexOpaque, None),
    ]
