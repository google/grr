#!/usr/bin/env python
"""Classes for exporting StatEntry."""

import logging
import time
from typing import Iterable, Union

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import mig_paths
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import collection
from grr_response_proto import export_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_server import export
from grr_response_server.export_converters import base
from grr_response_server.export_converters import buffer_reference

try:
  # pylint: disable=g-import-not-at-top
  from verify_sigs import auth_data
  from verify_sigs.asn1 import dn
  # pylint: enable=g-import-not-at-top
except ImportError:
  pass


class ExportedFile(rdf_structs.RDFProtoStruct):
  protobuf = export_pb2.ExportedFile
  rdf_deps = [
      base.ExportedMetadata,
      rdfvalue.RDFDatetimeSeconds,
      rdfvalue.RDFURN,
      rdf_client_fs.StatMode,
  ]


class ExportedRegistryKey(rdf_structs.RDFProtoStruct):
  protobuf = export_pb2.ExportedRegistryKey
  rdf_deps = [
      base.ExportedMetadata,
      rdfvalue.RDFDatetimeSeconds,
      rdfvalue.RDFURN,
  ]


class ExportedArtifactFilesDownloaderResult(rdf_structs.RDFProtoStruct):
  protobuf = export_pb2.ExportedArtifactFilesDownloaderResult
  rdf_deps = [
      ExportedFile,
      base.ExportedMetadata,
      ExportedRegistryKey,
  ]


