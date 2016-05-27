#!/usr/bin/env python
"""Compatibility mode.

This file defines a bunch of compatibility fixes to ensure we can run on older
versions of dependencies.
"""



def MonkeyPatch(cls, method_name, method):
  try:
    return getattr(cls, method_name)
  except AttributeError:
    setattr(cls, method_name, method)
    return method

# Fixup the protobuf implementation.
# pylint: disable=g-import-not-at-top
try:
  from google.protobuf import message

  # These are required to make protobufs pickle-able
  # pylint: disable=g-bad-name
  def Message__getstate__(self):
    """Support the pickle protocol."""
    return dict(serialized=self.SerializePartialToString())

  def Message__setstate__(self, state):
    """Support the pickle protocol."""
    self.__init__()
    self.ParseFromString(state["serialized"])

  MonkeyPatch(message.Message, "__getstate__", Message__getstate__)
  MonkeyPatch(message.Message, "__setstate__", Message__setstate__)

except ImportError:
  pass
