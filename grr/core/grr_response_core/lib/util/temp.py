#!/usr/bin/env python
# Lint as: python3
"""A module with utilities for dealing with temporary files and directories."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import platform
import shutil
import tempfile
from typing import Optional
from typing import Text

from absl import flags
from absl import logging

from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util import precondition

FLAGS = flags.FLAGS


def _TestTempRootPath() -> Optional[Text]:
  """Returns a default root path for storing temporary files during tests."""
  # `TEST_TMPDIR` and `FLAGS.test_tmpdir` are only defined only for test
  # environments. For non-test code, we use the default temporary directory.
  test_tmpdir = compatibility.Environ("TEST_TMPDIR", default=None)
  if test_tmpdir is None and hasattr(FLAGS, "test_tmpdir"):
    test_tmpdir = FLAGS.test_tmpdir

  if test_tmpdir is not None and not os.path.exists(test_tmpdir):
    # TODO: We add a try-catch block to avoid rare race condition.
    # In Python 3 the exception being thrown is way more specific
    # (`FileExistsError`) but in Python 2 `OSError` is the best we can do. Once
    # support for Python 2 is dropped we can switch to catching that and remove
    # the conditional (EAFP).
    try:
      os.makedirs(test_tmpdir)
    except OSError as err:
      logging.error(err)

  # TODO(hanuszczak): Investigate whether this check still makes sense.
  if platform.system() == "Windows":
    return None

  return test_tmpdir


def TempDirPath(suffix: Text = "", prefix: Text = "tmp") -> Text:
  """Creates a temporary directory based on the environment configuration.

  The directory will be placed in folder as specified by the `TEST_TMPDIR`
  environment variable if available or fallback to `FLAGS.test_tmpdir` if
  provided or just use Python's default.

  Args:
    suffix: A suffix to end the directory name with.
    prefix: A prefix to begin the directory name with.

  Returns:
    An absolute path to the created directory.
  """
  precondition.AssertType(suffix, Text)
  precondition.AssertType(prefix, Text)

  return tempfile.mkdtemp(suffix=suffix, prefix=prefix, dir=_TestTempRootPath())


def TempFilePath(suffix: Text = "", prefix: Text = "tmp",
                 dir: Text = None) -> Text:  # pylint: disable=redefined-builtin
  """Creates a temporary file based on the environment configuration.

  If no directory is specified the file will be placed in folder as specified by
  the `TEST_TMPDIR` environment variable if available or fallback to
  `FLAGS.test_tmpdir` if provided or just use Python's default.

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
  precondition.AssertType(suffix, Text)
  precondition.AssertType(prefix, Text)
  precondition.AssertOptionalType(dir, Text)

  root = _TestTempRootPath()
  if not dir:
    dir = root
  elif root and not os.path.commonprefix([dir, root]):
    raise ValueError("path '%s' must start with '%s'" % (dir, root))

  # `mkstemp` returns an open descriptor for the file. We don't care about it as
  # we are only concerned with the path, but we need to close it first or else
  # the file will remain open until the garbage collectors steps in.
  desc, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir)
  os.close(desc)
  return path


class AutoTempDirPath(object):
  """Creates a temporary directory based on the environment configuration.

  The directory will be placed in folder as specified by the `TEST_TMPDIR`
  environment variable if available or fallback to `FLAGS.test_tmpdir` if
  provided or just use Python's default.

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

  def __init__(self,
               suffix: Text = "",
               prefix: Text = "tmp",
               remove_non_empty: bool = False):
    precondition.AssertType(suffix, Text)
    precondition.AssertType(prefix, Text)
    precondition.AssertType(remove_non_empty, bool)

    self.suffix = suffix
    self.prefix = prefix
    self.remove_non_empty = remove_non_empty

  def __enter__(self) -> Text:
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
  `FLAGS.test_tmpdir` if provided or just default to Python's default.

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

  def __init__(self,
               suffix: Text = "",
               prefix: Text = "tmp",
               dir: Optional[Text] = None):  # pylint: disable=redefined-builtin
    precondition.AssertType(prefix, Text)
    precondition.AssertType(suffix, Text)
    precondition.AssertOptionalType(dir, Text)

    self.suffix = suffix
    self.prefix = prefix
    self.dir = dir

  def __enter__(self) -> Text:
    self.path = TempFilePath(
        suffix=self.suffix, prefix=self.prefix, dir=self.dir)
    return self.path

  def __exit__(self, exc_type, exc_value, traceback):
    del exc_type  # Unused.
    del exc_value  # Unused.
    del traceback  # Unused.

    os.remove(self.path)