class StatEntryToExportedFileConverter(base.ExportConverter):
  """Converts StatEntry to ExportedFile."""

  input_rdf_type = rdf_client_fs.StatEntry

  MAX_CONTENT_SIZE = 1024 * 64

  @staticmethod
  def ParseSignedData(signed_data, result):
    """Parses signed certificate data and updates result rdfvalue."""
    try:
      auth_data
    except NameError:
      # Verify_sigs is not available so we can't parse signatures. If you want
      # this functionality, please install the verify-sigs package:
      # https://github.com/anthrotype/verify-sigs
      # TODO(amoser): Make verify-sigs a pip package and add a dependency.
      return

    try:
      try:
        auth = auth_data.AuthData(signed_data.certificate)
      except Exception as e:  # pylint: disable=broad-except
        # If we failed to parse the certificate, we want the user to know it.
        result.cert_hasher_name = "Error parsing certificate: %s" % str(e)
        raise

      result.cert_hasher_name = auth.digest_algorithm().name
      result.cert_program_name = str(auth.program_name)
      result.cert_program_url = str(auth.program_url)
      result.cert_signing_id = str(auth.signing_cert_id)

      try:
        # This fills in auth.cert_chain_head. We ignore Asn1Error because
        # we want to extract as much data as possible, no matter if the
        # certificate has expired or not.
        auth.ValidateCertChains(time.gmtime())
      except auth_data.Asn1Error:
        pass
      result.cert_chain_head_issuer = str(auth.cert_chain_head[2])

      if auth.has_countersignature:
        result.cert_countersignature_chain_head_issuer = str(
            auth.counter_chain_head[2]
        )

      certs = []
      for (issuer, serial), cert in auth.certificates.items():
        subject = cert[0][0]["subject"]
        subject_dn = str(dn.DistinguishedName.TraverseRdn(subject[0]))
        not_before = cert[0][0]["validity"]["notBefore"]
        not_after = cert[0][0]["validity"]["notAfter"]
        not_before_time = not_before.ToPythonEpochTime()
        not_after_time = not_after.ToPythonEpochTime()
        not_before_time_str = time.asctime(time.gmtime(not_before_time))
        not_after_time_str = time.asctime(time.gmtime(not_after_time))

        certs.append(
            dict(
                issuer=issuer,
                serial=serial,
                subject=subject_dn,
                not_before_time=not_before_time_str,
                not_after_time=not_after_time_str,
            )
        )
      result.cert_certificates = str(certs)

    # Verify_sigs library can basically throw all kinds of exceptions so
    # we have to use broad except here.
    except Exception as e:  # pylint: disable=broad-except
      logging.error(e)

  @staticmethod
  def ParseFileHash(hash_obj, result):
    """Parses Hash rdfvalue into ExportedFile's fields."""
    if hash_obj.HasField("md5"):
      result.hash_md5 = str(hash_obj.md5)

    if hash_obj.HasField("sha1"):
      result.hash_sha1 = str(hash_obj.sha1)

    if hash_obj.HasField("sha256"):
      result.hash_sha256 = str(hash_obj.sha256)

    if hash_obj.HasField("pecoff_md5"):
      result.pecoff_hash_md5 = str(hash_obj.pecoff_md5)

    if hash_obj.HasField("pecoff_sha1"):
      result.pecoff_hash_sha1 = str(hash_obj.pecoff_sha1)

    if hash_obj.HasField("signed_data"):
      StatEntryToExportedFileConverter.ParseSignedData(
          hash_obj.signed_data[0], result
      )

  def Convert(self, metadata, stat_entry):
    """Converts StatEntry to ExportedFile.

    Does nothing if StatEntry corresponds to a registry entry and not to a file.

    Args:
      metadata: ExportedMetadata to be used for conversion.
      stat_entry: StatEntry to be converted.

    Returns:
      List or generator with resulting RDFValues. Empty list if StatEntry
      corresponds to a registry entry and not to a file.
    """
    return self.BatchConvert([(metadata, stat_entry)])

  def _RemoveRegistryKeys(self, metadata_value_pairs):
    """Filter out registry keys to operate on files."""
    filtered_pairs = []
    for metadata, stat_entry in metadata_value_pairs:
      # Ignore registry keys.
      if stat_entry.pathspec.pathtype != rdf_paths.PathSpec.PathType.REGISTRY:
        filtered_pairs.append((metadata, stat_entry))

    return filtered_pairs

  def _CreateExportedFile(self, metadata, stat_entry):
    return ExportedFile(
        metadata=metadata,
        urn=stat_entry.AFF4Path(metadata.client_urn),
        basename=stat_entry.pathspec.Basename(),
        st_mode=stat_entry.st_mode,
        st_ino=stat_entry.st_ino,
        st_dev=stat_entry.st_dev,
        st_nlink=stat_entry.st_nlink,
        st_uid=stat_entry.st_uid,
        st_gid=stat_entry.st_gid,
        st_size=stat_entry.st_size,
        st_atime=stat_entry.st_atime,
        st_mtime=stat_entry.st_mtime,
        st_ctime=stat_entry.st_ctime,
        st_btime=stat_entry.st_btime,
        st_blocks=stat_entry.st_blocks,
        st_blksize=stat_entry.st_blksize,
        st_rdev=stat_entry.st_rdev,
        symlink=stat_entry.symlink,
    )

  _BATCH_SIZE = 5000

  def _BatchConvert(self, metadata_value_pairs):
    """Convert given batch of metadata value pairs."""
    filtered_pairs = self._RemoveRegistryKeys(metadata_value_pairs)
    for fp_batch in collection.Batch(filtered_pairs, self._BATCH_SIZE):
      for metadata, stat_entry in fp_batch:
        result = self._CreateExportedFile(metadata, stat_entry)
        yield result

  def BatchConvert(self, metadata_value_pairs):
    """Converts a batch of StatEntry value to ExportedFile values at once.

    Args:
      metadata_value_pairs: a list or a generator of tuples (metadata, value),
        where metadata is ExportedMetadata to be used for conversion and value
        is a StatEntry to be converted.

    Yields:
      Resulting ExportedFile values. Empty list is a valid result and means that
      conversion wasn't possible.
    """
    result_generator = self._BatchConvert(metadata_value_pairs)

    for r in result_generator:
      yield r


class StatEntryToExportedFileConverterProto(
    base.ExportConverterProto[jobs_pb2.StatEntry]
):
  """Converts StatEntry protos to ExportedFile protos."""

  input_proto_type = jobs_pb2.StatEntry
  output_proto_types = (export_pb2.ExportedFile,)

  _BATCH_SIZE = 5000

  def BatchConvert(
      self,
      metadata_value_pairs: Iterable[
          tuple[export_pb2.ExportedMetadata, jobs_pb2.StatEntry]
      ],
  ) -> Iterable[export_pb2.ExportedFile]:
    """Converts a batch of StatEntry protos to ExportedFile protos.

    Args:
      metadata_value_pairs: An iterable of tuples (metadata, value), where
        metadata is ExportedMetadata to be used for conversion and value is a
        StatEntry to be converted.

    Yields:
      Resulting ExportedFile values.
    """
    for metadata, stat_entry_proto in metadata_value_pairs:
      # Ignore registry keys.
      if (
          stat_entry_proto.pathspec.pathtype
          != jobs_pb2.PathSpec.PathType.REGISTRY
      ):
        yield GetExportedFileFromStatEntry(metadata, stat_entry_proto)

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      stat_entry_proto: jobs_pb2.StatEntry,
  ) -> Iterable[export_pb2.ExportedFile]:
    return self.BatchConvert([(metadata, stat_entry_proto)])


