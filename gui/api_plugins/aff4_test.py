#!/usr/bin/env python
"""This modules contains tests for AFF4 API renderers."""



from grr.gui.api_plugins import aff4 as aff4_plugin

from grr.lib import aff4
from grr.lib import flags
from grr.lib import test_lib
from grr.lib import utils


class ApiAff4RendererTest(test_lib.GRRBaseTest):
  """Test for ApiAff4Renderer."""

  def setUp(self):
    super(ApiAff4RendererTest, self).setUp()
    self.renderer = aff4_plugin.ApiAff4Renderer()

  def testRendersAff4ObjectWithGivenPath(self):
    with test_lib.FakeTime(42):
      with aff4.FACTORY.Create("aff4:/tmp/foo/bar", "AFF4Volume",
                               token=self.token) as _:
        pass

    result = self.renderer.Render(utils.DataObject(aff4_path="tmp/foo/bar",
                                                   token=self.token))
    self.assertEqual(result["urn"], "aff4:/tmp/foo/bar")
    self.assertEqual(result["aff4_class"], "AFF4Volume")
    self.assertEqual(result["age_policy"], "NEWEST_TIME")
    self.assertEqual(result["attributes"]["metadata:last"], 42000000)


class ApiAff4IndexRendererTest(test_lib.GRRBaseTest):
  """Test for ApiAff4IndexRendererTest."""

  def setUp(self):
    super(ApiAff4IndexRendererTest, self).setUp()
    self.renderer = aff4_plugin.ApiAff4IndexRenderer()

  def testReturnsChildrenListWithTimestamps(self):
    with test_lib.FakeTime(42):
      with aff4.FACTORY.Create("aff4:/tmp/foo/bar1", "AFF4Volume",
                               token=self.token) as _:
        pass

    with test_lib.FakeTime(43):
      with aff4.FACTORY.Create("aff4:/tmp/foo/bar2", "AFF4Volume",
                               token=self.token) as _:
        pass

    result = self.renderer.Render(utils.DataObject(aff4_path="tmp/foo",
                                                   token=self.token))
    result = sorted(result, key=lambda x: x[0])
    self.assertEqual(result,
                     [["aff4:/tmp/foo/bar1", 42000000],
                      ["aff4:/tmp/foo/bar2", 43000000]])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
