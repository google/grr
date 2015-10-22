#!/usr/bin/env python
"""This modules contains tests for hunts API renderers."""



from grr.gui import api_test_lib
from grr.gui.api_plugins import hunt as hunt_plugin

from grr.lib import aff4
from grr.lib import access_control
from grr.lib import flags
from grr.lib import flow_runner
from grr.lib import hunts
from grr.lib import test_lib
from grr.lib.flows.general import transfer
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths


class ApiHuntsListRendererTest(test_lib.GRRBaseTest):
  """Test for ApiAff4Renderer."""

  @staticmethod
  def CreateSampleHunt(description, token=None):
    return hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        description=description,
        flow_runner_args=flow_runner.FlowRunnerArgs(
            flow_name="GetFile"),
        flow_args=transfer.GetFileArgs(
            pathspec=rdf_paths.PathSpec(
                path="/tmp/evil.txt",
                pathtype=rdf_paths.PathSpec.PathType.OS,
            )
        ), client_rate=0, token=token)

  def setUp(self):
    super(ApiHuntsListRendererTest, self).setUp()
    self.renderer = hunt_plugin.ApiHuntsListRenderer()

  def QueryParams(self, **kwargs):
    result = self.renderer.QuerySpec.HandleQueryParams(kwargs)
    result.token = self.token
    return result

  def testRendersListOfHuntObjects(self):
    for i in range(10):
      self.CreateSampleHunt("hunt_%d" % i, token=self.token)

    result = self.renderer.Render(hunt_plugin.ApiHuntsListRendererArgs(),
                                  token=self.token)
    descriptions = set(r["summary"]["description"]["value"]
                       for r in result["items"])

    self.assertEqual(len(descriptions), 10)
    for i in range(10):
      self.assertTrue("hunt_%d" % i in descriptions)

  def testHuntListIsSortedInReversedCreationTimestampOrder(self):
    for i in range(1, 11):
      with test_lib.FakeTime(i * 1000):
        self.CreateSampleHunt("hunt_%d" % i, token=self.token)

    result = self.renderer.Render(hunt_plugin.ApiHuntsListRendererArgs(),
                                  token=self.token)
    create_times = [r["summary"]["create_time"]["value"]
                    for r in result["items"]]

    self.assertEqual(len(create_times), 10)
    for index, expected_time in enumerate(reversed(range(1, 11))):
      self.assertEqual(create_times[index], expected_time * 1000000000)

  def testRendersSubrangeOfListOfHuntObjects(self):
    for i in range(1, 11):
      with test_lib.FakeTime(i * 1000):
        self.CreateSampleHunt("hunt_%d" % i, token=self.token)

    result = self.renderer.Render(hunt_plugin.ApiHuntsListRendererArgs(
        offset=2, count=2), token=self.token)
    create_times = [r["summary"]["create_time"]["value"]
                    for r in result["items"]]

    self.assertEqual(len(create_times), 2)
    self.assertEqual(create_times[0], 8 * 1000000000)
    self.assertEqual(create_times[1], 7 * 1000000000)

  def testFiltersHuntsByActivityTime(self):
    for i in range(1, 11):
      with test_lib.FakeTime(i * 60):
        self.CreateSampleHunt("hunt_%d" % i, token=self.token)

    with test_lib.FakeTime(10 * 60 + 1):
      result = self.renderer.Render(hunt_plugin.ApiHuntsListRendererArgs(
          active_within="2m"), token=self.token)

    create_times = [r["summary"]["create_time"]["value"]
                    for r in result["items"]]

    self.assertEqual(len(create_times), 2)
    self.assertEqual(create_times[0], 10 * 60 * 1000000)
    self.assertEqual(create_times[1], 9 * 60 * 1000000)

  def testRaisesIfCreatedByFilterUsedWithoutActiveWithinFilter(self):
    self.assertRaises(ValueError, self.renderer.Render,
                      hunt_plugin.ApiHuntsListRendererArgs(
                          created_by="user-bar"), token=self.token)

  def testFiltersHuntsByCreator(self):
    for i in range(5):
      self.CreateSampleHunt("foo_hunt_%d" % i,
                            token=access_control.ACLToken(username="user-foo"))

    for i in range(3):
      self.CreateSampleHunt("bar_hunt_%d" % i,
                            token=access_control.ACLToken(username="user-bar"))

    result = self.renderer.Render(hunt_plugin.ApiHuntsListRendererArgs(
        created_by="user-foo", active_within="1d"), token=self.token)
    self.assertEqual(len(result["items"]), 5)
    for item in result["items"]:
      self.assertEqual(item["summary"]["creator"]["value"], "user-foo")

    result = self.renderer.Render(hunt_plugin.ApiHuntsListRendererArgs(
        created_by="user-bar", active_within="1d"), token=self.token)
    self.assertEqual(len(result["items"]), 3)
    for item in result["items"]:
      self.assertEqual(item["summary"]["creator"]["value"], "user-bar")

  def testRaisesIfDescriptionContainsFilterUsedWithoutActiveWithinFilter(self):
    self.assertRaises(ValueError, self.renderer.Render,
                      hunt_plugin.ApiHuntsListRendererArgs(
                          description_contains="foo"), token=self.token)

  def testFiltersHuntsByDescriptionContainsMatch(self):
    for i in range(5):
      self.CreateSampleHunt("foo_hunt_%d" % i, token=self.token)

    for i in range(3):
      self.CreateSampleHunt("bar_hunt_%d" % i, token=self.token)

    result = self.renderer.Render(hunt_plugin.ApiHuntsListRendererArgs(
        description_contains="foo", active_within="1d"), token=self.token)
    self.assertEqual(len(result["items"]), 5)
    for item in result["items"]:
      self.assertTrue("foo" in item["summary"]["description"]["value"])

    result = self.renderer.Render(hunt_plugin.ApiHuntsListRendererArgs(
        description_contains="bar", active_within="1d"), token=self.token)
    self.assertEqual(len(result["items"]), 3)
    for item in result["items"]:
      self.assertTrue("bar" in item["summary"]["description"]["value"])

  def testOffsetIsRelativeToFilteredResultsWhenFilterIsPresent(self):
    for i in range(5):
      self.CreateSampleHunt("foo_hunt_%d" % i, token=self.token)

    for i in range(3):
      self.CreateSampleHunt("bar_hunt_%d" % i, token=self.token)

    result = self.renderer.Render(
        hunt_plugin.ApiHuntsListRendererArgs(
            description_contains="bar", active_within="1d", offset=1),
        token=self.token)
    self.assertEqual(len(result["items"]), 2)
    for item in result["items"]:
      self.assertTrue("bar" in item["summary"]["description"]["value"])

    result = self.renderer.Render(
        hunt_plugin.ApiHuntsListRendererArgs(
            description_contains="bar", active_within="1d", offset=2),
        token=self.token)
    self.assertEqual(len(result["items"]), 1)
    for item in result["items"]:
      self.assertTrue("bar" in item["summary"]["description"]["value"])

    result = self.renderer.Render(
        hunt_plugin.ApiHuntsListRendererArgs(
            description_contains="bar", active_within="1d", offset=3),
        token=self.token)
    self.assertEqual(len(result["items"]), 0)