def GetExportedFileFromStatEntry(
    metadata: export_pb2.ExportedMetadata,
    stat_entry_proto: jobs_pb2.StatEntry,
) -> export_pb2.ExportedFile:
  """Creates an ExportedFile proto from a StatEntry proto.

  Args:
    metadata: ExportedMetadata to be added to the ExportedFile proto.
    stat_entry_proto: The StatEntry proto to convert.

  Returns:
    An ExportedFile proto.
  """
  rdf_pathspec = mig_paths.ToRDFPathSpec(stat_entry_proto.pathspec)
  client_urn = rdfvalue.RDFURN(metadata.client_urn)
  path_urn = rdf_pathspec.AFF4Path(client_urn)

  exported_file = export_pb2.ExportedFile(
      metadata=metadata,
      urn=path_urn.SerializeToWireFormat(),
      basename=rdf_pathspec.Basename(),
      st_mode=stat_entry_proto.st_mode,
      st_ino=stat_entry_proto.st_ino,
      st_dev=stat_entry_proto.st_dev,
      st_nlink=stat_entry_proto.st_nlink,
      st_uid=stat_entry_proto.st_uid,
      st_gid=stat_entry_proto.st_gid,
      st_size=stat_entry_proto.st_size,
      # TODO: Add human-friendly timestamp fields to the exported
      # proto.
      st_atime=stat_entry_proto.st_atime,
      st_mtime=stat_entry_proto.st_mtime,
      st_ctime=stat_entry_proto.st_ctime,
      st_btime=stat_entry_proto.st_btime,
      st_blocks=stat_entry_proto.st_blocks,
      st_blksize=stat_entry_proto.st_blksize,
      st_rdev=stat_entry_proto.st_rdev,
      symlink=stat_entry_proto.symlink,
  )

  return exported_file


def AddHashToExportedFile(
    hash_obj: jobs_pb2.Hash, result: export_pb2.ExportedFile
) -> None:
  """Parses Hash proto into ExportedFile's fields."""
  if hash_obj.md5:
    result.hash_md5 = hash_obj.md5.hex()

  if hash_obj.sha1:
    result.hash_sha1 = hash_obj.sha1.hex()

  if hash_obj.sha256:
    result.hash_sha256 = hash_obj.sha256.hex()

  if hash_obj.pecoff_md5:
    result.pecoff_hash_md5 = hash_obj.pecoff_md5.hex()

  if hash_obj.pecoff_sha1:
    result.pecoff_hash_sha1 = hash_obj.pecoff_sha1.hex()


class StatEntryToExportedRegistryKeyConverter(base.ExportConverter):
  """Converts StatEntry to ExportedRegistryKey."""

  input_rdf_type = rdf_client_fs.StatEntry

  def Convert(self, metadata: base.ExportedMetadata, stat_entry):
    """Converts StatEntry to ExportedRegistryKey.

    Does nothing if StatEntry corresponds to a file and not a registry entry.

    Args:
      metadata: ExportedMetadata to be used for conversion.
      stat_entry: StatEntry to be converted.

    Returns:
      List or generator with resulting RDFValues. Empty list if StatEntry
      corresponds to a file and not to a registry entry.
    """
    if stat_entry.pathspec.pathtype != rdf_paths.PathSpec.PathType.REGISTRY:
      return []

    result = ExportedRegistryKey(
        metadata=metadata,
        urn=stat_entry.AFF4Path(metadata.client_urn),
        last_modified=stat_entry.st_mtime,
    )

    if stat_entry.HasField("registry_type") and stat_entry.HasField(
        "registry_data"
    ):

      result.type = stat_entry.registry_type

      # `data` can be value of arbitrary type and we need to return `bytes`. So,
      # if it is `bytes` we just pass it through. If it is not, we stringify it
      # to some human-readable form and turn it to `bytes` by UTF-8 encoding.
      data = stat_entry.registry_data.GetValue()
      if isinstance(data, bytes):
        result.data = data
      else:
        result.data = str(data).encode("utf-8")

    return [result]


