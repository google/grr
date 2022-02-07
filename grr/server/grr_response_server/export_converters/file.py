#!/usr/bin/env python
"""Classes for exporting StatEntry."""
import hashlib
import logging
import time

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import collection
from grr_response_proto import export_pb2
from grr_response_server import export
from grr_response_server import file_store
from grr_response_server.databases import db
from grr_response_server.export_converters import base
from grr_response_server.flows.general import collectors as flow_collectors

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
            auth.counter_chain_head[2])

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
                not_after_time=not_after_time_str))
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
      StatEntryToExportedFileConverter.ParseSignedData(hash_obj.signed_data[0],
                                                       result)

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
        symlink=stat_entry.symlink)

  _BATCH_SIZE = 5000

  def _BatchConvert(self, metadata_value_pairs):
    """Convert given batch of metadata value pairs."""
    filtered_pairs = self._RemoveRegistryKeys(metadata_value_pairs)
    for fp_batch in collection.Batch(filtered_pairs, self._BATCH_SIZE):

      if self.options.export_files_contents:
        client_paths = set()

        for metadata, stat_entry in fp_batch:
          # TODO(user): Deprecate client_urn in ExportedMetadata in favor of
          # client_id (to be added).
          client_paths.add(
              db.ClientPath.FromPathSpec(metadata.client_urn.Basename(),
                                         stat_entry.pathspec))

        data_by_path = {}
        for chunk in file_store.StreamFilesChunks(
            client_paths, max_size=self.MAX_CONTENT_SIZE):
          data_by_path.setdefault(chunk.client_path, []).append(chunk.data)

      for metadata, stat_entry in fp_batch:
        result = self._CreateExportedFile(metadata, stat_entry)
        clientpath = db.ClientPath.FromPathSpec(metadata.client_urn.Basename(),
                                                stat_entry.pathspec)

        if self.options.export_files_contents:
          try:
            data = data_by_path[clientpath]
            result.content = b"".join(data)[:self.MAX_CONTENT_SIZE]
            result.content_sha256 = hashlib.sha256(result.content).hexdigest()
          except KeyError:
            pass

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
        last_modified=stat_entry.st_mtime)

    if (stat_entry.HasField("registry_type") and
        stat_entry.HasField("registry_data")):

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


class FileFinderResultConverter(StatEntryToExportedFileConverter):
  """Export converter for FileFinderResult instances."""

  input_rdf_type = rdf_file_finder.FileFinderResult

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    # We only need to open the file if we're going to export the contents, we
    # already have the hash in the FileFinderResult
    self.open_file_for_read = self.options.export_files_contents

  def _SeparateTypes(self, metadata_value_pairs):
    """Separate files, registry keys, grep matches."""
    registry_pairs = []
    file_pairs = []
    match_pairs = []
    for metadata, result in metadata_value_pairs:
      if (result.stat_entry.pathspec.pathtype ==
          rdf_paths.PathSpec.PathType.REGISTRY):
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
        metadata_value_pairs)
    for fp_batch in collection.Batch(file_pairs, self._BATCH_SIZE):

      if self.options.export_files_contents:
        pathspec_by_client_path = {}
        for metadata, ff_result in fp_batch:
          # TODO(user): Deprecate client_urn in ExportedMetadata in favor of
          # client_id (to be added).
          client_path = db.ClientPath.FromPathSpec(
              metadata.client_urn.Basename(), ff_result.stat_entry.pathspec)
          pathspec_by_client_path[client_path] = ff_result.stat_entry.pathspec

        data_by_pathspec = {}
        for chunk in file_store.StreamFilesChunks(
            pathspec_by_client_path, max_size=self.MAX_CONTENT_SIZE):
          pathspec = pathspec_by_client_path[chunk.client_path]
          data_by_pathspec.setdefault(pathspec.CollapsePath(),
                                      []).append(chunk.data)

      for metadata, ff_result in fp_batch:
        result = self._CreateExportedFile(metadata, ff_result.stat_entry)

        # FileFinderResult has hashes in "hash_entry" attribute which is not
        # passed to ConvertValuesWithMetadata call. We have to process these
        # explicitly here.
        self.ParseFileHash(ff_result.hash_entry, result)

        if self.options.export_files_contents:
          try:
            data = data_by_pathspec[
                ff_result.stat_entry.pathspec.CollapsePath()]
            result.content = b"".join(data)[:self.MAX_CONTENT_SIZE]
            result.content_sha256 = hashlib.sha256(result.content).hexdigest()
          except KeyError:
            pass

        yield result

    # Now export the registry keys
    for result in export.ConvertValuesWithMetadata(
        registry_pairs, options=self.options):
      yield result

    # Now export the grep matches.
    for result in export.ConvertValuesWithMetadata(
        match_pairs, options=self.options):
      yield result

  def Convert(self, metadata, result):
    return self.BatchConvert([(metadata, result)])


