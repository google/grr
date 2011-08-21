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

"""Implement access to the windows registry."""


import os
import stat
import StringIO


from winsys import registry
from grr.client import vfs
from grr.lib import utils
from grr.proto import jobs_pb2


class RegistryFile(vfs.AbstractFileHandler):
  """Emulate registry access through the VFS."""

  supported_pathtype = jobs_pb2.Path.REGISTRY

  def __init__(self, pathspec):
    path = pathspec.path
    # Paths are always / in the VFS
    moniker = path.replace("/", "\\")

    self.request = pathspec

    try:
      # Maybe its a key
      self.path_type = "key"
      self.reg_handle = registry.registry(moniker, access="QR")
      if not self.reg_handle:
        # Maybe its a value
        path, value = os.path.split(path)

        # Account for the default value
        if value == "@": value = ""

        moniker = ":".join((path, value))
        self.path_type = "value"
        self.reg_handle = registry.registry(moniker, access="QR")
        self.fd = StringIO.StringIO(
            self.EncodeValue(self.reg_handle.value(), self.reg_handle.value_))

    except (registry.x_registry, registry.x_moniker):
      raise IOError

  def EncodeValue(self, value, reg_type):
    """Encode the value depending on its type."""
    reg_types = registry.REGISTRY_VALUE_TYPE

    # Unicode is UTF8 encoded.
    if reg_type in [reg_types.REG_SZ, reg_types.REG_EXPAND_SZ]:
      result = value.encode("utf8", "ignore")
    else:
      # Everything else is literal.
      result = str(value)

    return result

  def ListFiles(self):
    """A generator of all keys and values."""
    if self.path_type != "key":
      raise IOError("%s is not a directory" % self.path)

    # Keys first
    for k in self.reg_handle:
      response = jobs_pb2.StatResponse()
      response.path = k.name
      response.pathspec.CopyFrom(self.request)
      response.pathspec.path = utils.Join(response.pathspec.path, k.name)
      response.st_mode = stat.S_IFDIR
      # TODO(user): Come up with a way to map security descriptors to stat
      yield response

    # Now values
    for name, value, t in self.reg_handle.values(_want_types=True):
      value = self.EncodeValue(value, t)
      response = jobs_pb2.StatResponse()
      response.path = name
      response.pathspec.CopyFrom(self.request)
      response.pathspec.path = "/".join((response.pathspec.path, name))
      response.st_mode = stat.S_IFREG
      response.st_size = len(value)
      response.registry_type = t
      response.resident = value

      yield response
