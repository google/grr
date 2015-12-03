#!/usr/bin/env python
"""This modules contains tests for AFF4 API handlers."""



from grr.gui import api_test_lib
from grr.gui.api_plugins import aff4 as aff4_plugin

from grr.lib import aff4
from grr.lib import flags
from grr.lib import test_lib


class ApiGetAff4ObjectHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiGetAff4ObjectHandler."""

  def setUp(self):
    super(ApiGetAff4ObjectHandlerTest, self).setUp()
    self.handler = aff4_plugin.ApiGetAff4ObjectHandler()

  def testRendersAff4ObjectWithGivenPath(self):
    with test_lib.FakeTime(42):
      with aff4.FACTORY.Create("aff4:/tmp/foo/bar", "AFF4Volume",
                               token=self.token) as _:
        pass

    result = self.handler.Render(
        aff4_plugin.ApiGetAff4ObjectArgs(aff4_path="tmp/foo/bar"),
        token=self.token)
    self.assertEqual(result["urn"], "aff4:/tmp/foo/bar")
    self.assertEqual(result["aff4_class"], "AFF4Volume")
    self.assertEqual(result["age_policy"], "NEWEST_TIME")
    self.assertEqual(result["attributes"]["metadata:last"], {
        "value": 42000000,
        "type": "RDFDatetime",
        "age": 42000000})


class ApiGetAff4ObjectHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):

  handler = "ApiGetAff4ObjectHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      with aff4.FACTORY.Create("aff4:/foo/bar", "AFF4Object",
                               mode="rw", token=self.token) as sample_object:
        # Add labels to have some attributes filled in.
        sample_object.AddLabels("label1", "label2")

    self.Check("GET", "/api/aff4/foo/bar")


class ApiGetAff4IndexHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiGetAff4IndexHandlerTest."""

  def setUp(self):
    super(ApiGetAff4IndexHandlerTest, self).setUp()
    self.handler = aff4_plugin.ApiGetAff4IndexHandler()

  def testReturnsChildrenListWithTimestamps(self):
    with test_lib.FakeTime(42):
      with aff4.FACTORY.Create("aff4:/tmp/foo/bar1", "AFF4Volume",
                               token=self.token) as _:
        pass

    with test_lib.FakeTime(43):
      with aff4.FACTORY.Create("aff4:/tmp/foo/bar2", "AFF4Volume",
                               token=self.token) as _:
        pass

    result = self.handler.Render(
        aff4_plugin.ApiGetAff4IndexArgs(aff4_path="tmp/foo"),
        token=self.token)
    result = sorted(result, key=lambda x: x[0])
    self.assertEqual(result,
                     [["aff4:/tmp/foo/bar1", 42000000],
                      ["aff4:/tmp/foo/bar2", 43000000]])


class ApiGetAff4IndexHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):

  handler = "ApiGetAff4IndexHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      with aff4.FACTORY.Create("some/path", "AFF4Volume", token=self.token):
        pass

    with test_lib.FakeTime(43):
      with aff4.FACTORY.Create("some/path/foo", "AFF4Volume", token=self.token):
        pass

    with test_lib.FakeTime(44):
      with aff4.FACTORY.Create("some/path/bar", "AFF4Volume", token=self.token):
        pass

    self.Check("GET", "/api/aff4-index/some/path")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
