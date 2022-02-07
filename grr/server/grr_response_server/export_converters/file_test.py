#!/usr/bin/env python
import binascii
import os

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_server import data_store
from grr_response_server.export_converters import base
from grr_response_server.export_converters import buffer_reference
from grr_response_server.export_converters import file
from grr_response_server.flows.general import collectors
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import transfer
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import action_mocks
from grr.test_lib import export_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class StatEntryToExportedFileConverterTest(export_test_lib.ExportTestBase):
  """Tests for StatEntryToExportedFileConverter."""

  def testStatEntryToExportedFileConverterWithMissingAFF4File(self):
    stat = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="/some/path", pathtype=rdf_paths.PathSpec.PathType.OS),
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892,
        st_btime=1331331331)

    converter = file.StatEntryToExportedFileConverter()
    results = list(converter.Convert(self.metadata, stat))

    self.assertLen(results, 1)
    self.assertEqual(results[0].basename, "path")
    self.assertEqual(results[0].urn,
                     "aff4:/%s/fs/os/some/path" % self.client_id)
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
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "winexec_img.dd"))
    pathspec.Append(
        path="/Ext2IFS_1_10b.exe", pathtype=rdf_paths.PathSpec.PathType.TSK)

    client_mock = action_mocks.GetFileClientMock()
    flow_test_lib.TestFlowHelper(
        transfer.GetFile.__name__,
        client_mock,
        creator=self.test_username,
        client_id=self.client_id,
        pathspec=pathspec)

    path_info = data_store.REL_DB.ReadPathInfo(
        self.client_id,
        rdf_objects.PathInfo.PathType.TSK,
        components=tuple(pathspec.CollapsePath().lstrip("/").split("/")))
    stat = path_info.stat_entry

    self.assertTrue(stat)

    converter = file.StatEntryToExportedFileConverter()
    results = list(converter.Convert(self.metadata, stat))

    self.assertLen(results, 1)
    self.assertEqual(results[0].basename, "Ext2IFS_1_10b.exe")
    urn = "aff4:/%s/fs/tsk%s" % (self.client_id, pathspec.CollapsePath())
    self.assertEqual(results[0].urn, urn)

    # Check that by default file contents are not exported
    self.assertFalse(results[0].content)
    self.assertFalse(results[0].content_sha256)

    # Convert again, now specifying export_files_contents=True in options.
    converter = file.StatEntryToExportedFileConverter(
        options=base.ExportOptions(export_files_contents=True))
    results = list(converter.Convert(self.metadata, stat))
    self.assertTrue(results[0].content)
    self.assertEqual(
        results[0].content_sha256,
        "69264282ca1a3d4e7f9b1f43720f719a4ea47964f0bfd1b2ba88424f1c61395d")
    self.assertEqual("", results[0].metadata.annotations)

  def testStatEntryToExportedFileConverterWithHashedAFF4File(self):
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "winexec_img.dd"))
    pathspec.Append(
        path="/Ext2IFS_1_10b.exe", pathtype=rdf_paths.PathSpec.PathType.TSK)

    client_mock = action_mocks.GetFileClientMock()
    flow_test_lib.TestFlowHelper(
        transfer.GetFile.__name__,
        client_mock,
        creator=self.test_username,
        client_id=self.client_id,
        pathspec=pathspec)

    path_info = rdf_objects.PathInfo.FromPathSpec(pathspec)
    path_info = data_store.REL_DB.ReadPathInfo(self.client_id,
                                               path_info.path_type,
                                               tuple(path_info.components))
    hash_value = path_info.hash_entry

    self.assertTrue(hash_value)

    converter = file.StatEntryToExportedFileConverter()
    results = list(
        converter.Convert(self.metadata,
                          rdf_client_fs.StatEntry(pathspec=pathspec)))

    # Even though the file has a hash, it's not stored in StatEntry and
    # doesn't influence the result. Note: this is a change in behavior.
    # Previously StatEntry exporter was opening corresponding file objects
    # and reading hashes from these objects. This approach was questionable
    # at best, since there was no guarantee that hashes actually corresponded
    # to files in question.
    self.assertFalse(results[0].hash_md5)
    self.assertFalse(results[0].hash_sha1)
    self.assertFalse(results[0].hash_sha256)

  def testExportedFileConverterIgnoresRegistryKeys(self):
    stat = rdf_client_fs.StatEntry(
        st_mode=32768,
        st_size=51,
        st_mtime=1247546054,
        pathspec=rdf_paths.PathSpec(
            path="/HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/"
            "CurrentVersion/Run/Sidebar",
            pathtype=rdf_paths.PathSpec.PathType.REGISTRY))

    converter = file.StatEntryToExportedFileConverter()
    results = list(converter.Convert(self.metadata, stat))
    self.assertFalse(results)


