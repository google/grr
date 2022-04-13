#!/usr/bin/env python
"""Virtual filesystem module based on an unprivileged filesystem client."""

import contextlib
import stat
from typing import Any, Callable, Dict, Iterator, Optional, Text, Type, Tuple, NamedTuple

from grr_response_client import client_utils
from grr_response_client.unprivileged import communication
from grr_response_client.unprivileged.filesystem import client
from grr_response_client.unprivileged.filesystem import server
from grr_response_client.unprivileged.proto import filesystem_pb2
from grr_response_client.vfs_handlers import base as vfs_base
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths


class MountCacheItem(NamedTuple):
  client: client.Client
  server: communication.Server


class MountCache(utils.TimeBasedCache):

  def KillObject(self, obj: utils.TimeBasedCacheEntry) -> None:
    item = obj.value
    item.client.Close()
    item.server.Stop()


# Caches server instances.
MOUNT_CACHE = MountCache()


def _ConvertStatEntry(entry: filesystem_pb2.StatEntry,
                      pathspec: rdf_paths.PathSpec) -> rdf_client_fs.StatEntry:
  """Converts a stat entry from a filesystem_pb2 protobuf to RDF."""
  st = rdf_client_fs.StatEntry()
  st.pathspec = pathspec.Copy()

  if entry.HasField("st_mode"):
    st.st_mode = entry.st_mode
  # TODO: Expose st_ino as well.
  # It's not exposed at the moment for compatibility with
  # vfs_handlers/ntfs.py, which doesn't expose it.
  if entry.HasField("st_dev"):
    st.st_dev = entry.st_dev
  if entry.HasField("st_nlink"):
    st.st_nlink = entry.st_nlink
  if entry.HasField("st_uid"):
    st.st_uid = entry.st_uid
  if entry.HasField("st_gid"):
    st.st_gid = entry.st_gid
  if entry.HasField("st_size"):
    st.st_size = entry.st_size

  st.st_atime = rdfvalue.RDFDatetimeSeconds(entry.st_atime.seconds)
  st.st_mtime = rdfvalue.RDFDatetimeSeconds(entry.st_mtime.seconds)
  st.st_btime = rdfvalue.RDFDatetimeSeconds(entry.st_btime.seconds)
  st.st_ctime = rdfvalue.RDFDatetimeSeconds(entry.st_ctime.seconds)

  if entry.HasField("ntfs"):
    if entry.ntfs.is_directory:
      st.st_mode |= stat.S_IFDIR
    else:
      st.st_mode |= stat.S_IFREG

    flags = entry.ntfs.flags
    st.st_mode |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    if (flags & stat.FILE_ATTRIBUTE_READONLY) == 0:  # pytype: disable=module-attr
      st.st_mode |= stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
    if (flags & stat.FILE_ATTRIBUTE_HIDDEN) == 0:  # pytype: disable=module-attr
      st.st_mode |= stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH

  return st


class VFSHandlerDevice(client.Device):
  """A device implementation backed by a VFSHandler."""

  def __init__(self,
               vfs_handler: vfs_base.VFSHandler,
               device_file_descriptor: Optional[int] = None):
    super().__init__()
    self._vfs_handler = vfs_handler
    self._device_file_descriptor = device_file_descriptor

  def Read(self, offset: int, size: int) -> bytes:
    self._vfs_handler.seek(offset)
    return self._vfs_handler.read(size)

  @property
  def file_descriptor(self) -> Optional[int]:
    return self._device_file_descriptor