class ArtifactFilesDownloaderResultConverter(base.ExportConverter):
  """Converts ArtifactFilesDownloaderResult to its exported version."""

  input_rdf_type = flow_collectors.ArtifactFilesDownloaderResult

  def GetExportedResult(self, original_result, converter, metadata=None):
    """Converts original result via given converter.."""

    exported_results = list(
        converter.Convert(metadata or base.ExportedMetadata(), original_result))

    if not exported_results:
      raise export.ExportError("Got 0 exported result when a single one "
                               "was expected.")

    if len(exported_results) > 1:
      raise export.ExportError("Got > 1 exported results when a single "
                               "one was expected, seems like a logical bug.")

    return exported_results[0]

  def IsRegistryStatEntry(self, original_result):
    """Checks if given RDFValue is a registry StatEntry."""
    return (original_result.pathspec.pathtype ==
            rdf_paths.PathSpec.PathType.REGISTRY)

  def IsFileStatEntry(self, original_result):
    """Checks if given RDFValue is a file StatEntry."""
    return (original_result.pathspec.pathtype in [
        rdf_paths.PathSpec.PathType.OS,
        rdf_paths.PathSpec.PathType.TSK,
        rdf_paths.PathSpec.PathType.NTFS,
    ])

  def BatchConvert(self, metadata_value_pairs):
    metadata_value_pairs = list(metadata_value_pairs)

    results = []
    for metadata, value in metadata_value_pairs:
      original_result = value.original_result

      if not isinstance(original_result, rdf_client_fs.StatEntry):
        continue

      if self.IsRegistryStatEntry(original_result):
        exported_registry_key = self.GetExportedResult(
            original_result,
            StatEntryToExportedRegistryKeyConverter(),
            metadata=metadata)
        result = ExportedArtifactFilesDownloaderResult(
            metadata=metadata, original_registry_key=exported_registry_key)
      elif self.IsFileStatEntry(original_result):
        exported_file = self.GetExportedResult(
            original_result,
            StatEntryToExportedFileConverter(),
            metadata=metadata)
        result = ExportedArtifactFilesDownloaderResult(
            metadata=metadata, original_file=exported_file)
      else:
        # TODO(user): if original_result is not a registry key or a file,
        # we should still somehow export the data, otherwise the user will get
        # an impression that there was nothing to export at all.
        continue

      if value.HasField("found_pathspec"):
        result.found_path = value.found_pathspec.CollapsePath()

      downloaded_file = None
      if value.HasField("downloaded_file"):
        downloaded_file = value.downloaded_file

      results.append((result, downloaded_file))

    files_batch = [(r.metadata, f) for r, f in results if f is not None]
    files_converter = StatEntryToExportedFileConverter(options=self.options)
    converted_files = files_converter.BatchConvert(files_batch)
    converted_files_map = dict((f.urn, f) for f in converted_files)

    for result, downloaded_file in results:
      if downloaded_file:
        aff4path = downloaded_file.AFF4Path(result.metadata.client_urn)
        if aff4path in converted_files_map:
          result.downloaded_file = converted_files_map[aff4path]

      yield result

    # Feed all original results into the export pipeline. There are 2 good
    # reasons to do this:
    # * Export output of ArtifactFilesDownloader flow will be similar to export
    #   output of other file-related flows. I.e. it will produce
    #   ExportedFile entries and ExportedRegistryKey entries and what not, but
    #   in addition it will also generate ExportedArtifactFilesDownloaderResult
    #   entries, that one can use to understand how and where file paths
    #   were detected and how file paths detection algorithm can be possibly
    #   improved.
    # * ExportedArtifactFilesDownloaderResult can only be generated if original
    #   value is a StatEntry. However, original value may be anything, and no
    #   matter what type it has, we want it in the export output.
    original_pairs = [(m, v.original_result) for m, v in metadata_value_pairs]
    for result in export.ConvertValuesWithMetadata(
        original_pairs, options=None):
      yield result

  def Convert(self, metadata, value):
    """Converts a single ArtifactFilesDownloaderResult."""

    for r in self.BatchConvert([(metadata, value)]):
      yield r
