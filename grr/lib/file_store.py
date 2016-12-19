#!/usr/bin/env python
"""A manager for storing files locally."""


import os

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib.rdfvalues import client


class UploadFileStore(object):
  """A class to manage writing to a file location."""

  __metaclass__ = registry.MetaclassRegistry

  def open_for_writing(self, client_id, path):
    """Facilitates writing to the specified path.

    Args:
      client_id: The client making this request.
      path: The path to write on.

    Returns:
      a file like object ready for writing.

    Raises:
      IOError: If the writing is rejected.
    """


class FileStoreAFF4Object(aff4.AFF4Stream):
  """An AFF4 object which allows to read the files in the filestore."""

  class SchemaCls(aff4.AFF4Stream.SchemaCls):
    FILESTORE_PATH = aff4.Attribute("aff4:filestore_path", rdfvalue.RDFString,
                                    "The filestore path to read data from.")

    STAT = aff4.Attribute("aff4:stat", client.StatEntry,
                          "A StatEntry describing this file.", "stat")

  _file_handle = None

  @property
  def file_handle(self):
    if self._file_handle is None:
      filename = unicode(self.Get(self.Schema.FILESTORE_PATH)).strip(
          os.path.sep)
      path = os.path.join(config_lib.CONFIG["FileUploadFileStore.root_dir"],
                          filename)

      self._file_handle = open(path, "r")
    return self._file_handle

  def Read(self, length):
    return self.file_handle.read(length)

  def Seek(self, offset, whence=0):
    return self.file_handle.seek(offset, whence)

  def Tell(self):
    return self.file_handle.tell()

  def Write(self, data):
    raise NotImplementedError("Write is not implemented.")


class FileUploadFileStore(UploadFileStore):
  """An implementation of upload server based on files."""

  def _get_filestore_path(self, client_id, path):
    client_urn = client.ClientURN(client_id)
    return client_urn.Add(path).Path().lstrip(os.path.sep)

  def open_for_writing(self, client_id, path):
    root_dir = config_lib.CONFIG["FileUploadFileStore.root_dir"]
    path = os.path.join(root_dir, self._get_filestore_path(client_id, path))

    # Ensure the directory exists.
    try:
      os.makedirs(os.path.dirname(path))
    except (IOError, OSError):
      pass

    return open(path, "wb")

  def aff4_factory(self, client_id, path, token=None):
    """Returns an AFF4 object backed by the file store."""
    urn = client.ClientURN(client_id).Add(path)
    result = aff4.FACTORY.Create(
        urn, FileStoreAFF4Object, mode="w", token=token)
    result.Set(
        result.Schema.FILESTORE_PATH(self._get_filestore_path(client_id, path)))
    return result
