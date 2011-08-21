#!/usr/bin/env python

# Copyright 2010 Google Inc.
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

"""This file implements a VFS abstraction on the client."""


from grr.client import client_utils
from grr.lib import registry
from grr.lib import utils


class VFSHandler(object):
  """Base class for handling objects in the VFS."""
  # The altitude in the VFSHandler stack. Higher number is attempted
  # later.
  altitude = 10
  supported_pathtype = -1
  size = 0
  offset = 0

  __metaclass__ = registry.MetaclassRegistry

  def __init__(self, path):
    """Constructor.

    Args:
      path: A virtual filesystem path.
    Raises:
      IOError: if this handler can not be instantiated over the
      requested path.
    """
    self.path = path

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.Close()
    return False

  def Seek(self, offset, whence=0):
    if whence == 0:
      self.offset = offset
    elif whence == 1:
      self.offset += offset
    elif whence == 2:
      self.offset = self.size + offset
    else:
      raise RuntimeError("Illegal whence value %s" % whence)

  def Read(self, length):
    """Reads some data from the file."""
    raise IOError("Not implemented")

  def Stat(self):
    """Returns a StatResponse proto about this file."""
    raise IOError("Not implemented")

  def Tell(self):
    return self.offset

  def Close(self):
    """Close internal file descriptors."""

  # These are file object conformant namings for library functions that
  # grr uses, and that expect to interact with 'real' file objects.
  read = utils.Proxy("Read")
  seek = utils.Proxy("Seek")
  stat = utils.Proxy("Stat")
  tell = utils.Proxy("Tell")
  close = utils.Proxy("Close")


class AbstractFileHandler(VFSHandler):
  """Base class for handling files in the VFS."""


class AbstractDirectoryHandler(VFSHandler):
  """Base class for handling directories in the VFS."""

  def ListFiles(self):
    """An iterator over all VFS files contained in this directory.

    Generates a StatResponse proto for each file or directory.

    Raises:
      IOError: if this fails.
    """

# A registry of all VFSHandler registered
VFS_HANDLERS = None


def VFSInit():
  # These import populate the VFSHandler registry and must be done as
  # late as possible.
  from grr.client import vfs_handlers

  global VFS_HANDLERS

  VFS_HANDLERS = {}
  for handler in VFSHandler.classes.values():
    VFS_HANDLERS.setdefault(handler.supported_pathtype, []).append(handler)
  for l in VFS_HANDLERS:
    VFS_HANDLERS[l].sort(key=lambda x: x.altitude)


def VFSHandlerFactory(pathspec):
  """Creates a new VFSHandler for the specified pathspec.

  Args:
     pathspec: The path specification.

  Returns:
     A new VFSHandler.

  Raises:
     IOError: if this handler can not be instantiated.
  """
  if VFS_HANDLERS is None: VFSInit()

  # Normalize, interpolate, split.
  ps = client_utils.SplitPathspec(pathspec)

  for handler_cls in VFS_HANDLERS[ps.pathtype]:
    try:
      if handler_cls != VFSHandler:
        fd = handler_cls(ps)
        return fd
    except (IOError, OSError):
      continue

  raise IOError("Unable to open %s%s" % (ps.mountpoint, ps.path))
