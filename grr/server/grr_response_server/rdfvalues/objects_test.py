#!/usr/bin/env python
import os
import tempfile

from absl import app
from absl.testing import absltest

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import test_base as rdf_test_base
from grr_response_proto import objects_pb2
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import test_lib


class PathIDTest(rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  rdfvalue_class = rdf_objects.PathID

  def GenerateSample(self, number=0):
    return rdf_objects.PathID.FromComponents(["a"] * number)

  def testFromBytes(self):
    foo = rdf_objects.PathID(b"12345678" * 4)
    self.assertEqual(foo, b"12345678" * 4)

  def testFromRDFBytes(self):
    foo = rdf_objects.PathID(rdfvalue.RDFBytes(b"12345678" * 4))
    self.assertEqual(foo, b"12345678" * 4)

  def testFromBytesValidatesType(self):
    with self.assertRaises(TypeError):
      rdf_objects.PathID(42)

  def testFromBytesValidatesLength(self):
    with self.assertRaises(ValueError):
      rdf_objects.PathID(b"foobar")

  def testStr(self):
    string = str(rdf_objects.PathID.FromComponents(["foo", "bar", "baz"]))
    self.assertRegex(string, r"^PathID\(\'[0-9a-f]{64}\'\)$")

  def testStrEmpty(self):
    string = str(rdf_objects.PathID.FromComponents([]))
    self.assertEqual(string, "PathID('{}')".format("0" * 64))

  def testDefaultsToNull(self):
    string = str(rdf_objects.PathID())
    self.assertEqual(string, "PathID('{}')".format("0" * 64))


class PathInfoTest(absltest.TestCase):

  def testValidateEmptyComponent(self):
    with self.assertRaisesRegex(ValueError, "Empty"):
      rdf_objects.PathInfo(components=["foo", "", "bar"])

  def testValidateDotComponent(self):
    with self.assertRaisesRegex(ValueError, "Incorrect"):
      rdf_objects.PathInfo(components=["foo", "bar", ".", "quux"])

  def testValidateDoubleDotComponent(self):
    with self.assertRaisesRegex(ValueError, "Incorrect"):
      rdf_objects.PathInfo(components=["..", "foo", "bar"])

  def testFromStatEntrySimple(self):
    stat_entry = rdf_client_fs.StatEntry()
    stat_entry.pathspec.path = "foo/bar/baz"
    stat_entry.pathspec.pathtype = rdf_paths.PathSpec.PathType.OS

    path_info = rdf_objects.PathInfo.FromStatEntry(stat_entry)
    self.assertEqual(path_info.path_type, rdf_objects.PathInfo.PathType.OS)
    self.assertEqual(path_info.components, ["foo", "bar", "baz"])
    self.assertFalse(path_info.directory)

  def testFromStatEntryNested(self):
    stat_entry = rdf_client_fs.StatEntry()
    stat_entry.pathspec.path = "foo/bar"
    stat_entry.pathspec.pathtype = rdf_paths.PathSpec.PathType.TSK
    stat_entry.pathspec.nested_path.path = "norf/quux"
    stat_entry.pathspec.nested_path.pathtype = rdf_paths.PathSpec.PathType.TSK

    path_info = rdf_objects.PathInfo.FromStatEntry(stat_entry)
    self.assertEqual(path_info.path_type, rdf_objects.PathInfo.PathType.TSK)
    self.assertEqual(path_info.components, ["foo", "bar", "norf", "quux"])
    self.assertFalse(path_info.directory)

  def testFromStatEntryOsAndTsk(self):
    stat_entry = rdf_client_fs.StatEntry()
    stat_entry.pathspec.path = "foo"
    stat_entry.pathspec.pathtype = rdf_paths.PathSpec.PathType.OS
    stat_entry.pathspec.nested_path.path = "bar"
    stat_entry.pathspec.nested_path.pathtype = rdf_paths.PathSpec.PathType.TSK

    path_info = rdf_objects.PathInfo.FromStatEntry(stat_entry)
    self.assertEqual(path_info.path_type, rdf_objects.PathInfo.PathType.TSK)
    self.assertEqual(path_info.components, ["foo", "bar"])
    self.assertFalse(path_info.directory)

  def testFromStatEntryRegistry(self):
    stat_entry = rdf_client_fs.StatEntry()
    stat_entry.pathspec.path = "foo/bar"
    stat_entry.pathspec.pathtype = rdf_paths.PathSpec.PathType.REGISTRY

    path_info = rdf_objects.PathInfo.FromStatEntry(stat_entry)
    self.assertEqual(
        path_info.path_type, rdf_objects.PathInfo.PathType.REGISTRY
    )
    self.assertEqual(path_info.components, ["foo", "bar"])
    self.assertFalse(path_info.directory)

  def testFromStatEntryTemp(self):
    stat_entry = rdf_client_fs.StatEntry()
    stat_entry.pathspec.path = "tmp/quux"
    stat_entry.pathspec.pathtype = rdf_paths.PathSpec.PathType.TMPFILE

    path_info = rdf_objects.PathInfo.FromStatEntry(stat_entry)
    self.assertEqual(path_info.path_type, rdf_objects.PathInfo.PathType.TEMP)
    self.assertEqual(path_info.components, ["tmp", "quux"])
    self.assertFalse(path_info.directory)

  def testFromStatEntryOffset(self):
    stat_entry = rdf_client_fs.StatEntry()
    stat_entry.pathspec.path = "foo/bar/baz"
    stat_entry.pathspec.pathtype = rdf_paths.PathSpec.PathType.TSK
    stat_entry.pathspec.offset = 2048

    path_info = rdf_objects.PathInfo.FromStatEntry(stat_entry)
    self.assertEqual(path_info.path_type, rdf_objects.PathInfo.PathType.TSK)
    self.assertEqual(path_info.components, ["foo", "bar", "baz:2048"])

  def testFromStatEntryAds(self):
    stat_entry = rdf_client_fs.StatEntry()
    stat_entry.pathspec.path = "foo/bar/baz"
    stat_entry.pathspec.pathtype = rdf_paths.PathSpec.PathType.OS
    stat_entry.pathspec.stream_name = "quux"

    path_info = rdf_objects.PathInfo.FromStatEntry(stat_entry)
    self.assertEqual(path_info.path_type, rdf_objects.PathInfo.PathType.OS)
    self.assertEqual(path_info.components, ["foo", "bar", "baz:quux"])

  def testFromStatEntryMetadata(self):
    stat_entry = rdf_client_fs.StatEntry()
    stat_entry.pathspec.path = "foo/bar"
    stat_entry.pathspec.pathtype = rdf_paths.PathSpec.PathType.OS

    stat_obj = os.stat(tempfile.gettempdir())
    stat_entry.st_mode = stat_obj.st_mode
    stat_entry.st_ino = stat_obj.st_ino
    stat_entry.st_dev = stat_obj.st_dev

    path_info = rdf_objects.PathInfo.FromStatEntry(stat_entry)
    self.assertEqual(path_info.path_type, rdf_objects.PathInfo.PathType.OS)
    self.assertEqual(path_info.components, ["foo", "bar"])
    self.assertTrue(path_info.directory)
    self.assertEqual(path_info.stat_entry.st_mode, stat_obj.st_mode)
    self.assertEqual(path_info.stat_entry.st_ino, stat_obj.st_ino)
    self.assertEqual(path_info.stat_entry.st_dev, stat_obj.st_dev)

  def testBasenameRoot(self):
    path_info = rdf_objects.PathInfo.OS(components=[], directory=True)
    self.assertEqual(path_info.basename, "")

  def testBasenameSingleComponent(self):
    path_info = rdf_objects.PathInfo.OS(components=["foo"], directory=False)
    self.assertEqual(path_info.basename, "foo")

  def testBasenameMultiComponent(self):
    path_info = rdf_objects.PathInfo.TSK(
        components=["foo", "bar", "baz", "quux"]
    )
    self.assertEqual(path_info.basename, "quux")

  def testGetParentNonRoot(self):
    path_info = rdf_objects.PathInfo.TSK(
        components=["foo", "bar"], directory=False
    )

    parent_path_info = path_info.GetParent()
    self.assertIsNotNone(parent_path_info)
    self.assertEqual(parent_path_info.components, ["foo"])
    self.assertEqual(
        parent_path_info.path_type, rdf_objects.PathInfo.PathType.TSK
    )
    self.assertEqual(parent_path_info.directory, True)

  def testGetParentAlmostRoot(self):
    path_info = rdf_objects.PathInfo.OS(components=["foo"], directory=False)

    parent_path_info = path_info.GetParent()
    self.assertIsNotNone(parent_path_info)
    self.assertEqual(parent_path_info.components, [])
    self.assertEqual(
        parent_path_info.path_type, rdf_objects.PathInfo.PathType.OS
    )
    self.assertTrue(parent_path_info.root)
    self.assertTrue(parent_path_info.directory)

  def testGetParentRoot(self):
    path_info = rdf_objects.PathInfo.Registry(components=[], directory=True)

    self.assertIsNone(path_info.GetParent())

  def testGetAncestorsEmpty(self):
    path_info = rdf_objects.PathInfo(components=[], directory=True)
    self.assertEqual(list(path_info.GetAncestors()), [])

  def testGetAncestorsRoot(self):
    path_info = rdf_objects.PathInfo(components=["foo"])

    results = list(path_info.GetAncestors())
    self.assertLen(results, 1)
    self.assertEqual(results[0].components, [])

  def testGetAncestorsOrder(self):
    path_info = rdf_objects.PathInfo(components=["foo", "bar", "baz", "quux"])

    results = list(path_info.GetAncestors())
    self.assertLen(results, 4)
    self.assertEqual(results[0].components, ["foo", "bar", "baz"])
    self.assertEqual(results[1].components, ["foo", "bar"])
    self.assertEqual(results[2].components, ["foo"])
    self.assertEqual(results[3].components, [])

  def testUpdateFromValidatesType(self):
    with self.assertRaises(TypeError):
      rdf_objects.PathInfo(
          components=["usr", "local", "bin"],
      ).UpdateFrom("/usr/local/bin")

  def testUpdateFromValidatesPathType(self):
    with self.assertRaises(ValueError):
      rdf_objects.PathInfo.OS(components=["usr", "local", "bin"]).UpdateFrom(
          rdf_objects.PathInfo.TSK(components=["usr", "local", "bin"])
      )

  def testUpdateFromValidatesComponents(self):
    with self.assertRaises(ValueError):
      rdf_objects.PathInfo(components=["usr", "local", "bin"]).UpdateFrom(
          rdf_objects.PathInfo(components=["usr", "local", "bin", "protoc"])
      )

  def testUpdateFromStatEntryUpdate(self):
    dst = rdf_objects.PathInfo(components=["foo", "bar"])

    stat_entry = rdf_client_fs.StatEntry(st_mode=1337)
    src = rdf_objects.PathInfo(components=["foo", "bar"], stat_entry=stat_entry)

    dst.UpdateFrom(src)
    self.assertEqual(dst.stat_entry.st_mode, 1337)

  def testUpdateFromStatEntryOverride(self):
    stat_entry = rdf_client_fs.StatEntry(st_mode=707)
    dst = rdf_objects.PathInfo(components=["foo", "bar"], stat_entry=stat_entry)

    stat_entry = rdf_client_fs.StatEntry(st_mode=1337)
    src = rdf_objects.PathInfo(components=["foo", "bar"], stat_entry=stat_entry)

    dst.UpdateFrom(src)
    self.assertEqual(dst.stat_entry.st_mode, 1337)

  def testUpdateFromStatEntryRetain(self):
    stat_entry = rdf_client_fs.StatEntry(st_mode=707)
    dst = rdf_objects.PathInfo(components=["foo", "bar"], stat_entry=stat_entry)

    src = rdf_objects.PathInfo(components=["foo", "bar"])

    dst.UpdateFrom(src)
    self.assertEqual(dst.stat_entry.st_mode, 707)

  def testUpdateFromDirectory(self):
    dest = rdf_objects.PathInfo(components=["usr", "local", "bin"])
    self.assertFalse(dest.directory)
    dest.UpdateFrom(
        rdf_objects.PathInfo(components=["usr", "local", "bin"], directory=True)
    )
    self.assertTrue(dest.directory)

  def testMergePathInfoLastUpdate(self):
    components = ["usr", "local", "bin"]
    dest = rdf_objects.PathInfo(components=components)
    self.assertIsNone(dest.last_stat_entry_timestamp)

    dest.UpdateFrom(
        rdf_objects.PathInfo(
            components=components,
            last_stat_entry_timestamp=rdfvalue.RDFDatetime.FromHumanReadable(
                "2017-01-01"
            ),
        )
    )
    self.assertEqual(
        dest.last_stat_entry_timestamp,
        rdfvalue.RDFDatetime.FromHumanReadable("2017-01-01"),
    )

    # Merging in a record without last_stat_entry_timestamp shouldn't change
    # it.
    dest.UpdateFrom(rdf_objects.PathInfo(components=components))
    self.assertEqual(
        dest.last_stat_entry_timestamp,
        rdfvalue.RDFDatetime.FromHumanReadable("2017-01-01"),
    )

    # Merging in a record with an earlier last_stat_entry_timestamp shouldn't
    # change it.
    dest.UpdateFrom(
        rdf_objects.PathInfo(
            components=components,
            last_stat_entry_timestamp=rdfvalue.RDFDatetime.FromHumanReadable(
                "2016-01-01"
            ),
        )
    )
    self.assertEqual(
        dest.last_stat_entry_timestamp,
        rdfvalue.RDFDatetime.FromHumanReadable("2017-01-01"),
    )

    # Merging in a record with a later last_stat_entry_timestamp should change
    # it.
    dest.UpdateFrom(
        rdf_objects.PathInfo(
            components=components,
            last_stat_entry_timestamp=rdfvalue.RDFDatetime.FromHumanReadable(
                "2018-01-01"
            ),
        )
    )
    self.assertEqual(
        dest.last_stat_entry_timestamp,
        rdfvalue.RDFDatetime.FromHumanReadable("2018-01-01"),
    )


class CategorizedPathTest(absltest.TestCase):

  def testParseOs(self):
    path_type, components = rdf_objects.ParseCategorizedPath("fs/os/foo/bar")
    self.assertEqual(path_type, objects_pb2.PathInfo.PathType.OS)
    self.assertEqual(components, ("foo", "bar"))

  def testParseTsk(self):
    path_type, components = rdf_objects.ParseCategorizedPath("fs/tsk/quux/norf")
    self.assertEqual(path_type, objects_pb2.PathInfo.PathType.TSK)
    self.assertEqual(components, ("quux", "norf"))

  def testParseNtfs(self):
    path_type, components = rdf_objects.ParseCategorizedPath(
        "fs/ntfs/quux/norf"
    )
    self.assertEqual(path_type, objects_pb2.PathInfo.PathType.NTFS)
    self.assertEqual(components, ("quux", "norf"))

  def testParseRegistry(self):
    path_type, components = rdf_objects.ParseCategorizedPath(
        "registry/thud/blargh"
    )
    self.assertEqual(path_type, objects_pb2.PathInfo.PathType.REGISTRY)
    self.assertEqual(components, ("thud", "blargh"))

  def testParseTemp(self):
    path_type, components = rdf_objects.ParseCategorizedPath("temp/os/registry")
    self.assertEqual(path_type, objects_pb2.PathInfo.PathType.TEMP)
    self.assertEqual(components, ("os", "registry"))

  def testParseOsRoot(self):
    path_type, components = rdf_objects.ParseCategorizedPath("fs/os")
    self.assertEqual(path_type, objects_pb2.PathInfo.PathType.OS)
    self.assertEqual(components, ())

  def testParseTskExtraSlashes(self):
    path_type, components = rdf_objects.ParseCategorizedPath(
        "/fs///tsk/foo///bar"
    )
    self.assertEqual(path_type, objects_pb2.PathInfo.PathType.TSK)
    self.assertEqual(components, ("foo", "bar"))

  def testParseIncorrect(self):
    with self.assertRaisesRegex(ValueError, "does not start with a VFS prefix"):
      rdf_objects.ParseCategorizedPath("foo/bar")

    with self.assertRaisesRegex(ValueError, "does not start with a VFS prefix"):
      rdf_objects.ParseCategorizedPath("fs")

  def testSerializeOs(self):
    path_type = rdf_objects.PathInfo.PathType.OS
    path = rdf_objects.ToCategorizedPath(path_type, ("foo", "bar"))
    self.assertEqual(path, "fs/os/foo/bar")

  def testSerializeTsk(self):
    path_type = rdf_objects.PathInfo.PathType.TSK
    path = rdf_objects.ToCategorizedPath(path_type, ("quux", "norf"))
    self.assertEqual(path, "fs/tsk/quux/norf")

  def testSerializeNtfs(self):
    path_type = rdf_objects.PathInfo.PathType.NTFS
    path = rdf_objects.ToCategorizedPath(path_type, ("quux", "norf"))
    self.assertEqual(path, "fs/ntfs/quux/norf")

  def testSerializeRegistry(self):
    path_type = rdf_objects.PathInfo.PathType.REGISTRY
    path = rdf_objects.ToCategorizedPath(path_type, ("thud", "baz"))
    self.assertEqual(path, "registry/thud/baz")

  def testSerializeTemp(self):
    path_type = rdf_objects.PathInfo.PathType.TEMP
    path = rdf_objects.ToCategorizedPath(path_type, ("blargh",))
    self.assertEqual(path, "temp/blargh")

  def testSerializeOsRoot(self):
    path_type = rdf_objects.PathInfo.PathType.OS
    path = rdf_objects.ToCategorizedPath(path_type, ())
    self.assertEqual(path, "fs/os")

  def testSerializeIncorrectType(self):
    with self.assertRaisesRegex(ValueError, "type"):
      rdf_objects.ToCategorizedPath("MEMORY", ("foo", "bar"))


class VfsFileReferenceToPathTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.client_id = "C.0000000000000000"

  def testOsPathIsConvertedVfsPathStringCorrectly(self):
    v = objects_pb2.VfsFileReference(
        client_id=self.client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        path_components=["a", "b", "c"],
    )
    self.assertEqual(rdf_objects.VfsFileReferenceToPath(v), "fs/os/a/b/c")

  def testTskPathIsConvertedVfsPathStringCorrectly(self):
    v = objects_pb2.VfsFileReference(
        client_id=self.client_id,
        path_type=objects_pb2.PathInfo.PathType.TSK,
        path_components=["a", "b", "c"],
    )
    self.assertEqual(rdf_objects.VfsFileReferenceToPath(v), "fs/tsk/a/b/c")

  def testNtfsPathIsConvertedVfsPathStringCorrectly(self):
    v = objects_pb2.VfsFileReference(
        client_id=self.client_id,
        path_type=objects_pb2.PathInfo.PathType.NTFS,
        path_components=["a", "b", "c"],
    )
    self.assertEqual(rdf_objects.VfsFileReferenceToPath(v), "fs/ntfs/a/b/c")

  def testRegistryPathIsConvertedVfsPathStringCorrectly(self):
    v = objects_pb2.VfsFileReference(
        client_id=self.client_id,
        path_type=objects_pb2.PathInfo.PathType.REGISTRY,
        path_components=["a", "b", "c"],
    )
    self.assertEqual(rdf_objects.VfsFileReferenceToPath(v), "registry/a/b/c")

  def testTempPathIsConvertedVfsPathStringCorrectly(self):
    v = objects_pb2.VfsFileReference(
        client_id=self.client_id,
        path_type=objects_pb2.PathInfo.PathType.TEMP,
        path_components=["a", "b", "c"],
    )
    self.assertEqual(rdf_objects.VfsFileReferenceToPath(v), "temp/a/b/c")

  def testConvertingPathVfsPathStringWithUnknownTypeRaises(self):
    with self.assertRaises(ValueError):
      rdf_objects.VfsFileReferenceToPath(objects_pb2.VfsFileReference())


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
