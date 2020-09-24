#!/usr/bin/env python
# Lint as: python3
"""This file contains code to generate ZIP/TAR archives."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import enum
import io
import os
from typing import Dict, Iterable, Iterator
import zipfile

from grr_response_core.lib import utils
from grr_response_core.lib.util import collection
from grr_response_core.lib.util.compat import yaml
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import flow_base
from grr_response_server.flows.general import export as flow_export
from grr_response_server.gui.api_plugins import client as api_client
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import objects as rdf_objects


def _ClientPathToString(client_path, prefix=""):
  """Returns a path-like String of client_path with optional prefix."""
  return os.path.join(prefix, client_path.client_id, client_path.vfs_path)


class ArchiveFormat(enum.Enum):
  ZIP = 1
  TAR_GZ = 2


# TODO(user): this is a general purpose class that is designed to export
# files archives for any flow or hunt. I'd expect this class to be phased out
# as soon as flow-specific implementations mapping-based implementations
# are done for all the flows (see FlowArchiveGenerator below).
class CollectionArchiveGenerator(object):
  """Class that generates downloaded files archive from a collection."""

  ZIP = ArchiveFormat.ZIP
  TAR_GZ = ArchiveFormat.TAR_GZ

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
    super().__init__()

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

  def Generate(self, items):
    """Generates archive from a given collection.

    Iterates the collection and generates an archive by yielding contents
    of every referenced file.

    Args:
      items: Iterable of rdf_client_fs.StatEntry objects

    Yields:
      Binary chunks comprising the generated archive.
    """

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
      client_infos = data_store.REL_DB.MultiReadClientFullInfo(client_ids)
      for client_id, client_info in client_infos.items():
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


class FlowArchiveGenerator:
  """Archive generator for new-style flows that provide custom file mappings."""

  BATCH_SIZE = 1000

  def __init__(self, flow: rdf_flow_objects.Flow,
               archive_format: ArchiveFormat):
    self.flow = flow
    self.archive_format = archive_format
    if archive_format == ArchiveFormat.ZIP:
      self.archive_generator = utils.StreamingZipGenerator(
          compression=zipfile.ZIP_DEFLATED)
      extension = "zip"
    elif archive_format == ArchiveFormat.TAR_GZ:
      self.archive_generator = utils.StreamingTarGenerator()
      extension = "tar.gz"
    else:
      raise ValueError(f"Unknown archive format: {archive_format}")

    self.prefix = "{}_{}_{}".format(
        flow.client_id.replace(".", "_"), flow.flow_id, flow.flow_class_name)
    self.filename = f"{self.prefix}.{extension}"
    self.num_archived_files = 0

  def _GenerateDescription(self, processed_files: Dict[str, str],
                           missing_files: Iterable[str]) -> Iterable[bytes]:
    """Generates a MANIFEST file in the archive."""

    manifest = {
        "processed_files": processed_files,
        "missing_files": missing_files,
        "client_id": self.flow.client_id,
        "flow_id": self.flow.flow_id,
    }

    manifest_fd = io.BytesIO()
    manifest_fd.write(yaml.Dump(manifest).encode("utf-8"))

    manifest_fd.seek(0)
    st = os.stat_result(
        (0o644, 0, 0, 0, 0, 0, len(manifest_fd.getvalue()), 0, 0, 0))

    for chunk in self.archive_generator.WriteFromFD(
        manifest_fd, os.path.join(self.prefix, "MANIFEST"), st=st):
      yield chunk

  def _WriteFileChunk(self, chunk: file_store.StreamedFileChunk,
                      archive_paths_by_id: Dict[rdf_objects.PathID, str]):
    """Yields binary chunks, respecting archive file headers and footers.

    Args:
      chunk: the StreamedFileChunk to be written
      archive_paths_by_id:
    """
    if chunk.chunk_index == 0:
      # Make sure size of the original file is passed. It's required
      # when output_writer is StreamingTarWriter.
      st = os.stat_result((0o644, 0, 0, 0, 0, 0, chunk.total_size, 0, 0, 0))
      archive_path = (archive_paths_by_id or {}).get(chunk.client_path.path_id)
      target_path = os.path.join(self.prefix, archive_path)

      yield self.archive_generator.WriteFileHeader(target_path, st=st)

    yield self.archive_generator.WriteFileChunk(chunk.data)

    if chunk.chunk_index == chunk.total_chunks - 1:
      self.num_archived_files += 1
      yield self.archive_generator.WriteFileFooter()

  def Generate(
      self, mappings: Iterator[flow_base.ClientPathArchiveMapping]
  ) -> Iterator[bytes]:
    """Generates archive from a given set of client path mappings.

    Iterates the mappings and generates an archive by yielding contents
    of every referenced file.

    Args:
      mappings: A set of mappings defining the archive structure.

    Yields:
      Chunks of bytes of the generated archive.
    """
    processed_files = {}
    missing_files = set()
    for mappings_batch in collection.Batch(mappings, self.BATCH_SIZE):

      archive_paths_by_id = {}
      for mapping in mappings_batch:
        archive_paths_by_id[mapping.client_path.path_id] = mapping.archive_path

      processed_in_batch = set()
      for chunk in file_store.StreamFilesChunks(
          [m.client_path for m in mappings_batch]):
        processed_in_batch.add(chunk.client_path.path_id)
        processed_files[chunk.client_path.vfs_path] = archive_paths_by_id[
            chunk.client_path.path_id]
        for output in self._WriteFileChunk(chunk, archive_paths_by_id):
          yield output

      for mapping in mappings_batch:
        if mapping.client_path.path_id in processed_in_batch:
          continue

        missing_files.add(mapping.client_path.vfs_path)

    for chunk in self._GenerateDescription(processed_files, missing_files):
      yield chunk

    yield self.archive_generator.Close()

  @property
  def output_size(self):
    return self.archive_generator.output_size
