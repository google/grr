#!/usr/bin/env python
"""Utilities for protobufs."""

from typing import Optional
from google.protobuf import message as message_pb2


def CopyAttr(
    src_proto: message_pb2.Message,
    dest_proto: message_pb2.Message,
    field_name: str,
    dest_field_name: Optional[str] = None,
) -> None:
  """Copies a field from src_proto to dest_proto and maintains unset fields.

  When accessing an unset field in Proto2 the default value of the field is
  returned, i.e. "" for `string`s, or 0 for `int`s (if not specified
  differently).
  So when simply assigning a value from one proto to another proto
  unset fields are generally not maintained. This function adds a check for
  unset fields and keeps them unset in the `dest_proto`.

  Args:
    src_proto: Proto to copy a value from.
    dest_proto: Proto to copy a value to.
    field_name: Name of the field to copy from.
    dest_field_name: Name of the filed to copy to if unset `field_name` is used.
  """
  if not dest_field_name:
    dest_field_name = field_name
  if src_proto.HasField(field_name):
    setattr(dest_proto, dest_field_name, getattr(src_proto, field_name))
  else:
    dest_proto.ClearField(dest_field_name)