class StatEntryToExportedRegistryKeyConverterTest(export_test_lib.ExportTestBase
                                                 ):
  """Tests for StatEntryToExportedRegistryKeyConverter."""

  def testStatEntryToExportedRegistryKeyConverter(self):
    stat = rdf_client_fs.StatEntry(
        st_mode=32768,
        st_size=51,
        st_mtime=1247546054,
        registry_type=rdf_client_fs.StatEntry.RegistryType.REG_EXPAND_SZ,
        pathspec=rdf_paths.PathSpec(
            path="/HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/"
            "CurrentVersion/Run/Sidebar",
            pathtype=rdf_paths.PathSpec.PathType.REGISTRY),
        registry_data=rdf_protodict.DataBlob(string="Sidebar.exe"))

    converter = file.StatEntryToExportedRegistryKeyConverter()
    results = list(converter.Convert(self.metadata, stat))

    self.assertLen(results, 1)
    self.assertEqual(
        results[0].urn, "aff4:/%s/registry/HKEY_USERS/S-1-5-20/Software/"
        "Microsoft/Windows/CurrentVersion/Run/Sidebar" % self.client_id)
    self.assertEqual(results[0].last_modified,
                     rdfvalue.RDFDatetimeSeconds(1247546054))
    self.assertEqual(results[0].type,
                     rdf_client_fs.StatEntry.RegistryType.REG_EXPAND_SZ)
    self.assertEqual(results[0].data, b"Sidebar.exe")

  def testRegistryKeyConverterIgnoresNonRegistryStatEntries(self):
    stat = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="/some/path", pathtype=rdf_paths.PathSpec.PathType.OS),
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892,
        st_btime=1333333331)

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
            path="/HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/"
            "CurrentVersion/Run/Sidebar",
            pathtype=rdf_paths.PathSpec.PathType.REGISTRY))

    converter = file.StatEntryToExportedRegistryKeyConverter()
    results = list(converter.Convert(self.metadata, stat))

    self.assertLen(results, 1)
    self.assertEqual(
        results[0].urn,
        rdfvalue.RDFURN("aff4:/%s/registry/HKEY_USERS/S-1-5-20/Software/"
                        "Microsoft/Windows/CurrentVersion/Run/Sidebar" %
                        self.client_id))
    self.assertEqual(results[0].last_modified,
                     rdfvalue.RDFDatetimeSeconds(1247546054))
    self.assertEqual(results[0].data, b"")
    self.assertEqual(results[0].type, 0)


