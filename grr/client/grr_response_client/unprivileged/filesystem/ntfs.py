#!/usr/bin/env python
"""pyfsntfs implementation of a filesystem."""

import os
from typing import Optional, Iterable
import pyfsntfs
from grr_response_client.unprivileged.filesystem import filesystem
from grr_response_client.unprivileged.proto import filesystem_pb2


class DeviceWrapper:
  """Wraps a Device into a file-like object.

  It implements only the methods which are needed by pyfsntfs.
  """

  def __init__(self, filesystem_obj: filesystem.Filesystem):
    self._filesystem = filesystem_obj
    self._offset = 0

  def seek(self, offset: int, whence: int) -> None:
    if whence != os.SEEK_SET:
      raise ValueError("seek supports only whence=0.")
    self._offset = offset

  def read(self, size: int) -> bytes:
    data = self._filesystem.device.Read(offset=self._offset, size=size)
    self._offset += len(data)
    return data

  def tell(self) -> int:
    return self._offset


class NtfsFile(filesystem.File):
  """pyfsntfs implementation of File."""

  def __init__(self, filesystem_obj: filesystem.Filesystem,
               fd: pyfsntfs.file_entry,
               data_stream: Optional[pyfsntfs.data_stream]):
    super().__init__(filesystem_obj)
    self.fd = fd
    self.data_stream = data_stream

  def Read(self, offset: int, size: int) -> bytes:
    if self.fd.has_directory_entries_index():
      raise IOError("Attempting to read from a directory.")
    if self.data_stream is None:
      raise IOError("Missing data stream.")
    self.data_stream.seek(offset)
    data = self.data_stream.read(size)
    return data

  def Close(self) -> None:
    pass

  def ListFiles(self) -> Iterable[filesystem_pb2.StatEntry]:
    if self.fd.has_directory_entries_index():
      for entry in self.fd.sub_file_entries:
        data_stream = entry if entry.has_default_data_stream() else None
        yield self._Stat(entry, data_stream)

        # Create extra entries for alternate data streams
        for data_stream in entry.alternate_data_streams:
          yield self._Stat(entry, data_stream)
    else:
      for data_stream in self.fd.alternate_data_streams:
        yield self._Stat(self.fd, data_stream)

  def ListNames(self) -> Iterable[str]:
    if self.fd.has_directory_entries_index():
      for entry in self.fd.sub_file_entries:
        yield entry.name
    else:
      for data_stream in self.fd.alternate_data_streams:
        yield data_stream.name

  def LookupCaseInsensitive(self, name: str) -> Optional[str]:
    name_lower = name.lower()
    if self.fd.has_directory_entries_index():
      for entry in self.fd.sub_file_entries:
        if entry.name.lower() == name_lower:
          return entry.name
    else:
      for data_stream in self.fd.alternate_data_streams:
        if data_stream.name.lower() == name_lower:
          return data_stream.name
    return None

  def Stat(self) -> filesystem_pb2.StatEntry:
    return self._Stat(self.fd, self.data_stream)

  def _Stat(
      self,
      entry: pyfsntfs.file_entry,
      data_stream: Optional[pyfsntfs.data_stream],
  ) -> filesystem_pb2.StatEntry:
    st = filesystem_pb2.StatEntry()
    if entry.name is not None:
      st.name = entry.name
    st.st_ino = entry.file_reference
    st.st_atime.FromDatetime(entry.get_access_time())
    st.st_mtime.FromDatetime(entry.get_modification_time())
    st.st_btime.FromDatetime(entry.get_creation_time())
    st.st_ctime.FromDatetime(entry.get_entry_modification_time())
    st.ntfs.is_directory = entry.has_directory_entries_index()
    if not entry.has_directory_entries_index() and data_stream is not None:
      st.st_size = data_stream.get_size()
    if entry != data_stream and data_stream is not None:
      st.stream_name = data_stream.name
    st.ntfs.flags = entry.file_attribute_flags
    return st

  def Inode(self) -> int:
    return self.fd.file_reference


def _get_data_stream(
    entry: pyfsntfs.file_entry,
    stream_name: Optional[str]) -> Optional[pyfsntfs.data_stream]:
  """Returns a data stream by name, or the default data stream."""
  if stream_name is None:
    if entry.has_default_data_stream():
      return entry
    else:
      return None
  data_stream = entry.get_alternate_data_stream_by_name(stream_name)
  if data_stream is None:
    raise IOError(f"Failed to open data stream {stream_name}.")
  return data_stream


class NtfsFilesystem(filesystem.Filesystem):
  """pyfstnfs implementation of a Filesystem."""

  def __init__(self, device: filesystem.Device):
    super().__init__(device)

    self.volume = pyfsntfs.volume()
    self.volume.open_file_object(DeviceWrapper(self))

  def Open(self, path: str, stream_name: Optional[str]) -> NtfsFile:
    entry = self.volume.get_file_entry_by_path(path)

    if entry is None:
      raise IOError(f"Failed to open file {path}.")

    data_stream = _get_data_stream(entry, stream_name)

    return NtfsFile(self, entry, data_stream)

  def OpenByInode(self, inode: int, stream_name: Optional[str]) -> NtfsFile:
    # The lower 48 bits of the file_reference are the MFT index.
    mft_index = inode & ((1 << 48) - 1)
    entry = self.volume.get_file_entry(mft_index)

    if entry is None:
      raise IOError(f"Failed to open inode {inode}.")

    # If the file_reference changed, then the MFT entry points now to
    # a different file. Reopen it by path.
    if entry.file_reference != inode:
      raise filesystem.StaleInodeError("Inode {inode} is stale.")

    data_stream = _get_data_stream(entry, stream_name)

    return NtfsFile(self, entry, data_stream)
