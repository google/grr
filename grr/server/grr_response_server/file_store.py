#!/usr/bin/env python
"""A manager for storing files locally."""

import hashlib
import os
import shutil

from grr import config
from grr.lib import rdfvalue
from grr.lib import registry
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server.aff4_objects import standard


class UploadFileStore(object):
  """A class to manage writing to a file location."""

  __metaclass__ = registry.MetaclassRegistry

  def CreateFileStoreFile(self):
    """Creates a new file for writing."""


class FileStoreAFF4Object(aff4.AFF4Stream):
  """An AFF4 object which allows to read the files in the filestore."""

  class SchemaCls(aff4.AFF4Stream.SchemaCls):
    FILE_ID = aff4.Attribute("aff4:file_id", rdfvalue.RDFString,
                             "This string uniquely identifies a "
                             "file stored in the file store. Passing "
                             "this id to the file store grants read "
                             "access to the corresponding data.")

    STAT = standard.VFSDirectory.SchemaCls.STAT

  _file_handle = None

  @property
  def file_handle(self):
    if self._file_handle is None:
      file_id = self.Get(self.Schema.FILE_ID)
      file_store = UploadFileStore.GetPlugin(
          config.CONFIG["Frontend.upload_store"])()
      self._file_handle = file_store.OpenForReading(file_id)
    return self._file_handle

  def Read(self, length):
    return self.file_handle.read(length)

  def Seek(self, offset, whence=0):
    return self.file_handle.seek(offset, whence)

  def Tell(self):
    return self.file_handle.tell()

  def Write(self, data):
    raise NotImplementedError("Write is not implemented.")


class FileStoreFDCreator(object):
  """A handle to a file opened via the FileUploadFileStore."""

  def __init__(self):
    self.tmp_path = FileUploadFileStore.PathForId(
        os.urandom(32).encode("hex"), prefix="tmp")
    # Ensure the directory exists.
    try:
      os.makedirs(os.path.dirname(self.tmp_path))
    except (IOError, OSError):
      pass

    self._fd = open(self.tmp_path, mode="wb")
    self.hasher = hashlib.sha256()

  def Write(self, data):
    self._fd.write(data)
    self.hasher.update(data)

  def Flush(self):
    self._fd.flush()

  def Close(self):
    self._fd.close()

  write = Write
  flush = Flush
  close = Close

  def Finalize(self):
    """Move the file to the hash based filename and return the file id."""
    self._fd.close()
    final_id = self.hasher.hexdigest()
    final_filename = FileUploadFileStore.PathForId(final_id)

    if not os.path.exists(final_filename):
      # Ensure the directory exists.
      try:
        os.makedirs(os.path.dirname(final_filename))
      except (IOError, OSError):
        pass
      shutil.move(self.tmp_path, final_filename)
    else:
      os.remove(self.tmp_path)

    return final_id


class FileUploadFileStore(UploadFileStore):
  """An implementation of upload server based on files."""

  @classmethod
  def PathForId(cls, file_id, prefix=""):
    root_dir = config.CONFIG["FileUploadFileStore.root_dir"]
    return os.path.join(root_dir, prefix, file_id[0], file_id[1], file_id[2],
                        file_id[3:])

  def CreateFileStoreFile(self):
    return FileStoreFDCreator()

  def OpenForReading(self, file_id):
    path = self.PathForId(file_id)
    return open(path, "rb")

  def Aff4ObjectForFileId(self, urn, file_id, token=None):
    """Returns an AFF4 object backed by the file store."""
    result = aff4.FACTORY.Create(
        urn, FileStoreAFF4Object, mode="w", token=token)
    result.Set(result.Schema.FILE_ID(file_id))
    return result
