#!/usr/bin/env python
import binascii
import os

from absl import app
from absl.testing import absltest

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_proto import export_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_server import data_store
from grr_response_server.databases import db
from grr_response_server.export_converters import buffer_reference
from grr_response_server.export_converters import file
from grr_response_server.flows.general import file_finder
from grr_response_server.rdfvalues import mig_objects
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import action_mocks
from grr.test_lib import export_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


class StatEntryToExportedFileConverterTest(export_test_lib.ExportTestBase):
  """Tests for StatEntryToExportedFileConverter."""

  def testStatEntryToExportedFileConverterWithMissingAFF4File(self):
    stat = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="/some/path", pathtype=rdf_paths.PathSpec.PathType.OS
        ),
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892,
        st_btime=1331331331,
    )

    converter = file.StatEntryToExportedFileConverter()
    results = list(converter.Convert(self.metadata, stat))

    self.assertLen(results, 1)
    self.assertEqual(results[0].basename, "path")
    self.assertEqual(
        results[0].urn, "aff4:/%s/fs/os/some/path" % self.client_id
    )
    self.assertEqual(results[0].st_mode, 33184)
    self.assertEqual(results[0].st_ino, 1063090)
    self.assertEqual(results[0].st_atime, 1336469177)
    self.assertEqual(results[0].st_mtime, 1336129892)
    self.assertEqual(results[0].st_ctime, 1336129892)
    self.assertEqual(results[0].st_btime, 1331331331)

    self.assertFalse(results[0].HasField("content"))
    self.assertFalse(results[0].HasField("content_sha256"))
    self.assertFalse(results[0].HasField("hash_md5"))
    self.assertFalse(results[0].HasField("hash_sha1"))
    self.assertFalse(results[0].HasField("hash_sha256"))

  def testStatEntryToExportedFileConverterWithFetchedAFF4File(self):
    # No matter the flow, the intention of the test is making sure that
    # even if the file is fetched, it's not exported by default.
    # So it's relevant to have:
    #  - blobs in blobstore
    #  - hashes in file store
    #  - path info in the database
    path = db.ClientPath.TSK(self.client_id, ["foo", "bar"])
    vfs_test_lib.CreateFile(path, b"foo-TSK")

    proto_path_info = data_store.REL_DB.ReadPathInfo(
        self.client_id,
        rdf_objects.PathInfo.PathType.TSK,
        components=("foo", "bar"),
    )
    path_info = mig_objects.ToRDFPathInfo(proto_path_info)
    stat = path_info.stat_entry
    self.assertTrue(stat)

    converter = file.StatEntryToExportedFileConverter()
    results = list(converter.Convert(self.metadata, stat))

    self.assertLen(results, 1)
    self.assertEqual(results[0].basename, "bar")
    urn = "aff4:/%s/fs/tsk%s" % (self.client_id, "/foo/bar")
    self.assertEqual(results[0].urn, urn)

    # Check that by default file contents are not exported
    self.assertFalse(results[0].content)
    self.assertFalse(results[0].content_sha256)
    self.assertEqual("", results[0].metadata.annotations)

  def testStatEntryToExportedFileConverterWithHashedAFF4File(self):
    # No matter the flow, the intention of the test is making sure that
    # even if the file is fetched, it's not exported by default.
    # So it's relevant to have:
    #  - blobs in blobstore
    #  - hashes in file store
    #  - path info in the database
    path = db.ClientPath.TSK(self.client_id, ["foo", "bar"])
    vfs_test_lib.CreateFile(path, b"foo-TSK")

    proto_path_info = data_store.REL_DB.ReadPathInfo(
        self.client_id,
        rdf_objects.PathInfo.PathType.TSK,
        components=("foo", "bar"),
    )
    path_info = mig_objects.ToRDFPathInfo(proto_path_info)
    hash_value = path_info.hash_entry

    self.assertTrue(hash_value)
    self.assertTrue(path_info.stat_entry)

    converter = file.StatEntryToExportedFileConverter()
    results = list(converter.Convert(self.metadata, path_info.stat_entry))

    # Even though the file has a hash, it's not stored in StatEntry and
    # doesn't influence the result. Note: this is a change in behavior.
    # Previously StatEntry exporter was opening corresponding file objects
    # and reading hashes from these objects. This approach was questionable
    # at best, since there was no guarantee that hashes actually corresponded
    # to files in question.
    self.assertFalse(results[0].hash_md5)
    self.assertFalse(results[0].hash_sha1)
    self.assertFalse(results[0].hash_sha256)

  def testStatEntryToExportedFileConverterWithLargeNumbers(self):
    # One over uint32 (max value is 2**32 - 1)
    one_over_32 = 2**32
    # Max uint64
    max_64 = (2**64) - 1

    stat = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="/some/path", pathtype=rdf_paths.PathSpec.PathType.OS
        ),
        st_mode=one_over_32,
        st_ino=max_64,
        st_dev=one_over_32,
        st_nlink=max_64,
        st_size=one_over_32,
        st_atime=max_64,
        st_mtime=one_over_32,
        st_ctime=max_64,
        st_btime=one_over_32,
        st_blocks=max_64,
        st_blksize=one_over_32,
        st_rdev=max_64,
    )

    converter = file.StatEntryToExportedFileConverter()
    results = list(converter.Convert(self.metadata, stat))

    self.assertLen(results, 1)
    rdf_result = results[0]
    self.assertEqual(rdf_result.basename, "path")
    self.assertEqual(rdf_result.urn, f"aff4:/{self.client_id}/fs/os/some/path")
    self.assertEqual(rdf_result.st_mode, one_over_32)
    self.assertEqual(rdf_result.st_ino, max_64)
    self.assertEqual(rdf_result.st_dev, one_over_32)
    self.assertEqual(rdf_result.st_nlink, max_64)
    self.assertEqual(rdf_result.st_size, one_over_32)
    self.assertEqual(rdf_result.st_atime, max_64)
    self.assertEqual(rdf_result.st_mtime, one_over_32)
    self.assertEqual(rdf_result.st_ctime, max_64)
    self.assertEqual(rdf_result.st_btime, one_over_32)
    self.assertEqual(rdf_result.st_blocks, max_64)
    self.assertEqual(rdf_result.st_blksize, one_over_32)
    self.assertEqual(rdf_result.st_rdev, max_64)

    proto_result = rdf_result.AsPrimitiveProto()
    self.assertEqual(proto_result.basename, "path")
    self.assertEqual(
        proto_result.urn, f"aff4:/{self.client_id}/fs/os/some/path"
    )
    self.assertEqual(proto_result.st_mode, one_over_32)
    self.assertEqual(proto_result.st_ino, max_64)
    self.assertEqual(proto_result.st_dev, one_over_32)
    self.assertEqual(proto_result.st_nlink, max_64)
    self.assertEqual(proto_result.st_size, one_over_32)
    self.assertEqual(proto_result.st_atime, max_64)
    self.assertEqual(proto_result.st_mtime, one_over_32)
    self.assertEqual(proto_result.st_ctime, max_64)
    self.assertEqual(proto_result.st_btime, one_over_32)
    self.assertEqual(proto_result.st_blocks, max_64)
    self.assertEqual(proto_result.st_blksize, one_over_32)
    self.assertEqual(proto_result.st_rdev, max_64)

  def testExportedFileConverterIgnoresRegistryKeys(self):
    stat = rdf_client_fs.StatEntry(
        st_mode=32768,
        st_size=51,
        st_mtime=1247546054,
        pathspec=rdf_paths.PathSpec(
            path=(
                "/HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/"
                "CurrentVersion/Run/Sidebar"
            ),
            pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
        ),
    )

    converter = file.StatEntryToExportedFileConverter()
    results = list(converter.Convert(self.metadata, stat))
    self.assertFalse(results)


