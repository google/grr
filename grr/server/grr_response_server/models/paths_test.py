#!/usr/bin/env python
from absl.testing import absltest

from grr_response_proto import objects_pb2
from grr_response_server.models import paths as models_paths
from grr_response_server.rdfvalues import mig_objects


class IsRootPathInfoTest(absltest.TestCase):

  def testEmptyProto(self):
    path_info = objects_pb2.PathInfo()
    self.assertTrue(models_paths.IsRootPathInfo(path_info))

    # TODO: Remove when rdf_objects.PathInfo is removed.
    rdf_path_info = mig_objects.ToRDFPathInfo(path_info)
    self.assertEqual(models_paths.IsRootPathInfo(path_info), rdf_path_info.root)

  def testEmptyList(self):
    path_info = objects_pb2.PathInfo(components=[])
    self.assertTrue(models_paths.IsRootPathInfo(path_info))

    # TODO: Remove when rdf_objects.PathInfo is removed.
    rdf_path_info = mig_objects.ToRDFPathInfo(path_info)
    self.assertEqual(models_paths.IsRootPathInfo(path_info), rdf_path_info.root)

  def testNonEmptyList(self):
    path_info = objects_pb2.PathInfo(components=["foo"])
    self.assertFalse(models_paths.IsRootPathInfo(path_info))

    # TODO: Remove when rdf_objects.PathInfo is removed.
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

    # TODO: Remove when rdf_objects.PathInfo is removed.
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

    # TODO: Remove when rdf_objects.PathInfo is removed.
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

    # TODO: Remove when rdf_objects.PathInfo is removed.
    rdf_path_info = mig_objects.ToRDFPathInfo(path_info)
    self.assertEqual(parent_path_info, rdf_path_info.GetParent())


class GetAncestorPathInfosTest(absltest.TestCase):

  def testEmpty(self):
    path_info = objects_pb2.PathInfo(components=["foo"])

    results = list(models_paths.GetAncestorPathInfos(path_info))
    self.assertLen(results, 1)
    self.assertEqual(results[0].components, [])

    # TODO: Remove when rdf_objects.PathInfo is removed.
    rdf_results = list(mig_objects.ToRDFPathInfo(path_info).GetAncestors())
    self.assertEqual(results[0].components, rdf_results[0].components)
    self.assertEqual(results[0].directory, rdf_results[0].directory)
    self.assertEqual(results[0].path_type, rdf_results[0].path_type)

  def testRoot(self):
    path_info = objects_pb2.PathInfo(components=["foo"])

    results = list(models_paths.GetAncestorPathInfos(path_info))
    self.assertLen(results, 1)
    self.assertEqual(results[0].components, [])

    # TODO: Remove when rdf_objects.PathInfo is removed.
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

    # TODO: Remove when rdf_objects.PathInfo is removed.
    rdf_results = list(mig_objects.ToRDFPathInfo(path_info).GetAncestors())
    for i in range(4):
      self.assertEqual(results[i].components, rdf_results[i].components)
      self.assertEqual(results[i].directory, rdf_results[i].directory)
      self.assertEqual(results[i].path_type, rdf_results[i].path_type)


if __name__ == "__main__":
  absltest.main()