class StatEntryToExportedRegistryKeyConverterProto(
    base.ExportConverterProto[jobs_pb2.StatEntry]
):
  """Converts StatEntry protos to ExportedRegistryKey protos."""

  input_proto_type = jobs_pb2.StatEntry
  output_proto_types = (export_pb2.ExportedRegistryKey,)

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      stat_entry: jobs_pb2.StatEntry,
  ) -> Iterable[export_pb2.ExportedRegistryKey]:
    """Converts StatEntry to ExportedRegistryKey.

    Args:
      metadata: ExportedMetadata to be used for conversion.
      stat_entry: StatEntry to be converted.

    Returns:
      List or generator with resulting RDFValues. Empty list if StatEntry
      corresponds to a file and not to a registry entry.
    """
    if stat_entry.pathspec.pathtype != jobs_pb2.PathSpec.PathType.REGISTRY:
      return []

    rdf_pathspec = mig_paths.ToRDFPathSpec(stat_entry.pathspec)
    client_urn = rdfvalue.RDFURN(metadata.client_urn)
    path_urn = rdf_pathspec.AFF4Path(client_urn)

    result = export_pb2.ExportedRegistryKey(
        metadata=metadata,
        urn=path_urn.SerializeToWireFormat(),
        last_modified=stat_entry.st_mtime,
    )

    if stat_entry.HasField("registry_type") and stat_entry.HasField(
        "registry_data"
    ):
      result.type = stat_entry.registry_type
      result.data = stat_entry.registry_data.data

    return [result]


class FileFinderResultConverter(StatEntryToExportedFileConverter):
  """Export converter for FileFinderResult instances."""

  input_rdf_type = rdf_file_finder.FileFinderResult

  def _SeparateTypes(self, metadata_value_pairs):
    """Separate files, registry keys, grep matches."""
    registry_pairs = []
    file_pairs = []
    match_pairs = []
    for metadata, result in metadata_value_pairs:
      if (
          result.stat_entry.pathspec.pathtype
          == rdf_paths.PathSpec.PathType.REGISTRY
      ):
        registry_pairs.append((metadata, result.stat_entry))
      else:
        file_pairs.append((metadata, result))

      for match in result.matches:
        if match.HasField("pathspec"):
          match_to_add = match
        else:
          match_to_add = match.Copy()
          match_to_add.pathspec = result.stat_entry.pathspec

        match_pairs.append((metadata, match_to_add))

    return registry_pairs, file_pairs, match_pairs

  def BatchConvert(self, metadata_value_pairs):
    """Convert FileFinder results.

    Args:
      metadata_value_pairs: array of ExportedMetadata and rdfvalue tuples.

    Yields:
      ExportedFile, ExportedRegistryKey, or ExportedMatch

    FileFinderResult objects have 3 types of results that need to be handled
    separately. Files, registry keys, and grep matches. The file results are
    similar to statentry exports, and share some code, but different because we
    already have the hash available without having to go back to the database to
    retrieve it from the aff4 object.
    """
    result_generator = self._BatchConvert(metadata_value_pairs)

    for r in result_generator:
      yield r

  _BATCH_SIZE = 5000

  def _BatchConvert(self, metadata_value_pairs):
    registry_pairs, file_pairs, match_pairs = self._SeparateTypes(
        metadata_value_pairs
    )
    for fp_batch in collection.Batch(file_pairs, self._BATCH_SIZE):
      for metadata, ff_result in fp_batch:
        result = self._CreateExportedFile(metadata, ff_result.stat_entry)

        # FileFinderResult has hashes in "hash_entry" attribute which is not
        # passed to ConvertValuesWithMetadata call. We have to process these
        # explicitly here.
        self.ParseFileHash(ff_result.hash_entry, result)
        yield result

    # Now export the registry keys
    for result in export.ConvertValuesWithMetadata(
        registry_pairs, options=self.options
    ):
      yield result

    # Now export the grep matches.
    for result in export.ConvertValuesWithMetadata(
        match_pairs, options=self.options
    ):
      yield result

  def Convert(self, metadata, result):
    return self.BatchConvert([(metadata, result)])