class StatEntryToExportedFileConverterProtoTest(absltest.TestCase):
  """Tests for StatEntryToExportedFileConverterProto."""

  def setUp(self):
    super().setUp()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testStatEntryToExportedFileConverterProtoBasicCase(self):
    stat = jobs_pb2.StatEntry(
        pathspec=jobs_pb2.PathSpec(
            path="/some/path", pathtype=jobs_pb2.PathSpec.PathType.OS
        ),
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129893,
        st_btime=1331331331,
    )

    converter = file.StatEntryToExportedFileConverterProto()
    results = list(converter.Convert(self.metadata_proto, stat))

    self.assertLen(results, 1)
    self.assertEqual(results[0].basename, "path")
    self.assertEqual(results[0].urn, f"aff4:/{self.client_id}/fs/os/some/path")
    self.assertEqual(results[0].st_mode, 33184)
    self.assertEqual(results[0].st_ino, 1063090)
    self.assertEqual(results[0].st_atime, 1336469177)
    self.assertEqual(results[0].st_mtime, 1336129892)
    self.assertEqual(results[0].st_ctime, 1336129893)
    self.assertEqual(results[0].st_btime, 1331331331)

    self.assertFalse(results[0].HasField("content"))
    self.assertFalse(results[0].HasField("content_sha256"))
    self.assertFalse(results[0].HasField("hash_md5"))
    self.assertFalse(results[0].HasField("hash_sha1"))
    self.assertFalse(results[0].HasField("hash_sha256"))

  def testStatEntryToExportedFileConverterProtoWithLargeNumbers(self):
    # One over uint32 (max value is 2**32 - 1)
    one_over_32 = 2**32
    # Max uint64
    max_64 = (2**64) - 1

    stat = jobs_pb2.StatEntry(
        pathspec=jobs_pb2.PathSpec(
            path="/some/path", pathtype=jobs_pb2.PathSpec.PathType.OS
        ),
        st_mode=one_over_32,
        st_ino=max_64,
        st_dev=one_over_32,
        st_nlink=max_64,
        st_size=one_over_32,
        st_atime=max_64,
        st_mtime=one_over_32,
        st_ctime=max_64,
        st_btime=one_over_32,
        st_blocks=max_64,
        st_blksize=one_over_32,
        st_rdev=max_64,
    )

    converter = file.StatEntryToExportedFileConverterProto()
    results = list(converter.Convert(self.metadata_proto, stat))
    self.assertLen(results, 1)
    proto_result = results[0]
    self.assertEqual(proto_result.basename, "path")
    self.assertEqual(
        proto_result.urn, f"aff4:/{self.client_id}/fs/os/some/path"
    )
    self.assertEqual(proto_result.st_mode, one_over_32)
    self.assertEqual(proto_result.st_ino, max_64)
    self.assertEqual(proto_result.st_dev, one_over_32)
    self.assertEqual(proto_result.st_nlink, max_64)
    self.assertEqual(proto_result.st_size, one_over_32)
    self.assertEqual(proto_result.st_atime, max_64)
    self.assertEqual(proto_result.st_mtime, one_over_32)
    self.assertEqual(proto_result.st_ctime, max_64)
    self.assertEqual(proto_result.st_btime, one_over_32)
    self.assertEqual(proto_result.st_blocks, max_64)
    self.assertEqual(proto_result.st_blksize, one_over_32)
    self.assertEqual(proto_result.st_rdev, max_64)

  def testExportedFileConverterProtoIgnoresRegistryKeys(self):
    stat = jobs_pb2.StatEntry(
        st_mode=32768,
        st_size=51,
        st_mtime=1247546054,
        pathspec=jobs_pb2.PathSpec(
            path=(
                "/HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/"
                "CurrentVersion/Run/Sidebar"
            ),
            pathtype=jobs_pb2.PathSpec.PathType.REGISTRY,
        ),
    )

    converter = file.StatEntryToExportedFileConverterProto()
    results = list(converter.Convert(self.metadata_proto, stat))
    self.assertFalse(results)


