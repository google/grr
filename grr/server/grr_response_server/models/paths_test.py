#!/usr/bin/env python
from absl.testing import absltest

from grr_response_core.lib.rdfvalues import mig_client_fs
from grr_response_core.lib.rdfvalues import mig_paths
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_server.models import paths as models_paths
from grr_response_server.rdfvalues import mig_objects
from grr_response_server.rdfvalues import objects as rdf_objects


class IsRootPathInfoTest(absltest.TestCase):

  def testEmptyProto(self):
    path_info = objects_pb2.PathInfo()
    self.assertTrue(models_paths.IsRootPathInfo(path_info))

    # TODO - Remove when rdf_objects.PathInfo is removed.
    rdf_path_info = mig_objects.ToRDFPathInfo(path_info)
    self.assertEqual(models_paths.IsRootPathInfo(path_info), rdf_path_info.root)

  def testEmptyList(self):
    path_info = objects_pb2.PathInfo(components=[])
    self.assertTrue(models_paths.IsRootPathInfo(path_info))

    # TODO - Remove when rdf_objects.PathInfo is removed.
    rdf_path_info = mig_objects.ToRDFPathInfo(path_info)
    self.assertEqual(models_paths.IsRootPathInfo(path_info), rdf_path_info.root)

  def testNonEmptyList(self):
    path_info = objects_pb2.PathInfo(components=["foo"])
    self.assertFalse(models_paths.IsRootPathInfo(path_info))

    # TODO - Remove when rdf_objects.PathInfo is removed.
    rdf_path_info = mig_objects.ToRDFPathInfo(path_info)
    self.assertEqual(models_paths.IsRootPathInfo(path_info), rdf_path_info.root)


class GetParentPathInfoTest(absltest.TestCase):

  def testNonRoot(self):
    path_info = objects_pb2.PathInfo(
        path_type=objects_pb2.PathInfo.PathType.TSK,
        components=["foo", "bar"],
        directory=False,
    )
    parent_path_info = models_paths.GetParentPathInfo(path_info)
    self.assertIsNotNone(parent_path_info)
    self.assertEqual(parent_path_info.components, ["foo"])
    self.assertEqual(
        parent_path_info.path_type, objects_pb2.PathInfo.PathType.TSK
    )
    self.assertTrue(parent_path_info.directory)

    # TODO - Remove when rdf_objects.PathInfo is removed.
    rdf_path_info = mig_objects.ToRDFPathInfo(path_info)
    self.assertEqual(
        parent_path_info, mig_objects.ToProtoPathInfo(rdf_path_info.GetParent())
    )

  def testAlmostRoot(self):
    path_info = objects_pb2.PathInfo(
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=["foo"],
        directory=False,
    )
    parent_path_info = models_paths.GetParentPathInfo(path_info)
    self.assertIsNotNone(parent_path_info)
    self.assertEqual(parent_path_info.components, [])
    self.assertEqual(
        parent_path_info.path_type, objects_pb2.PathInfo.PathType.OS
    )
    self.assertTrue(parent_path_info.directory)

    # TODO - Remove when rdf_objects.PathInfo is removed.
    rdf_path_info = mig_objects.ToRDFPathInfo(path_info)
    self.assertEqual(
        parent_path_info, mig_objects.ToProtoPathInfo(rdf_path_info.GetParent())
    )

  def testRoot(self):
    path_info = objects_pb2.PathInfo(
        path_type=objects_pb2.PathInfo.PathType.REGISTRY,
        components=[],
        directory=True,
    )
    parent_path_info = models_paths.GetParentPathInfo(path_info)
    self.assertIsNone(parent_path_info)

    # TODO - Remove when rdf_objects.PathInfo is removed.
    rdf_path_info = mig_objects.ToRDFPathInfo(path_info)
    self.assertEqual(parent_path_info, rdf_path_info.GetParent())


