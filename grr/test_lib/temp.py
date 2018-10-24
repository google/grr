#!/usr/bin/env python
"""A module with utilities for dealing with temporary files and directories."""
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import platform
import shutil
import tempfile

from grr_response_core import config


# TODO(hanuszczak): Consider moving this to the `util` module - classes defined
# here are general enough and can be useful in non-test code as well. They are
# essentially extensions of the standard library and therefore `util` is a good
# place for them.


def _TempRootPath():
  """Returns a default root path for storing temporary files."""
  try:
    root = os.environ.get("TEST_TMPDIR") or config.CONFIG["Test.tmpdir"]
  except RuntimeError:
    return None

  if platform.system() != "Windows":
    return root
  else:
    return None


def TempDirPath(suffix="", prefix="tmp"):
  """Creates a temporary directory based on the environment configuration.

  The directory will be placed in folder as specified by the `TEST_TMPDIR`
  environment variable if available or fallback to `Test.tmpdir` of the current
  configuration if not.

  Args:
    suffix: A suffix to end the directory name with.
    prefix: A prefix to begin the directory name with.

  Returns:
    An absolute path to the created directory.
  """
  return tempfile.mkdtemp(suffix=suffix, prefix=prefix, dir=_TempRootPath())


def TempFilePath(suffix="", prefix="tmp", dir=None):  # pylint: disable=redefined-builtin
  """Creates a temporary file based on the environment configuration.

  If no directory is specified the file will be placed in folder as specified by
  the `TEST_TMPDIR` environment variable if available or fallback to
  `Test.tmpdir` of the current configuration if not.

  If directory is specified it must be part of the default test temporary
  directory.

  Args:
    suffix: A suffix to end the file name with.
    prefix: A prefix to begin the file name with.
    dir: A directory to place the file in.

  Returns:
    An absolute path to the created file.

  Raises:
    ValueError: If the specified directory is not part of the default test
        temporary directory.
  """
  root = _TempRootPath()
  if not dir:
    dir = root
  elif root and not os.path.commonprefix([dir, root]):
    raise ValueError("path '%s' must start with '%s'" % (dir, root))

  _, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir)
  return path


class AutoTempDirPath(object):
  """Creates a temporary directory based on the environment configuration.

  The directory will be placed in folder as specified by the `TEST_TMPDIR`
  environment variable if available or fallback to `Test.tmpdir` of the current
  configuration if not.

  This object is a context manager and the directory is automatically removed
  when it goes out of scope.

  Args:
    suffix: A suffix to end the directory name with.
    prefix: A prefix to begin the directory name with.
    remove_non_empty: If set to `True` the directory removal will succeed even
      if it is not empty.

  Returns:
    An absolute path to the created directory.
  """

  def __init__(self, suffix="", prefix="tmp", remove_non_empty=False):
    self.suffix = suffix
    self.prefix = prefix
    self.remove_non_empty = remove_non_empty

  def __enter__(self):
    self.path = TempDirPath(suffix=self.suffix, prefix=self.prefix)
    return self.path

  def __exit__(self, exc_type, exc_value, traceback):
    del exc_type  # Unused.
    del exc_value  # Unused.
    del traceback  # Unused.

    if self.remove_non_empty:
      shutil.rmtree(self.path)
    else:
      os.rmdir(self.path)


class AutoTempFilePath(object):
  """Creates a temporary file based on the environment configuration.

  If no directory is specified the file will be placed in folder as specified by
  the `TEST_TMPDIR` environment variable if available or fallback to
  `Test.tmpdir` of the current configuration if not.

  If directory is specified it must be part of the default test temporary
  directory.

  This object is a context manager and the associated file is automatically
  removed when it goes out of scope.

  Args:
    suffix: A suffix to end the file name with.
    prefix: A prefix to begin the file name with.
    dir: A directory to place the file in.

  Returns:
    An absolute path to the created file.

  Raises:
    ValueError: If the specified directory is not part of the default test
        temporary directory.
  """

  def __init__(self, suffix="", prefix="tmp", dir=None):  # pylint: disable=redefined-builtin
    self.suffix = suffix
    self.prefix = prefix
    self.dir = dir

  def __enter__(self):
    self.path = TempFilePath(
        suffix=self.suffix, prefix=self.prefix, dir=self.dir)
    return self.path

  def __exit__(self, exc_type, exc_value, traceback):
    del exc_type  # Unused.
    del exc_value  # Unused.
    del traceback  # Unused.

    os.remove(self.path)