class StatEntryToExportedRegistryKeyConverterTest(
    export_test_lib.ExportTestBase
):
  """Tests for StatEntryToExportedRegistryKeyConverter."""

  def testStatEntryToExportedRegistryKeyConverter(self):
    stat = rdf_client_fs.StatEntry(
        st_mode=32768,
        st_size=51,
        st_mtime=1247546054,
        registry_type=rdf_client_fs.StatEntry.RegistryType.REG_EXPAND_SZ,
        pathspec=rdf_paths.PathSpec(
            path=(
                "/HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/"
                "CurrentVersion/Run/Sidebar"
            ),
            pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
        ),
        registry_data=rdf_protodict.DataBlob(string="Sidebar.exe"),
    )

    converter = file.StatEntryToExportedRegistryKeyConverter()
    results = list(converter.Convert(self.metadata, stat))

    self.assertLen(results, 1)
    self.assertEqual(
        results[0].urn,
        "aff4:/%s/registry/HKEY_USERS/S-1-5-20/Software/"
        "Microsoft/Windows/CurrentVersion/Run/Sidebar"
        % self.client_id,
    )
    self.assertEqual(
        results[0].last_modified, rdfvalue.RDFDatetimeSeconds(1247546054)
    )
    self.assertEqual(
        results[0].type, rdf_client_fs.StatEntry.RegistryType.REG_EXPAND_SZ
    )
    self.assertEqual(results[0].data, b"Sidebar.exe")

  def testRegistryKeyConverterIgnoresNonRegistryStatEntries(self):
    stat = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="/some/path", pathtype=rdf_paths.PathSpec.PathType.OS
        ),
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892,
        st_btime=1333333331,
    )

    converter = file.StatEntryToExportedRegistryKeyConverter()
    results = list(converter.Convert(self.metadata, stat))

    self.assertFalse(results)

  def testRegistryKeyConverterWorksWithRegistryKeys(self):
    # Registry keys won't have registry_type and registry_data set.
    stat = rdf_client_fs.StatEntry(
        st_mode=32768,
        st_size=51,
        st_mtime=1247546054,
        pathspec=rdf_paths.PathSpec(
            path=(
                "/HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/"
                "CurrentVersion/Run/Sidebar"
            ),
            pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
        ),
    )

    converter = file.StatEntryToExportedRegistryKeyConverter()
    results = list(converter.Convert(self.metadata, stat))

    self.assertLen(results, 1)
    self.assertEqual(
        results[0].urn,
        rdfvalue.RDFURN(
            "aff4:/%s/registry/HKEY_USERS/S-1-5-20/Software/"
            "Microsoft/Windows/CurrentVersion/Run/Sidebar"
            % self.client_id
        ),
    )
    self.assertEqual(
        results[0].last_modified, rdfvalue.RDFDatetimeSeconds(1247546054)
    )
    self.assertEqual(results[0].data, b"")
    self.assertEqual(results[0].type, 0)


class StatEntryToExportedRegistryKeyConverterProtoTest(absltest.TestCase):
  """Tests for StatEntryToExportedRegistryKeyConverterProto."""

  def setUp(self):
    super().setUp()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testStatEntryToExportedRegistryKeyConverter(self):
    stat = jobs_pb2.StatEntry(
        st_mode=32768,
        st_size=51,
        st_mtime=1247546054,
        registry_type=jobs_pb2.StatEntry.RegistryType.REG_EXPAND_SZ,
        pathspec=jobs_pb2.PathSpec(
            path=(
                "/HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/"
                "CurrentVersion/Run/Sidebar"
            ),
            pathtype=jobs_pb2.PathSpec.PathType.REGISTRY,
        ),
        registry_data=jobs_pb2.DataBlob(data=b"Sidebar.exe"),
    )

    converter = file.StatEntryToExportedRegistryKeyConverterProto()
    results = list(converter.Convert(self.metadata_proto, stat))

    self.assertLen(results, 1)
    self.assertEqual(
        results[0].urn,
        "aff4:/%s/registry/HKEY_USERS/S-1-5-20/Software/"
        "Microsoft/Windows/CurrentVersion/Run/Sidebar"
        % self.client_id,
    )
    self.assertEqual(results[0].last_modified, 1247546054)
    self.assertEqual(
        results[0].type, jobs_pb2.StatEntry.RegistryType.REG_EXPAND_SZ
    )
    self.assertEqual(results[0].data, b"Sidebar.exe")

  def testRegistryKeyConverterIgnoresNonRegistryStatEntries(self):
    stat = jobs_pb2.StatEntry(
        pathspec=jobs_pb2.PathSpec(
            path="/some/path", pathtype=jobs_pb2.PathSpec.PathType.OS
        ),
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892,
        st_btime=1333333331,
    )

    converter = file.StatEntryToExportedRegistryKeyConverterProto()
    results = list(converter.Convert(self.metadata_proto, stat))

    self.assertFalse(results)

  def testRegistryKeyConverterWorksWithRegistryKeys(self):
    # Registry keys won't have registry_type and registry_data set.
    stat = jobs_pb2.StatEntry(
        st_mode=32768,
        st_size=51,
        st_mtime=1247546054,
        pathspec=jobs_pb2.PathSpec(
            path=(
                "/HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/"
                "CurrentVersion/Run/Sidebar"
            ),
            pathtype=jobs_pb2.PathSpec.PathType.REGISTRY,
        ),
    )

    converter = file.StatEntryToExportedRegistryKeyConverterProto()
    results = list(converter.Convert(self.metadata_proto, stat))

    self.assertLen(results, 1)
    self.assertEqual(
        results[0].urn,
        "aff4:/%s/registry/HKEY_USERS/S-1-5-20/Software/"
        "Microsoft/Windows/CurrentVersion/Run/Sidebar"
        % self.client_id,
    )
    self.assertEqual(results[0].last_modified, 1247546054)
    self.assertEqual(results[0].data, b"")
    self.assertEqual(results[0].type, 0)