class GetAncestorPathInfosTest(absltest.TestCase):

  def testEmpty(self):
    path_info = objects_pb2.PathInfo(components=["foo"])

    results = list(models_paths.GetAncestorPathInfos(path_info))
    self.assertLen(results, 1)
    self.assertEqual(results[0].components, [])

    # TODO - Remove when rdf_objects.PathInfo is removed.
    rdf_results = list(mig_objects.ToRDFPathInfo(path_info).GetAncestors())
    self.assertEqual(results[0].components, rdf_results[0].components)
    self.assertEqual(results[0].directory, rdf_results[0].directory)
    self.assertEqual(results[0].path_type, rdf_results[0].path_type)

  def testRoot(self):
    path_info = objects_pb2.PathInfo(components=["foo"])

    results = list(models_paths.GetAncestorPathInfos(path_info))
    self.assertLen(results, 1)
    self.assertEqual(results[0].components, [])

    # TODO - Remove when rdf_objects.PathInfo is removed.
    rdf_results = list(mig_objects.ToRDFPathInfo(path_info).GetAncestors())
    self.assertEqual(results[0].components, rdf_results[0].components)
    self.assertEqual(results[0].directory, rdf_results[0].directory)
    self.assertEqual(results[0].path_type, rdf_results[0].path_type)

  def testOrder(self):
    path_info = objects_pb2.PathInfo(components=["foo", "bar", "baz", "quux"])

    results = list(models_paths.GetAncestorPathInfos(path_info))
    self.assertLen(results, 4)
    self.assertEqual(results[0].components, ["foo", "bar", "baz"])
    self.assertEqual(results[1].components, ["foo", "bar"])
    self.assertEqual(results[2].components, ["foo"])
    self.assertEqual(results[3].components, [])

    # TODO - Remove when rdf_objects.PathInfo is removed.
    rdf_results = list(mig_objects.ToRDFPathInfo(path_info).GetAncestors())
    for i in range(4):
      self.assertEqual(results[i].components, rdf_results[i].components)
      self.assertEqual(results[i].directory, rdf_results[i].directory)
      self.assertEqual(results[i].path_type, rdf_results[i].path_type)


class PathInfoFromPathSpecTest(absltest.TestCase):

  def testOS(self):
    pathspec = jobs_pb2.PathSpec(
        path="/foo/bar", pathtype=jobs_pb2.PathSpec.PathType.OS
    )
    path_info = models_paths.PathInfoFromPathSpec(pathspec)
    self.assertEqual(path_info.path_type, objects_pb2.PathInfo.PathType.OS)
    self.assertEqual(path_info.components, ["foo", "bar"])

    # TODO - Remove when rdf_objects.PathInfo is removed.
    rdf_pathspec = mig_paths.ToRDFPathSpec(pathspec)
    rdf_path_info = rdf_objects.PathInfo.FromPathSpec(rdf_pathspec)
    self.assertEqual(path_info, mig_objects.ToProtoPathInfo(rdf_path_info))

  def testNested(self):
    pathspec_inner = jobs_pb2.PathSpec(
        path="inner", pathtype=jobs_pb2.PathSpec.PathType.TSK
    )
    pathspec_outer = jobs_pb2.PathSpec(
        path="/outer",
        pathtype=jobs_pb2.PathSpec.PathType.OS,
        nested_path=pathspec_inner,
    )
    path_info = models_paths.PathInfoFromPathSpec(pathspec_outer)
    self.assertEqual(path_info.path_type, objects_pb2.PathInfo.PathType.TSK)
    self.assertEqual(path_info.components, ["outer", "inner"])

    # TODO - Remove when rdf_objects.PathInfo is removed.
    rdf_pathspec = mig_paths.ToRDFPathSpec(pathspec_outer)
    rdf_path_info = rdf_objects.PathInfo.FromPathSpec(rdf_pathspec)
    self.assertEqual(path_info, mig_objects.ToProtoPathInfo(rdf_path_info))

  def testOffsetAndStream(self):
    pathspec = jobs_pb2.PathSpec(
        path="/foo",
        offset=10,
        stream_name="bar",
        pathtype=jobs_pb2.PathSpec.PathType.NTFS,
    )
    path_info = models_paths.PathInfoFromPathSpec(pathspec)
    self.assertEqual(path_info.path_type, objects_pb2.PathInfo.PathType.NTFS)
    self.assertEqual(path_info.components, ["foo:10:bar"])

    # TODO - Remove when rdf_objects.PathInfo is removed.
    rdf_pathspec = mig_paths.ToRDFPathSpec(pathspec)
    rdf_path_info = rdf_objects.PathInfo.FromPathSpec(rdf_pathspec)
    self.assertEqual(path_info, mig_objects.ToProtoPathInfo(rdf_path_info))

  def testRegistry(self):
    pathspec = jobs_pb2.PathSpec(
        path="foo/bar", pathtype=jobs_pb2.PathSpec.PathType.REGISTRY
    )
    path_info = models_paths.PathInfoFromPathSpec(pathspec)
    self.assertEqual(
        path_info.path_type, objects_pb2.PathInfo.PathType.REGISTRY
    )
    self.assertEqual(path_info.components, ["foo", "bar"])

    # TODO - Remove when rdf_objects.PathInfo is removed.
    rdf_pathspec = mig_paths.ToRDFPathSpec(pathspec)
    rdf_path_info = rdf_objects.PathInfo.FromPathSpec(rdf_pathspec)
    self.assertEqual(path_info, mig_objects.ToProtoPathInfo(rdf_path_info))

  def testTemp(self):
    pathspec = jobs_pb2.PathSpec(
        path="tmp/quux", pathtype=jobs_pb2.PathSpec.PathType.TMPFILE
    )
    path_info = models_paths.PathInfoFromPathSpec(pathspec)
    self.assertEqual(path_info.path_type, objects_pb2.PathInfo.PathType.TEMP)
    self.assertEqual(path_info.components, ["tmp", "quux"])

    # TODO - Remove when rdf_objects.PathInfo is removed.
    rdf_pathspec = mig_paths.ToRDFPathSpec(pathspec)
    rdf_path_info = rdf_objects.PathInfo.FromPathSpec(rdf_pathspec)
    self.assertEqual(path_info, mig_objects.ToProtoPathInfo(rdf_path_info))

  def testMultiNested(self):
    pathspec_inner = jobs_pb2.PathSpec(
        path="norf/quux", pathtype=jobs_pb2.PathSpec.PathType.TSK
    )
    pathspec_outer = jobs_pb2.PathSpec(
        path="foo/bar",
        pathtype=jobs_pb2.PathSpec.PathType.TSK,
        nested_path=pathspec_inner,
    )
    path_info = models_paths.PathInfoFromPathSpec(pathspec_outer)
    self.assertEqual(path_info.path_type, objects_pb2.PathInfo.PathType.TSK)
    self.assertEqual(path_info.components, ["foo", "bar", "norf", "quux"])

    # TODO - Remove when rdf_objects.PathInfo is removed.
    rdf_pathspec = mig_paths.ToRDFPathSpec(pathspec_outer)
    rdf_path_info = rdf_objects.PathInfo.FromPathSpec(rdf_pathspec)
    self.assertEqual(path_info, mig_objects.ToProtoPathInfo(rdf_path_info))


