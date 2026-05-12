#!/usr/bin/env python
import binascii

from absl import app
from absl.testing import absltest

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_proto import export_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_server.export_converters import file
from grr.test_lib import test_lib


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
    file_result = flows_pb2.FileFinderResult(
        stat_entry=jobs_pb2.StatEntry(
            pathspec=file_pathspec,
            st_mode=33184,
            st_ino=1063090,
            st_atime=1336469177,
            st_mtime=1336129892,
            st_ctime=1336129892,
            st_btime=1313131313,
        ),
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
            (self.metadata_proto, file_result),
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
    file_result = flows_pb2.FileFinderResult(
        stat_entry=jobs_pb2.StatEntry(
            pathspec=file_pathspec,
            st_mode=33184,
            st_ino=1063090,
            st_atime=1336469177,
            st_mtime=1336129892,
            st_ctime=1336129892,
            st_btime=1313131313,
        ),
    )

    converter = file.FileFinderResultConverterProto()
    results = list(converter.Convert(self.metadata_proto, file_result))

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