class FileFinderResultConverterTest(export_test_lib.ExportTestBase):
  """Tests for FileFinderResultConverter."""

  @export_test_lib.WithAllExportConverters
  def testFileFinderResultExportConverter(self):
    pathspec = rdf_paths.PathSpec(
        path="/some/path", pathtype=rdf_paths.PathSpec.PathType.OS
    )

    match1 = rdf_client.BufferReference(
        offset=42, length=43, data=b"somedata1", pathspec=pathspec
    )
    match2 = rdf_client.BufferReference(
        offset=44, length=45, data=b"somedata2", pathspec=pathspec
    )
    stat_entry = rdf_client_fs.StatEntry(
        pathspec=pathspec,
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892,
        st_btime=1313131313,
    )

    file_finder_result = rdf_file_finder.FileFinderResult(
        stat_entry=stat_entry, matches=[match1, match2]
    )

    converter = file.FileFinderResultConverter()
    results = list(converter.Convert(self.metadata, file_finder_result))

    # We expect 1 ExportedFile instance in the results
    exported_files = [
        result for result in results if isinstance(result, file.ExportedFile)
    ]
    self.assertLen(exported_files, 1)

    self.assertEqual(exported_files[0].basename, "path")
    self.assertEqual(
        exported_files[0].urn, "aff4:/%s/fs/os/some/path" % self.client_id
    )
    self.assertEqual(exported_files[0].st_mode, 33184)
    self.assertEqual(exported_files[0].st_ino, 1063090)
    self.assertEqual(exported_files[0].st_atime, 1336469177)
    self.assertEqual(exported_files[0].st_mtime, 1336129892)
    self.assertEqual(exported_files[0].st_ctime, 1336129892)
    self.assertEqual(exported_files[0].st_btime, 1313131313)

    self.assertFalse(exported_files[0].HasField("content"))
    self.assertFalse(exported_files[0].HasField("content_sha256"))
    self.assertFalse(exported_files[0].HasField("hash_md5"))
    self.assertFalse(exported_files[0].HasField("hash_sha1"))
    self.assertFalse(exported_files[0].HasField("hash_sha256"))

    # We expect 2 ExportedMatch instances in the results
    exported_matches = [
        result
        for result in results
        if isinstance(result, buffer_reference.ExportedMatch)
    ]
    exported_matches = sorted(exported_matches, key=lambda x: x.offset)
    self.assertLen(exported_matches, 2)

    self.assertEqual(exported_matches[0].offset, 42)
    self.assertEqual(exported_matches[0].length, 43)
    self.assertEqual(exported_matches[0].data, b"somedata1")
    self.assertEqual(
        exported_matches[0].urn, "aff4:/%s/fs/os/some/path" % self.client_id
    )

    self.assertEqual(exported_matches[1].offset, 44)
    self.assertEqual(exported_matches[1].length, 45)
    self.assertEqual(exported_matches[1].data, b"somedata2")
    self.assertEqual(
        exported_matches[1].urn, "aff4:/%s/fs/os/some/path" % self.client_id
    )

    # Also test registry entries.
    data = rdf_protodict.DataBlob()
    data.SetValue(b"testdata")
    stat_entry = rdf_client_fs.StatEntry(
        registry_type="REG_SZ",
        registry_data=data,
        pathspec=rdf_paths.PathSpec(
            path="HKEY_USERS/S-1-1-1-1/Software", pathtype="REGISTRY"
        ),
    )
    file_finder_result = rdf_file_finder.FileFinderResult(stat_entry=stat_entry)
    converter = file.FileFinderResultConverter()
    results = list(converter.Convert(self.metadata, file_finder_result))

    self.assertLen(results, 1)
    self.assertIsInstance(results[0], file.ExportedRegistryKey)
    result = results[0]

    self.assertEqual(result.data, b"testdata")
    self.assertEqual(
        result.urn,
        "aff4:/%s/registry/HKEY_USERS/S-1-1-1-1/Software" % self.client_id,
    )

  @export_test_lib.WithAllExportConverters
  def testFileFinderResultExportConverterConvertsBufferRefsWithoutPathspecs(
      self,
  ):
    pathspec = rdf_paths.PathSpec(
        path="/some/path", pathtype=rdf_paths.PathSpec.PathType.OS
    )

    match1 = rdf_client.BufferReference(offset=42, length=43, data=b"somedata1")
    match2 = rdf_client.BufferReference(offset=44, length=45, data=b"somedata2")
    stat_entry = rdf_client_fs.StatEntry(
        pathspec=pathspec,
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892,
        st_btime=1313131313,
    )

    file_finder_result = rdf_file_finder.FileFinderResult(
        stat_entry=stat_entry, matches=[match1, match2]
    )

    converter = file.FileFinderResultConverter()
    results = list(converter.Convert(self.metadata, file_finder_result))

    # We expect 2 ExportedMatch instances in the results
    exported_matches = [
        result
        for result in results
        if isinstance(result, buffer_reference.ExportedMatch)
    ]
    exported_matches = sorted(exported_matches, key=lambda x: x.offset)
    self.assertLen(exported_matches, 2)

    self.assertEqual(exported_matches[0].offset, 42)
    self.assertEqual(exported_matches[0].length, 43)
    self.assertEqual(exported_matches[0].data, b"somedata1")
    self.assertEqual(
        exported_matches[0].urn, "aff4:/%s/fs/os/some/path" % self.client_id
    )

    self.assertEqual(exported_matches[1].offset, 44)
    self.assertEqual(exported_matches[1].length, 45)
    self.assertEqual(exported_matches[1].data, b"somedata2")
    self.assertEqual(
        exported_matches[1].urn, "aff4:/%s/fs/os/some/path" % self.client_id
    )

  def testFileFinderResultExportConverterConvertsHashes(self):
    pathspec = rdf_paths.PathSpec(
        path="/some/path", pathtype=rdf_paths.PathSpec.PathType.OS
    )
    pathspec2 = rdf_paths.PathSpec(
        path="/some/path2", pathtype=rdf_paths.PathSpec.PathType.OS
    )

    sha256 = binascii.unhexlify(
        "0e8dc93e150021bb4752029ebbff51394aa36f069cf19901578e4f06017acdb5"
    )
    sha1 = binascii.unhexlify("7dd6bee591dfcb6d75eb705405302c3eab65e21a")
    md5 = binascii.unhexlify("bb0a15eefe63fd41f8dc9dee01c5cf9a")
    pecoff_md5 = binascii.unhexlify("7dd6bee591dfcb6d75eb705405302c3eab65e21a")
    pecoff_sha1 = binascii.unhexlify("7dd6bee591dfcb6d75eb705405302c3eab65e21a")

    stat_entry = rdf_client_fs.StatEntry(
        pathspec=pathspec,
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892,
        st_btime=1331133113,
    )
    hash_entry = rdf_crypto.Hash(
        sha256=sha256,
        sha1=sha1,
        md5=md5,
        pecoff_md5=pecoff_md5,
        pecoff_sha1=pecoff_sha1,
    )

    sha256 = binascii.unhexlify(
        "9e8dc93e150021bb4752029ebbff51394aa36f069cf19901578e4f06017acdb5"
    )
    sha1 = binascii.unhexlify("6dd6bee591dfcb6d75eb705405302c3eab65e21a")
    md5 = binascii.unhexlify("8b0a15eefe63fd41f8dc9dee01c5cf9a")
    pecoff_md5 = binascii.unhexlify("1dd6bee591dfcb6d75eb705405302c3eab65e21a")
    pecoff_sha1 = binascii.unhexlify("1dd6bee591dfcb6d75eb705405302c3eab65e21a")

    stat_entry2 = rdf_client_fs.StatEntry(
        pathspec=pathspec2,
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892,
        st_btime=1331331331,
    )
    hash_entry2 = rdf_crypto.Hash(
        sha256=sha256,
        sha1=sha1,
        md5=md5,
        pecoff_md5=pecoff_md5,
        pecoff_sha1=pecoff_sha1,
    )

    file_finder_result = rdf_file_finder.FileFinderResult(
        stat_entry=stat_entry, hash_entry=hash_entry
    )
    file_finder_result2 = rdf_file_finder.FileFinderResult(
        stat_entry=stat_entry2, hash_entry=hash_entry2
    )

    converter = file.FileFinderResultConverter()
    results = list(
        converter.BatchConvert([
            (self.metadata, file_finder_result),
            (self.metadata, file_finder_result2),
        ])
    )

    exported_files = [
        result for result in results if isinstance(result, file.ExportedFile)
    ]
    self.assertLen(exported_files, 2)
    self.assertCountEqual(
        [x.basename for x in exported_files], ["path", "path2"]
    )

    for export_result in exported_files:
      if export_result.basename == "path":
        self.assertEqual(
            export_result.hash_sha256,
            "0e8dc93e150021bb4752029ebbff51394aa36f069cf19901578e4f06017acdb5",
        )
        self.assertEqual(
            export_result.hash_sha1, "7dd6bee591dfcb6d75eb705405302c3eab65e21a"
        )
        self.assertEqual(
            export_result.hash_md5, "bb0a15eefe63fd41f8dc9dee01c5cf9a"
        )
        self.assertEqual(
            export_result.pecoff_hash_md5,
            "7dd6bee591dfcb6d75eb705405302c3eab65e21a",
        )
        self.assertEqual(
            export_result.pecoff_hash_sha1,
            "7dd6bee591dfcb6d75eb705405302c3eab65e21a",
        )
      elif export_result.basename == "path2":
        self.assertEqual(export_result.basename, "path2")
        self.assertEqual(
            export_result.hash_sha256,
            "9e8dc93e150021bb4752029ebbff51394aa36f069cf19901578e4f06017acdb5",
        )
        self.assertEqual(
            export_result.hash_sha1, "6dd6bee591dfcb6d75eb705405302c3eab65e21a"
        )
        self.assertEqual(
            export_result.hash_md5, "8b0a15eefe63fd41f8dc9dee01c5cf9a"
        )
        self.assertEqual(
            export_result.pecoff_hash_md5,
            "1dd6bee591dfcb6d75eb705405302c3eab65e21a",
        )
        self.assertEqual(
            export_result.pecoff_hash_sha1,
            "1dd6bee591dfcb6d75eb705405302c3eab65e21a",
        )

  def testFileFinderResultExportConverterConvertsContent(self):
    client_mock = action_mocks.FileFinderClientMockWithTimestamps()

    action = rdf_file_finder.FileFinderAction(
        action_type=rdf_file_finder.FileFinderAction.Action.DOWNLOAD
    )

    path = os.path.join(self.base_path, "winexec_img.dd")
    flow_id = flow_test_lib.StartAndRunFlow(
        file_finder.FileFinder,
        client_mock,
        client_id=self.client_id,
        flow_args=rdf_file_finder.FileFinderArgs(
            paths=[path],
            action=action,
            pathtype=rdf_paths.PathSpec.PathType.OS,
        ),
        creator=self.test_username,
    )

    flow_results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(flow_results, 1)

    converter = file.FileFinderResultConverter()
    results = list(converter.Convert(self.metadata, flow_results[0]))

    self.assertLen(results, 1)

    self.assertEqual(results[0].basename, "winexec_img.dd")

    # Check that by default file contents are not exported
    self.assertFalse(results[0].content)
    self.assertFalse(results[0].content_sha256)


