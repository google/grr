#!/usr/bin/env python
"""This file implements a VFS abstraction on the client."""


from grr.client import client_utils
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import utils


# A central Cache for vfs handlers. This can be used to keep objects alive
# for a limited time.
DEVICE_CACHE = utils.TimeBasedCache()


class VFSHandler(object):
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

  __metaclass__ = registry.MetaclassRegistry

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
      self.pathspec = rdfvalue.PathSpec()
    else:
      # Make a copy of the base pathspec.
      self.pathspec = base_fd.pathspec.Copy()
    self.metadata = {}

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.Close()
    return False

  def Seek(self, offset, whence=0):
    """Seek to an offset in the file."""
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
    raise NotImplementedError

  def Stat(self):
    """Returns a StatResponse proto about this file."""
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

    # TODO(user): Add support for more container here (e.g. registries, zip
    # files etc).
    else:  # For now just guess TSK.
      return VFS_HANDLERS[rdfvalue.PathSpec.PathType.TSK](
          self, rdfvalue.PathSpec(path="/",
                                  pathtype=rdfvalue.PathSpec.PathType.TSK),
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

    new_pathspec = rdfvalue.PathSpec(path=component,
                                     pathtype=fd.supported_pathtype)

    return new_pathspec

  def ListFiles(self):
    """An iterator over all VFS files contained in this directory.

    Generates a StatResponse proto for each file or directory.

    Raises:
      IOError: if this fails.
    """

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
      raise IOError(
          "VFS handler %d not supported." % component.pathtype)

    # We will not do any case folding unless requested.
    if component.path_options == rdfvalue.PathSpec.Options.CASE_LITERAL:
      return handler(base_fd=fd, pathspec=component)

    path_components = client_utils.LocalPathToCanonicalPath(component.path)
    path_components = ["/"] + filter(None, path_components.split("/"))
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
          raise IOError(
              "VFS handler %d not supported." % new_pathspec.pathtype)

        fd = handler(base_fd=fd, pathspec=new_pathspec,
                     progress_callback=progress_callback)
      except IOError:
        # Can not open the first component, we must raise here.
        if i <= 1:
          raise IOError("File not found")

        # Insert the remaining path at the front of the pathspec.
        pathspec.Insert(0, path=utils.JoinPath(*path_components[i:]),
                        pathtype=rdfvalue.PathSpec.PathType.TSK)
        break

    return fd

  def GetMetadata(self):
    return self.metadata


# A registry of all VFSHandler registered
VFS_HANDLERS = {}


class VFSInit(registry.InitHook):
  """Register all known vfs handlers to open a pathspec types."""

  def Run(self):
    for handler in VFSHandler.classes.values():
      if handler.auto_register:
        VFS_HANDLERS[handler.supported_pathtype] = handler


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

  # Opening changes the pathspec so we work on a copy.
  pathspec = pathspec.Copy()

  # For each pathspec step, we get the handler for it and instantiate it with
  # the old object, and the current step.
  while pathspec:

    component = pathspec.Pop()
    try:
      handler = VFS_HANDLERS[component.pathtype]
    except KeyError:
      raise IOError(
          "VFS handler %d not supported." % component.pathtype)

    try:
      # Open the component.
      fd = handler.Open(fd, component, pathspec=pathspec,
                        progress_callback=progress_callback)
    except IOError as e:
      raise IOError("%s: %s" % (e, component))

  return fd


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
