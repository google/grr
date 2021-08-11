#!/usr/bin/env python
"""Common code and abstractions for filesystem implementations."""

import abc

from typing import Dict, Optional, Iterable

from grr_response_client.unprivileged.proto import filesystem_pb2


class Error(Exception):
  """Base class for filesystem error."""
  pass


class StaleInodeError(Error):
  """The inode provided to open a file is stale / outdated."""
  pass


class Device(abc.ABC):
  """A device underlying a filesystem."""

  @abc.abstractmethod
  def Read(self, offset: int, size: int) -> bytes:
    """Reads from the file."""
    pass


class File(abc.ABC):
  """An open file."""

  def __init__(self, filesystem: "Filesystem"):
    self.filesystem = filesystem

  @abc.abstractmethod
  def Read(self, offset: int, size: int) -> bytes:
    """Read from a file at the given offset."""
    pass

  @abc.abstractmethod
  def Close(self) -> None:
    """Close the file."""
    pass

  @abc.abstractmethod
  def ListFiles(self) -> Iterable[filesystem_pb2.StatEntry]:
    """Lists files in a directory.

    If the file is a regular file, lists alternate data streams.
    """
    pass

  @abc.abstractmethod
  def ListNames(self) -> Iterable[str]:
    """Lists file names in a directory.

    If the file is a regular file, lists alternate data stream names.
    """
    pass

  @abc.abstractmethod
  def Stat(self) -> filesystem_pb2.StatEntry:
    """Returns information about the file."""
    pass

  @abc.abstractmethod
  def Inode(self) -> int:
    """Returns the inode number of the file."""
    pass

  @abc.abstractmethod
  def LookupCaseInsensitive(self, name: str) -> Optional[str]:
    """Looks up a name in case insensitive mode.

    Args:
      name: Case-insensitive name to match.
    Returns: the case-literal name or None if the case-insensitive name couldn't
      be found.
    """
    pass


class Filesystem(abc.ABC):
  """A filesystem implementation."""

  def __init__(self, device: Device):
    self.device = device

  @abc.abstractmethod
  def Open(self, path: str, stream_name: Optional[str]) -> File:
    pass

  @abc.abstractmethod
  def OpenByInode(self, inode: int, stream_name: Optional[str]) -> File:
    pass


class Files:
  """A collection of open files identified by integer ids."""

  def __init__(self):
    self._table = {}  # type: Dict[int, File]
    self._file_id_counter = 0

  def Add(self, file: File) -> int:
    file_id = self._file_id_counter
    self._file_id_counter += 1
    self._table[file_id] = file
    return file_id

  def Remove(self, file_id: int) -> None:
    del self._table[file_id]

  def Get(self, file_id: int) -> File:
    return self._table[file_id]
