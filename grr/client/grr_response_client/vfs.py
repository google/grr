#!/usr/bin/env python
"""This file implements a VFS abstraction on the client."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import functools
import platform


from typing import Any, Optional, Callable, Dict, Type

from grr_response_client.vfs_handlers import base as vfs_base
from grr_response_client.vfs_handlers import files  # pylint: disable=unused-import
from grr_response_client.vfs_handlers import sleuthkit  # pylint: disable=unused-import
# pylint: disable=g-import-not-at-top
if platform.system() == "Windows":
  from grr_response_client.vfs_handlers import registry as vfs_registry  # pylint: disable=unused-import
else:
  vfs_registry = None
from grr_response_core import config
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import context
from grr_response_core.lib.util import precondition
# pylint: enable=g-import-not-at-top

VFSHandler = vfs_base.VFSHandler
UnsupportedHandlerError = vfs_base.UnsupportedHandlerError

# A registry of all VFSHandler registered
# TODO: Dictionary keys are of type rdf_paths.PathSpec.PathType,
# but this is currently not representable as type information in Python.
VFS_HANDLERS = {}  # type: Dict[Any, Type[vfs_base.VFSHandler]]

# The paths we should use as virtual root for VFS operations.
_VFS_VIRTUALROOTS = {}


def Init():
  """Register all known vfs handlers to open a pathspec types."""
  VFS_HANDLERS.clear()
  _VFS_VIRTUALROOTS.clear()
  vfs_virtualroots = config.CONFIG["Client.vfs_virtualroots"]

  VFS_HANDLERS[files.File.supported_pathtype] = files.File
  VFS_HANDLERS[files.TempFile.supported_pathtype] = files.TempFile
  VFS_HANDLERS[sleuthkit.TSKFile.supported_pathtype] = sleuthkit.TSKFile
  if vfs_registry is not None:
    VFS_HANDLERS[vfs_registry.RegistryFile
                 .supported_pathtype] = vfs_registry.RegistryFile

  for vfs_virtualroot in vfs_virtualroots:
    try:
      handler_string, root = vfs_virtualroot.split(":", 1)
    except ValueError:
      raise ValueError(
          "Badly formatted vfs virtual root: %s. Correct format is "
          "os:/path/to/virtual_root" % vfs_virtualroot)

    handler_string = handler_string.upper()
    handler = rdf_paths.PathSpec.PathType.enum_dict.get(handler_string)
    if handler is None:
      raise ValueError(
          "VFSHandler {} could not be registered, because it was not found in"
          " PathSpec.PathType {}".format(handler_string,
                                         rdf_paths.PathSpec.PathType.enum_dict))

    # We need some translation here, TSK needs an OS virtual root base. For
    # every other handler we can just keep the type the same.
    if handler == rdf_paths.PathSpec.PathType.TSK:
      base_type = rdf_paths.PathSpec.PathType.OS
    else:
      base_type = handler
    _VFS_VIRTUALROOTS[handler] = rdf_paths.PathSpec(
        path=root, pathtype=base_type, is_virtualroot=True)


def VFSOpen(pathspec,
            progress_callback = None
           ):
  """Expands pathspec to return an expanded Path.

  A pathspec is a specification of how to access the file by recursively opening
  each part of the path by different drivers. For example the following
  pathspec:

  pathtype: OS
  path: "/dev/sda1"
  nested_path {
    pathtype: TSK
    path: "/home/image2.img"
    nested_path {
      pathtype: TSK
      path: "/home/a.txt"
    }
  }

  Instructs the system to:
  1) open /dev/sda1 using the OS driver.
  2) Pass the obtained filelike object to the TSK driver to open
  "/home/image2.img".
  3) The obtained filelike object should be passed to the TSK driver to open
  "/home/a.txt".

  The problem remains how to get to this expanded path specification. Since the
  server is not aware of all the files on the client, the server may request
  this:

  pathtype: OS
  path: "/dev/sda1"
  nested_path {
    pathtype: TSK
    path: "/home/image2.img/home/a.txt"
  }

  Or even this:

  pathtype: OS
  path: "/dev/sda1/home/image2.img/home/a.txt"

  This function converts the pathspec requested by the server into an expanded
  pathspec required to actually open the file. This is done by expanding each
  component of the pathspec in turn.

  Expanding the component is done by opening each leading directory in turn and
  checking if it is a directory of a file. If its a file, we examine the file
  headers to determine the next appropriate driver to use, and create a nested
  pathspec.

  Note that for some clients there might be a virtual root specified. This
  is a directory that gets prepended to all pathspecs of a given
  pathtype. For example if there is a virtual root defined as
  ["os:/virtualroot"], a path specification like

  pathtype: OS
  path: "/home/user/*"

  will get translated into

  pathtype: OS
  path: "/virtualroot"
  is_virtualroot: True
  nested_path {
    pathtype: OS
    path: "/dev/sda1"
  }

  Args:
    pathspec: A Path() protobuf to normalize.
    progress_callback: A callback to indicate that the open call is still
      working but needs more time.

  Returns:
    The open filelike object. This will contain the expanded Path() protobuf as
    the member fd.pathspec.

  Raises:
    IOError: if one of the path components can not be opened.

  """
  # Initialize the dictionary of VFS handlers lazily, if not yet done.
  if not VFS_HANDLERS:
    Init()

  fd = None

  # Adjust the pathspec in case we are using a vfs_virtualroot.
  vroot = _VFS_VIRTUALROOTS.get(pathspec.pathtype)

  # If we have a virtual root for this vfs handler, we need to prepend
  # it to the incoming pathspec except if the pathspec is explicitly
  # marked as containing a virtual root already or if it isn't marked but
  # the path already contains the virtual root.
  if (not vroot or pathspec.is_virtualroot or
      pathspec.CollapsePath().startswith(vroot.CollapsePath())):
    # No virtual root but opening changes the pathspec so we always work on a
    # copy.
    working_pathspec = pathspec.Copy()
  else:
    # We're in a virtual root, put the target pathspec inside the virtual root
    # as a nested path.
    working_pathspec = vroot.Copy()
    working_pathspec.last.nested_path = pathspec.Copy()

  # For each pathspec step, we get the handler for it and instantiate it with
  # the old object, and the current step.
  while working_pathspec:
    component = working_pathspec.Pop()
    try:
      handler = VFS_HANDLERS[component.pathtype]
    except KeyError:
      raise UnsupportedHandlerError(component.pathtype)

    # Open the component.
    fd = handler.Open(
        fd=fd,
        component=component,
        handlers=dict(VFS_HANDLERS),
        pathspec=working_pathspec,
        progress_callback=progress_callback)

  if fd is None:
    raise ValueError("VFSOpen cannot be called with empty PathSpec.")

  return fd


def VFSMultiOpen(pathspecs, progress_callback=None):
  """Opens multiple files specified by given path-specs.

  See documentation for `VFSOpen` for more information.

  Args:
    pathspecs: A list of pathspec instances of files to open.
    progress_callback: A callback function to call to notify about progress

  Returns:
    A context manager yielding file-like objects.
  """
  precondition.AssertIterableType(pathspecs, rdf_paths.PathSpec)

  vfs_open = functools.partial(VFSOpen, progress_callback=progress_callback)
  return context.MultiContext(map(vfs_open, pathspecs))


def ReadVFS(pathspec, offset, length, progress_callback=None):
  """Read from the VFS and return the contents.

  Args:
    pathspec: path to read from
    offset: number of bytes to skip
    length: number of bytes to read
    progress_callback: A callback to indicate that the open call is still
      working but needs more time.

  Returns:
    VFS file contents
  """
  fd = VFSOpen(pathspec, progress_callback=progress_callback)
  fd.Seek(offset)
  return fd.Read(length)
