#!/usr/bin/env python
"""This file contains code to generate ZIP/TAR archives."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import os
import zipfile


from future.utils import iteritems

from grr_response_core.lib import utils
from grr_response_core.lib.util import collection
from grr_response_core.lib.util.compat import yaml
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server.flows.general import export as flow_export
from grr_response_server.gui.api_plugins import client as api_client

# export Aff4CollectionArchiveGenerator from this file
from grr_response_server.gui.archive_generator_aff4 import Aff4CollectionArchiveGenerator


def CompatCollectionArchiveGenerator(*args, **kwargs):
  """Returns an instance of (Aff4)CollectionArchiveGenerator.

  Args:
    *args: the args, passed to the constructor
    **kwargs: the kwargs, passed to the constructor
  """
  return GetCompatClass()(*args, **kwargs)


def GetCompatClass():
  """Returns the (Aff4)CollectionArchiveGenerator class."""
  if data_store.RelationalDBEnabled():
    return CollectionArchiveGenerator
  else:
    return Aff4CollectionArchiveGenerator


def _ClientPathToString(client_path, prefix=""):
  """Returns a path-like String of client_path with optional prefix."""
  return os.path.join(prefix, client_path.client_id, client_path.vfs_path)


class CollectionArchiveGenerator(object):
  """Class that generates downloaded files archive from a collection."""

  ZIP = "zip"
  TAR_GZ = "tar.gz"

  FILES_SKIPPED_WARNING = (
      "# NOTE: Some files were skipped because they were referenced in the \n"
      "# collection but were not downloaded by GRR, so there were no data \n"
      "# blobs in the data store to archive.\n").encode("utf-8")

  BATCH_SIZE = 1000

  def __init__(self,
               archive_format=ZIP,
               prefix=None,
               description=None,
               predicate=None,
               client_id=None):
    """CollectionArchiveGenerator constructor.

    Args:
      archive_format: May be ArchiveCollectionGenerator.ZIP or
        ArchiveCollectionGenerator.TAR_GZ. Defaults to ZIP.
      prefix: Name of the folder inside the archive that will contain all the
        generated data.
      description: String describing archive's contents. It will be included
        into the auto-generated MANIFEST file. Defaults to 'Files archive
        collection'.
      predicate: If not None, only the files matching the predicate will be
        archived, all others will be skipped. The predicate receives a
        db.ClientPath as input.
      client_id: The client_id to use when exporting a flow results collection.

    Raises:
      ValueError: if prefix is None.
    """
    super(CollectionArchiveGenerator, self).__init__()

    if archive_format == self.ZIP:
      self.archive_generator = utils.StreamingZipGenerator(
          compression=zipfile.ZIP_DEFLATED)
    elif archive_format == self.TAR_GZ:
      self.archive_generator = utils.StreamingTarGenerator()
    else:
      raise ValueError("Unknown archive format: %s" % archive_format)

    if not prefix:
      raise ValueError("Prefix can't be None.")
    self.prefix = prefix

    self.description = description or "Files archive collection"

    self.archived_files = set()
    self.ignored_files = set()
    self.failed_files = set()
    self.processed_files = set()

    self.predicate = predicate or (lambda _: True)
    self.client_id = client_id

  @property
  def output_size(self):
    return self.archive_generator.output_size

  @property
  def total_files(self):
    return len(self.processed_files)

  def _GenerateDescription(self):
    """Generates description into a MANIFEST file in the archive."""

    manifest = {
        "description": self.description,
        "processed_files": len(self.processed_files),
        "archived_files": len(self.archived_files),
        "ignored_files": len(self.ignored_files),
        "failed_files": len(self.failed_files)
    }
    if self.ignored_files:
      manifest["ignored_files_list"] = [
          _ClientPathToString(cp, prefix="aff4:") for cp in self.ignored_files
      ]
    if self.failed_files:
      manifest["failed_files_list"] = [
          _ClientPathToString(cp, prefix="aff4:") for cp in self.failed_files
      ]

    manifest_fd = io.BytesIO()
    if self.total_files != len(self.archived_files):
      manifest_fd.write(self.FILES_SKIPPED_WARNING)
    manifest_fd.write(yaml.Dump(manifest).encode("utf-8"))

    manifest_fd.seek(0)
    st = os.stat_result(
        (0o644, 0, 0, 0, 0, 0, len(manifest_fd.getvalue()), 0, 0, 0))

    for chunk in self.archive_generator.WriteFromFD(
        manifest_fd, os.path.join(self.prefix, "MANIFEST"), st=st):
      yield chunk

  def _GenerateClientInfo(self, client_id, client_fd):
    """Yields chucks of archive information for given client."""
    summary_dict = client_fd.ToPrimitiveDict(stringify_leaf_fields=True)
    summary = yaml.Dump(summary_dict).encode("utf-8")

    client_info_path = os.path.join(self.prefix, client_id, "client_info.yaml")
    st = os.stat_result((0o644, 0, 0, 0, 0, 0, len(summary), 0, 0, 0))
    yield self.archive_generator.WriteFileHeader(client_info_path, st=st)
    yield self.archive_generator.WriteFileChunk(summary)
    yield self.archive_generator.WriteFileFooter()

  def Generate(self, items, token=None):
    """Generates archive from a given collection.

    Iterates the collection and generates an archive by yielding contents
    of every referenced AFF4Stream.

    Args:
      items: Iterable of rdf_client_fs.StatEntry objects
      token: User's ACLToken.

    Yields:
      Binary chunks comprising the generated archive.
    """

    del token  # unused, to be removed with AFF4 code

    client_ids = set()
    for item_batch in collection.Batch(items, self.BATCH_SIZE):

      client_paths = set()
      for item in item_batch:
        try:
          client_path = flow_export.CollectionItemToClientPath(
              item, self.client_id)
        except flow_export.ItemNotExportableError:
          continue

        if not self.predicate(client_path):
          self.ignored_files.add(client_path)
          self.processed_files.add(client_path)
          continue

        client_ids.add(client_path.client_id)
        client_paths.add(client_path)

      for chunk in file_store.StreamFilesChunks(client_paths):
        self.processed_files.add(chunk.client_path)
        for output in self._WriteFileChunk(chunk=chunk):
          yield output

      self.processed_files |= client_paths - (
          self.ignored_files | self.archived_files)

    if client_ids:
      for client_id, client_info in iteritems(
          data_store.REL_DB.MultiReadClientFullInfo(client_ids)):
        client = api_client.ApiClient().InitFromClientInfo(client_info)
        for chunk in self._GenerateClientInfo(client_id, client):
          yield chunk

    for chunk in self._GenerateDescription():
      yield chunk

    yield self.archive_generator.Close()

  def _WriteFileChunk(self, chunk):
    """Yields binary chunks, respecting archive file headers and footers.

    Args:
      chunk: the StreamedFileChunk to be written
    """
    if chunk.chunk_index == 0:
      # Make sure size of the original file is passed. It's required
      # when output_writer is StreamingTarWriter.
      st = os.stat_result((0o644, 0, 0, 0, 0, 0, chunk.total_size, 0, 0, 0))
      target_path = _ClientPathToString(chunk.client_path, prefix=self.prefix)
      yield self.archive_generator.WriteFileHeader(target_path, st=st)

    yield self.archive_generator.WriteFileChunk(chunk.data)

    if chunk.chunk_index == chunk.total_chunks - 1:
      yield self.archive_generator.WriteFileFooter()
      self.archived_files.add(chunk.client_path)