class FileFinderResultConverterProtoTest(absltest.TestCase):
  """Tests for FileFinderResultConverterProto."""

  def setUp(self):
    super().setUp()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testBatchConvertWithAllTypes(self):
    file_pathspec = jobs_pb2.PathSpec(
        path="/some/path", pathtype=jobs_pb2.PathSpec.PathType.OS
    )
    file_result_with_matches = flows_pb2.FileFinderResult(
        stat_entry=jobs_pb2.StatEntry(
            pathspec=file_pathspec,
            st_mode=33184,
            st_ino=1063090,
            st_atime=1336469177,
            st_mtime=1336129892,
            st_ctime=1336129892,
            st_btime=1313131313,
        ),
        matches=[
            jobs_pb2.BufferReference(
                offset=42,
                length=43,
                data=b"somedata1",
                pathspec=file_pathspec,
            ),
            jobs_pb2.BufferReference(
                offset=44,
                length=45,
                data=b"somedata2",
                pathspec=file_pathspec,
            ),
        ],
    )
    registry_result = flows_pb2.FileFinderResult(
        stat_entry=jobs_pb2.StatEntry(
            registry_type=jobs_pb2.StatEntry.RegistryType.REG_SZ,
            registry_data=jobs_pb2.DataBlob(data=b"testdata"),
            pathspec=jobs_pb2.PathSpec(
                path="HKEY_USERS/S-1-1-1-1/Software",
                pathtype=jobs_pb2.PathSpec.PathType.REGISTRY,
            ),
        )
    )

    converter = file.FileFinderResultConverterProto()
    results = list(
        converter.BatchConvert([
            (self.metadata_proto, file_result_with_matches),
            (self.metadata_proto, registry_result),
        ])
    )

    # We expect 1 ExportedFile instance in the results
    exported_files = [
        r for r in results if isinstance(r, export_pb2.ExportedFile)
    ]
    self.assertLen(exported_files, 1)
    self.assertEqual(exported_files[0].basename, "path")
    self.assertEqual(
        exported_files[0].urn, f"aff4:/{self.client_id}/fs/os/some/path"
    )
    self.assertEqual(exported_files[0].st_mode, 33184)
    self.assertEqual(exported_files[0].st_ino, 1063090)
    self.assertEqual(exported_files[0].st_atime, 1336469177)
    self.assertEqual(exported_files[0].st_mtime, 1336129892)
    self.assertEqual(exported_files[0].st_ctime, 1336129892)
    self.assertEqual(exported_files[0].st_btime, 1313131313)

    self.assertFalse(exported_files[0].HasField("content"))
    self.assertFalse(exported_files[0].HasField("content_sha256"))
    self.assertFalse(exported_files[0].HasField("hash_md5"))
    self.assertFalse(exported_files[0].HasField("hash_sha1"))
    self.assertFalse(exported_files[0].HasField("hash_sha256"))

    # We expect 2 ExportedMatch instances in the results
    exported_matches = [
        r for r in results if isinstance(r, export_pb2.ExportedMatch)
    ]
    exported_matches = sorted(exported_matches, key=lambda x: x.offset)
    self.assertLen(exported_matches, 2)

    self.assertEqual(exported_matches[0].offset, 42)
    self.assertEqual(exported_matches[0].length, 43)
    self.assertEqual(exported_matches[0].data, b"somedata1")
    self.assertEqual(
        exported_matches[0].urn, f"aff4:/{self.client_id}/fs/os/some/path"
    )

    self.assertEqual(exported_matches[1].offset, 44)
    self.assertEqual(exported_matches[1].length, 45)
    self.assertEqual(exported_matches[1].data, b"somedata2")
    self.assertEqual(
        exported_matches[1].urn, f"aff4:/{self.client_id}/fs/os/some/path"
    )

    # We expect 1 ExportedRegistryKey instance in the results
    exported_registry_keys = [
        r for r in results if isinstance(r, export_pb2.ExportedRegistryKey)
    ]
    self.assertLen(exported_registry_keys, 1)
    self.assertEqual(exported_registry_keys[0].data, b"testdata")
    self.assertEqual(
        exported_registry_keys[0].urn,
        f"aff4:/{self.client_id}/registry/HKEY_USERS/S-1-1-1-1/Software",
    )

  def testConvertFileResult(self):
    file_pathspec = jobs_pb2.PathSpec(
        path="/some/path", pathtype=jobs_pb2.PathSpec.PathType.OS
    )
    file_result_with_matches = flows_pb2.FileFinderResult(
        stat_entry=jobs_pb2.StatEntry(
            pathspec=file_pathspec,
            st_mode=33184,
            st_ino=1063090,
            st_atime=1336469177,
            st_mtime=1336129892,
            st_ctime=1336129892,
            st_btime=1313131313,
        ),
        matches=[
            jobs_pb2.BufferReference(
                offset=42,
                length=43,
                data=b"somedata1",
                pathspec=file_pathspec,
            ),
            jobs_pb2.BufferReference(
                offset=44,
                length=45,
                data=b"somedata2",
                pathspec=file_pathspec,
            ),
        ],
    )

    converter = file.FileFinderResultConverterProto()
    results = list(
        converter.Convert(self.metadata_proto, file_result_with_matches)
    )

    # We expect 1 ExportedFile instance in the results
    exported_files = [
        r for r in results if isinstance(r, export_pb2.ExportedFile)
    ]
    self.assertLen(exported_files, 1)
    self.assertEqual(exported_files[0].basename, "path")
    self.assertEqual(
        exported_files[0].urn, f"aff4:/{self.client_id}/fs/os/some/path"
    )
    self.assertEqual(exported_files[0].st_mode, 33184)
    self.assertEqual(exported_files[0].st_ino, 1063090)
    self.assertEqual(exported_files[0].st_atime, 1336469177)
    self.assertEqual(exported_files[0].st_mtime, 1336129892)
    self.assertEqual(exported_files[0].st_ctime, 1336129892)
    self.assertEqual(exported_files[0].st_btime, 1313131313)

    self.assertFalse(exported_files[0].HasField("content"))
    self.assertFalse(exported_files[0].HasField("content_sha256"))
    self.assertFalse(exported_files[0].HasField("hash_md5"))
    self.assertFalse(exported_files[0].HasField("hash_sha1"))
    self.assertFalse(exported_files[0].HasField("hash_sha256"))

    # We expect 2 ExportedMatch instances in the results
    exported_matches = [
        r for r in results if isinstance(r, export_pb2.ExportedMatch)
    ]
    exported_matches = sorted(exported_matches, key=lambda x: x.offset)
    self.assertLen(exported_matches, 2)

    self.assertEqual(exported_matches[0].offset, 42)
    self.assertEqual(exported_matches[0].length, 43)
    self.assertEqual(exported_matches[0].data, b"somedata1")
    self.assertEqual(
        exported_matches[0].urn, f"aff4:/{self.client_id}/fs/os/some/path"
    )

    self.assertEqual(exported_matches[1].offset, 44)
    self.assertEqual(exported_matches[1].length, 45)
    self.assertEqual(exported_matches[1].data, b"somedata2")
    self.assertEqual(
        exported_matches[1].urn, f"aff4:/{self.client_id}/fs/os/some/path"
    )

  def testConvertRegistryResult(self):
    stat_entry = jobs_pb2.StatEntry(
        registry_type=jobs_pb2.StatEntry.RegistryType.REG_SZ,
        registry_data=jobs_pb2.DataBlob(data=b"testdata"),
        pathspec=jobs_pb2.PathSpec(
            path="HKEY_USERS/S-1-1-1-1/Software",
            pathtype=jobs_pb2.PathSpec.PathType.REGISTRY,
        ),
    )
    file_finder_result = flows_pb2.FileFinderResult(stat_entry=stat_entry)

    converter = file.FileFinderResultConverterProto()
    results = list(converter.Convert(self.metadata_proto, file_finder_result))

    self.assertLen(results, 1)
    # pytype is not happy with assertIsInstance but understands the assert.
    assert isinstance(results[0], export_pb2.ExportedRegistryKey)
    self.assertEqual(results[0].data, b"testdata")
    self.assertEqual(
        results[0].urn,
        f"aff4:/{self.client_id}/registry/HKEY_USERS/S-1-1-1-1/Software",
    )

  def testConvertsMatches_WithoutInnerPathspecFallback(self):
    no_pathspec = jobs_pb2.BufferReference(
        offset=42, length=43, data=b"somedata1"
    )
    stat_entry = jobs_pb2.StatEntry(
        pathspec=jobs_pb2.PathSpec(
            path="/some/path", pathtype=jobs_pb2.PathSpec.PathType.OS
        )
    )
    file_finder_result = flows_pb2.FileFinderResult(
        stat_entry=stat_entry, matches=[no_pathspec]
    )

    converter = file.FileFinderResultConverterProto()
    results = list(converter.Convert(self.metadata_proto, file_finder_result))

    exported_matches = [
        r for r in results if isinstance(r, export_pb2.ExportedMatch)
    ]
    self.assertLen(exported_matches, 1)
    self.assertEqual(
        exported_matches[0].urn, f"aff4:/{self.client_id}/fs/os/some/path"
    )

  def testConvertsMatches_InnerPathspecPrecedence(self):
    pathspec = jobs_pb2.PathSpec(
        path="/stat_entry/path", pathtype=jobs_pb2.PathSpec.PathType.OS
    )
    with_different_pathspec = jobs_pb2.BufferReference(
        offset=44,
        length=45,
        data=b"somedata2",
        pathspec=jobs_pb2.PathSpec(
            # This path is different from the one in the stat entry.
            path="/match/path",
            pathtype=jobs_pb2.PathSpec.PathType.OS,
        ),
    )
    stat_entry = jobs_pb2.StatEntry(pathspec=pathspec)
    file_finder_result = flows_pb2.FileFinderResult(
        stat_entry=stat_entry, matches=[with_different_pathspec]
    )

    converter = file.FileFinderResultConverterProto()
    results = list(converter.Convert(self.metadata_proto, file_finder_result))

    exported_matches = [
        r for r in results if isinstance(r, export_pb2.ExportedMatch)
    ]
    self.assertLen(exported_matches, 1)
    self.assertEqual(
        exported_matches[0].urn, f"aff4:/{self.client_id}/fs/os/match/path"
    )

  def testFileFinderResultExportConverterConvertsHashes(self):
    pathspec = jobs_pb2.PathSpec(
        path="/some/path", pathtype=jobs_pb2.PathSpec.PathType.OS
    )
    pathspec2 = jobs_pb2.PathSpec(
        path="/some/path2", pathtype=jobs_pb2.PathSpec.PathType.TSK
    )

    sha256_1 = binascii.unhexlify(
        "0e8dc93e150021bb4752029ebbff51394aa36f069cf19901578e4f06017acdb5"
    )
    sha1_1 = binascii.unhexlify("7dd6bee591dfcb6d75eb705405302c3eab65e21a")
    md5_1 = binascii.unhexlify("bb0a15eefe63fd41f8dc9dee01c5cf9a")
    pecoff_md5_1 = binascii.unhexlify(
        "7dd6bee591dfcb6d75eb705405302c3eab65e21a"
    )
    pecoff_sha1_1 = binascii.unhexlify(
        "7dd6bee591dfcb6d75eb705405302c3eab65e21a"
    )

    stat_entry = jobs_pb2.StatEntry(
        pathspec=pathspec,
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892,
        st_btime=1331133113,
    )
    hash_entry = jobs_pb2.Hash(
        sha256=sha256_1,
        sha1=sha1_1,
        md5=md5_1,
        pecoff_md5=pecoff_md5_1,
        pecoff_sha1=pecoff_sha1_1,
    )

    sha256_2 = binascii.unhexlify(
        "9e8dc93e150021bb4752029ebbff51394aa36f069cf19901578e4f06017acdb5"
    )
    sha1_2 = binascii.unhexlify("6dd6bee591dfcb6d75eb705405302c3eab65e21a")
    md5_2 = binascii.unhexlify("8b0a15eefe63fd41f8dc9dee01c5cf9a")
    pecoff_md5_2 = binascii.unhexlify(
        "1dd6bee591dfcb6d75eb705405302c3eab65e21a"
    )
    pecoff_sha1_2 = binascii.unhexlify(
        "1dd6bee591dfcb6d75eb705405302c3eab65e21a"
    )

    stat_entry2 = jobs_pb2.StatEntry(
        pathspec=pathspec2,
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892,
        st_btime=1331331331,
    )
    hash_entry2 = jobs_pb2.Hash(
        sha256=sha256_2,
        sha1=sha1_2,
        md5=md5_2,
        pecoff_md5=pecoff_md5_2,
        pecoff_sha1=pecoff_sha1_2,
    )

    file_finder_result = flows_pb2.FileFinderResult(
        stat_entry=stat_entry, hash_entry=hash_entry
    )
    file_finder_result2 = flows_pb2.FileFinderResult(
        stat_entry=stat_entry2, hash_entry=hash_entry2
    )

    converter = file.FileFinderResultConverterProto()
    results = list(
        converter.BatchConvert([
            (self.metadata_proto, file_finder_result),
            (self.metadata_proto, file_finder_result2),
        ])
    )

    exported_files = [
        result
        for result in results
        if isinstance(result, export_pb2.ExportedFile)
    ]
    self.assertLen(exported_files, 2)
    self.assertCountEqual(
        [x.basename for x in exported_files], ["path", "path2"]
    )

    for export_result in exported_files:
      if export_result.basename == "path":
        self.assertEqual(
            export_result.hash_sha256,
            "0e8dc93e150021bb4752029ebbff51394aa36f069cf19901578e4f06017acdb5",
        )
        self.assertEqual(
            export_result.hash_sha1, "7dd6bee591dfcb6d75eb705405302c3eab65e21a"
        )
        self.assertEqual(
            export_result.hash_md5, "bb0a15eefe63fd41f8dc9dee01c5cf9a"
        )
        self.assertEqual(
            export_result.pecoff_hash_md5,
            "7dd6bee591dfcb6d75eb705405302c3eab65e21a",
        )
        self.assertEqual(
            export_result.pecoff_hash_sha1,
            "7dd6bee591dfcb6d75eb705405302c3eab65e21a",
        )
      elif export_result.basename == "path2":
        self.assertEqual(
            export_result.hash_sha256,
            "9e8dc93e150021bb4752029ebbff51394aa36f069cf19901578e4f06017acdb5",
        )
        self.assertEqual(
            export_result.hash_sha1, "6dd6bee591dfcb6d75eb705405302c3eab65e21a"
        )
        self.assertEqual(
            export_result.hash_md5, "8b0a15eefe63fd41f8dc9dee01c5cf9a"
        )
        self.assertEqual(
            export_result.pecoff_hash_md5,
            "1dd6bee591dfcb6d75eb705405302c3eab65e21a",
        )
        self.assertEqual(
            export_result.pecoff_hash_sha1,
            "1dd6bee591dfcb6d75eb705405302c3eab65e21a",
        )