class PathInfoFromStatEntryTest(absltest.TestCase):

  def testFile(self):
    pathspec = jobs_pb2.PathSpec(
        path="/foo", pathtype=jobs_pb2.PathSpec.PathType.OS
    )
    stat_entry = jobs_pb2.StatEntry(pathspec=pathspec, st_mode=0o100644)
    path_info = models_paths.PathInfoFromStatEntry(stat_entry)
    self.assertEqual(path_info.components, ["foo"])
    self.assertFalse(path_info.directory)
    self.assertEqual(path_info.stat_entry, stat_entry)

    # TODO - Remove when rdf_objects.PathInfo is removed.
    rdf_stat_entry = mig_client_fs.ToRDFStatEntry(stat_entry)
    rdf_path_info = rdf_objects.PathInfo.FromStatEntry(rdf_stat_entry)
    self.assertEqual(path_info, mig_objects.ToProtoPathInfo(rdf_path_info))

  def testDirectory(self):
    pathspec = jobs_pb2.PathSpec(
        path="/bar", pathtype=jobs_pb2.PathSpec.PathType.OS
    )
    stat_entry = jobs_pb2.StatEntry(pathspec=pathspec, st_mode=0o040755)
    path_info = models_paths.PathInfoFromStatEntry(stat_entry)
    self.assertEqual(path_info.components, ["bar"])
    self.assertTrue(path_info.directory)
    self.assertEqual(path_info.stat_entry, stat_entry)

    # TODO - Remove when rdf_objects.PathInfo is removed.
    rdf_stat_entry = mig_client_fs.ToRDFStatEntry(stat_entry)
    rdf_path_info = rdf_objects.PathInfo.FromStatEntry(rdf_stat_entry)
    self.assertEqual(path_info, mig_objects.ToProtoPathInfo(rdf_path_info))

  def testMetadata(self):
    pathspec = jobs_pb2.PathSpec(
        path="/foo/bar", pathtype=jobs_pb2.PathSpec.PathType.OS
    )
    stat_entry = jobs_pb2.StatEntry(
        pathspec=pathspec,
        st_mode=0o040755,
        st_ino=12345,
        st_dev=67890,
    )
    path_info = models_paths.PathInfoFromStatEntry(stat_entry)
    self.assertEqual(path_info.path_type, objects_pb2.PathInfo.PathType.OS)
    self.assertEqual(path_info.components, ["foo", "bar"])
    self.assertTrue(path_info.directory)
    self.assertEqual(path_info.stat_entry.st_mode, 0o040755)
    self.assertEqual(path_info.stat_entry.st_ino, 12345)
    self.assertEqual(path_info.stat_entry.st_dev, 67890)

    # TODO - Remove when rdf_objects.PathInfo is removed.
    rdf_stat_entry = mig_client_fs.ToRDFStatEntry(stat_entry)
    rdf_path_info = rdf_objects.PathInfo.FromStatEntry(rdf_stat_entry)
    self.assertEqual(path_info, mig_objects.ToProtoPathInfo(rdf_path_info))


if __name__ == "__main__":
  absltest.main()