class ApiHuntsListRendererRegressionTest(
    api_test_lib.ApiCallRendererRegressionTest):

  renderer = "ApiHuntsListRenderer"

  def Run(self):
    replace = {}
    for i in range(0, 2):
      with test_lib.FakeTime((1 + i) * 1000):
        with ApiHuntsListRendererTest.CreateSampleHunt(
            "hunt_%d" % i, token=self.token) as hunt_obj:
          if i % 2:
            hunt_obj.Stop()

          replace[hunt_obj.urn.Basename()] = "H:00000%d" % i

    self.Check("GET", "/api/hunts", replace=replace)
    self.Check("GET", "/api/hunts?count=1", replace=replace)
    self.Check("GET", "/api/hunts?offset=1&count=1", replace=replace)


class ApiHuntSummaryRendererRegressionTest(
    api_test_lib.ApiCallRendererRegressionTest):

  renderer = "ApiHuntSummaryRenderer"

  def Run(self):
    with test_lib.FakeTime(42):
      with ApiHuntsListRendererTest.CreateSampleHunt(
          "the hunt", token=self.token) as hunt_obj:
        hunt_urn = hunt_obj.urn

    self.Check("GET", "/api/hunts/" + hunt_urn.Basename(),
               replace={hunt_urn.Basename(): "H:123456"})


