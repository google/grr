#!/usr/bin/env python
"""This modules contains tests for hunts API handlers."""



import os
import pdb
import StringIO
import tarfile
import zipfile


import yaml

from grr.gui import api_test_lib

from grr.gui.api_plugins import hunt as hunt_plugin
from grr.lib import access_control
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow_runner
from grr.lib import hunts
from grr.lib import output_plugin
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.flows.general import file_finder
from grr.lib.flows.general import processes
from grr.lib.hunts import process_results
from grr.lib.hunts import results as hunt_results
from grr.lib.hunts import standard_test
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows


class ApiListHuntsHandlerTest(test_lib.GRRBaseTest,
                              standard_test.StandardHuntTestMixin):
  """Test for ApiAff4Handler."""

  def setUp(self):
    super(ApiListHuntsHandlerTest, self).setUp()
    self.handler = hunt_plugin.ApiListHuntsHandler()

  def testHandlesListOfHuntObjects(self):
    for i in range(10):
      self.CreateHunt(description="hunt_%d" % i)

    result = self.handler.Handle(hunt_plugin.ApiListHuntsArgs(),
                                 token=self.token)
    descriptions = set(r.description for r in result.items)

    self.assertEqual(len(descriptions), 10)
    for i in range(10):
      self.assertTrue("hunt_%d" % i in descriptions)

  def testHuntListIsSortedInReversedCreationTimestampOrder(self):
    for i in range(1, 11):
      with test_lib.FakeTime(i * 1000):
        self.CreateHunt(description="hunt_%d" % i)

    result = self.handler.Handle(hunt_plugin.ApiListHuntsArgs(),
                                 token=self.token)
    create_times = [r.created.AsMicroSecondsFromEpoch() for r in result.items]

    self.assertEqual(len(create_times), 10)
    for index, expected_time in enumerate(reversed(range(1, 11))):
      self.assertEqual(create_times[index], expected_time * 1000000000)

  def testHandlesSubrangeOfListOfHuntObjects(self):
    for i in range(1, 11):
      with test_lib.FakeTime(i * 1000):
        self.CreateHunt(description="hunt_%d" % i)

    result = self.handler.Handle(
        hunt_plugin.ApiListHuntsArgs(offset=2, count=2),
        token=self.token)
    create_times = [r.created.AsMicroSecondsFromEpoch() for r in result.items]

    self.assertEqual(len(create_times), 2)
    self.assertEqual(create_times[0], 8 * 1000000000)
    self.assertEqual(create_times[1], 7 * 1000000000)

  def testFiltersHuntsByActivityTime(self):
    for i in range(1, 11):
      with test_lib.FakeTime(i * 60):
        self.CreateHunt(description="hunt_%d" % i)

    with test_lib.FakeTime(10 * 60 + 1):
      result = self.handler.Handle(
          hunt_plugin.ApiListHuntsArgs(active_within="2m"),
          token=self.token)

    create_times = [r.created for r in result.items]

    self.assertEqual(len(create_times), 2)
    self.assertEqual(create_times[0], 10 * 60 * 1000000)
    self.assertEqual(create_times[1], 9 * 60 * 1000000)

  def testRaisesIfCreatedByFilterUsedWithoutActiveWithinFilter(self):
    self.assertRaises(ValueError,
                      self.handler.Handle,
                      hunt_plugin.ApiListHuntsArgs(created_by="user-bar"),
                      token=self.token)

  def testFiltersHuntsByCreator(self):
    for i in range(5):
      self.CreateHunt(description="foo_hunt_%d" % i,
                      token=access_control.ACLToken(username="user-foo"))

    for i in range(3):
      self.CreateHunt(description="bar_hunt_%d" % i,
                      token=access_control.ACLToken(username="user-bar"))

    result = self.handler.Handle(
        hunt_plugin.ApiListHuntsArgs(created_by="user-foo",
                                     active_within="1d"),
        token=self.token)
    self.assertEqual(len(result.items), 5)
    for item in result.items:
      self.assertEqual(item.creator, "user-foo")

    result = self.handler.Handle(
        hunt_plugin.ApiListHuntsArgs(created_by="user-bar",
                                     active_within="1d"),
        token=self.token)
    self.assertEqual(len(result.items), 3)
    for item in result.items:
      self.assertEqual(item.creator, "user-bar")

  def testRaisesIfDescriptionContainsFilterUsedWithoutActiveWithinFilter(self):
    self.assertRaises(ValueError,
                      self.handler.Handle,
                      hunt_plugin.ApiListHuntsArgs(description_contains="foo"),
                      token=self.token)

  def testFiltersHuntsByDescriptionContainsMatch(self):
    for i in range(5):
      self.CreateHunt(description="foo_hunt_%d" % i)

    for i in range(3):
      self.CreateHunt(description="bar_hunt_%d")

    result = self.handler.Handle(
        hunt_plugin.ApiListHuntsArgs(description_contains="foo",
                                     active_within="1d"),
        token=self.token)
    self.assertEqual(len(result.items), 5)
    for item in result.items:
      self.assertTrue("foo" in item.description)

    result = self.handler.Handle(
        hunt_plugin.ApiListHuntsArgs(description_contains="bar",
                                     active_within="1d"),
        token=self.token)
    self.assertEqual(len(result.items), 3)
    for item in result.items:
      self.assertTrue("bar" in item.description)

  def testOffsetIsRelativeToFilteredResultsWhenFilterIsPresent(self):
    for i in range(5):
      self.CreateHunt(description="foo_hunt_%d" % i)

    for i in range(3):
      self.CreateHunt(description="bar_hunt_%d" % i)

    result = self.handler.Handle(
        hunt_plugin.ApiListHuntsArgs(description_contains="bar",
                                     active_within="1d",
                                     offset=1),
        token=self.token)
    self.assertEqual(len(result.items), 2)
    for item in result.items:
      self.assertTrue("bar" in item.description)

    result = self.handler.Handle(
        hunt_plugin.ApiListHuntsArgs(description_contains="bar",
                                     active_within="1d",
                                     offset=2),
        token=self.token)
    self.assertEqual(len(result.items), 1)
    for item in result.items:
      self.assertTrue("bar" in item.description)

    result = self.handler.Handle(
        hunt_plugin.ApiListHuntsArgs(description_contains="bar",
                                     active_within="1d",
                                     offset=3),
        token=self.token)
    self.assertEqual(len(result.items), 0)


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


class ApiListHuntResultsRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):

  handler = "ApiListHuntResultsHandler"

  def Run(self):
    hunt_urn = rdfvalue.RDFURN("aff4:/hunts/H:123456")
    results_urn = hunt_urn.Add("Results")

    with aff4.FACTORY.Create(results_urn,
                             aff4_type=hunt_results.HuntResultCollection,
                             token=self.token) as results:

      result = rdf_flows.GrrMessage(
          payload=rdfvalue.RDFString("blah1"),
          age=rdfvalue.RDFDatetime().FromSecondsFromEpoch(1))
      results.Add(result, timestamp=result.age + rdfvalue.Duration("1s"))

      result = rdf_flows.GrrMessage(
          payload=rdfvalue.RDFString("blah2-foo"),
          age=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42))
      results.Add(result, timestamp=result.age + rdfvalue.Duration("1s"))

    self.Check("GET", "/api/hunts/H:123456/results")
    self.Check("GET", "/api/hunts/H:123456/results?count=1")
    self.Check("GET", "/api/hunts/H:123456/results?offset=1&count=1")
    self.Check("GET", "/api/hunts/H:123456/results?filter=foo")


class ApiGetHuntHandlerRegressionTest(api_test_lib.ApiCallHandlerRegressionTest,
                                      standard_test.StandardHuntTestMixin):

  handler = "ApiGetHuntHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      with self.CreateHunt(description="the hunt") as hunt_obj:
        hunt_urn = hunt_obj.urn

        hunt_stats = hunt_obj.state.context.usage_stats
        hunt_stats.user_cpu_stats.sum = 5000
        hunt_stats.network_bytes_sent_stats.sum = 1000000

    self.Check("GET",
               "/api/hunts/" + hunt_urn.Basename(),
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

    self.Check("GET",
               "/api/hunts/%s/log" % hunt_obj.urn.Basename(),
               replace={hunt_obj.urn.Basename(): "H:123456"})
    self.Check("GET",
               "/api/hunts/%s/log?count=1" % hunt_obj.urn.Basename(),
               replace={hunt_obj.urn.Basename(): "H:123456"})
    self.Check("GET",
               ("/api/hunts/%s/log?offset=1&count=1" % hunt_obj.urn.Basename()),
               replace={hunt_obj.urn.Basename(): "H:123456"})


class ApiListHuntErrorsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest,
    standard_test.StandardHuntTestMixin):

  handler = "ApiListHuntErrorsHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      with self.CreateHunt(description="the hunt") as hunt_obj:

        with test_lib.FakeTime(52):
          hunt_obj.LogClientError(
              rdf_client.ClientURN("C.0000111122223333"), "Error foo.")

        with test_lib.FakeTime(55):
          hunt_obj.LogClientError(
              rdf_client.ClientURN("C.1111222233334444"), "Error bar.",
              "<some backtrace>")

    self.Check("GET",
               "/api/hunts/%s/errors" % hunt_obj.urn.Basename(),
               replace={hunt_obj.urn.Basename(): "H:123456"})
    self.Check("GET",
               "/api/hunts/%s/errors?count=1" % hunt_obj.urn.Basename(),
               replace={hunt_obj.urn.Basename(): "H:123456"})
    self.Check("GET", ("/api/hunts/%s/errors?offset=1&count=1" %
                       hunt_obj.urn.Basename()),
               replace={hunt_obj.urn.Basename(): "H:123456"})


