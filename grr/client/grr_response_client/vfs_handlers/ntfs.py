#!/usr/bin/env python
"""Virtual filesystem module based on pyfsntfs."""

from collections.abc import Callable, Iterable
import stat
from typing import Any, Optional

import pyfsntfs

from grr_response_client import client_utils
from grr_response_client.vfs_handlers import base as vfs_base
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths


# Caches pyfsntfs.volume instances.
MOUNT_CACHE = utils.TimeBasedCache()


# See
# https://github.com/libyal/libfsntfs/blob/master/documentation/New%20Technologies%20File%20System%20(NTFS).asciidoc#file_attribute_flags
FILE_ATTRIBUTE_READONLY = 0x00000001
FILE_ATTRIBUTE_HIDDEN = 0x00000002


def _GetAlternateDataStreamCaseInsensitive(
    fd: pyfsntfs.file_entry, name: str
) -> Optional[pyfsntfs.data_stream]:
  name = name.lower()
  for data_stream in fd.alternate_data_streams:
    if data_stream.name.lower() == name:
      return data_stream


class NTFSFile(vfs_base.VFSHandler):
  """VFSHandler implementation based on pyfsntfs."""

  supported_pathtype = rdf_paths.PathSpec.PathType.NTFS  # pyrefly: ignore[missing-attribute]

  def __init__(
      self,
      base_fd: Optional[vfs_base.VFSHandler],
      handlers: dict[Any, type[vfs_base.VFSHandler]],
      pathspec: Optional[rdf_paths.PathSpec] = None,
      progress_callback: Optional[Callable[[], None]] = None,
  ):
    super().__init__(
        base_fd,
        handlers=handlers,
        pathspec=pathspec,
        progress_callback=progress_callback,
    )

    # self.pathspec is initialized to a copy of base_fd

    if base_fd is None:
      raise ValueError("NTFS driver must have a file base.")
    elif isinstance(base_fd, NTFSFile) and base_fd.IsDirectory():
      self.volume = base_fd.volume
      last_path = utils.JoinPath(self.pathspec.last.path, pathspec.path)  # pyrefly: ignore[missing-attribute]
      # Replace the last component with this one.
      self.pathspec.Pop(-1)  # pyrefly: ignore[missing-attribute]
      self.pathspec.Append(pathspec)  # pyrefly: ignore[missing-attribute]
      self.pathspec.last.path = last_path  # pyrefly: ignore[missing-attribute]
    elif not base_fd.IsDirectory():
      cache_key = base_fd.pathspec.SerializeToBytes()  # pyrefly: ignore[missing-attribute]
      try:
        self.volume = MOUNT_CACHE.Get(cache_key)
      except KeyError:
        self.volume = pyfsntfs.volume()
        self.volume.open_file_object(base_fd)
        MOUNT_CACHE.Put(cache_key, self.volume)
      self.pathspec.Append(pathspec)  # pyrefly: ignore[missing-attribute]
    elif base_fd.IsDirectory():
      raise IOError("Base must be a file.")

    self.fd = None
    self.data_stream = None

    # Try to open by "inode" number.
    if pathspec is not None and pathspec.HasField("inode"):
      # The lower 48 bits of the file_reference are the MFT index.
      mft_index = pathspec.inode & ((1 << 48) - 1)  # pyrefly: ignore[missing-attribute]
      self.fd = self.volume.get_file_entry(mft_index)
      # If the file_reference changed, then the MFT entry points now to
      # a different file. Reopen it by path.
      if self.fd is not None and self.fd.file_reference != pathspec.inode:  # pyrefly: ignore[missing-attribute]
        self.fd = None

    # Try to open by path
    if self.fd is None:
      path = self.pathspec.last.path  # pyrefly: ignore[missing-attribute]
      path = path.replace("/", "\\")
      self.fd = self.volume.get_file_entry_by_path(path)

    if self.fd is None:
      raise IOError("Failed to open {}".format(path))

    # Determine data stream
    if pathspec is not None and pathspec.HasField("stream_name"):
      if pathspec.path_options == rdf_paths.PathSpec.Options.CASE_LITERAL:  # pyrefly: ignore[missing-attribute]
        self.data_stream = self.fd.get_alternate_data_stream_by_name(
            pathspec.stream_name  # pyrefly: ignore[missing-attribute]
        )
      else:
        self.data_stream = _GetAlternateDataStreamCaseInsensitive(
            self.fd, pathspec.stream_name  # pyrefly: ignore[missing-attribute]
        )
      if self.data_stream is None:
        raise IOError(
            "Failed to open data stream {} in {}.".format(
                pathspec.stream_name, path  # pyrefly: ignore[missing-attribute]
            )
        )
      self.pathspec.last.stream_name = self.data_stream.name  # pyrefly: ignore[missing-attribute]
    else:
      if self.fd.has_default_data_stream():
        self.data_stream = self.fd

    # self.pathspec will be used for future access to this file.

    # The name is now literal, so disable case-insensitive lookup (expensive).
    self.pathspec.last.path_options = rdf_paths.PathSpec.Options.CASE_LITERAL  # pyrefly: ignore[missing-attribute]

    # Access the file by file_reference, to skip path lookups.
    self.pathspec.last.inode = self.fd.file_reference  # pyrefly: ignore[missing-attribute]

    if not self.IsDirectory():
      if self.data_stream is not None:
        self.size = self.data_stream.get_size()
      else:
        self.size = 0

  def Stat(
      self, ext_attrs: bool = False, follow_symlink: bool = True
  ) -> rdf_client_fs.StatEntry:
    return self._Stat(self.fd, self.data_stream, self.pathspec.Copy())  # pyrefly: ignore[missing-attribute]

  def Read(self, length: int) -> bytes:
    self._CheckIsFile()
    assert self.data_stream is not None
    self.data_stream.seek(self.offset)
    data = self.data_stream.read(length)
    self.offset += len(data)
    return data

  def IsDirectory(self) -> bool:
    return self.fd.has_directory_entries_index()  # pyrefly: ignore[missing-attribute]

  def ListFiles(
      self,
      ext_attrs: bool = False,
  ) -> Iterable[rdf_client_fs.StatEntry]:
    del ext_attrs  # Unused.

    self._CheckIsDirectory()

    for entry in self.fd.sub_file_entries:  # pyrefly: ignore[missing-attribute]
      pathspec = self.pathspec.Copy()  # pyrefly: ignore[missing-attribute]
      pathspec.last.path = utils.JoinPath(pathspec.last.path, entry.name)
      pathspec.last.inode = entry.file_reference
      pathspec.last.options = rdf_paths.PathSpec.Options.CASE_LITERAL  # pyrefly: ignore[missing-attribute]
      data_stream = entry if entry.has_default_data_stream() else None
      yield self._Stat(entry, data_stream, pathspec.Copy())

      # Create extra entries for alternate data streams
      for data_stream in entry.alternate_data_streams:
        pathspec.last.stream_name = data_stream.name
        yield self._Stat(entry, data_stream, pathspec.Copy())

  def ListNames(self) -> Iterable[str]:
    self._CheckIsDirectory()
    for entry in self.fd.sub_file_entries:  # pyrefly: ignore[missing-attribute]
      yield entry.name

  def _CheckIsDirectory(self) -> None:
    if not self.IsDirectory():
      raise IOError(
          "{} is not a directory".format(self.pathspec.CollapsePath())  # pyrefly: ignore[missing-attribute]
      )

  def _CheckIsFile(self) -> None:
    if self.IsDirectory():
      raise IOError("{} is not a file".format(self.pathspec.CollapsePath()))  # pyrefly: ignore[missing-attribute]

  def _Stat(
      self,
      entry: pyfsntfs.file_entry,
      data_stream: pyfsntfs.data_stream,
      pathspec: rdf_paths.PathSpec,
  ) -> rdf_client_fs.StatEntry:
    st = rdf_client_fs.StatEntry()
    st.pathspec = pathspec  # pyrefly: ignore[missing-attribute]

    st.st_atime = rdfvalue.RDFDatetimeSeconds.FromDatetime(  # pyrefly: ignore[missing-attribute]
        entry.get_access_time()
    )
    st.st_mtime = rdfvalue.RDFDatetimeSeconds.FromDatetime(  # pyrefly: ignore[missing-attribute]
        entry.get_modification_time()
    )
    st.st_btime = rdfvalue.RDFDatetimeSeconds.FromDatetime(  # pyrefly: ignore[missing-attribute]
        entry.get_creation_time()
    )
    st.st_ctime = rdfvalue.RDFDatetimeSeconds.FromDatetime(  # pyrefly: ignore[missing-attribute]
        entry.get_entry_modification_time()
    )
    if entry.has_directory_entries_index():
      st.st_mode = stat.S_IFDIR  # pyrefly: ignore[missing-attribute]
    else:
      st.st_mode = stat.S_IFREG  # pyrefly: ignore[missing-attribute]
      if data_stream is not None:
        st.st_size = data_stream.get_size()  # pyrefly: ignore[missing-attribute]
    flags = entry.file_attribute_flags
    st.st_mode |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH  # pyrefly: ignore[missing-attribute]
    if (flags & FILE_ATTRIBUTE_READONLY) == 0:
      st.st_mode |= stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH  # pyrefly: ignore[missing-attribute]
    if (flags & FILE_ATTRIBUTE_HIDDEN) == 0:
      st.st_mode |= stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH  # pyrefly: ignore[missing-attribute]
    return st

  @classmethod
  def Open(
      cls,
      fd: Optional[vfs_base.VFSHandler],
      component: rdf_paths.PathSpec,
      handlers: dict[Any, type[vfs_base.VFSHandler]],
      pathspec: Optional[rdf_paths.PathSpec] = None,
      progress_callback: Optional[Callable[[], None]] = None,
  ) -> Optional[vfs_base.VFSHandler]:
    # A Pathspec which starts with NTFS means we need to resolve the mount
    # point at runtime.
    if (
        fd is None
        and component.pathtype == rdf_paths.PathSpec.PathType.NTFS  # pyrefly: ignore[missing-attribute]
        and pathspec is not None
    ):
      # We are the top level handler. This means we need to check the system
      # mounts to work out the exact mount point and device we need to
      # open. We then modify the pathspec so we get nested in the raw
      # pathspec.
      raw_pathspec, corrected_path = client_utils.GetRawDevice(component.path)  # pyrefly: ignore[missing-attribute]

      # Insert the raw device before the component in the pathspec and correct
      # the path
      component.path = corrected_path  # pyrefly: ignore[missing-attribute]
      pathspec.Insert(0, component)
      pathspec.Insert(0, raw_pathspec)

      # Allow incoming pathspec to be given in the local system path
      # conventions.
      for component in pathspec:
        if component.path:  # pyrefly: ignore[missing-attribute]
          component.path = client_utils.LocalPathToCanonicalPath(component.path)  # pyrefly: ignore[missing-attribute]

      # We have not actually opened anything in this iteration, but modified the
      # pathspec. Next time we should be able to open it properly.
      return fd

    # If an inode is specified, just use it directly.
    # This is necessary so that component.path is ignored.
    elif component.HasField("inode"):
      return NTFSFile(
          fd, handlers, component, progress_callback=progress_callback
      )
    else:
      return super(NTFSFile, cls).Open(
          fd=fd,
          component=component,
          handlers=handlers,
          pathspec=pathspec,
          progress_callback=progress_callback,
      )
