#!/usr/bin/env python
"""Utilities for working with RRG filesystem paths."""

import abc
import ntpath
import pathlib
import posixpath
from typing import Sequence, Union

from grr_response_proto.rrg import fs_pb2 as rrg_fs_pb2
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2


class PurePath(pathlib.PurePath, abc.ABC):
  """Abstract base class for RRG extensions for the Python standard paths."""

  @classmethod
  def For(
      cls,
      os_type: rrg_os_pb2.Type,
      *paths: Union[str, "PurePath", rrg_fs_pb2.Path],
  ) -> "PurePath":
    """Converts the given RRG path object to pure absolute path object.

    Bytes that do not correspond to valid Unicode characters (which might be the
    case for Linux and Windows paths) will be either escaped or replaced with
    Unicode replacement character (�).

    Args:
      os_type: RRG operating system to use for determining type of the path.
      *paths: RRG path parts to convert.

    Returns:
      Pure absolute path object corresponding to the given path.
    """
    if os_type == rrg_os_pb2.LINUX or os_type == rrg_os_pb2.MACOS:
      return PurePosixPath(*paths)
    if os_type == rrg_os_pb2.WINDOWS:
      return PureWindowsPath(*paths)

    raise ValueError(f"Unexpected operating system type: {os_type}")

  @property
  @abc.abstractmethod
  def components(self) -> Sequence[str]:
    """Returns path's individual components.

    This is similar to `PurePath.parts` accessor except that more suited for our
    internal usage. As path is guaranteed to be absolute, there is no need to
    use `/` as the first component for Linux paths or to add superflous slash
    after drive letter for Windows paths.

    Raises:
      ValueError: If path is not absolute.
    """

  @property
  @abc.abstractmethod
  def normal(self) -> "PureWindowsPath":
    """Returns normalized variant of the path."""


class PurePosixPath(pathlib.PurePosixPath, PurePath):
  """POSIX-specific RRG extension of the Python standard path object.

  Bytes that do not correspond to valid Unicode characters (which might be the
  case for Linux) will be escaped.
  """

  # TODO: There is a discrepancy between how Python 3.10 and 3.12
  # declare the constructor and to support both we need to do weird gymnastics
  # here. Once support for Python 3.10 is gone, we can remove the weird branch
  # in `__init__` and simplify `__new__`.

  def __new__(
      cls,
      *paths: Union[str, pathlib.PurePosixPath, rrg_fs_pb2.Path],
  ) -> "PurePosixPath":
    paths_str = []
    for path in paths:
      if isinstance(path, pathlib.PurePosixPath):
        paths_str.append(str(path))
      elif isinstance(path, str):
        paths_str.append(path)
      elif isinstance(path, rrg_fs_pb2.Path):
        # We know we are not dealing with the Windows path and thus backslash is
        # not a character with special meaning, so we can use escaping.
        paths_str.append(path.raw_bytes.decode("utf-8", "backslashreplace"))
      else:
        raise TypeError(f"Unexpected path type: {type(path)}")

    self = super().__new__(cls, *paths_str)
    self._paths_str = paths_str  # pylint: disable=assigning-non-slot
    return self

  def __init__(
      self,
      *paths: Union[str, pathlib.PurePosixPath, rrg_fs_pb2.Path],
  ) -> None:
    del paths  # Unused.

    if pathlib.PurePosixPath.__init__ is not object.__init__:
      super().__init__(*self._paths_str)  # pytype: disable=attribute-error

    del self._paths_str  # pytype: disable=attribute-error

  # TODO: Use `@override` once we are on Python 3.12+.
  @property
  def components(self) -> Sequence[str]:
    """Returns path's individual components.

    This is similar to `PurePath.parts` accessor except that more suited for our
    internal usage. As path is guaranteed to be absolute, there is no need to
    use `/` as the first component for Linux paths.

    Raises:
      ValueError: If path is not absolute.
    """
    if not self.is_absolute():
      raise ValueError("Components are available only for absolute paths")

    # POSIX paths are parsed with `/` as the first component, so we just do not
    # include it.
    return self.parts[1:]

  @property
  def normal(self) -> "PurePosixPath":
    """Returns normalized variant of the path."""
    return PurePosixPath(posixpath.normpath(str(self)))


class PureWindowsPath(pathlib.PureWindowsPath, PurePath):
  """Windows-specific RRG extension of the Python standard path object.

  Bytes that do not correspond to valid Unicode characters (which might be the
  case with unpaired surrogate 16-bit code units) will be replaced with Unicode
  replacement character (�).
  """

  # TODO: There is a discrepancy between how Python 3.10 and 3.12
  # declare the constructor and to support both we need to do weird gymnastics
  # here. Once support for Python 3.10 is gone, we can remove the weird branch
  # in `__init__` and simplify `__new__`.

  def __new__(
      cls,
      *paths: Union[str, pathlib.PureWindowsPath, rrg_fs_pb2.Path],
  ) -> "PureWindowsPath":
    paths_str = []
    for path in paths:
      if isinstance(path, pathlib.PureWindowsPath):
        paths_str.append(str(path))
      elif isinstance(path, str):
        paths_str.append(path)
      elif isinstance(path, rrg_fs_pb2.Path):
        # Unlike with POSIX path, we can't use `backslashreplace` here as in
        # Windows paths backslash is used as path separator.
        paths_str.append(path.raw_bytes.decode("utf-8", "replace"))
      else:
        raise TypeError(f"Unexpected path type: {type(path)}")

    self = super().__new__(cls, *paths_str)
    self._paths_str = paths_str  # pylint: disable=assigning-non-slot
    return self

  def __init__(
      self,
      *paths: Union[str, pathlib.PureWindowsPath, rrg_fs_pb2.Path],
  ) -> None:
    del paths  # Unused.

    if pathlib.PureWindowsPath.__init__ is not object.__init__:
      super().__init__(*self._paths_str)  # pytype: disable=attribute-error

    del self._paths_str  # pytype: disable=attribute-error

  # TODO: Use `@override` once we are on Python 3.12+.
  @property
  def components(self) -> Sequence[str]:
    """Returns path's individual components.

    This is similar to `PurePath.parts` accessor except that more suited for our
    internal usage. As path is guaranteed to be absolute, there is no need to
    add superflous slash after drive letter for Windows paths.

    Raises:
      ValueError: If path is not absolute.
    """
    if not self.is_absolute():
      raise ValueError("Components are available only for absolute paths")

    # Windows paths are parsed with `X:\\` as the first component (note the
    # trailing slash), so we bypass this by taking the drive and skipping the
    # root part.
    return (self.drive,) + self.parts[1:]

  @property
  def normal(self) -> "PureWindowsPath":
    """Returns normalized variant of the path."""
    return PureWindowsPath(ntpath.normpath(str(self)))