class ApiGetHuntFilesArchiveHandlerTest(test_lib.GRRBaseTest,
                                        standard_test.StandardHuntTestMixin):

  def setUp(self):
    super(ApiGetHuntFilesArchiveHandlerTest, self).setUp()

    self.handler = hunt_plugin.ApiGetHuntFilesArchiveHandler()

    self.hunt = hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        flow_runner_args=flow_runner.FlowRunnerArgs(
            flow_name=file_finder.FileFinder.__name__),
        flow_args=file_finder.FileFinderArgs(
            paths=[os.path.join(self.base_path, "test.plist")],
            action=file_finder.FileFinderAction(action_type="DOWNLOAD"),),
        client_rate=0,
        token=self.token)
    self.hunt.Run()

    client_ids = self.SetupClients(10)
    self.AssignTasksToClients(client_ids=client_ids)
    action_mock = action_mocks.ActionMock("TransferBuffer", "StatFile",
                                          "HashFile", "HashBuffer")
    test_lib.TestHuntHelper(action_mock, client_ids, token=self.token)

  def testGeneratesZipArchive(self):
    result = self.handler.Handle(
        hunt_plugin.ApiGetHuntFilesArchiveArgs(hunt_id=self.hunt.urn.Basename(),
                                               archive_format="ZIP"),
        token=self.token)

    out_fd = StringIO.StringIO()
    for chunk in result.GenerateContent():
      out_fd.write(chunk)

    zip_fd = zipfile.ZipFile(out_fd, "r")
    manifest = None
    for name in zip_fd.namelist():
      if name.endswith("MANIFEST"):
        manifest = yaml.safe_load(zip_fd.read(name))

    self.assertEqual(manifest["archived_files"], 10)
    self.assertEqual(manifest["failed_files"], 0)
    self.assertEqual(manifest["processed_files"], 10)
    self.assertEqual(manifest["skipped_files"], 0)

  def testGeneratesTarGzArchive(self):
    result = self.handler.Handle(
        hunt_plugin.ApiGetHuntFilesArchiveArgs(hunt_id=self.hunt.urn.Basename(),
                                               archive_format="TAR_GZ"),
        token=self.token)

    with utils.TempDirectory() as temp_dir:
      tar_path = os.path.join(temp_dir, "archive.tar.gz")
      with open(tar_path, "w") as fd:
        for chunk in result.GenerateContent():
          fd.write(chunk)

      with tarfile.open(tar_path) as tar_fd:
        tar_fd.extractall(path=temp_dir)

      manifest_file_path = None
      for parent, _, files in os.walk(temp_dir):
        if "MANIFEST" in files:
          manifest_file_path = os.path.join(parent, "MANIFEST")
          break

      self.assertTrue(manifest_file_path)
      with open(manifest_file_path) as fd:
        manifest = yaml.safe_load(fd.read())

        self.assertEqual(manifest["archived_files"], 10)
        self.assertEqual(manifest["failed_files"], 0)
        self.assertEqual(manifest["processed_files"], 10)
        self.assertEqual(manifest["skipped_files"], 0)


