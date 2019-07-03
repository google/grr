#!/usr/bin/env python
"""Tests for grr_response_server.aff4_objects.standard."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from absl import app

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import aff4
from grr_response_server.aff4_objects import standard as aff4_standard
from grr.test_lib import aff4_test_lib
from grr.test_lib import test_lib


class LabelSetTest(aff4_test_lib.AFF4ObjectTest):

  def testAddListRemoveLabels(self):
    index = aff4.FACTORY.Create(
        "aff4:/index/labels/client_set_test",
        aff4_standard.LabelSet,
        mode="rw",
        token=self.token)
    self.assertListEqual([], index.ListLabels())
    index.Add("label1")
    index.Add("label2")
    self.assertListEqual(["label1", "label2"], sorted(index.ListLabels()))
    index.Remove("label2")
    index.Add("label3")
    self.assertListEqual(["label1", "label3"], sorted(index.ListLabels()))


class VFSDirectoryTest(aff4_test_lib.AFF4ObjectTest):

  def testRealPathspec(self):

    client_id = rdf_client.ClientURN("C.%016X" % 1234)
    for path in ["a/b", "a/b/c/d"]:
      d = aff4.FACTORY.Create(
          client_id.Add("fs/os").Add(path),
          aff4_type=aff4_standard.VFSDirectory,
          token=self.token)
      pathspec = rdf_paths.PathSpec(
          path=path, pathtype=rdf_paths.PathSpec.PathType.OS)
      d.Set(d.Schema.PATHSPEC, pathspec)
      d.Close()

    d = aff4.FACTORY.Create(
        client_id.Add("fs/os").Add("a/b/c"),
        aff4_type=aff4_standard.VFSDirectory,
        mode="rw",
        token=self.token)
    self.assertEqual(d.real_pathspec.CollapsePath(), "a/b/c")


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
