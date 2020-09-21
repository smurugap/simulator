# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: authentication.proto

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='authentication.proto',
  package='authentication',
  syntax='proto3',
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_pb=b'\n\x14\x61uthentication.proto\x12\x0e\x61uthentication\"F\n\x0cLoginRequest\x12\x11\n\tuser_name\x18\x01 \x01(\t\x12\x10\n\x08password\x18\x02 \x01(\t\x12\x11\n\tclient_id\x18\x03 \x01(\t\"\x1c\n\nLoginReply\x12\x0e\n\x06result\x18\x01 \x01(\x08\x32Q\n\x05Login\x12H\n\nLoginCheck\x12\x1c.authentication.LoginRequest\x1a\x1a.authentication.LoginReply\"\x00\x62\x06proto3'
)




_LOGINREQUEST = _descriptor.Descriptor(
  name='LoginRequest',
  full_name='authentication.LoginRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='user_name', full_name='authentication.LoginRequest.user_name', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='password', full_name='authentication.LoginRequest.password', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='client_id', full_name='authentication.LoginRequest.client_id', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=40,
  serialized_end=110,
)


_LOGINREPLY = _descriptor.Descriptor(
  name='LoginReply',
  full_name='authentication.LoginReply',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='result', full_name='authentication.LoginReply.result', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=112,
  serialized_end=140,
)

DESCRIPTOR.message_types_by_name['LoginRequest'] = _LOGINREQUEST
DESCRIPTOR.message_types_by_name['LoginReply'] = _LOGINREPLY
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

LoginRequest = _reflection.GeneratedProtocolMessageType('LoginRequest', (_message.Message,), {
  'DESCRIPTOR' : _LOGINREQUEST,
  '__module__' : 'authentication_pb2'
  # @@protoc_insertion_point(class_scope:authentication.LoginRequest)
  })
_sym_db.RegisterMessage(LoginRequest)

LoginReply = _reflection.GeneratedProtocolMessageType('LoginReply', (_message.Message,), {
  'DESCRIPTOR' : _LOGINREPLY,
  '__module__' : 'authentication_pb2'
  # @@protoc_insertion_point(class_scope:authentication.LoginReply)
  })
_sym_db.RegisterMessage(LoginReply)



_LOGIN = _descriptor.ServiceDescriptor(
  name='Login',
  full_name='authentication.Login',
  file=DESCRIPTOR,
  index=0,
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_start=142,
  serialized_end=223,
  methods=[
  _descriptor.MethodDescriptor(
    name='LoginCheck',
    full_name='authentication.Login.LoginCheck',
    index=0,
    containing_service=None,
    input_type=_LOGINREQUEST,
    output_type=_LOGINREPLY,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
])
_sym_db.RegisterServiceDescriptor(_LOGIN)

DESCRIPTOR.services_by_name['Login'] = _LOGIN

# @@protoc_insertion_point(module_scope)