class ApiGetHuntFileHandlerTest(test_lib.GRRBaseTest,
                                standard_test.StandardHuntTestMixin):

  def setUp(self):
    super(ApiGetHuntFileHandlerTest, self).setUp()

    self.handler = hunt_plugin.ApiGetHuntFileHandler()

    self.file_path = os.path.join(self.base_path, "test.plist")
    self.hunt = hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        flow_runner_args=flow_runner.FlowRunnerArgs(
            flow_name=file_finder.FileFinder.__name__),
        flow_args=file_finder.FileFinderArgs(
            paths=[self.file_path],
            action=file_finder.FileFinderAction(action_type="DOWNLOAD"),),
        client_rate=0,
        token=self.token)
    self.hunt.Run()

    self.results_urn = self.hunt.state.context.results_collection_urn
    self.aff4_file_path = rdfvalue.RDFURN("os").Add(self.file_path)

    self.client_id = self.SetupClients(1)[0]
    self.AssignTasksToClients(client_ids=[self.client_id])
    action_mock = action_mocks.ActionMock("TransferBuffer", "StatFile",
                                          "HashFile", "HashBuffer")
    test_lib.TestHuntHelper(action_mock, [self.client_id], token=self.token)

  def testRaisesIfOneOfArgumentAttributesIsNone(self):
    model_args = hunt_plugin.ApiGetHuntFileArgs(
        hunt_id=self.hunt.urn.Basename(),
        client_id=self.client_id,
        vfs_path=self.aff4_file_path,
        timestamp=rdfvalue.RDFDatetime().Now())

    with self.assertRaises(ValueError):
      args = model_args.Copy()
      args.hunt_id = None
      self.handler.Handle(args)

    with self.assertRaises(ValueError):
      args = model_args.Copy()
      args.client_id = None
      self.handler.Handle(args)

    with self.assertRaises(ValueError):
      args = model_args.Copy()
      args.vfs_path = None
      self.handler.Handle(args)

    with self.assertRaises(ValueError):
      args = model_args.Copy()
      args.timestamp = None
      self.handler.Handle(args)

  def testRaisesIfResultIsBeforeTimestamp(self):
    results = aff4.FACTORY.Open(self.results_urn, token=self.token)

    args = hunt_plugin.ApiGetHuntFileArgs(
        hunt_id=self.hunt.urn.Basename(),
        client_id=self.client_id,
        vfs_path=self.aff4_file_path,
        timestamp=results[0].age + rdfvalue.Duration("1s"))
    with self.assertRaises(hunt_plugin.HuntFileNotFoundError):
      self.handler.Handle(args, token=self.token)

  def _FillInStubResults(self):
    original_results = aff4.FACTORY.Open(self.results_urn, token=self.token)
    original_result = original_results[0]

    with aff4.FACTORY.Create(self.results_urn,
                             aff4_type=hunt_results.HuntResultCollection,
                             mode="rw",
                             token=self.token) as new_results:
      for i in range(self.handler.MAX_RECORDS_TO_CHECK):
        wrong_result = rdf_flows.GrrMessage(
            payload=rdfvalue.RDFString("foo/bar"),
            age=(original_result.age - (self.handler.MAX_RECORDS_TO_CHECK - i +
                                        1) * rdfvalue.Duration("1s")))
        new_results.Add(wrong_result, timestamp=wrong_result.age)

    return original_result

  def testRaisesIfResultIsAfterMaxRecordsAfterTimestamp(self):
    original_result = self._FillInStubResults()

    args = hunt_plugin.ApiGetHuntFileArgs(
        hunt_id=self.hunt.urn.Basename(),
        client_id=self.client_id,
        vfs_path=self.aff4_file_path,
        timestamp=original_result.age -
        (self.handler.MAX_RECORDS_TO_CHECK + 1) * rdfvalue.Duration("1s"))

    with self.assertRaises(hunt_plugin.HuntFileNotFoundError):
      self.handler.Handle(args, token=self.token)

  def testReturnsResultIfWithinMaxRecordsAfterTimestamp(self):
    original_result = self._FillInStubResults()

    args = hunt_plugin.ApiGetHuntFileArgs(
        hunt_id=self.hunt.urn.Basename(),
        client_id=self.client_id,
        vfs_path=self.aff4_file_path,
        timestamp=original_result.age - self.handler.MAX_RECORDS_TO_CHECK *
        rdfvalue.Duration("1s"))

    self.handler.Handle(args, token=self.token)

  def testRaisesIfResultFileIsNotStream(self):
    original_results = aff4.FACTORY.Open(self.results_urn, token=self.token)
    original_result = original_results[0]

    with aff4.FACTORY.Create(original_result.payload.stat_entry.aff4path,
                             aff4_type=aff4.AFF4Volume,
                             token=self.token) as _:
      pass

    args = hunt_plugin.ApiGetHuntFileArgs(hunt_id=self.hunt.urn.Basename(),
                                          client_id=self.client_id,
                                          vfs_path=self.aff4_file_path,
                                          timestamp=original_result.age)

    with self.assertRaises(hunt_plugin.HuntFileNotFoundError):
      self.handler.Handle(args, token=self.token)

  def testRaisesIfResultIsEmptyStream(self):
    original_results = aff4.FACTORY.Open(self.results_urn, token=self.token)
    original_result = original_results[0]

    aff4.FACTORY.Delete(original_result.payload.stat_entry.aff4path,
                        token=self.token)
    with aff4.FACTORY.Create(original_result.payload.stat_entry.aff4path,
                             aff4_type=aff4_grr.VFSFile,
                             token=self.token) as _:
      pass

    args = hunt_plugin.ApiGetHuntFileArgs(hunt_id=self.hunt.urn.Basename(),
                                          client_id=self.client_id,
                                          vfs_path=self.aff4_file_path,
                                          timestamp=original_result.age)

    with self.assertRaises(hunt_plugin.HuntFileNotFoundError):
      self.handler.Handle(args, token=self.token)

  def testReturnsBinaryStreamIfResultFound(self):
    results = aff4.FACTORY.Open(self.results_urn, token=self.token)

    args = hunt_plugin.ApiGetHuntFileArgs(hunt_id=self.hunt.urn.Basename(),
                                          client_id=self.client_id,
                                          vfs_path=self.aff4_file_path,
                                          timestamp=results[0].age)

    result = self.handler.Handle(args, token=self.token)
    self.assertTrue(hasattr(result, "GenerateContent"))
    self.assertEqual(result.content_length,
                     results[0].payload.stat_entry.st_size)


class ApiListHuntCrashesHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest,
    standard_test.StandardHuntTestMixin):

  handler = "ApiListHuntCrashesHandler"

  def Run(self):
    client_ids = self.SetupClients(1)
    client_mocks = dict([(client_id, test_lib.CrashClientMock(client_id,
                                                              self.token))
                         for client_id in client_ids])

    with test_lib.FakeTime(42):
      with self.CreateHunt(description="the hunt") as hunt_obj:
        hunt_obj.Run()

    with test_lib.FakeTime(45):
      self.AssignTasksToClients(client_ids)
      test_lib.TestHuntHelperWithMultipleMocks(client_mocks, False, self.token)

    crashes = aff4.FACTORY.Open(
        hunt_obj.urn.Add("crashes"),
        mode="r", token=self.token)
    crash = list(crashes)[0]
    session_id = crash.session_id.Basename()
    replace = {hunt_obj.urn.Basename(): "H:123456", session_id: "H:11223344"}

    self.Check("GET",
               "/api/hunts/%s/crashes" % hunt_obj.urn.Basename(),
               replace=replace)
    self.Check("GET",
               "/api/hunts/%s/crashes?count=1" % hunt_obj.urn.Basename(),
               replace=replace)
    self.Check("GET", ("/api/hunts/%s/crashes?offset=1&count=1" %
                       hunt_obj.urn.Basename()),
               replace=replace)


class ApiGetHuntClientCompletionStatsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest,
    standard_test.StandardHuntTestMixin):

  handler = "ApiGetHuntClientCompletionStatsHandler"

  def Run(self):
    client_ids = self.SetupClients(10)
    client_mock = test_lib.SampleHuntMock()

    with test_lib.FakeTime(42):
      with self.CreateHunt(description="the hunt") as hunt_obj:
        hunt_obj.Run()

    time_offset = 0
    for client_id in client_ids:
      with test_lib.FakeTime(45 + time_offset):
        self.AssignTasksToClients([client_id])
        test_lib.TestHuntHelper(client_mock, [client_id], False, self.token)
        time_offset += 10

    replace = {hunt_obj.urn.Basename(): "H:123456"}
    base_url = ("/api/hunts/%s/client-completion-stats"
                "?strip_type_info=1" % hunt_obj.urn.Basename())
    self.Check("GET", base_url, replace=replace)
    self.Check("GET", base_url + "&size=4", replace=replace)
    self.Check("GET", base_url + "&size=1000", replace=replace)


class ApiGetHuntResultsExportCommandHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest,
    standard_test.StandardHuntTestMixin):

  handler = "ApiGetHuntResultsExportCommandHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      with self.CreateHunt(description="the hunt") as hunt_obj:
        pass

    self.Check("GET",
               "/api/hunts/%s/results/export-command" % hunt_obj.urn.Basename(),
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
                      fetch_binaries=True))
          ]) as hunt_obj:
        pass

    self.Check("GET",
               "/api/hunts/%s/output-plugins" % hunt_obj.urn.Basename(),
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
                filename_regex="foo")), output_plugin.OutputPluginDescriptor(
                    plugin_name=DummyHuntTestOutputPlugin.__name__,
                    plugin_args=DummyHuntTestOutputPlugin.args_type(
                        filename_regex="bar"))
    ]

  def RunHuntWithOutputPlugins(self, output_plugins):
    hunt_urn = self.StartHunt(description="the hunt",
                              output_plugins=output_plugins)

    for client_id in self.client_ids:
      self.AssignTasksToClients(client_ids=[client_id])
      self.RunHunt(failrate=-1)
      self.ProcessHuntOutputPlugins()

    return hunt_urn

  def testReturnsLogsWhenJustOnePlugin(self):
    hunt_urn = self.RunHuntWithOutputPlugins([self.output_plugins[0]])
    result = self.handler.Handle(
        hunt_plugin.ApiListHuntOutputPluginLogsArgs(
            hunt_id=hunt_urn.Basename(),
            plugin_id=DummyHuntTestOutputPlugin.__name__ + "_0"),
        token=self.token)

    self.assertEqual(result.total_count, 5)
    self.assertEqual(len(result.items), 5)
    for item in result.items:
      self.assertEqual("foo", item.plugin_descriptor.plugin_args.filename_regex)

  def testReturnsLogsWhenMultiplePlugins(self):
    hunt_urn = self.RunHuntWithOutputPlugins(self.output_plugins)
    result = self.handler.Handle(
        hunt_plugin.ApiListHuntOutputPluginLogsArgs(
            hunt_id=hunt_urn.Basename(),
            plugin_id=DummyHuntTestOutputPlugin.__name__ + "_1"),
        token=self.token)

    self.assertEqual(result.total_count, 5)
    self.assertEqual(len(result.items), 5)
    for item in result.items:
      self.assertEqual("bar", item.plugin_descriptor.plugin_args.filename_regex)

  def testSlicesLogsWhenJustOnePlugin(self):
    hunt_urn = self.RunHuntWithOutputPlugins([self.output_plugins[0]])
    result = self.handler.Handle(
        hunt_plugin.ApiListHuntOutputPluginLogsArgs(
            hunt_id=hunt_urn.Basename(),
            offset=2,
            count=2,
            plugin_id=DummyHuntTestOutputPlugin.__name__ + "_0"),
        token=self.token)

    self.assertEqual(result.total_count, 5)
    self.assertEqual(len(result.items), 2)

  def testSlicesLogsWhenMultiplePlugins(self):
    hunt_urn = self.RunHuntWithOutputPlugins(self.output_plugins)
    result = self.handler.Handle(
        hunt_plugin.ApiListHuntOutputPluginLogsArgs(
            hunt_id=hunt_urn.Basename(),
            offset=2,
            count=2,
            plugin_id=DummyHuntTestOutputPlugin.__name__ + "_1"),
        token=self.token)

    self.assertEqual(result.total_count, 5)
    self.assertEqual(len(result.items), 2)


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
                      fetch_binaries=True))
          ])

      self.client_ids = self.SetupClients(2)
      for index, client_id in enumerate(self.client_ids):
        self.AssignTasksToClients(client_ids=[client_id])
        self.RunHunt(failrate=-1)
        with test_lib.FakeTime(100042 + index * 100):
          self.ProcessHuntOutputPlugins()

    self.Check("GET",
               "/api/hunts/%s/output-plugins/"
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
                  plugin_name=standard_test.FailingDummyHuntOutputPlugin.
                  __name__)
          ])

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

    self.Check("GET",
               "/api/hunts/%s/output-plugins/"
               "FailingDummyHuntOutputPlugin_0/errors" % hunt_urn.Basename(),
               replace={hunt_urn.Basename(): "H:123456"})


class ApiGetHuntStatsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest,
    standard_test.StandardHuntTestMixin):

  handler = "ApiGetHuntStatsHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      hunt_urn = self.StartHunt(description="the hunt")

      self.client_ids = self.SetupClients(1)
      self.AssignTasksToClients(client_ids=self.client_ids)
      self.RunHunt()

    # Create replace dictionary.
    replace = {hunt_urn.Basename(): "H:123456"}
    with aff4.FACTORY.Open(hunt_urn, mode="r", token=self.token) as hunt:
      stats = hunt.GetRunner().context.usage_stats
      for performance in stats.worst_performers:
        session_id = performance.session_id.Basename()
        replace[session_id] = "<replaced session value>"

    self.Check("GET",
               "/api/hunts/%s/stats" % hunt_urn.Basename(),
               replace=replace)


class ApiListHuntClientsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest,
    standard_test.StandardHuntTestMixin):

  handler = "ApiListHuntClientsHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      hunt_urn = self.StartHunt(description="the hunt")

      self.client_ids = self.SetupClients(5)
      self.AssignTasksToClients(client_ids=self.client_ids)
      self.RunHunt(client_ids=self.client_ids[3:])

    # Create replace dictionary.
    replace = {hunt_urn.Basename(): "H:123456"}

    # Add all sub flows to replace dict.
    all_flows = hunts.GRRHunt.GetAllSubflowUrns(hunt_urn, self.client_ids,
                                                self.token)

    for flow_urn in all_flows:
      replace[flow_urn.Basename()] = "W:123456"

    self.Check("GET",
               "/api/hunts/%s/clients/started" % hunt_urn.Basename(),
               replace=replace)
    self.Check("GET",
               "/api/hunts/%s/clients/outstanding" % hunt_urn.Basename(),
               replace=replace)
    self.Check("GET",
               "/api/hunts/%s/clients/completed" % hunt_urn.Basename(),
               replace=replace)


