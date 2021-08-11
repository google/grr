#!/usr/bin/env python
"""TSK implementation of a filesystem."""

import logging
import stat
from typing import Optional, Iterator
import pytsk3
from grr_response_client.unprivileged.filesystem import filesystem
from grr_response_client.unprivileged.proto import filesystem_pb2

# List of file names in a directory listing to ignore.
_LIST_FILES_IGNORE = frozenset([
    "$OrphanFiles",  # Special TSK dir that invokes processing.
    ".",
    "..",
])

# Stream types which correspond to alternate data streams.
_ALTERNATE_DATA_STREAM_TYPES = frozenset([
    pytsk3.TSK_FS_ATTR_TYPE_NTFS_DATA,
    pytsk3.TSK_FS_ATTR_TYPE_DEFAULT,
])

# Maps TSK name types to stat bits.
_FS_NAME_TYPE_LOOKUP = {
    pytsk3.TSK_FS_NAME_TYPE_UNDEF: 0,
    pytsk3.TSK_FS_NAME_TYPE_FIFO: stat.S_IFIFO,
    pytsk3.TSK_FS_NAME_TYPE_CHR: stat.S_IFCHR,
    pytsk3.TSK_FS_NAME_TYPE_DIR: stat.S_IFDIR,
    pytsk3.TSK_FS_NAME_TYPE_BLK: stat.S_IFBLK,
    pytsk3.TSK_FS_NAME_TYPE_REG: stat.S_IFREG,
    pytsk3.TSK_FS_NAME_TYPE_LNK: stat.S_IFLNK,
    pytsk3.TSK_FS_NAME_TYPE_SOCK: stat.S_IFSOCK,
}

# Maps TSK meta types to stat bits.
_FS_META_TYPE_LOOKUP = {
    pytsk3.TSK_FS_META_TYPE_BLK: 0,
    pytsk3.TSK_FS_META_TYPE_CHR: stat.S_IFCHR,
    pytsk3.TSK_FS_META_TYPE_DIR: stat.S_IFDIR,
    pytsk3.TSK_FS_META_TYPE_FIFO: stat.S_IFIFO,
    pytsk3.TSK_FS_META_TYPE_LNK: stat.S_IFLNK,
    pytsk3.TSK_FS_META_TYPE_REG: stat.S_IFREG,
    pytsk3.TSK_FS_META_TYPE_SOCK: stat.S_IFSOCK,
}


def _IsAlternateDataStream(attribute: pytsk3.Attribute) -> bool:
  if not attribute.info.name:
    return False
  return int(attribute.info.type) in _ALTERNATE_DATA_STREAM_TYPES


def _DecodeName(value: bytes) -> str:
  try:
    return value.decode("utf-8")
  except UnicodeDecodeError as e:
    result = value.decode("utf-8", "replace")
    logging.warning("%s. Decoded %r to %r", e, value, result)
    return result


def _FixNtfsMode(mode: int) -> int:
  """Fix NTFS permissions returned by TSK."""
  # TSK with NTFS reports the following permissions:
  # r-xr-xr-x for hidden files
  # -wx-wx-wx for read-only files
  # We want to report the reversed mapping, because it makes more sense.

  permissions = mode & 0o777

  if permissions == 0o333:
    return (mode & ~0o777) | 0o555
  elif permissions == 0o555:
    return (mode & ~0o777) | 0o333
  else:
    return mode


def _FixInt(value: int) -> int:
  """Fix negative integer values returned by TSK."""
  if value < 0:
    value &= 0xFFFFFFFF
  return value


class DeviceWrapper(pytsk3.Img_Info):
  """An Img_Info implementation suitable for TSK."""

  def __init__(self, filesystem_obj: filesystem.Filesystem):
    super().__init__()
    self._filesystem = filesystem_obj

  def read(self, offset: int, length: int) -> bytes:
    return self._filesystem.device.Read(offset=offset, size=length)

  def get_size(self) -> int:  # pylint: disable=g-bad-name
    # Windows is unable to report the true size of the raw device and allows
    # arbitrary reading past the end - so we lie here to force TSK to read it
    # anyway.
    return 1 << 62


