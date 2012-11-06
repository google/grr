#!/usr/bin/env python
# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


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
# pylint: disable=C6204
try:
  from google.protobuf import message

  # These are required to make protobufs pickle-able
  # pylint: disable=C6409
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