class ApiGetHuntContextHandlerTest(test_lib.GRRBaseTest,
                                   standard_test.StandardHuntTestMixin):
  """Test for ApiGetHuntContextHandler.

  This is done as unit test, since the hunt context is a dictionary and
  may change frequently.
  """

  def _CallHandler(self):
    result = self.handler.Handle(
        hunt_plugin.ApiGetHuntContextArgs(hunt_id=self.hunt.urn.Basename()),
        token=self.token)
    return result.context

  def _FindValueByKey(self, items, key):
    return next((item.value for item in items if item.key == key), None)

  def _IsFieldInvalid(self, items, key):
    return next((item.invalid for item in items if item.key == key), False)

  def setUp(self):
    super(ApiGetHuntContextHandlerTest, self).setUp()
    self.handler = hunt_plugin.ApiGetHuntContextHandler()

    # Set up mock hunt and context.
    with self.CreateHunt(description="the hunt") as hunt:
      # Assign for easier access.
      self.hunt = hunt
      self.context = self.hunt.state.context

      # Add custom properties for the tests.
      self.context.Register("string_prop", "some test value")
      self.context.Register("time_prop", rdfvalue.RDFDatetime().Now())
      self.context.Register("int_prop", 42)
      self.context.Register("valid_float_prop", 42.0)
      self.context.Register("invalid_float_prop", 42.5)
      self.context.Register("bool_prop", True)
      self.context.Register("none_prop", None)
      self.context.Register("non_proto_prop", object())
      self.context.Register(
          "proto_prop",
          hunt_plugin.ApiGetHuntContextArgs(hunt_id=hunt.urn.Basename()))

  def testPrimitivePropertiesAreReturnedCorrectly(self):
    result = self._CallHandler()

    self.assertEqual(
        self._FindValueByKey(result.items, "string_prop"),
        self.context["string_prop"])
    self.assertEqual(
        self._FindValueByKey(result.items, "time_prop"),
        self.context["time_prop"])
    self.assertEqual(
        self._FindValueByKey(result.items, "int_prop"),
        self.context["int_prop"])
    self.assertEqual(
        self._FindValueByKey(result.items, "valid_float_prop"),
        self.context["valid_float_prop"])
    self.assertEqual(
        self._FindValueByKey(result.items, "bool_prop"),
        self.context["bool_prop"])
    self.assertTrue(self._IsFieldInvalid(result.items, "invalid_float_prop"))

  def testNoneIsReturnedAsInvalid(self):
    result = self._CallHandler()
    self.assertTrue(self._IsFieldInvalid(result.items, "none_prop"))

  def testNonProtoNonPrimitivePropertiesAreReturnedAsInvalid(self):
    result = self._CallHandler()
    self.assertTrue(self._IsFieldInvalid(result.items, "non_proto_prop"))

  def testProtoPropertiesAreReturnedCorrectly(self):
    result = self._CallHandler()

    value = self._FindValueByKey(result.items, "proto_prop")
    self.assertEqual(value.__class__.__name__, "ApiGetHuntContextArgs")
    self.assertEqual(value.hunt_id, self.hunt.urn.Basename())


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
