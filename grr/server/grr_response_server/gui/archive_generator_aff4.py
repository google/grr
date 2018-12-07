#!/usr/bin/env python
"""This file contains code to generate ZIP/TAR archives."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import logging
import os
import zipfile


import yaml

from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.util import collection
from grr_response_server import aff4
from grr_response_server import db
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.flows.general import export as flow_export


class Aff4CollectionArchiveGenerator(object):
  """Class that generates downloaded files archive from a collection."""

  ZIP = "zip"
  TAR_GZ = "tar.gz"

  FILES_SKIPPED_WARNING = (
      "# NOTE: Some files were skipped because they were referenced in the \n"
      "# collection but were not downloaded by GRR, so there were no data \n"
      "# blobs in the data store to archive.\n")

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
    super(Aff4CollectionArchiveGenerator, self).__init__()

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

    self.total_files = 0
    self.archived_files = 0
    self.ignored_files = []
    self.failed_files = []

    self.predicate = predicate or (lambda _: True)
    self.client_id = client_id

  @property
  def output_size(self):
    return self.archive_generator.output_size

  def _ItemsToUrns(self, items):
    """Converts collection items to aff4 urns suitable for downloading."""
    for item in items:
      try:
        yield flow_export.CollectionItemToAff4Path(item, self.client_id)
      except flow_export.ItemNotExportableError:
        pass

  def _GenerateDescription(self):
    """Generates description into a MANIFEST file in the archive."""

    manifest = {
        "description": self.description,
        "processed_files": self.total_files,
        "archived_files": self.archived_files,
        "ignored_files": len(self.ignored_files),
        "failed_files": len(self.failed_files)
    }
    if self.ignored_files:
      manifest["ignored_files_list"] = self.ignored_files
    if self.failed_files:
      manifest["failed_files_list"] = self.failed_files

    manifest_fd = io.StringIO()
    if self.total_files != self.archived_files:
      manifest_fd.write(self.FILES_SKIPPED_WARNING)
    manifest_fd.write(yaml.safe_dump(manifest).decode("utf-8"))

    manifest_fd.seek(0)
    st = os.stat_result((0o644, 0, 0, 0, 0, 0, len(manifest_fd.getvalue()), 0,
                         0, 0))

    for chunk in self.archive_generator.WriteFromFD(
        manifest_fd, os.path.join(self.prefix, "MANIFEST"), st=st):
      yield chunk

  def _GenerateClientInfo(self, client_fd):
    """Yields chucks of archive information for given client."""
    summary_dict = client_fd.GetSummary().ToPrimitiveDict(
        serialize_leaf_fields=True)
    summary = yaml.safe_dump(summary_dict).decode("utf-8")

    client_info_path = os.path.join(self.prefix, client_fd.urn.Basename(),
                                    "client_info.yaml")
    st = os.stat_result((0o644, 0, 0, 0, 0, 0, len(summary), 0, 0, 0))
    yield self.archive_generator.WriteFileHeader(client_info_path, st=st)
    yield self.archive_generator.WriteFileChunk(summary)
    yield self.archive_generator.WriteFileFooter()

  def Generate(self, items, token=None):
    """Generates archive from a given collection.

    Iterates the collection and generates an archive by yielding contents
    of every referenced AFF4Stream.

    Args:
      items: Iterable with items that point to aff4 paths.
      token: User's ACLToken.

    Yields:
      Binary chunks comprising the generated archive.
    """
    clients = set()
    for fd_urn_batch in collection.Batch(
        self._ItemsToUrns(items), self.BATCH_SIZE):

      fds_to_write = {}
      for fd in aff4.FACTORY.MultiOpen(fd_urn_batch, token=token):
        self.total_files += 1

        # Derive a ClientPath from AFF4 URN to make new and old
        # archive_generator predicate input consistent.
        # TODO(user): This code is clearly hacky and intended to be removed.
        urn_components = fd.urn.Split()
        if urn_components[1:3] != ["fs", "os"]:
          raise AssertionError("URN components are expected to start with "
                               "client, 'fs', 'os'. Got %r" % (urn_components,))

        client_path = db.ClientPath.OS(
            client_id=urn_components[0], components=urn_components[3:])

        if not self.predicate(client_path):
          self.ignored_files.append(utils.SmartUnicode(fd.urn))
          continue

        # Any file-like object with data in AFF4 should inherit AFF4Stream.
        if isinstance(fd, aff4.AFF4Stream):
          urn_components = fd.urn.Split()
          clients.add(rdf_client.ClientURN(urn_components[0]))

          content_path = os.path.join(self.prefix, *urn_components)
          self.archived_files += 1

          # Make sure size of the original file is passed. It's required
          # when output_writer is StreamingTarWriter.
          st = os.stat_result((0o644, 0, 0, 0, 0, 0, fd.size, 0, 0, 0))
          fds_to_write[fd] = (content_path, st)

      if fds_to_write:
        prev_fd = None
        for fd, chunk, exception in aff4.AFF4Stream.MultiStream(fds_to_write):
          if exception:
            logging.exception(exception)

            self.archived_files -= 1
            self.failed_files.append(utils.SmartUnicode(fd.urn))
            continue

          if prev_fd != fd:
            if prev_fd:
              yield self.archive_generator.WriteFileFooter()
            prev_fd = fd

            content_path, st = fds_to_write[fd]
            yield self.archive_generator.WriteFileHeader(content_path, st=st)

          yield self.archive_generator.WriteFileChunk(chunk)

        if self.archive_generator.is_file_write_in_progress:
          yield self.archive_generator.WriteFileFooter()

    if clients:
      for client_urn_batch in collection.Batch(clients, self.BATCH_SIZE):
        for fd in aff4.FACTORY.MultiOpen(
            client_urn_batch, aff4_type=aff4_grr.VFSGRRClient, token=token):
          for chunk in self._GenerateClientInfo(fd):
            yield chunk

    for chunk in self._GenerateDescription():
      yield chunk

    yield self.archive_generator.Close()
