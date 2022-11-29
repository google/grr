#!/usr/bin/env python
"""Utils common to macOS and Linux."""

import io
import logging
import os
from typing import Text

import xattr

from google.protobuf import message
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.util import precondition


def VerifyFileOwner(filename):
  stat_info = os.lstat(filename)
  return os.getuid() == stat_info.st_uid


def CanonicalPathToLocalPath(path: Text) -> Text:
  """Linux uses a normal path.

  We always want to encode as UTF-8 here. If the environment for the
  client is broken, Python might assume an ASCII based filesystem
  (those should be rare nowadays) and things will go wrong if we let
  Python decide what to do. If the filesystem actually is ASCII,
  encoding and decoding will not change anything so things will still
  work as expected.

  Args:
    path: the canonical path as an Unicode string

  Returns:
    A unicode string.
  """
  precondition.AssertType(path, Text)
  return utils.NormalizePath(path)


def LocalPathToCanonicalPath(path: Text) -> Text:
  """Linux uses a normal path."""
  precondition.AssertType(path, Text)
  return utils.NormalizePath(path)


def GetExtAttrs(filepath):
  """Fetches extended file attributes.

  Args:
    filepath: A path to the file.

  Yields:
    `ExtAttr` pairs.
  """
  path = CanonicalPathToLocalPath(filepath)

  try:
    attr_names = xattr.listxattr(path)
  except (IOError, OSError, UnicodeDecodeError) as error:
    msg = "Failed to retrieve extended attributes for '%s': %s"
    logging.error(msg, path, error)
    return

  # `xattr` (version 0.9.2) decodes names as UTF-8. Since we (and the system)
  # allows for names and values to be arbitrary byte strings, we use `bytes`
  # rather than `unicode` objects here. Therefore we have to re-encode what
  # `xattr` has decoded. Additionally, because the decoding that `xattr` does
  # may fail, we additionally guard against such exceptions.
  def EncodeUtf8(attr_name):
    if isinstance(attr_name, Text):
      return attr_name.encode("utf-8")
    if isinstance(attr_name, bytes):
      return attr_name
    raise TypeError("Unexpected type `%s`" % type(attr_name))

  for attr_name in attr_names:
    attr_name = EncodeUtf8(attr_name)
    try:
      attr_value = xattr.getxattr(path, attr_name)
    except (IOError, OSError) as error:
      msg = "Failed to retrieve attribute '%s' for '%s': %s"
      logging.error(msg, attr_name, path, error)
      continue

    yield rdf_client_fs.ExtAttr(name=attr_name, value=attr_value)


class TransactionLog(object):
  """A class to manage a transaction log for client processing."""

  max_log_size = 100000000

  def __init__(self, logfile=None):
    self.logfile = logfile or config.CONFIG["Client.transaction_log_file"]

  def Write(self, grr_message):
    """Write the message into the transaction log."""
    grr_message = grr_message.SerializeToBytes()

    try:
      with io.open(self.logfile, "wb") as fd:
        fd.write(grr_message)
    except (IOError, OSError):
      # Check if we're missing directories and try to create them.
      if not os.path.isdir(os.path.dirname(self.logfile)):
        try:
          os.makedirs(os.path.dirname(self.logfile))
          with io.open(self.logfile, "wb") as fd:
            fd.write(grr_message)
        except (IOError, OSError):
          logging.exception("Couldn't write the transaction log to %s",
                            self.logfile)

  def Sync(self):
    # Not implemented on Linux.
    pass

  def Clear(self):
    """Wipes the transaction log."""
    try:
      with io.open(self.logfile, "wb") as fd:
        fd.write(b"")
    except (IOError, OSError):
      pass

  def Get(self):
    """Return a GrrMessage instance from the transaction log or None."""
    try:
      with io.open(self.logfile, "rb") as fd:
        data = fd.read(self.max_log_size)
    except (IOError, OSError):
      return

    try:
      if data:
        return rdf_flows.GrrMessage.FromSerializedBytes(data)
    except (message.Error, rdfvalue.Error):
      return
