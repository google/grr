#!/usr/bin/env python
"""This file implements a VFS abstraction on the client."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import abc
import os


from future.builtins import filter
from future.utils import with_metaclass
from typing import Optional

from grr_response_client import client_utils
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths


class Error(Exception):
  """Base class for VFS-related Errors."""


class UnsupportedHandlerError(Error):
  """Raised when an unsupported VFSHandler is used."""

  def __init__(self, pathtype):
    super(UnsupportedHandlerError,
          self).__init__("VFSHandler {} is not supported.".format(pathtype))


class VFSHandler(with_metaclass(abc.ABCMeta, object)):
  """Base class for handling objects in the VFS."""
  supported_pathtype = -1

  # Should this handler be auto-registered?
  auto_register = False

  size = 0
  offset = 0

  # This is the VFS path to this specific handler.
  # TODO: "/" is a problematic default value because it is not
  # guaranteed that path is set correctly (e.g. by TSK). None would be a better
  # default and to guarantee a valid value would be best.
  path = "/"

  # This will be set by the VFSOpen factory to the pathspec of the final
  # destination of this handler. This pathspec will be case corrected and
  # updated to reflect any potential recursion.
  pathspec = None
  base_fd = None

  def __init__(self, base_fd, handlers, pathspec=None, progress_callback=None):
    """Constructor.

    Args:
      base_fd: A handler to the predecessor handler.
      handlers: A mapping from rdf_paths.PathSpec.PathType to classes
        implementing VFSHandler.
      pathspec: The pathspec to open.
      progress_callback: A callback to indicate that the open call is still
        working but needs more time.

    Raises:
      IOError: if this handler can not be instantiated over the
      requested path.
    """
    del pathspec  # Unused.
    self.base_fd = base_fd
    self.progress_callback = progress_callback
    self._handlers = handlers
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

  @abc.abstractmethod
  def Read(self, length):
    """Reads some data from the file."""
    raise NotImplementedError

  @abc.abstractmethod
  def Stat(self, ext_attrs = False):
    """Returns a StatEntry about this file."""
    raise NotImplementedError

  @abc.abstractmethod
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
      tsk_handler = self._handlers[rdf_paths.PathSpec.PathType.TSK]
      tsk_pathspec = rdf_paths.PathSpec(
          path="/", pathtype=rdf_paths.PathSpec.PathType.TSK)
      return tsk_handler(
          base_fd=self,
          handlers=self._handlers,
          pathspec=tsk_pathspec,
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
  def Open(cls, fd, component, handlers, pathspec=None, progress_callback=None):
    """Try to correct the casing of component.

    This method is called when we failed to open the component directly. We try
    to transform the component into something which is likely to work.

    In this implementation, we correct the case of the component until we can
    not open the path any more.

    Args:
      fd: The base fd we will use.
      component: The component we should open.
      handlers: A mapping from rdf_paths.PathSpec.PathType to classes
        implementing VFSHandler.
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
      handler = handlers[component.pathtype]
    except KeyError:
      raise UnsupportedHandlerError(component.pathtype)

    # We will not do any case folding unless requested.
    if component.path_options == rdf_paths.PathSpec.Options.CASE_LITERAL:
      return handler(base_fd=fd, pathspec=component, handlers=handlers)

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
          handler = handlers[new_pathspec.pathtype]
        except KeyError:
          raise UnsupportedHandlerError(new_pathspec.pathtype)

        fd = handler(
            base_fd=fd,
            handlers=handlers,
            pathspec=new_pathspec,
            progress_callback=progress_callback)
      except IOError as e:
        # Can not open the first component, we must raise here.
        if i <= 1:
          raise IOError("File not found: {}".format(component))

        # Do not try to use TSK to open a not-found registry entry, fail
        # instead. Using TSK would lead to confusing error messages, hiding
        # the fact that the Registry entry is simply not there.
        if component.pathtype == rdf_paths.PathSpec.PathType.REGISTRY:
          raise IOError("Registry entry not found: {}".format(e))

        # Insert the remaining path at the front of the pathspec.
        pathspec.Insert(
            0,
            path=utils.JoinPath(*path_components[i:]),
            pathtype=rdf_paths.PathSpec.PathType.TSK)
        break

    return fd

  def GetMetadata(self):
    return self.metadata