class CollectMultipleFilesResultConverterProtoTest(absltest.TestCase):
  """Tests for CollectMultipleFilesResultConverterProto."""

  def setUp(self):
    super().setUp()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testConvertsFileResultWithHash(self):
    pathspec = jobs_pb2.PathSpec(
        path="/some/path", pathtype=jobs_pb2.PathSpec.PathType.OS
    )

    sha256 = binascii.unhexlify(
        "0e8dc93e150021bb4752029ebbff51394aa36f069cf19901578e4f06017acdb5"
    )
    sha1 = binascii.unhexlify("7dd6bee591dfcb6d75eb705405302c3eab65e21a")
    md5 = binascii.unhexlify("bb0a15eefe63fd41f8dc9dee01c5cf9a")
    pecoff_md5 = binascii.unhexlify("7dd6bee591dfcb6d75eb705405302c3eab65e21a")
    pecoff_sha1 = binascii.unhexlify("7dd6bee591dfcb6d75eb705405302c3eab65e21a")

    stat_entry = jobs_pb2.StatEntry(
        pathspec=pathspec,
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892,
        st_btime=1331133113,
    )
    hash_entry = jobs_pb2.Hash(
        sha256=sha256,
        sha1=sha1,
        md5=md5,
        pecoff_md5=pecoff_md5,
        pecoff_sha1=pecoff_sha1,
    )

    collect_files_result = flows_pb2.CollectMultipleFilesResult(
        stat=stat_entry,
        hash=hash_entry,
        status=flows_pb2.CollectMultipleFilesResult.Status.COLLECTED,
    )

    converter = file.CollectMultipleFilesResultToExportedFileConverterProto()
    results = list(converter.Convert(self.metadata_proto, collect_files_result))
    self.assertLen(results, 1)

    exported_file = results[0]
    self.assertEqual(exported_file.basename, "path")
    self.assertEqual(
        exported_file.urn, f"aff4:/{self.client_id}/fs/os/some/path"
    )
    self.assertEqual(exported_file.st_mode, 33184)
    self.assertEqual(exported_file.st_ino, 1063090)
    self.assertEqual(exported_file.st_atime, 1336469177)
    self.assertEqual(exported_file.st_mtime, 1336129892)
    self.assertEqual(exported_file.st_ctime, 1336129892)
    self.assertEqual(exported_file.st_btime, 1331133113)
    self.assertEqual(
        exported_file.hash_sha256,
        "0e8dc93e150021bb4752029ebbff51394aa36f069cf19901578e4f06017acdb5",
    )
    self.assertEqual(
        exported_file.hash_sha1, "7dd6bee591dfcb6d75eb705405302c3eab65e21a"
    )
    self.assertEqual(exported_file.hash_md5, "bb0a15eefe63fd41f8dc9dee01c5cf9a")
    self.assertEqual(
        exported_file.pecoff_hash_md5,
        "7dd6bee591dfcb6d75eb705405302c3eab65e21a",
    )
    self.assertEqual(
        exported_file.pecoff_hash_sha1,
        "7dd6bee591dfcb6d75eb705405302c3eab65e21a",
    )

  def testIgnoresRegistryEntries(self):
    stat_entry = jobs_pb2.StatEntry(
        registry_type=jobs_pb2.StatEntry.RegistryType.REG_SZ,
        registry_data=jobs_pb2.DataBlob(data=b"testdata"),
        pathspec=jobs_pb2.PathSpec(
            path="HKEY_USERS/S-1-1-1-1/Software",
            pathtype=jobs_pb2.PathSpec.PathType.REGISTRY,
        ),
    )
    collect_files_result = flows_pb2.CollectMultipleFilesResult(stat=stat_entry)

    converter = file.CollectMultipleFilesResultToExportedFileConverterProto()
    results = list(converter.Convert(self.metadata_proto, collect_files_result))
    self.assertEmpty(results)