class UnprivilegedFileBase(vfs_base.VFSHandler):
  """VFSHandler implementation based on pyfsntfs."""

  implementation_type = filesystem_pb2.UNDEFINED

  def __init__(self,
               base_fd: Optional[vfs_base.VFSHandler],
               handlers: Dict[Any, Type[vfs_base.VFSHandler]],
               pathspec: Optional[rdf_paths.PathSpec] = None,
               progress_callback: Optional[Callable[[], None]] = None):
    super().__init__(
        base_fd,
        handlers=handlers,
        pathspec=pathspec,
        progress_callback=progress_callback)

    # self.pathspec is initialized to a copy of base_fd

    if base_fd is None:
      raise ValueError("UnprivilegedFileBase driver must have a file base.")
    elif isinstance(base_fd, UnprivilegedFileBase) and base_fd.IsDirectory():
      self.client = base_fd.client
      last_path = utils.JoinPath(self.pathspec.last.path, pathspec.path)
      # Replace the last component with this one.
      self.pathspec.Pop(-1)
      self.pathspec.Append(pathspec)
      self.pathspec.last.path = last_path
    elif not base_fd.IsDirectory():
      cache_key = base_fd.pathspec.SerializeToBytes() + str(
          self.implementation_type).encode("utf-8")
      try:
        self.client = MOUNT_CACHE.Get(cache_key).client
      except KeyError:
        device_path = base_fd.native_path
        with contextlib.ExitStack() as stack:
          if device_path is None:
            server_obj = server.CreateFilesystemServer()
            stack.enter_context(server_obj)
            self.client = stack.enter_context(
                client.CreateFilesystemClient(server_obj.Connect(),
                                              self.implementation_type,
                                              VFSHandlerDevice(base_fd)))
          else:
            with open(device_path, "rb") as device_file:
              server_obj = server.CreateFilesystemServer(device_file.fileno())
              stack.enter_context(server_obj)
              self.client = stack.enter_context(
                  client.CreateFilesystemClient(
                      server_obj.Connect(), self.implementation_type,
                      VFSHandlerDevice(base_fd, device_file.fileno())))
          MOUNT_CACHE.Put(cache_key,
                          MountCacheItem(server=server_obj, client=self.client))
          # Transfer ownership of resources to MOUNT_CACHE.
          stack.pop_all()
      self.pathspec.Append(pathspec)
    elif base_fd.IsDirectory():
      raise IOError("Base must be a file.")

    self.fd = None

    if pathspec is None:
      raise ValueError("pathspec can't be None.")

    try:
      if pathspec.HasField("stream_name"):
        if pathspec.path_options == rdf_paths.PathSpec.Options.CASE_LITERAL:
          # If the stream name is case literal, we just open the stream.
          self.fd = self._OpenPathSpec(pathspec)
        else:
          # The VFS layer is not taking care of case insensitive stream names
          # (as it does for case insensitive paths).
          # We have to find the corresponding case literal stream name in this
          # case ourselves.
          self.fd, self.pathspec.last.stream_name = (
              self._OpenStreamCaseInsensitive(pathspec))
      else:
        self.fd = self._OpenPathSpec(pathspec)
    except client.OperationError as e:
      raise IOError(f"Failed to open {pathspec}.") from e

    # self.pathspec will be used for future access to this file.

    # The name is now literal, so disable case-insensitive lookup (expensive).
    self.pathspec.last.path_options = rdf_paths.PathSpec.Options.CASE_LITERAL

    # Access the file by file_reference, to skip path lookups.
    self.pathspec.last.inode = self.fd.inode

    self._stat_result = _ConvertStatEntry(self.fd.Stat(), self.pathspec)

  def _OpenPathSpec(self, pathspec: rdf_paths.PathSpec) -> client.File:
    if pathspec.HasField("stream_name"):
      stream_name = pathspec.stream_name
    else:
      stream_name = None

    if pathspec.HasField("inode"):
      return self.client.OpenByInode(pathspec.inode, stream_name)
    else:
      path = self._ToClientPath(pathspec.last.path)
      return self.client.Open(path, stream_name)

  def _ToClientPath(self, path: str) -> str:
    """Converts a VFS path to a path suitable to be passed to a client.

    Subclasses can override this method if the respective implementation
    requires a conversion.

    Args:
      path: The input path.

    Returns:
      The converted path.
    """
    return path

  def _OpenStreamCaseInsensitive(
      self, pathspec: rdf_paths.PathSpec) -> Tuple[client.File, str]:
    """Opens a stream by pathspec with a case-insensitvie stream name.

    Args:
      pathspec: Pathspec for stream.

    Returns:
      A tuple: the opened file, the case sensitive stream name.
    """
    stream_name = pathspec.stream_name
    file_pathspec = pathspec.Copy()
    file_pathspec.stream_name = None
    result = pathspec.Copy()
    result.stream_name = self._GetStreamNameCaseLiteral(file_pathspec,
                                                        stream_name)
    return self._OpenPathSpec(result), result.stream_name

  def _GetStreamNameCaseLiteral(self, file_pathspec: rdf_paths.PathSpec,
                                stream_name_case_insensitive: str) -> str:
    """Returns the case literal stream name.

    Args:
      file_pathspec: Pathspec to the containing file.
      stream_name_case_insensitive: The case insensitive stream name.

    Raises:
      IOError: if the stream is not found.
    """
    with self._OpenPathSpec(file_pathspec) as file_obj:
      result = file_obj.LookupCaseInsensitive(stream_name_case_insensitive)
      if result is not None:
        return result
    raise IOError(f"Failed to open stream {stream_name_case_insensitive} in "
                  f"{file_pathspec}.")

  @property
  def size(self) -> int:
    return self._stat_result.st_size

  def Stat(self,
           ext_attrs: bool = False,
           follow_symlink: bool = True) -> rdf_client_fs.StatEntry:
    return self._stat_result

  def Read(self, length: int) -> bytes:
    self._CheckIsFile()
    data = self.fd.Read(self.offset, length)
    self.offset += len(data)
    return data

  def IsDirectory(self) -> bool:
    return (self._stat_result.st_mode & stat.S_IFDIR) != 0

  def ListFiles(self,
                ext_attrs: bool = False) -> Iterator[rdf_client_fs.StatEntry]:
    del ext_attrs  # Unused.

    self._CheckIsDirectory()

    for entry in self.fd.ListFiles():
      pathspec = self.pathspec.Copy()
      pathspec.last.path = utils.JoinPath(pathspec.last.path, entry.name)
      pathspec.last.inode = entry.st_ino
      pathspec.last.options = rdf_paths.PathSpec.Options.CASE_LITERAL
      if entry.HasField("stream_name"):
        pathspec.last.stream_name = entry.stream_name
      yield _ConvertStatEntry(entry, pathspec)

  def ListNames(self) -> Iterator[Text]:
    self._CheckIsDirectory()
    return iter(self.fd.ListNames())

  def _CheckIsDirectory(self) -> None:
    if not self.IsDirectory():
      raise IOError("{} is not a directory".format(
          self.pathspec.CollapsePath()))

  def _CheckIsFile(self) -> None:
    if self.IsDirectory():
      raise IOError("{} is not a file".format(self.pathspec.CollapsePath()))

  def Close(self) -> None:
    self.fd.Close()

  def MatchBestComponentName(
      self, component: str, pathtype: rdf_paths.PathSpec) -> rdf_paths.PathSpec:
    fd = self.OpenAsContainer(pathtype)

    new_component = self.fd.LookupCaseInsensitive(component)
    if new_component is not None:
      component = new_component

    if fd.supported_pathtype != self.pathspec.pathtype:
      new_pathspec = rdf_paths.PathSpec(
          path=component, pathtype=fd.supported_pathtype)
    else:
      new_pathspec = self.pathspec.last.Copy()
      new_pathspec.path = component

    return new_pathspec

  @classmethod
  def Open(
      cls,
      fd: Optional[vfs_base.VFSHandler],
      component: rdf_paths.PathSpec,
      handlers: Dict[Any, Type[vfs_base.VFSHandler]],
      pathspec: Optional[rdf_paths.PathSpec] = None,
      progress_callback: Optional[Callable[[], None]] = None
  ) -> Optional[vfs_base.VFSHandler]:
    # A Pathspec which starts with NTFS means we need to resolve the mount
    # point at runtime.
    if (fd is None and component.pathtype == cls.supported_pathtype and
        pathspec is not None):
      # We are the top level handler. This means we need to check the system
      # mounts to work out the exact mount point and device we need to
      # open. We then modify the pathspec so we get nested in the raw
      # pathspec.
      raw_pathspec, corrected_path = client_utils.GetRawDevice(component.path)  # pytype: disable=attribute-error

      # Insert the raw device before the component in the pathspec and correct
      # the path
      component.path = corrected_path
      pathspec.Insert(0, component)
      pathspec.Insert(0, raw_pathspec)

      # Allow incoming pathspec to be given in the local system path
      # conventions.
      for component in pathspec:
        if component.path:
          component.path = client_utils.LocalPathToCanonicalPath(component.path)

      # We have not actually opened anything in this iteration, but modified the
      # pathspec. Next time we should be able to open it properly.
      return fd

    # If an inode is specified, just use it directly.
    # This is necessary so that component.path is ignored.
    elif component.HasField("inode"):
      return cls(fd, handlers, component, progress_callback=progress_callback)
    else:
      return vfs_base.VFSHandler.Open(
          fd=fd,
          component=component,
          handlers=handlers,
          pathspec=pathspec,
          progress_callback=progress_callback)


class UnprivilegedNtfsFile(UnprivilegedFileBase):
  supported_pathtype = rdf_paths.PathSpec.PathType.NTFS
  implementation_type = filesystem_pb2.NTFS

  def _ToClientPath(self, path: str) -> str:
    return path.replace("/", "\\")


class UnprivilegedTskFile(UnprivilegedFileBase):
  supported_pathtype = rdf_paths.PathSpec.PathType.TSK
  implementation_type = filesystem_pb2.TSK
