#!/usr/bin/env python
"""Classes for exporting StatEntry."""

from typing import Iterable, Union

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import mig_paths
from grr_response_proto import export_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_server.export_converters import base


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
      # TODO - Add human-friendly timestamp fields to the exported
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
