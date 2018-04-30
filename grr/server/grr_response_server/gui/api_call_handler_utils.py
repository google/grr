#!/usr/bin/env python
"""This file contains utility functions used in ApiCallHandler classes."""


import cStringIO
import itertools
import logging
import os
import re
import sys
import zipfile


import yaml

from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import api_utils_pb2
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server.aff4_objects import aff4_grr
from grr.server.grr_response_server.flows.general import export as flow_export


class CollectionArchiveGenerator(object):
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
      prefix: Name of the folder inside the archive that will contain all
          the generated data.
      description: String describing archive's contents. It will be included
          into the auto-generated MANIFEST file. Defaults to
          'Files archive collection'.
      predicate: If not None, only the files matching the predicate will be
          archived, all others will be skipped.
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

    manifest_fd = cStringIO.StringIO()
    if self.total_files != self.archived_files:
      manifest_fd.write(self.FILES_SKIPPED_WARNING)
    manifest_fd.write(yaml.safe_dump(manifest))

    manifest_fd.seek(0)
    st = os.stat_result((0644, 0, 0, 0, 0, 0, len(manifest_fd.getvalue()), 0, 0,
                         0))

    for chunk in self.archive_generator.WriteFromFD(
        manifest_fd, os.path.join(self.prefix, "MANIFEST"), st=st):
      yield chunk

  def _GenerateClientInfo(self, client_fd):
    summary = yaml.safe_dump(
        client_fd.GetSummary().ToPrimitiveDict(serialize_leaf_fields=True))
    client_info_path = os.path.join(self.prefix,
                                    client_fd.urn.Basename(),
                                    "client_info.yaml")
    st = os.stat_result((0644, 0, 0, 0, 0, 0, len(summary), 0, 0, 0))
    yield self.archive_generator.WriteFileHeader(client_info_path, st=st)
    yield self.archive_generator.WriteFileChunk(summary)
    yield self.archive_generator.WriteFileFooter()

  def Generate(self, collection, token=None):
    """Generates archive from a given collection.

    Iterates the collection and generates an archive by yielding contents
    of every referenced AFF4Stream.

    Args:
      collection: Iterable with items that point to aff4 paths.
      token: User's ACLToken.

    Yields:
      Binary chunks comprising the generated archive.
    """
    clients = set()
    for fd_urn_batch in utils.Grouper(
        self._ItemsToUrns(collection), self.BATCH_SIZE):

      fds_to_write = {}
      for fd in aff4.FACTORY.MultiOpen(fd_urn_batch, token=token):
        self.total_files += 1

        if not self.predicate(fd):
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
          st = os.stat_result((0644, 0, 0, 0, 0, 0, fd.size, 0, 0, 0))
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
      for client_urn_batch in utils.Grouper(clients, self.BATCH_SIZE):
        for fd in aff4.FACTORY.MultiOpen(
            client_urn_batch, aff4_type=aff4_grr.VFSGRRClient, token=token):
          for chunk in self._GenerateClientInfo(fd):
            yield chunk

    for chunk in self._GenerateDescription():
      yield chunk

    yield self.archive_generator.Close()


class ApiDataObjectKeyValuePair(rdf_structs.RDFProtoStruct):
  """Defines a proto for returning key value pairs of data objects."""

  protobuf = api_utils_pb2.ApiDataObjectKeyValuePair

  def InitFromKeyValue(self, key, value):
    self.key = key

    # Convert primitive types to rdf values so they can be serialized.
    if isinstance(value, float) and not value.is_integer():
      # TODO(user): Do not convert float values here and mark them invalid
      # later. ATM, we do not have means to properly represent floats. Change
      # this part once we have a RDFFloat implementation.
      pass
    elif rdfvalue.RDFInteger.IsNumeric(value):
      value = rdfvalue.RDFInteger(value)
    elif isinstance(value, basestring):
      value = rdfvalue.RDFString(value)
    elif isinstance(value, bool):
      value = rdfvalue.RDFBool(value)

    if isinstance(value, rdfvalue.RDFValue):
      self.type = value.__class__.__name__
      self.value = value
    else:
      self.invalid = True

    return self

  def GetArgsClass(self):
    try:
      return rdfvalue.RDFValue.GetPlugin(self.type)
    except KeyError:
      raise ValueError("No class found for type %s." % self.type)


class ApiDataObject(rdf_structs.RDFProtoStruct):
  """Defines a proto for returning Data Objects over the API."""

  protobuf = api_utils_pb2.ApiDataObject
  rdf_deps = [
      ApiDataObjectKeyValuePair,
  ]

  def InitFromDataObject(self, data_object):
    for key, value in sorted(data_object.iteritems()):
      item = ApiDataObjectKeyValuePair().InitFromKeyValue(key, value)
      self.items.append(item)

    return self


def FilterCollection(collection, offset, count=0, filter_value=None):
  """Filters an aff4 collection, getting count elements, starting at offset."""

  if offset < 0:
    raise ValueError("Offset needs to be greater than or equal to zero")

  if count < 0:
    raise ValueError("Count needs to be greater than or equal to zero")

  count = count or sys.maxint
  if filter_value:
    index = 0
    items = []
    for item in collection.GenerateItems():
      serialized_item = item.SerializeToString()
      if re.search(re.escape(filter_value), serialized_item, re.I):
        if index >= offset:
          items.append(item)
        index += 1

        if len(items) >= count:
          break
  else:
    items = list(itertools.islice(collection.GenerateItems(offset), count))

  return items