class ApiHuntLogRendererRegressionTest(
    api_test_lib.ApiCallRendererRegressionTest):

  renderer = "ApiHuntLogRenderer"

  def Run(self):
    with test_lib.FakeTime(42):
      with ApiHuntsListRendererTest.CreateSampleHunt(
          "the hunt", token=self.token) as hunt_obj:

        with test_lib.FakeTime(52):
          hunt_obj.Log("Sample message: foo.")

        with test_lib.FakeTime(55):
          hunt_obj.Log("Sample message: bar.")

    self.Check("GET", "/api/hunts/%s/log" % hunt_obj.urn.Basename(),
               replace={hunt_obj.urn.Basename(): "H:123456"})
    self.Check("GET", "/api/hunts/%s/log?count=1" % hunt_obj.urn.Basename(),
               replace={hunt_obj.urn.Basename(): "H:123456"})
    self.Check("GET", ("/api/hunts/%s/log?offset=1&count=1" %
                       hunt_obj.urn.Basename()),
               replace={hunt_obj.urn.Basename(): "H:123456"})


class ApiHuntErrorsRendererRegressionTest(
    api_test_lib.ApiCallRendererRegressionTest):

  renderer = "ApiHuntErrorsRenderer"

  def Run(self):
    with test_lib.FakeTime(42):
      with ApiHuntsListRendererTest.CreateSampleHunt(
          "the hunt", token=self.token) as hunt_obj:

        with test_lib.FakeTime(52):
          hunt_obj.LogClientError(rdf_client.ClientURN("C.0000111122223333"),
                                  "Error foo.")

        with test_lib.FakeTime(55):
          hunt_obj.LogClientError(rdf_client.ClientURN("C.1111222233334444"),
                                  "Error bar.", "<some backtrace>")

    self.Check("GET", "/api/hunts/%s/errors" % hunt_obj.urn.Basename(),
               replace={hunt_obj.urn.Basename(): "H:123456"})
    self.Check("GET", "/api/hunts/%s/errors?count=1" % hunt_obj.urn.Basename(),
               replace={hunt_obj.urn.Basename(): "H:123456"})
    self.Check("GET", ("/api/hunts/%s/errors?offset=1&count=1" %
                       hunt_obj.urn.Basename()),
               replace={hunt_obj.urn.Basename(): "H:123456"})


class ApiHuntArchiveFilesRendererRegressionTest(
    api_test_lib.ApiCallRendererRegressionTest):
  renderer = "ApiHuntArchiveFilesRenderer"

  def Run(self):
    with test_lib.FakeTime(42):
      with ApiHuntsListRendererTest.CreateSampleHunt(
          "the hunt", token=self.token) as hunt_obj:
        pass

    def ReplaceFlowAndHuntId():
      flows_fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add("flows"),
                                   token=self.token)
      flow_urn = list(flows_fd.ListChildren())[-1]

      return {flow_urn.Basename(): "W:123456",
              hunt_obj.urn.Basename(): "H:ABCDEF"}

    with test_lib.FakeTime(42):
      self.Check(
          "POST",
          "/api/hunts/%s/results/archive-files" % hunt_obj.urn.Basename(),
          replace=ReplaceFlowAndHuntId)


class ApiHuntResultsExportCommandRendererRegressionTest(
    api_test_lib.ApiCallRendererRegressionTest):

  renderer = "ApiHuntHuntResultsExportCommandRenderer"

  def Run(self):
    with test_lib.FakeTime(42):
      with ApiHuntsListRendererTest.CreateSampleHunt(
          "the hunt", token=self.token) as hunt_obj:
        pass

    self.Check(
        "GET", "/api/hunts/%s/results/export-command" % hunt_obj.urn.Basename(),
        replace={hunt_obj.urn.Basename(): "H:123456"})


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
