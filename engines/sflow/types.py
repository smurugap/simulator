from builtins import str
import binascii
import ipaddress

from sflow.base import Base, BaseStruct


class Int(Base):
    @staticmethod
    def encode(value, packer):
        return packer.pack_int(value)

class UInt(Base):
    @staticmethod
    def encode(value, packer):
        return packer.pack_uint(value)

class UHyper(Base):
    @staticmethod
    def encode(value, packer):
        return packer.pack_uhyper(value)

class String(Base):
    @staticmethod
    def encode(value, packer):
        return packer.pack_string(value)

class Opaque(Base):
    @staticmethod
    def encode(value, packer):
        return packer.pack_opaque(value)

class HexOpaque(Base):
    @staticmethod
    def encode(value, packer):
        packer.pack_opaque(value)

class Array(object):
    def __init__(self, t):
        self._type = t

    def _encode_item(self, value, packer):
        return self._type.encode(value, packer)

    def encode(self, values, packer):
        packer.pack_array(values, lambda y: self._encode_item(y, packer))

class IPv4(Base):
    @staticmethod
    def encode(value, packer):
        packer.pack_uint(value)

class IPv6(Base):
    @staticmethod
    def encode(value, packer):
        packer.pack_fopaque(16, value)

class Address(Base):
    UNKNOWN = 0
    IP_V4 = 1
    IP_V6 = 2

    @classmethod
    def encode(cls, value, packer):
        address = ipaddress.ip_address(str(value))
        ip_version = address.version
        if ip_version == 4:
            packer.pack_uint(cls.IP_V4)
            IPv4.encode(address._ip, packer)
        elif ip_version == 6:
            packer.pack_uint(cls.IP_V6)
            IPv6.encode(address._ip, packer)
        else:
            raise TypeError('Unknown address type: {}'.format(ip_version))

class DataFormat(Base):
    @staticmethod
    def encode(value, packer):
        enterprise, data_type = value
        enterprise = (enterprise & 0x000FFFFF) << 12
        data_type = (data_type & 0x00000FFF)
        packer.pack_uint(enterprise | data_type)