class TskFile(filesystem.File):
  """TSK implementation of File."""

  def __init__(self, filesystem_obj: filesystem.Filesystem,
               fs_info: pytsk3.FS_Info, fd: pytsk3.File,
               data_stream: Optional[pytsk3.Attribute]):
    super().__init__(filesystem_obj)
    self._fs_info = fs_info
    self._fd = fd
    self._data_stream = data_stream

  @property
  def _file_size(self) -> int:
    if self._IsDirectory():
      raise IOError("Attempting to get size of directory.")

    if self._data_stream is None:
      return _FixInt(self._fd.info.meta.size)
    else:
      return self._data_stream.info.size

  def Read(self, offset: int, size: int) -> bytes:
    if self._IsDirectory():
      raise IOError("Attempting to read from a directory.")

    available = min(self._file_size - offset, size)

    # TSK fails with an error when reading past the end.
    if available <= 0:
      return b""

    if self._data_stream is None:
      return self._fd.read_random(offset, available)
    else:
      return self._fd.read_random(offset, available,
                                  self._data_stream.info.type,
                                  self._data_stream.info.id)

  def Close(self) -> None:
    pass

  def ListFiles(self) -> Iterator[filesystem_pb2.StatEntry]:
    if self._IsDirectory():
      # If this is a directory, list directory contents.
      for fd in self._fd.as_directory():
        name = _DecodeName(fd.info.name.name)
        if name in _LIST_FILES_IGNORE:
          continue
        if fd.info.meta is not None:
          # This is a deleted file.
          if int(fd.info.meta.flags) & pytsk3.TSK_FS_META_FLAG_UNALLOC != 0:
            continue
        # This is another type of deleted file.
        if int(fd.info.name.flags) & pytsk3.TSK_FS_NAME_FLAG_UNALLOC != 0:
          continue
        yield self._Stat(fd, None)
        for attribute in fd:
          if _IsAlternateDataStream(attribute):
            yield self._Stat(fd, attribute)
    else:
      # If this is a file, list alternate data streams.
      for attribute in self._fd:
        if _IsAlternateDataStream(attribute):
          yield self._Stat(self._fd, attribute)

  def ListNames(self) -> Iterator[str]:
    if self._IsDirectory():
      # Return file names.
      for fd in self._fd.as_directory():
        name = _DecodeName(fd.info.name.name)
        if name in _LIST_FILES_IGNORE:
          continue
        yield name
    else:
      # Return alternate data stream names.
      for attribute in self._fd:
        if _IsAlternateDataStream(attribute):
          yield _DecodeName(attribute.info.name)

  def LookupCaseInsensitive(self, name: str) -> Optional[str]:
    name_lower = name.lower()
    if self._IsDirectory():
      # If this is a directory, lookup a file in the directory in
      # case-insensitive mode.
      for fd in self._fd.as_directory():
        candidate_name = _DecodeName(fd.info.name.name)
        if candidate_name.lower() == name_lower:
          return candidate_name
    else:
      # If this is not a directory, lookup an alternate data stream in the file
      # in case-insensitive mode.
      for attribute in self._fd:
        if _IsAlternateDataStream(attribute):
          candidate_name = _DecodeName(attribute.info.name)
          if candidate_name.lower() == name_lower:
            return candidate_name
    return None

  def Stat(self) -> filesystem_pb2.StatEntry:
    return self._Stat(self._fd, self._data_stream)

  def _Stat(
      self,
      fd: pytsk3.File,
      data_stream: Optional[pytsk3.Attribute],
  ) -> filesystem_pb2.StatEntry:
    st = filesystem_pb2.StatEntry()

    if fd.info.name is not None:
      name = fd.info.name
      if name.name is not None:
        st.name = _DecodeName(name.name)
      st.st_mode |= _FS_NAME_TYPE_LOOKUP.get(int(name.type), 0)

    if fd.info.meta is not None:
      meta = fd.info.meta
      if hasattr(meta, "mode"):
        st.st_mode |= _FixInt(int(meta.mode))
      if hasattr(meta, "nlink"):
        st.st_nlink = _FixInt(meta.nlink)
      if hasattr(meta, "uid"):
        st.st_uid = _FixInt(meta.uid)
      if hasattr(meta, "gid"):
        st.st_gid = _FixInt(meta.gid)
      if hasattr(meta, "addr"):
        st.st_ino = meta.addr
      if hasattr(meta, "atime"):
        st.st_atime.FromSeconds(_FixInt(meta.atime))
      if hasattr(meta, "mtime"):
        st.st_mtime.FromSeconds(_FixInt(meta.mtime))
      if hasattr(meta, "crtime"):
        st.st_btime.FromSeconds(_FixInt(meta.crtime))
      if hasattr(meta, "ctime"):
        st.st_ctime.FromSeconds(_FixInt(meta.ctime))
      if hasattr(meta, "type"):
        st.st_mode |= _FS_META_TYPE_LOOKUP.get(_FixInt(int(meta.type)), 0)
      if hasattr(meta, "size"):
        if not stat.S_ISDIR(st.st_mode):
          st.st_size = _FixInt(meta.size)

    if data_stream is not None:
      if data_stream.info.name is not None:
        st.stream_name = _DecodeName(data_stream.info.name)
      st.st_size = data_stream.info.size

    if self._fs_info.info.ftype == pytsk3.TSK_FS_TYPE_NTFS:
      st.st_mode = _FixNtfsMode(st.st_mode)

    return st

  def Inode(self) -> int:
    return self._fd.info.meta.addr

  def _IsDirectory(self) -> bool:
    if self._data_stream is not None:
      return False
    if self._fd.info.meta is None:
      return False
    return self._fd.info.meta.type == pytsk3.TSK_FS_META_TYPE_DIR


def _GetDataStream(fd: pytsk3.File,
                   stream_name: Optional[str]) -> Optional[pytsk3.Attribute]:
  if stream_name is None:
    return None
  for attribute in fd:
    if (attribute.info.name is not None and
        _DecodeName(attribute.info.name) == stream_name and
        attribute.info.type == pytsk3.TSK_FS_ATTR_TYPE_NTFS_DATA):
      return attribute
  raise IOError(f"Failed to open data stream {stream_name}.")


class TskFilesystem(filesystem.Filesystem):
  """TSK implementation of a Filesystem."""

  def __init__(self, device: filesystem.Device):
    super().__init__(device)
    self._fs_info = pytsk3.FS_Info(DeviceWrapper(self), 0)

  def Open(self, path: str, stream_name: Optional[str]) -> TskFile:
    fd = self._fs_info.open(path)

    if fd is None:
      raise IOError(f"Failed to open file {path}.")

    data_stream = _GetDataStream(fd, stream_name)

    return TskFile(self, self._fs_info, fd, data_stream)

  def OpenByInode(self, inode: int, stream_name: Optional[str]) -> TskFile:
    fd = self._fs_info.open_meta(inode)

    data_stream = _GetDataStream(fd, stream_name)

    return TskFile(self, self._fs_info, fd, data_stream)