class FileFinderResultConverterTest(export_test_lib.ExportTestBase):
  """Tests for FileFinderResultConverter."""

  @export_test_lib.WithAllExportConverters
  def testFileFinderResultExportConverter(self):
    pathspec = rdf_paths.PathSpec(
        path="/some/path", pathtype=rdf_paths.PathSpec.PathType.OS)

    match1 = rdf_client.BufferReference(
        offset=42, length=43, data=b"somedata1", pathspec=pathspec)
    match2 = rdf_client.BufferReference(
        offset=44, length=45, data=b"somedata2", pathspec=pathspec)
    stat_entry = rdf_client_fs.StatEntry(
        pathspec=pathspec,
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892,
        st_btime=1313131313)

    file_finder_result = rdf_file_finder.FileFinderResult(
        stat_entry=stat_entry, matches=[match1, match2])

    converter = file.FileFinderResultConverter()
    results = list(converter.Convert(self.metadata, file_finder_result))

    # We expect 1 ExportedFile instance in the results
    exported_files = [
        result for result in results if isinstance(result, file.ExportedFile)
    ]
    self.assertLen(exported_files, 1)

    self.assertEqual(exported_files[0].basename, "path")
    self.assertEqual(exported_files[0].urn,
                     "aff4:/%s/fs/os/some/path" % self.client_id)
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
        result for result in results
        if isinstance(result, buffer_reference.ExportedMatch)
    ]
    exported_matches = sorted(exported_matches, key=lambda x: x.offset)
    self.assertLen(exported_matches, 2)

    self.assertEqual(exported_matches[0].offset, 42)
    self.assertEqual(exported_matches[0].length, 43)
    self.assertEqual(exported_matches[0].data, b"somedata1")
    self.assertEqual(exported_matches[0].urn,
                     "aff4:/%s/fs/os/some/path" % self.client_id)

    self.assertEqual(exported_matches[1].offset, 44)
    self.assertEqual(exported_matches[1].length, 45)
    self.assertEqual(exported_matches[1].data, b"somedata2")
    self.assertEqual(exported_matches[1].urn,
                     "aff4:/%s/fs/os/some/path" % self.client_id)

    # Also test registry entries.
    data = rdf_protodict.DataBlob()
    data.SetValue(b"testdata")
    stat_entry = rdf_client_fs.StatEntry(
        registry_type="REG_SZ",
        registry_data=data,
        pathspec=rdf_paths.PathSpec(
            path="HKEY_USERS/S-1-1-1-1/Software", pathtype="REGISTRY"))
    file_finder_result = rdf_file_finder.FileFinderResult(stat_entry=stat_entry)
    converter = file.FileFinderResultConverter()
    results = list(converter.Convert(self.metadata, file_finder_result))

    self.assertLen(results, 1)
    self.assertIsInstance(results[0], file.ExportedRegistryKey)
    result = results[0]

    self.assertEqual(result.data, b"testdata")
    self.assertEqual(
        result.urn,
        "aff4:/%s/registry/HKEY_USERS/S-1-1-1-1/Software" % self.client_id)

  @export_test_lib.WithAllExportConverters
  def testFileFinderResultExportConverterConvertsBufferRefsWithoutPathspecs(
      self):
    pathspec = rdf_paths.PathSpec(
        path="/some/path", pathtype=rdf_paths.PathSpec.PathType.OS)

    match1 = rdf_client.BufferReference(offset=42, length=43, data=b"somedata1")
    match2 = rdf_client.BufferReference(offset=44, length=45, data=b"somedata2")
    stat_entry = rdf_client_fs.StatEntry(
        pathspec=pathspec,
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892,
        st_btime=1313131313)

    file_finder_result = rdf_file_finder.FileFinderResult(
        stat_entry=stat_entry, matches=[match1, match2])

    converter = file.FileFinderResultConverter()
    results = list(converter.Convert(self.metadata, file_finder_result))

    # We expect 2 ExportedMatch instances in the results
    exported_matches = [
        result for result in results
        if isinstance(result, buffer_reference.ExportedMatch)
    ]
    exported_matches = sorted(exported_matches, key=lambda x: x.offset)
    self.assertLen(exported_matches, 2)

    self.assertEqual(exported_matches[0].offset, 42)
    self.assertEqual(exported_matches[0].length, 43)
    self.assertEqual(exported_matches[0].data, b"somedata1")
    self.assertEqual(exported_matches[0].urn,
                     "aff4:/%s/fs/os/some/path" % self.client_id)

    self.assertEqual(exported_matches[1].offset, 44)
    self.assertEqual(exported_matches[1].length, 45)
    self.assertEqual(exported_matches[1].data, b"somedata2")
    self.assertEqual(exported_matches[1].urn,
                     "aff4:/%s/fs/os/some/path" % self.client_id)

  def testFileFinderResultExportConverterConvertsHashes(self):
    pathspec = rdf_paths.PathSpec(
        path="/some/path", pathtype=rdf_paths.PathSpec.PathType.OS)
    pathspec2 = rdf_paths.PathSpec(
        path="/some/path2", pathtype=rdf_paths.PathSpec.PathType.OS)

    sha256 = binascii.unhexlify(
        "0e8dc93e150021bb4752029ebbff51394aa36f069cf19901578e4f06017acdb5")
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
        st_btime=1331133113)
    hash_entry = rdf_crypto.Hash(
        sha256=sha256,
        sha1=sha1,
        md5=md5,
        pecoff_md5=pecoff_md5,
        pecoff_sha1=pecoff_sha1)

    sha256 = binascii.unhexlify(
        "9e8dc93e150021bb4752029ebbff51394aa36f069cf19901578e4f06017acdb5")
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
        st_btime=1331331331)
    hash_entry2 = rdf_crypto.Hash(
        sha256=sha256,
        sha1=sha1,
        md5=md5,
        pecoff_md5=pecoff_md5,
        pecoff_sha1=pecoff_sha1)

    file_finder_result = rdf_file_finder.FileFinderResult(
        stat_entry=stat_entry, hash_entry=hash_entry)
    file_finder_result2 = rdf_file_finder.FileFinderResult(
        stat_entry=stat_entry2, hash_entry=hash_entry2)

    converter = file.FileFinderResultConverter()
    results = list(
        converter.BatchConvert([(self.metadata, file_finder_result),
                                (self.metadata, file_finder_result2)]))

    exported_files = [
        result for result in results if isinstance(result, file.ExportedFile)
    ]
    self.assertLen(exported_files, 2)
    self.assertCountEqual([x.basename for x in exported_files],
                          ["path", "path2"])

    for export_result in exported_files:
      if export_result.basename == "path":
        self.assertEqual(
            export_result.hash_sha256,
            "0e8dc93e150021bb4752029ebbff51394aa36f069cf19901578e4"
            "f06017acdb5")
        self.assertEqual(export_result.hash_sha1,
                         "7dd6bee591dfcb6d75eb705405302c3eab65e21a")
        self.assertEqual(export_result.hash_md5,
                         "bb0a15eefe63fd41f8dc9dee01c5cf9a")
        self.assertEqual(export_result.pecoff_hash_md5,
                         "7dd6bee591dfcb6d75eb705405302c3eab65e21a")
        self.assertEqual(export_result.pecoff_hash_sha1,
                         "7dd6bee591dfcb6d75eb705405302c3eab65e21a")
      elif export_result.basename == "path2":
        self.assertEqual(export_result.basename, "path2")
        self.assertEqual(
            export_result.hash_sha256,
            "9e8dc93e150021bb4752029ebbff51394aa36f069cf19901578e4"
            "f06017acdb5")
        self.assertEqual(export_result.hash_sha1,
                         "6dd6bee591dfcb6d75eb705405302c3eab65e21a")
        self.assertEqual(export_result.hash_md5,
                         "8b0a15eefe63fd41f8dc9dee01c5cf9a")
        self.assertEqual(export_result.pecoff_hash_md5,
                         "1dd6bee591dfcb6d75eb705405302c3eab65e21a")
        self.assertEqual(export_result.pecoff_hash_sha1,
                         "1dd6bee591dfcb6d75eb705405302c3eab65e21a")

  def testFileFinderResultExportConverterConvertsContent(self):
    client_mock = action_mocks.FileFinderClientMockWithTimestamps()

    action = rdf_file_finder.FileFinderAction(
        action_type=rdf_file_finder.FileFinderAction.Action.DOWNLOAD)

    path = os.path.join(self.base_path, "winexec_img.dd")
    flow_id = flow_test_lib.TestFlowHelper(
        file_finder.FileFinder.__name__,
        client_mock,
        client_id=self.client_id,
        paths=[path],
        pathtype=rdf_paths.PathSpec.PathType.OS,
        action=action,
        creator=self.test_username)

    flow_results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(flow_results, 1)

    converter = file.FileFinderResultConverter()
    results = list(converter.Convert(self.metadata, flow_results[0]))

    self.assertLen(results, 1)

    self.assertEqual(results[0].basename, "winexec_img.dd")

    # Check that by default file contents are not exported
    self.assertFalse(results[0].content)
    self.assertFalse(results[0].content_sha256)

    # Convert again, now specifying export_files_contents=True in options.
    converter = file.FileFinderResultConverter(
        options=base.ExportOptions(export_files_contents=True))
    results = list(converter.Convert(self.metadata, flow_results[0]))
    self.assertTrue(results[0].content)

    self.assertEqual(
        results[0].content_sha256,
        "0652da33d5602c165396856540c173cd37277916fba07a9bf3080bc5a6236f03")


