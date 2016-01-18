#!/usr/bin/env python
"""This modules contains tests for hunts API handlers."""



import pdb

from grr.gui import api_test_lib

from grr.gui.api_plugins import hunt as hunt_plugin
from grr.lib import access_control
from grr.lib import aff4
from grr.lib import flags
from grr.lib import output_plugin
from grr.lib import test_lib
from grr.lib.flows.general import processes
from grr.lib.hunts import process_results
from grr.lib.hunts import standard_test
from grr.lib.rdfvalues import client as rdf_client


class ApiListHuntsHandlerTest(test_lib.GRRBaseTest,
                              standard_test.StandardHuntTestMixin):
  """Test for ApiAff4Handler."""

  def setUp(self):
    super(ApiListHuntsHandlerTest, self).setUp()
    self.handler = hunt_plugin.ApiListHuntsHandler()

  def testRendersListOfHuntObjects(self):
    for i in range(10):
      self.CreateHunt(description="hunt_%d" % i)

    result = self.handler.Render(hunt_plugin.ApiListHuntsArgs(),
                                 token=self.token)
    descriptions = set(r["summary"]["description"]["value"]
                       for r in result["items"])

    self.assertEqual(len(descriptions), 10)
    for i in range(10):
      self.assertTrue("hunt_%d" % i in descriptions)

  def testHuntListIsSortedInReversedCreationTimestampOrder(self):
    for i in range(1, 11):
      with test_lib.FakeTime(i * 1000):
        self.CreateHunt(description="hunt_%d" % i)

    result = self.handler.Render(hunt_plugin.ApiListHuntsArgs(),
                                 token=self.token)
    create_times = [r["summary"]["create_time"]["value"]
                    for r in result["items"]]

    self.assertEqual(len(create_times), 10)
    for index, expected_time in enumerate(reversed(range(1, 11))):
      self.assertEqual(create_times[index], expected_time * 1000000000)

  def testRendersSubrangeOfListOfHuntObjects(self):
    for i in range(1, 11):
      with test_lib.FakeTime(i * 1000):
        self.CreateHunt(description="hunt_%d" % i)

    result = self.handler.Render(hunt_plugin.ApiListHuntsArgs(
        offset=2, count=2), token=self.token)
    create_times = [r["summary"]["create_time"]["value"]
                    for r in result["items"]]

    self.assertEqual(len(create_times), 2)
    self.assertEqual(create_times[0], 8 * 1000000000)
    self.assertEqual(create_times[1], 7 * 1000000000)

  def testFiltersHuntsByActivityTime(self):
    for i in range(1, 11):
      with test_lib.FakeTime(i * 60):
        self.CreateHunt(description="hunt_%d" % i)

    with test_lib.FakeTime(10 * 60 + 1):
      result = self.handler.Render(hunt_plugin.ApiListHuntsArgs(
          active_within="2m"), token=self.token)

    create_times = [r["summary"]["create_time"]["value"]
                    for r in result["items"]]

    self.assertEqual(len(create_times), 2)
    self.assertEqual(create_times[0], 10 * 60 * 1000000)
    self.assertEqual(create_times[1], 9 * 60 * 1000000)

  def testRaisesIfCreatedByFilterUsedWithoutActiveWithinFilter(self):
    self.assertRaises(ValueError, self.handler.Render,
                      hunt_plugin.ApiListHuntsArgs(
                          created_by="user-bar"), token=self.token)

  def testFiltersHuntsByCreator(self):
    for i in range(5):
      self.CreateHunt(description="foo_hunt_%d" % i,
                      token=access_control.ACLToken(username="user-foo"))

    for i in range(3):
      self.CreateHunt(description="bar_hunt_%d" % i,
                      token=access_control.ACLToken(username="user-bar"))

    result = self.handler.Render(hunt_plugin.ApiListHuntsArgs(
        created_by="user-foo", active_within="1d"), token=self.token)
    self.assertEqual(len(result["items"]), 5)
    for item in result["items"]:
      self.assertEqual(item["summary"]["creator"]["value"], "user-foo")

    result = self.handler.Render(hunt_plugin.ApiListHuntsArgs(
        created_by="user-bar", active_within="1d"), token=self.token)
    self.assertEqual(len(result["items"]), 3)
    for item in result["items"]:
      self.assertEqual(item["summary"]["creator"]["value"], "user-bar")

  def testRaisesIfDescriptionContainsFilterUsedWithoutActiveWithinFilter(self):
    self.assertRaises(ValueError, self.handler.Render,
                      hunt_plugin.ApiListHuntsArgs(
                          description_contains="foo"), token=self.token)

  def testFiltersHuntsByDescriptionContainsMatch(self):
    for i in range(5):
      self.CreateHunt(description="foo_hunt_%d" % i)

    for i in range(3):
      self.CreateHunt(description="bar_hunt_%d")

    result = self.handler.Render(hunt_plugin.ApiListHuntsArgs(
        description_contains="foo", active_within="1d"), token=self.token)
    self.assertEqual(len(result["items"]), 5)
    for item in result["items"]:
      self.assertTrue("foo" in item["summary"]["description"]["value"])

    result = self.handler.Render(hunt_plugin.ApiListHuntsArgs(
        description_contains="bar", active_within="1d"), token=self.token)
    self.assertEqual(len(result["items"]), 3)
    for item in result["items"]:
      self.assertTrue("bar" in item["summary"]["description"]["value"])

  def testOffsetIsRelativeToFilteredResultsWhenFilterIsPresent(self):
    for i in range(5):
      self.CreateHunt(description="foo_hunt_%d" % i)

    for i in range(3):
      self.CreateHunt(description="bar_hunt_%d" % i)

    result = self.handler.Render(
        hunt_plugin.ApiListHuntsArgs(
            description_contains="bar", active_within="1d", offset=1),
        token=self.token)
    self.assertEqual(len(result["items"]), 2)
    for item in result["items"]:
      self.assertTrue("bar" in item["summary"]["description"]["value"])

    result = self.handler.Render(
        hunt_plugin.ApiListHuntsArgs(
            description_contains="bar", active_within="1d", offset=2),
        token=self.token)
    self.assertEqual(len(result["items"]), 1)
    for item in result["items"]:
      self.assertTrue("bar" in item["summary"]["description"]["value"])

    result = self.handler.Render(
        hunt_plugin.ApiListHuntsArgs(
            description_contains="bar", active_within="1d", offset=3),
        token=self.token)
    self.assertEqual(len(result["items"]), 0)


class ApiListHuntsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest,
    standard_test.StandardHuntTestMixin):

  handler = "ApiListHuntsHandler"

  def Run(self):
    replace = {}
    for i in range(0, 2):
      with test_lib.FakeTime((1 + i) * 1000):
        with self.CreateHunt(description="hunt_%d" % i) as hunt_obj:
          if i % 2:
            hunt_obj.Stop()

          replace[hunt_obj.urn.Basename()] = "H:00000%d" % i

    self.Check("GET", "/api/hunts", replace=replace)
    self.Check("GET", "/api/hunts?count=1", replace=replace)
    self.Check("GET", "/api/hunts?offset=1&count=1", replace=replace)


class ApiGetHuntHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest,
    standard_test.StandardHuntTestMixin):

  handler = "ApiGetHuntHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      with self.CreateHunt(description="the hunt") as hunt_obj:
        hunt_urn = hunt_obj.urn

    self.Check("GET", "/api/hunts/" + hunt_urn.Basename(),
               replace={hunt_urn.Basename(): "H:123456"})


class ApiListHuntLogsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest,
    standard_test.StandardHuntTestMixin):

  handler = "ApiListHuntLogsHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      with self.CreateHunt(description="the hunt") as hunt_obj:

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


class ApiListHuntErrorsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest,
    standard_test.StandardHuntTestMixin):

  handler = "ApiListHuntErrorsHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      with self.CreateHunt(description="the hunt") as hunt_obj:

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


class ApiArchiveHuntFilesHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest,
    standard_test.StandardHuntTestMixin):
  handler = "ApiArchiveHuntFilesHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      with self.CreateHunt(description="the hunt") as hunt_obj:
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


class ApiGetHuntResultsExportCommandHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest,
    standard_test.StandardHuntTestMixin):

  handler = "ApiGetHuntResultsExportCommandHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      with self.CreateHunt(description="the hunt") as hunt_obj:
        pass

    self.Check(
        "GET", "/api/hunts/%s/results/export-command" % hunt_obj.urn.Basename(),
        replace={hunt_obj.urn.Basename(): "H:123456"})


class DummyHuntTestOutputPlugin(output_plugin.OutputPlugin):
  """A dummy output plugin."""

  name = "dummy"
  description = "Dummy do do."
  args_type = processes.ListProcessesArgs

  def ProcessResponses(self, responses):
    pass


class ApiListHuntOutputPluginsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest,
    standard_test.StandardHuntTestMixin):

  handler = "ApiListHuntOutputPluginsHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      with self.CreateHunt(
          description="the hunt",
          output_plugins=[
              output_plugin.OutputPluginDescriptor(
                  plugin_name=DummyHuntTestOutputPlugin.__name__,
                  plugin_args=DummyHuntTestOutputPlugin.args_type(
                      filename_regex="blah!",
                      fetch_binaries=True))]) as hunt_obj:
        pass

    self.Check(
        "GET", "/api/hunts/%s/output-plugins" % hunt_obj.urn.Basename(),
        replace={hunt_obj.urn.Basename(): "H:123456"})


class ApiListHuntOutputPluginLogsHandlerTest(
    test_lib.GRRBaseTest, standard_test.StandardHuntTestMixin):
  """Test for ApiListHuntOutputPluginLogsHandler."""

  def setUp(self):
    super(ApiListHuntOutputPluginLogsHandlerTest, self).setUp()

    self.client_ids = self.SetupClients(5)
    self.handler = hunt_plugin.ApiListHuntOutputPluginLogsHandler()
    self.output_plugins = [
        output_plugin.OutputPluginDescriptor(
            plugin_name=DummyHuntTestOutputPlugin.__name__,
            plugin_args=DummyHuntTestOutputPlugin.args_type(
                filename_regex="foo")),
        output_plugin.OutputPluginDescriptor(
            plugin_name=DummyHuntTestOutputPlugin.__name__,
            plugin_args=DummyHuntTestOutputPlugin.args_type(
                filename_regex="bar"))]

  def RunHuntWithOutputPlugins(self, output_plugins):
    hunt_urn = self.StartHunt(
        description="the hunt",
        output_plugins=output_plugins)

    for client_id in self.client_ids:
      self.AssignTasksToClients(client_ids=[client_id])
      self.RunHunt(failrate=-1)
      self.ProcessHuntOutputPlugins()

    return hunt_urn

  def testReturnsLogsWhenJustOnePlugin(self):
    hunt_urn = self.RunHuntWithOutputPlugins([self.output_plugins[0]])
    result = self.handler.Render(
        hunt_plugin.ApiListHuntOutputPluginLogsArgs(
            hunt_id=hunt_urn.Basename(),
            plugin_id=DummyHuntTestOutputPlugin.__name__ + "_0"),
        token=self.token)

    self.assertEqual(result["count"], 5)
    self.assertEqual(result["total_count"], 5)
    self.assertEqual(len(result["items"]), 5)
    for item in result["items"]:
      self.assertEqual("foo",
                       item["value"]["plugin_descriptor"]
                       ["value"]["plugin_args"]
                       ["value"]["filename_regex"]["value"])

  def testReturnsLogsWhenMultiplePlugins(self):
    hunt_urn = self.RunHuntWithOutputPlugins(self.output_plugins)
    result = self.handler.Render(
        hunt_plugin.ApiListHuntOutputPluginLogsArgs(
            hunt_id=hunt_urn.Basename(),
            plugin_id=DummyHuntTestOutputPlugin.__name__ + "_1"),
        token=self.token)

    self.assertEqual(result["count"], 5)
    self.assertEqual(result["total_count"], 5)
    self.assertEqual(len(result["items"]), 5)
    for item in result["items"]:
      self.assertEqual("bar",
                       item["value"]["plugin_descriptor"]
                       ["value"]["plugin_args"]
                       ["value"]["filename_regex"]["value"])

  def testSlicesLogsWhenJustOnePlugin(self):
    hunt_urn = self.RunHuntWithOutputPlugins([self.output_plugins[0]])
    result = self.handler.Render(
        hunt_plugin.ApiListHuntOutputPluginLogsArgs(
            hunt_id=hunt_urn.Basename(), offset=2, count=2,
            plugin_id=DummyHuntTestOutputPlugin.__name__ + "_0"),
        token=self.token)

    self.assertEqual(result["count"], 2)
    self.assertEqual(result["total_count"], 5)
    self.assertEqual(len(result["items"]), 2)

  def testSlicesLogsWhenMultiplePlugins(self):
    hunt_urn = self.RunHuntWithOutputPlugins(self.output_plugins)
    result = self.handler.Render(
        hunt_plugin.ApiListHuntOutputPluginLogsArgs(
            hunt_id=hunt_urn.Basename(), offset=2, count=2,
            plugin_id=DummyHuntTestOutputPlugin.__name__ + "_1"),
        token=self.token)

    self.assertEqual(result["count"], 2)
    self.assertEqual(result["total_count"], 5)
    self.assertEqual(len(result["items"]), 2)


class ApiListHuntOutputPluginLogsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest,
    standard_test.StandardHuntTestMixin):

  handler = "ApiListHuntOutputPluginLogsHandler"

  def Run(self):
    with test_lib.FakeTime(42, increment=1):
      hunt_urn = self.StartHunt(
          description="the hunt",
          output_plugins=[
              output_plugin.OutputPluginDescriptor(
                  plugin_name=DummyHuntTestOutputPlugin.__name__,
                  plugin_args=DummyHuntTestOutputPlugin.args_type(
                      filename_regex="blah!",
                      fetch_binaries=True))])

      self.client_ids = self.SetupClients(2)
      for index, client_id in enumerate(self.client_ids):
        self.AssignTasksToClients(client_ids=[client_id])
        self.RunHunt(failrate=-1)
        with test_lib.FakeTime(100042 + index * 100):
          self.ProcessHuntOutputPlugins()

    self.Check(
        "GET", "/api/hunts/%s/output-plugins/"
        "DummyHuntTestOutputPlugin_0/logs" % hunt_urn.Basename(),
        replace={hunt_urn.Basename(): "H:123456"})


class ApiListHuntOutputPluginErrorsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest,
    standard_test.StandardHuntTestMixin):

  handler = "ApiListHuntOutputPluginErrorsHandler"

  def Run(self):
    with test_lib.FakeTime(42, increment=1):
      hunt_urn = self.StartHunt(
          description="the hunt",
          output_plugins=[
              output_plugin.OutputPluginDescriptor(
                  plugin_name=
                  standard_test.FailingDummyHuntOutputPlugin.__name__)])

      self.client_ids = self.SetupClients(2)
      for index, client_id in enumerate(self.client_ids):
        self.AssignTasksToClients(client_ids=[client_id])
        self.RunHunt(failrate=-1)
        with test_lib.FakeTime(100042 + index * 100):
          try:
            self.ProcessHuntOutputPlugins()
          except process_results.ResultsProcessingError:
            if flags.FLAGS.debug:
              pdb.post_mortem()

    self.Check(
        "GET", "/api/hunts/%s/output-plugins/"
        "FailingDummyHuntOutputPlugin_0/errors" % hunt_urn.Basename(),
        replace={hunt_urn.Basename(): "H:123456"})


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
