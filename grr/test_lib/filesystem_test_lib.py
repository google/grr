#!/usr/bin/env python
"""A test utilities for interacting with filesystem."""

import io
import os
import platform
import subprocess
import unittest

from typing import Text


def CreateFile(filepath: Text, content: bytes = b"") -> None:
  """Creates a file at specified path.

  Note that if a file at the specified path already exists, its old content will
  be overwritten.

  Args:
    filepath: A path to the file to touch.
    content: An (optional) content to write to the file.
  """
  # There is a slight chance of a race condition here (the directory might have
  # been created after the `os.path.exists` check). This utility is a test-only
  # thing so wo do not care that much and just swallow any `OSError` exceptions.
  # If we don't have right permissions, `io.open` will fail later anyway.
  dirpath = os.path.dirname(filepath)
  if not os.path.exists(dirpath):
    try:
      os.makedirs(dirpath)
    except OSError:
      pass

  with io.open(filepath, "wb") as filedesc:
    filedesc.write(content)


def Command(name, args=None, system=None, message=None):
  """Executes given command as a subprocess for testing purposes.

  If the command fails, is not available or is not compatible with the operating
  system a test case that tried to called is skipped.

  Args:
    name: A name of the command to execute (e.g. `ls`).
    args: A list of arguments for the command (e.g. `-l`, `-a`).
    system: An operating system that the command should be compatible with.
    message: A message to skip the test with in case of a failure.

  Raises:
    SkipTest: If command execution fails.
  """
  args = args or []
  if system is not None and platform.system() != system:
    raise unittest.SkipTest("`%s` available only on `%s`" % (name, system))
  if subprocess.call(["which", name], stdout=open("/dev/null", "w")) != 0:
    raise unittest.SkipTest("`%s` command is not available" % name)
  if subprocess.call([name] + args, stdout=open("/dev/null", "w")) != 0:
    raise unittest.SkipTest(message or "`%s` call failed" % name)


def Chflags(filepath, flags=None):
  """Executes a `chflags` command with specified flags for testing purposes.

  Calling this on platforms different than macOS will skip the test.

  Args:
    filepath: A path to the file to change the flags of.
    flags: A list of flags to be changed (see `chflags` documentation).
  """
  flags = flags or []
  Command("chflags", args=[",".join(flags), filepath], system="Darwin")


def Chattr(filepath, attrs=None):
  """Executes a `chattr` command with specified attributes for testing purposes.

  Calling this on platforms different than Linux will skip the test.

  Args:
    filepath: A path to the file to change the attributes of.
    attrs: A list of attributes to be changed (see `chattr` documentation).
  """
  attrs = attrs or []
  message = "file attributes not supported by filesystem"
  Command("chattr", args=attrs + [filepath], system="Linux", message=message)


def SetExtAttr(filepath, name, value):
  """Sets an extended file attribute of a given file for testing purposes.

  Calling this on platforms different than Linux or macOS will skip the test.

  Args:
    filepath: A path to the file to set an extended attribute of.
    name: A name of the extended attribute to set.
    value: A value of the extended attribute being set.

  Raises:
    SkipTest: If called on unsupported platform.
  """
  system = platform.system()
  if system == "Linux":
    _SetExtAttrLinux(filepath, name=name, value=value)
  elif system == "Darwin":
    _SetExtAttrOsx(filepath, name=name, value=value)
  else:
    message = "setting extended attributes is not supported on `%s`" % system
    raise unittest.SkipTest(message)


def _SetExtAttrLinux(filepath, name, value):
  args = ["-n", name, "-v", value, filepath]
  message = "extended attributes not supported by filesystem"
  Command("setfattr", args=args, system="Linux", message=message)


def _SetExtAttrOsx(filepath, name, value):
  args = ["-w", name, value, filepath]
  message = "extended attributes are not supported"
  Command("xattr", args=args, system="Drawin", message=message)