class ArtifactFilesDownloaderResultConverterTest(export_test_lib.ExportTestBase
                                                ):
  """Tests for ArtifactFilesDownloaderResultConverter."""

  def setUp(self):
    super().setUp()

    self.registry_stat = rdf_client_fs.StatEntry(
        registry_type=rdf_client_fs.StatEntry.RegistryType.REG_SZ,
        pathspec=rdf_paths.PathSpec(
            path="/HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/"
            "CurrentVersion/Run/Sidebar",
            pathtype=rdf_paths.PathSpec.PathType.REGISTRY),
        registry_data=rdf_protodict.DataBlob(string="C:\\Windows\\Sidebar.exe"))

    self.file_stat = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="/tmp/bar.exe", pathtype=rdf_paths.PathSpec.PathType.OS))

  def testExportsOriginalResultAnywayIfItIsNotStatEntry(self):
    result = collectors.ArtifactFilesDownloaderResult(
        original_result=export_test_lib.DataAgnosticConverterTestValue())

    converter = file.ArtifactFilesDownloaderResultConverter()
    converted = list(converter.Convert(self.metadata, result))

    # Test that something gets exported and that this something wasn't
    # produced by ArtifactFilesDownloaderResultConverter.
    self.assertLen(converted, 1)
    self.assertNotIsInstance(converted[0],
                             file.ExportedArtifactFilesDownloaderResult)

  def testExportsOriginalResultIfOriginalResultIsNotRegistryOrFileStatEntry(
      self):
    stat = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="some/path", pathtype=rdf_paths.PathSpec.PathType.TMPFILE))
    result = collectors.ArtifactFilesDownloaderResult(original_result=stat)

    converter = file.ArtifactFilesDownloaderResultConverter()
    converted = list(converter.Convert(self.metadata, result))

    # Test that something gets exported and that this something wasn't
    # produced by ArtifactFilesDownloaderResultConverter.
    self.assertLen(converted, 1)
    self.assertNotIsInstance(converted[0],
                             file.ExportedArtifactFilesDownloaderResult)

  def testYieldsOneResultAndOneOriginalValueForFileStatEntry(self):
    result = collectors.ArtifactFilesDownloaderResult(
        original_result=self.file_stat)

    converter = file.ArtifactFilesDownloaderResultConverter()
    converted = list(converter.Convert(self.metadata, result))

    default_exports = [
        v for v in converted
        if not isinstance(v, file.ExportedArtifactFilesDownloaderResult)
    ]
    self.assertLen(default_exports, 1)
    self.assertLen(default_exports, 1)

    downloader_exports = [
        v for v in converted
        if isinstance(v, file.ExportedArtifactFilesDownloaderResult)
    ]
    self.assertLen(downloader_exports, 1)
    self.assertEqual(downloader_exports[0].original_file.basename, "bar.exe")

  def testYieldsOneResultForRegistryStatEntryIfNoPathspecsWereFound(self):
    result = collectors.ArtifactFilesDownloaderResult(
        original_result=self.registry_stat)

    converter = file.ArtifactFilesDownloaderResultConverter()
    converted = list(converter.Convert(self.metadata, result))

    downloader_exports = [
        v for v in converted
        if isinstance(v, file.ExportedArtifactFilesDownloaderResult)
    ]
    self.assertLen(downloader_exports, 1)
    self.assertEqual(downloader_exports[0].original_registry_key.type, "REG_SZ")
    self.assertEqual(downloader_exports[0].original_registry_key.data,
                     b"C:\\Windows\\Sidebar.exe")

  def testIncludesRegistryStatEntryFoundPathspecIntoYieldedResult(self):
    result = collectors.ArtifactFilesDownloaderResult(
        original_result=self.registry_stat,
        found_pathspec=rdf_paths.PathSpec(path="foo", pathtype="OS"))

    converter = file.ArtifactFilesDownloaderResultConverter()
    converted = list(converter.Convert(self.metadata, result))

    downloader_exports = [
        v for v in converted
        if isinstance(v, file.ExportedArtifactFilesDownloaderResult)
    ]
    self.assertLen(downloader_exports, 1)
    self.assertEqual(downloader_exports[0].found_path, "foo")

  def testIncludesFileStatEntryFoundPathspecIntoYieldedResult(self):
    result = collectors.ArtifactFilesDownloaderResult(
        original_result=self.file_stat, found_pathspec=self.file_stat.pathspec)

    converter = file.ArtifactFilesDownloaderResultConverter()
    converted = list(converter.Convert(self.metadata, result))

    downloader_exports = [
        v for v in converted
        if isinstance(v, file.ExportedArtifactFilesDownloaderResult)
    ]
    self.assertLen(downloader_exports, 1)
    self.assertEqual(downloader_exports[0].found_path, "/tmp/bar.exe")

  def testIncludesDownloadedFileIntoResult(self):
    result = collectors.ArtifactFilesDownloaderResult(
        original_result=self.registry_stat,
        found_pathspec=rdf_paths.PathSpec(path="foo", pathtype="OS"),
        downloaded_file=rdf_client_fs.StatEntry(
            pathspec=rdf_paths.PathSpec(path="foo", pathtype="OS")))

    converter = file.ArtifactFilesDownloaderResultConverter()
    converted = list(converter.Convert(self.metadata, result))

    downloader_exports = [
        v for v in converted
        if isinstance(v, file.ExportedArtifactFilesDownloaderResult)
    ]
    self.assertLen(downloader_exports, 1)
    self.assertEqual(downloader_exports[0].downloaded_file.basename, "foo")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