class FileFinderResultConverterProto(
    base.ExportConverterProto[flows_pb2.FileFinderResult]
):
  """Export converter for FileFinderResult protos."""

  input_proto_type = flows_pb2.FileFinderResult
  output_proto_types = (
      export_pb2.ExportedFile,
      export_pb2.ExportedRegistryKey,
      export_pb2.ExportedMatch,
  )

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      result: flows_pb2.FileFinderResult,
  ) -> Iterable[
      Union[
          export_pb2.ExportedFile,
          export_pb2.ExportedRegistryKey,
          export_pb2.ExportedMatch,
      ]
  ]:
    """Converts a FileFinderResult.

    Args:
      metadata: ExportedMetadata to be used for conversion.
      result: FileFinderResult to be converted.

    Yields:
      ExportedFile, ExportedRegistryKey, or ExportedMatch values.
    """
    if (
        result.stat_entry.pathspec.pathtype
        == jobs_pb2.PathSpec.PathType.REGISTRY
    ):
      registry_converter = StatEntryToExportedRegistryKeyConverterProto()
      yield from registry_converter.Convert(metadata, result.stat_entry)
    else:
      exported_file = GetExportedFileFromStatEntry(metadata, result.stat_entry)

      # FileFinderResult has hashes in "hash_entry" attribute which is not
      # passed to GetExportedFileFromStatEntry call. We have to process these
      # explicitly here.
      AddHashToExportedFile(result.hash_entry, exported_file)
      yield exported_file

    # Now export the grep matches.
    match_converter = (
        buffer_reference.BufferReferenceToExportedMatchConverterProto()
    )
    for buffer_ref in result.matches:
      if buffer_ref.HasField("pathspec"):
        match_buffer = buffer_ref
      else:
        match_buffer = jobs_pb2.BufferReference()
        match_buffer.CopyFrom(buffer_ref)
        match_buffer.pathspec.CopyFrom(result.stat_entry.pathspec)

      yield from match_converter.Convert(metadata, match_buffer)


class CollectMultipleFilesResultToExportedFileConverterProto(
    base.ExportConverterProto[flows_pb2.CollectMultipleFilesResult]
):
  """Export converter for CollectMultipleFilesResult protos."""

  input_proto_type = flows_pb2.CollectMultipleFilesResult
  output_proto_types = (export_pb2.ExportedFile,)

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      result: flows_pb2.CollectMultipleFilesResult,
  ) -> Iterable[export_pb2.ExportedFile]:
    """Converts a CollectMultipleFilesResult.

    Args:
      metadata: ExportedMetadata to be used for conversion.
      result: CollectMultipleFilesResult to be converted.

    Yields:
      ExportedFile values.
    """
    # CollectMultipleFiles flows do not support registry keys, so this if should
    # never trigger.
    if result.stat.pathspec.pathtype == jobs_pb2.PathSpec.PathType.REGISTRY:
      return

    exported_file = GetExportedFileFromStatEntry(metadata, result.stat)
    AddHashToExportedFile(result.hash, exported_file)
    yield exported_file


class CollectFilesByKnownPathResultToExportedFileConverterProto(
    base.ExportConverterProto[flows_pb2.CollectFilesByKnownPathResult]
):
  """Export converter for CollectFilesByKnownPathResult protos."""

  input_proto_type = flows_pb2.CollectFilesByKnownPathResult
  output_proto_types = (export_pb2.ExportedFile,)

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      result: flows_pb2.CollectFilesByKnownPathResult,
  ) -> Iterable[export_pb2.ExportedFile]:
    """Converts a CollectFilesByKnownPathResult.

    Args:
      metadata: ExportedMetadata to be used for conversion.
      result: CollectFilesByKnownPathResult to be converted.

    Yields:
      ExportedFile values.
    """
    # CollectFilesByKnownPath flow does not support registry keys, so this if
    # should never trigger.
    if result.stat.pathspec.pathtype == jobs_pb2.PathSpec.PathType.REGISTRY:
      return

    exported_file = GetExportedFileFromStatEntry(metadata, result.stat)
    AddHashToExportedFile(result.hash, exported_file)
    yield exported_file
