#!/usr/bin/env python
"""This file implements a VFS abstraction on the client."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import functools
import os


from builtins import filter  # pylint: disable=redefined-builtin
from future.utils import itervalues
from future.utils import with_metaclass

from grr_response_client import client_utils
from grr_response_core import config
from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import context
from grr_response_core.lib.util import precondition

# A central Cache for vfs handlers. This can be used to keep objects alive
# for a limited time.
DEVICE_CACHE = utils.TimeBasedCache()


class VFSHandler(with_metaclass(registry.MetaclassRegistry, object)):
  """Base class for handling objects in the VFS."""
  supported_pathtype = -1

  # Should this handler be auto-registered?
  auto_register = False

  size = 0
  offset = 0

  # This is the VFS path to this specific handler.
  path = "/"

  # This will be set by the VFSOpen factory to the pathspec of the final
  # destination of this handler. This pathspec will be case corrected and
  # updated to reflect any potential recursion.
  pathspec = None
  base_fd = None

  def __init__(self, base_fd, pathspec=None, progress_callback=None):
    """Constructor.

    Args:
      base_fd: A handler to the predecessor handler.
      pathspec: The pathspec to open.
      progress_callback: A callback to indicate that the open call is still
        working but needs more time.

    Raises:
      IOError: if this handler can not be instantiated over the
      requested path.
    """
    _ = pathspec
    self.base_fd = base_fd
    self.progress_callback = progress_callback
    if base_fd is None:
      self.pathspec = rdf_paths.PathSpec()
    else:
      # Make a copy of the base pathspec.
      self.pathspec = base_fd.pathspec.Copy()
    self.metadata = {}

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.Close()
    return False

  def Seek(self, offset, whence=os.SEEK_SET):
    """Seek to an offset in the file."""
    if whence == os.SEEK_SET:
      self.offset = offset
    elif whence == os.SEEK_CUR:
      self.offset += offset
    elif whence == os.SEEK_END:
      self.offset = self.size + offset
    else:
      raise ValueError("Illegal whence value %s" % whence)

  def Read(self, length):
    """Reads some data from the file."""
    raise NotImplementedError

  def Stat(self, ext_attrs=None):
    """Returns a StatEntry about this file."""
    del ext_attrs  # Unused.
    raise NotImplementedError

  def IsDirectory(self):
    """Returns true if this object can contain other objects."""
    raise NotImplementedError

  def Tell(self):
    return self.offset

  def Close(self):
    """Close internal file descriptors."""

  def OpenAsContainer(self):
    """Guesses a container from the current object."""
    if self.IsDirectory():
      return self

    # TODO(user): Add support for more containers here (e.g. registries, zip
    # files etc).
    else:  # For now just guess TSK.
      return VFS_HANDLERS[rdf_paths.PathSpec.PathType.TSK](
          self,
          rdf_paths.PathSpec(
              path="/", pathtype=rdf_paths.PathSpec.PathType.TSK),
          progress_callback=self.progress_callback)

  def MatchBestComponentName(self, component):
    """Returns the name of the component which matches best our base listing.

    In order to do the best case insensitive matching we list the files in the
    base handler and return the base match for this component.

    Args:
      component: A component name which should be present in this directory.

    Returns:
      the best component name.
    """
    fd = self.OpenAsContainer()

    # Adjust the component casing
    file_listing = set(fd.ListNames())

    # First try an exact match
    if component not in file_listing:
      # Now try to match lower case
      lower_component = component.lower()
      for x in file_listing:
        if lower_component == x.lower():
          component = x
          break

    if fd.supported_pathtype != self.pathspec.pathtype:
      new_pathspec = rdf_paths.PathSpec(
          path=component, pathtype=fd.supported_pathtype)
    else:
      new_pathspec = self.pathspec.last.Copy()
      new_pathspec.path = component

    return new_pathspec

  def ListFiles(self, ext_attrs=False):
    """An iterator over all VFS files contained in this directory.

    Generates a StatEntry for each file or directory.

    Args:
      ext_attrs: Whether stat entries should contain extended attributes.

    Raises:
      IOError: if this fails.
    """
    del ext_attrs  # Unused.

  def ListNames(self):
    """A generator for all names in this directory."""
    return []

  # These are file object conformant namings for library functions that
  # grr uses, and that expect to interact with 'real' file objects.
  read = utils.Proxy("Read")
  seek = utils.Proxy("Seek")
  stat = utils.Proxy("Stat")
  tell = utils.Proxy("Tell")
  close = utils.Proxy("Close")

  @classmethod
  def Open(cls, fd, component, pathspec=None, progress_callback=None):
    """Try to correct the casing of component.

    This method is called when we failed to open the component directly. We try
    to transform the component into something which is likely to work.

    In this implementation, we correct the case of the component until we can
    not open the path any more.

    Args:
      fd: The base fd we will use.
      component: The component we should open.
      pathspec: The rest of the pathspec object.
      progress_callback: A callback to indicate that the open call is still
        working but needs more time.

    Returns:
      A file object.

    Raises:
      IOError: If nothing could be opened still.
    """
    # The handler for this component
    try:
      handler = VFS_HANDLERS[component.pathtype]
    except KeyError:
      raise IOError("VFS handler %d not supported." % component.pathtype)

    # We will not do any case folding unless requested.
    if component.path_options == rdf_paths.PathSpec.Options.CASE_LITERAL:
      return handler(base_fd=fd, pathspec=component)

    path_components = client_utils.LocalPathToCanonicalPath(component.path)
    path_components = ["/"] + list(filter(None, path_components.split("/")))
    for i, path_component in enumerate(path_components):
      try:
        if fd:
          new_pathspec = fd.MatchBestComponentName(path_component)
        else:
          new_pathspec = component
          new_pathspec.path = path_component

        # The handler for this component
        try:
          handler = VFS_HANDLERS[new_pathspec.pathtype]
        except KeyError:
          raise IOError("VFS handler %d not supported." % new_pathspec.pathtype)

        fd = handler(
            base_fd=fd,
            pathspec=new_pathspec,
            progress_callback=progress_callback)
      except IOError:
        # Can not open the first component, we must raise here.
        if i <= 1:
          raise IOError("File not found")

        # Insert the remaining path at the front of the pathspec.
        pathspec.Insert(
            0,
            path=utils.JoinPath(*path_components[i:]),
            pathtype=rdf_paths.PathSpec.PathType.TSK)
        break

    return fd

  def GetMetadata(self):
    return self.metadata


# A registry of all VFSHandler registered
VFS_HANDLERS = {}

# The paths we should use as virtual root for VFS operations.
VFS_VIRTUALROOTS = {}


class VFSInit(registry.InitHook):
  """Register all known vfs handlers to open a pathspec types."""

  def Run(self):
    VFS_HANDLERS.clear()
    for handler in itervalues(VFSHandler.classes):
      if handler.auto_register:
        VFS_HANDLERS[handler.supported_pathtype] = handler

    VFS_VIRTUALROOTS.clear()
    vfs_virtualroots = config.CONFIG["Client.vfs_virtualroots"]
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
        raise ValueError("Unsupported vfs handler: %s." % handler_string)

      # We need some translation here, TSK needs an OS virtual root base. For
      # every other handler we can just keep the type the same.
      base_types = {
          rdf_paths.PathSpec.PathType.TSK: rdf_paths.PathSpec.PathType.OS
      }
      base_type = base_types.get(handler, handler)
      VFS_VIRTUALROOTS[handler] = rdf_paths.PathSpec(
          path=root, pathtype=base_type, is_virtualroot=True)


def VFSOpen(pathspec, progress_callback=None):
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
  fd = None

  # Adjust the pathspec in case we are using a vfs_virtualroot.
  vroot = VFS_VIRTUALROOTS.get(pathspec.pathtype)

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
      raise IOError("VFS handler %d not supported." % component.pathtype)

    try:
      # Open the component.
      fd = handler.Open(
          fd,
          component,
          pathspec=working_pathspec,
          progress_callback=progress_callback)
    except IOError as e:
      raise IOError("%s: %s" % (e, pathspec))

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