class CollectFilesByKnownPathResultConverterProtoTest(absltest.TestCase):
  """Tests for CollectFilesByKnownPathResultConverterProto."""

  def setUp(self):
    super().setUp()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testConvertsFileResultWithHash(self):
    pathspec = jobs_pb2.PathSpec(
        path="/some/path", pathtype=jobs_pb2.PathSpec.PathType.OS
    )

    sha256 = binascii.unhexlify(
        "0e8dc93e150021bb4752029ebbff51394aa36f069cf19901578e4f06017acdb5"
    )
    sha1 = binascii.unhexlify("7dd6bee591dfcb6d75eb705405302c3eab65e21a")
    md5 = binascii.unhexlify("bb0a15eefe63fd41f8dc9dee01c5cf9a")
    pecoff_md5 = binascii.unhexlify("7dd6bee591dfcb6d75eb705405302c3eab65e21a")
    pecoff_sha1 = binascii.unhexlify("7dd6bee591dfcb6d75eb705405302c3eab65e21a")

    stat_entry = jobs_pb2.StatEntry(
        pathspec=pathspec,
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892,
        st_btime=1331133113,
    )
    hash_entry = jobs_pb2.Hash(
        sha256=sha256,
        sha1=sha1,
        md5=md5,
        pecoff_md5=pecoff_md5,
        pecoff_sha1=pecoff_sha1,
    )

    result = flows_pb2.CollectFilesByKnownPathResult(
        stat=stat_entry,
        hash=hash_entry,
        status=flows_pb2.CollectFilesByKnownPathResult.Status.COLLECTED,
    )

    converter = file.CollectFilesByKnownPathResultToExportedFileConverterProto()
    results = list(converter.Convert(self.metadata_proto, result))
    self.assertLen(results, 1)

    exported_file = results[0]
    self.assertEqual(exported_file.basename, "path")
    self.assertEqual(
        exported_file.urn, f"aff4:/{self.client_id}/fs/os/some/path"
    )
    self.assertEqual(exported_file.st_mode, 33184)
    self.assertEqual(exported_file.st_ino, 1063090)
    self.assertEqual(exported_file.st_atime, 1336469177)
    self.assertEqual(exported_file.st_mtime, 1336129892)
    self.assertEqual(exported_file.st_ctime, 1336129892)
    self.assertEqual(exported_file.st_btime, 1331133113)
    self.assertEqual(
        exported_file.hash_sha256,
        "0e8dc93e150021bb4752029ebbff51394aa36f069cf19901578e4f06017acdb5",
    )
    self.assertEqual(
        exported_file.hash_sha1, "7dd6bee591dfcb6d75eb705405302c3eab65e21a"
    )
    self.assertEqual(exported_file.hash_md5, "bb0a15eefe63fd41f8dc9dee01c5cf9a")
    self.assertEqual(
        exported_file.pecoff_hash_md5,
        "7dd6bee591dfcb6d75eb705405302c3eab65e21a",
    )
    self.assertEqual(
        exported_file.pecoff_hash_sha1,
        "7dd6bee591dfcb6d75eb705405302c3eab65e21a",
    )
    self.assertFalse(exported_file.HasField("content"))
    self.assertFalse(exported_file.HasField("content_sha256"))

  def testIgnoresRegistryEntries(self):
    stat_entry = jobs_pb2.StatEntry(
        registry_type=jobs_pb2.StatEntry.RegistryType.REG_SZ,
        registry_data=jobs_pb2.DataBlob(data=b"testdata"),
        pathspec=jobs_pb2.PathSpec(
            path="HKEY_USERS/S-1-1-1-1/Software",
            pathtype=jobs_pb2.PathSpec.PathType.REGISTRY,
        ),
    )
    result = flows_pb2.CollectFilesByKnownPathResult(
        stat=stat_entry,
        status=flows_pb2.CollectFilesByKnownPathResult.Status.COLLECTED,
    )

    converter = file.CollectFilesByKnownPathResultToExportedFileConverterProto()
    results = list(converter.Convert(self.metadata_proto, result))
    self.assertEmpty(results)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
