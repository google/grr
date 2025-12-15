#!/usr/bin/env python
"""This modules contains tests for hunts API handlers."""

import csv
import io
import os
import tarfile
from typing import Callable, Iterable, Iterator
import zipfile

from absl import app
from absl.testing import absltest
import yaml

from google.protobuf import any_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import config as rdf_config
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import test_base as rdf_test_base
from grr_response_proto import flows_pb2
from grr_response_proto import hunts_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto.api import hunt_pb2 as api_hunt_pb2
from grr_response_server import data_store
from grr_response_server import hunt
from grr_response_server import instant_output_plugin
from grr_response_server.databases import db
from grr_response_server.databases import db_test_utils
from grr_response_server.export_converters import log_message
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import large_file
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_test_lib
from grr_response_server.gui.api_plugins import hunt as hunt_plugin
from grr_response_server.instant_output_plugins import csv_instant_plugin
from grr_response_server.output_plugins import test_plugins
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import hunt_objects as rdf_hunt_objects
from grr_response_server.rdfvalues import mig_hunt_objects
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import export_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


class ApiHuntIdTest(rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  """Test for ApiHuntId."""

  rdfvalue_class = hunt_plugin.ApiHuntId

  def GenerateSample(self, number=0):
    return hunt_plugin.ApiHuntId("H:%d" % number)

  def testRaisesWhenInitializedFromInvalidValues(self):
    with self.assertRaises(ValueError):
      hunt_plugin.ApiHuntId("bl%ah")

    with self.assertRaises(ValueError):
      hunt_plugin.ApiHuntId("H:")

    with self.assertRaises(ValueError):
      hunt_plugin.ApiHuntId("H:1234/foo")

  def testRaisesWhenToStringCalledOnUninitializedValue(self):
    hunt_id = hunt_plugin.ApiHuntId()
    with self.assertRaises(ValueError):
      hunt_id.ToString()

  def testConvertsToString(self):
    hunt_id = hunt_plugin.ApiHuntId("1234")
    hunt_id_str = hunt_id.ToString()

    self.assertEqual(hunt_id_str, "1234")


class ApiCreateHuntHandlerTest(
    api_test_lib.ApiCallHandlerTest, hunt_test_lib.StandardHuntTestMixin
):
  """Test for ApiCreateHuntHandler."""

  def setUp(self):
    super().setUp()
    self.handler = hunt_plugin.ApiCreateHuntHandler()

  def testNetworkBytesLimitHuntRunnerArgumentIsRespected(self):
    args = api_hunt_pb2.ApiCreateHuntArgs(
        flow_name=file_finder.ClientFileFinder.__name__
    )
    args.hunt_runner_args.network_bytes_limit = 123

    result = self.handler.Handle(args, context=self.context)
    self.assertEqual(123, result.hunt_runner_args.network_bytes_limit)

  def testNetworkBytesLimitHuntRunnerArgumentDefaultRespected(self):
    args = api_hunt_pb2.ApiCreateHuntArgs(
        flow_name=file_finder.ClientFileFinder.__name__
    )

    result = self.handler.Handle(args, context=self.context)
    self.assertFalse(result.hunt_runner_args.HasField("network_bytes_limit"))

  def testCollectLargeFileBlocksHuntCreationRespected(self):
    args = api_hunt_pb2.ApiCreateHuntArgs(
        flow_name=large_file.CollectLargeFileFlow.__name__
    )
    self.assertRaises(
        ValueError, self.handler.Handle, args, context=self.context
    )

  def testPresubmit_HasPresbmitRule(self):
    hunt_cfg = rdf_config.AdminUIHuntConfig(
        default_exclude_labels=["no-no"],
        presubmit_check_with_skip_tag="NOT_USED",
        presubmit_warning_message="not cool",
    )
    with test_lib.ConfigOverrider({"AdminUI.hunt_config": hunt_cfg}):
      args = api_hunt_pb2.ApiCreateHuntArgs(
          flow_name=file_finder.ClientFileFinder.__name__,
          hunt_runner_args=flows_pb2.HuntRunnerArgs(
              client_rule_set=jobs_pb2.ForemanClientRuleSet(
                  match_mode=jobs_pb2.ForemanClientRuleSet.MatchMode.MATCH_ALL,
                  rules=[
                      jobs_pb2.ForemanClientRule(
                          rule_type=jobs_pb2.ForemanClientRule.Type.LABEL,
                          label=jobs_pb2.ForemanLabelClientRule(
                              match_mode=jobs_pb2.ForemanLabelClientRule.MatchMode.DOES_NOT_MATCH_ANY,
                              label_names=["irrelevant"],
                          ),
                      ),
                      jobs_pb2.ForemanClientRule(
                          rule_type=jobs_pb2.ForemanClientRule.Type.LABEL,
                          label=jobs_pb2.ForemanLabelClientRule(
                              match_mode=jobs_pb2.ForemanLabelClientRule.MatchMode.DOES_NOT_MATCH_ANY,
                              label_names=["no-no"],
                          ),
                      ),
                  ],
              )
          ),
      )
      # Should not raise.
      self.handler.Handle(args, context=self.context)

  def testPresubmit_HasPresbmitRuleWithExtraLabels(self):
    hunt_cfg = rdf_config.AdminUIHuntConfig(
        default_exclude_labels=["no-no"],
        presubmit_check_with_skip_tag="NOT_USED",
        presubmit_warning_message="not cool",
    )
    with test_lib.ConfigOverrider({"AdminUI.hunt_config": hunt_cfg}):
      args = api_hunt_pb2.ApiCreateHuntArgs(
          flow_name=file_finder.ClientFileFinder.__name__,
          hunt_runner_args=flows_pb2.HuntRunnerArgs(
              client_rule_set=jobs_pb2.ForemanClientRuleSet(
                  match_mode=jobs_pb2.ForemanClientRuleSet.MatchMode.MATCH_ALL,
                  rules=[
                      jobs_pb2.ForemanClientRule(
                          rule_type=jobs_pb2.ForemanClientRule.Type.LABEL,
                          label=jobs_pb2.ForemanLabelClientRule(
                              match_mode=jobs_pb2.ForemanLabelClientRule.MatchMode.DOES_NOT_MATCH_ANY,
                              label_names=["no-no", "irrelevant"],
                          ),
                      ),
                  ],
              )
          ),
      )
      # Should not raise.
      self.handler.Handle(args, context=self.context)

  def testPresubmit_NoLabelRule(self):
    hunt_cfg = rdf_config.AdminUIHuntConfig(
        default_exclude_labels=["no-no"],
        presubmit_check_with_skip_tag="ENABLE",
        presubmit_warning_message="not cool",
    )
    with test_lib.ConfigOverrider({"AdminUI.hunt_config": hunt_cfg}):
      args = api_hunt_pb2.ApiCreateHuntArgs(
          flow_name=file_finder.ClientFileFinder.__name__
      )
      self.assertRaises(
          hunt_plugin.HuntPresubmitError,
          self.handler.Handle,
          args,
          context=self.context,
      )

  def testPresubmit_WrongLabelRule(self):
    hunt_cfg = rdf_config.AdminUIHuntConfig(
        default_exclude_labels=["no-no"],
        presubmit_check_with_skip_tag="NOT_THERE",
        presubmit_warning_message="not cool",
    )
    with test_lib.ConfigOverrider({"AdminUI.hunt_config": hunt_cfg}):
      args = api_hunt_pb2.ApiCreateHuntArgs(
          flow_name=file_finder.ClientFileFinder.__name__,
          hunt_runner_args=flows_pb2.HuntRunnerArgs(
              client_rule_set=jobs_pb2.ForemanClientRuleSet(
                  match_mode=jobs_pb2.ForemanClientRuleSet.MatchMode.MATCH_ALL,
                  rules=[
                      jobs_pb2.ForemanClientRule(
                          rule_type=jobs_pb2.ForemanClientRule.Type.LABEL,
                          label=jobs_pb2.ForemanLabelClientRule(
                              match_mode=jobs_pb2.ForemanLabelClientRule.MatchMode.MATCH_ALL,
                              label_names=["irrelevant"],
                          ),
                      ),
                      # Rule uses `MATCH_ALL` instead of `DOES_NOT_MATCH_ANY`.
                      jobs_pb2.ForemanClientRule(
                          rule_type=jobs_pb2.ForemanClientRule.Type.LABEL,
                          label=jobs_pb2.ForemanLabelClientRule(
                              match_mode=jobs_pb2.ForemanLabelClientRule.MatchMode.MATCH_ALL,
                              label_names=["no-no"],
                          ),
                      ),
                  ],
              )
          ),
      )
      self.assertRaises(
          hunt_plugin.HuntPresubmitError,
          self.handler.Handle,
          args,
          context=self.context,
      )

  def testPresubmit_ForceSubmit(self):
    hunt_cfg = rdf_config.AdminUIHuntConfig(
        default_exclude_labels=["no-no"],
        presubmit_check_with_skip_tag="FORCE",
        presubmit_warning_message="not cool",
    )
    with test_lib.ConfigOverrider({"AdminUI.hunt_config": hunt_cfg}):
      args = api_hunt_pb2.ApiCreateHuntArgs(
          flow_name=file_finder.ClientFileFinder.__name__,
          hunt_runner_args=flows_pb2.HuntRunnerArgs(
              description="something something FORCE=submit"
          ),
      )
      # Should not raise.
      self.handler.Handle(args, context=self.context)


class ApiListHuntCrashesHandlerTest(
    api_test_lib.ApiCallHandlerTest,
    hunt_test_lib.StandardHuntTestMixin,
):

  def setUp(self):
    super().setUp()
    self.handler = hunt_plugin.ApiListHuntCrashesHandler()

  @db_test_lib.WithDatabase
  def testHandlesListHuntCrashes(self, rel_db: db.Database):
    hunt_id = db_test_utils.InitializeHunt(rel_db)

    client_id_1 = db_test_utils.InitializeClient(rel_db)
    client_id_2 = db_test_utils.InitializeClient(rel_db)

    flow_id_1 = db_test_utils.InitializeFlow(
        rel_db,
        client_id=client_id_1,
        flow_id=hunt_id,
        parent_hunt_id=hunt_id,
    )
    db_test_utils.InitializeFlow(
        rel_db,
        client_id=client_id_2,
        flow_id=hunt_id,
        parent_hunt_id=hunt_id,
    )

    flow_obj_1 = rel_db.ReadFlowObject(client_id_1, flow_id_1)
    flow_obj_1.flow_state = flows_pb2.Flow.FlowState.CRASHED
    rel_db.UpdateFlow(
        client_id_1,
        flow_id_1,
        flow_obj=flow_obj_1,
        client_crash_info=jobs_pb2.ClientCrash(client_id=client_id_1),
    )

    result = self.handler.Handle(
        api_hunt_pb2.ApiListHuntCrashesArgs(hunt_id=hunt_id),
        context=self.context,
    )
    self.assertIsInstance(result, api_hunt_pb2.ApiListHuntCrashesResult)
    self.assertEqual(result.total_count, 1)
    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].client_id, client_id_1)

  @db_test_lib.WithDatabase
  def testListHuntCrashesReturnsEmptyListIfNoCrashes(self, rel_db: db.Database):
    hunt_id = db_test_utils.InitializeHunt(rel_db)
    client_id = db_test_utils.InitializeClient(rel_db)
    db_test_utils.InitializeFlow(
        rel_db,
        client_id=client_id,
        flow_id=hunt_id,
        parent_hunt_id=hunt_id,
    )

    result = self.handler.Handle(
        api_hunt_pb2.ApiListHuntCrashesArgs(hunt_id=hunt_id),
        context=self.context,
    )
    self.assertIsInstance(result, api_hunt_pb2.ApiListHuntCrashesResult)
    self.assertEqual(result.total_count, 0)
    self.assertEmpty(result.items)


class ApiGetHuntResultsExportCommandHandlerTest(
    api_test_lib.ApiCallHandlerTest,
    hunt_test_lib.StandardHuntTestMixin,
):

  def setUp(self):
    super().setUp()
    self.handler = hunt_plugin.ApiGetHuntResultsExportCommandHandler()

  def testHandlesGetHuntResultsExportCommand(self):
    hunt_id = "0123ABCD"
    args = api_hunt_pb2.ApiGetHuntResultsExportCommandArgs(hunt_id=hunt_id)
    result = self.handler.Handle(args, context=self.context)
    self.assertIsInstance(
        result, api_hunt_pb2.ApiGetHuntResultsExportCommandResult
    )
    self.assertNotEmpty(result.command)


class ApiListHuntsHandlerTest(
    api_test_lib.ApiCallHandlerTest, hunt_test_lib.StandardHuntTestMixin
):
  """Test for ApiListHuntsHandler."""

  def setUp(self):
    super().setUp()
    self.handler = hunt_plugin.ApiListHuntsHandler()

  def testHandlesListOfHuntObjects(self):
    for i in range(10):
      self.CreateHunt(description="hunt_%d" % i)

    result = self.handler.Handle(
        api_hunt_pb2.ApiListHuntsArgs(), context=self.context
    )
    descriptions = set(r.description for r in result.items)

    self.assertLen(descriptions, 10)
    for i in range(10):
      self.assertIn("hunt_%d" % i, descriptions)

  def testShowsFullSummaryWhenRequested(self):
    client_ids = self.SetupClients(1)
    hunt_id = self.StartHunt(
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=file_finder.FileFinder.__name__
        ),
        flow_args=rdf_file_finder.FileFinderArgs(
            paths=[os.path.join(self.base_path, "test.plist")],
            action=rdf_file_finder.FileFinderAction(action_type="DOWNLOAD"),
        ),
        client_rate=0,
        creator=self.context.username,
    )
    self.RunHunt(
        client_ids=client_ids, client_mock=action_mocks.FileFinderClientMock()
    )

    args = api_hunt_pb2.ApiGetHuntArgs(hunt_id=hunt_id)
    hunt_api_obj = hunt_plugin.ApiGetHuntHandler().Handle(
        args, context=self.context
    )
    self.assertEqual(hunt_api_obj.all_clients_count, 1)

    result = self.handler.Handle(
        api_hunt_pb2.ApiListHuntsArgs(with_full_summary=True),
        context=self.context,
    )

    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].all_clients_count, 1)

  def testHuntListIsSortedInReversedCreationTimestampOrder(self):
    for i in range(1, 11):
      with test_lib.FakeTime(i * 1000):
        self.CreateHunt(description="hunt_%d" % i)

    result = self.handler.Handle(
        api_hunt_pb2.ApiListHuntsArgs(), context=self.context
    )
    create_times = [r.created for r in result.items]

    self.assertLen(create_times, 10)
    for index, expected_time in enumerate(reversed(range(1, 11))):
      self.assertEqual(create_times[index], expected_time * 1000000000)

  def testHandlesSubrangeOfListOfHuntObjects(self):
    for i in range(1, 11):
      with test_lib.FakeTime(i * 1000):
        self.CreateHunt(description="hunt_%d" % i)

    result = self.handler.Handle(
        api_hunt_pb2.ApiListHuntsArgs(offset=2, count=2), context=self.context
    )
    create_times = [r.created for r in result.items]

    self.assertLen(create_times, 2)
    self.assertEqual(create_times[0], 8 * 1000000000)
    self.assertEqual(create_times[1], 7 * 1000000000)

  def testFiltersHuntsByActivityTime(self):
    for i in range(1, 11):
      with test_lib.FakeTime(i * 60):
        self.CreateHunt(description="hunt_%d" % i)

    with test_lib.FakeTime(10 * 60 + 1):
      result = self.handler.Handle(
          api_hunt_pb2.ApiListHuntsArgs(
              active_within=rdfvalue.DurationSeconds("2m").ToInt(
                  timeunit=rdfvalue.SECONDS
              )
          ),
          context=self.context,
      )

    create_times = [r.created for r in result.items]

    self.assertLen(create_times, 2)
    self.assertEqual(create_times[0], 10 * 60 * 1000000)
    self.assertEqual(create_times[1], 9 * 60 * 1000000)

  def testFiltersHuntsByCreator(self):
    for i in range(5):
      self.CreateHunt(description="foo_hunt_%d" % i, creator="user-foo")

    for i in range(3):
      self.CreateHunt(description="bar_hunt_%d" % i, creator="user-bar")

    result = self.handler.Handle(
        api_hunt_pb2.ApiListHuntsArgs(
            created_by="user-foo",
            active_within=rdfvalue.DurationSeconds("1d").ToInt(
                timeunit=rdfvalue.SECONDS
            ),
        ),
        context=self.context,
    )
    self.assertLen(result.items, 5)
    for item in result.items:
      self.assertEqual(item.creator, "user-foo")

    result = self.handler.Handle(
        api_hunt_pb2.ApiListHuntsArgs(
            created_by="user-bar",
            active_within=rdfvalue.DurationSeconds("1d").ToInt(
                timeunit=rdfvalue.SECONDS
            ),
        ),
        context=self.context,
    )
    self.assertLen(result.items, 3)
    for item in result.items:
      self.assertEqual(item.creator, "user-bar")

  def testFiltersHuntsByState(self):
    self.StartHunt(description="hunt_started")
    self.CreateHunt(description="hunt_not_started")

    result = self.handler.Handle(
        api_hunt_pb2.ApiListHuntsArgs(
            with_state=api_hunt_pb2.ApiHunt.State.PAUSED
        ),
        context=self.context,
    )

    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].description, "hunt_not_started")
    self.assertEqual(result.items[0].state, api_hunt_pb2.ApiHunt.State.PAUSED)

  def testRaisesIfDescriptionContainsFilterUsedWithoutActiveWithinFilter(self):
    self.assertRaises(
        ValueError,
        self.handler.Handle,
        api_hunt_pb2.ApiListHuntsArgs(description_contains="foo"),
        context=self.context,
    )

  def testFiltersHuntsByDescriptionContainsMatch(self):
    for i in range(5):
      self.CreateHunt(description="foo_hunt_%d" % i)

    for i in range(3):
      self.CreateHunt(description="bar_hunt_%d")

    result = self.handler.Handle(
        api_hunt_pb2.ApiListHuntsArgs(
            description_contains="foo",
            active_within=rdfvalue.DurationSeconds("1d").ToInt(
                timeunit=rdfvalue.SECONDS
            ),
        ),
        context=self.context,
    )
    self.assertLen(result.items, 5)
    for item in result.items:
      self.assertIn("foo", item.description)

    result = self.handler.Handle(
        api_hunt_pb2.ApiListHuntsArgs(
            description_contains="bar",
            active_within=rdfvalue.DurationSeconds("1d").ToInt(
                timeunit=rdfvalue.SECONDS
            ),
        ),
        context=self.context,
    )
    self.assertLen(result.items, 3)
    for item in result.items:
      self.assertIn("bar", item.description)

  def testOffsetIsRelativeToFilteredResultsWhenFilterIsPresent(self):
    for i in range(5):
      self.CreateHunt(description="foo_hunt_%d" % i)

    for i in range(3):
      self.CreateHunt(description="bar_hunt_%d" % i)

    result = self.handler.Handle(
        api_hunt_pb2.ApiListHuntsArgs(
            description_contains="bar",
            active_within=rdfvalue.DurationSeconds("1d").ToInt(
                timeunit=rdfvalue.SECONDS
            ),
            offset=1,
        ),
        context=self.context,
    )
    self.assertLen(result.items, 2)
    for item in result.items:
      self.assertIn("bar", item.description)

    result = self.handler.Handle(
        api_hunt_pb2.ApiListHuntsArgs(
            description_contains="bar",
            active_within=rdfvalue.DurationSeconds("1d").ToInt(
                timeunit=rdfvalue.SECONDS
            ),
            offset=2,
        ),
        context=self.context,
    )
    self.assertLen(result.items, 1)
    for item in result.items:
      self.assertIn("bar", item.description)

    result = self.handler.Handle(
        api_hunt_pb2.ApiListHuntsArgs(
            description_contains="bar",
            active_within=rdfvalue.DurationSeconds("1d").ToInt(
                timeunit=rdfvalue.SECONDS
            ),
            offset=3,
        ),
        context=self.context,
    )
    self.assertEmpty(result.items)


class ApiGetHuntHandlerTest(
    hunt_test_lib.StandardHuntTestMixin, api_test_lib.ApiCallHandlerTest
):

  def setUp(self):
    super().setUp()
    self.handler = hunt_plugin.ApiGetHuntHandler()

  def testHuntDuration(self):
    duration = rdfvalue.Duration.From(42, rdfvalue.MINUTES)
    hunt_obj = rdf_hunt_objects.Hunt()
    hunt_obj.hunt_id = "12345678"
    hunt_obj.duration = duration
    hunt_obj = mig_hunt_objects.ToProtoHunt(hunt_obj)
    data_store.REL_DB.WriteHuntObject(hunt_obj)

    args = api_hunt_pb2.ApiGetHuntArgs()
    args.hunt_id = "12345678"

    hunt_api_obj = self.handler.Handle(args, context=self.context)
    duration_seconds = duration.ToInt(timeunit=rdfvalue.SECONDS)
    self.assertEqual(hunt_api_obj.duration, duration_seconds)
    self.assertEqual(
        hunt_api_obj.hunt_runner_args.expiry_time,
        duration_seconds,
    )


class ApiGetHuntFilesArchiveHandlerTest(
    hunt_test_lib.StandardHuntTestMixin, api_test_lib.ApiCallHandlerTest
):

  def setUp(self):
    super().setUp()

    self.handler = hunt_plugin.ApiGetHuntFilesArchiveHandler()

    self.client_ids = self.SetupClients(10)
    self.hunt_id = self.StartHunt(
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=file_finder.FileFinder.__name__
        ),
        flow_args=rdf_file_finder.FileFinderArgs(
            paths=[os.path.join(self.base_path, "test.plist")],
            action=rdf_file_finder.FileFinderAction(action_type="DOWNLOAD"),
        ),
        client_rate=0,
        creator=self.context.username,
    )

    self.RunHunt(
        client_ids=self.client_ids,
        client_mock=action_mocks.FileFinderClientMock(),
    )

  def testGeneratesZipArchive(self):
    result = self.handler.Handle(
        api_hunt_pb2.ApiGetHuntFilesArchiveArgs(
            hunt_id=self.hunt_id, archive_format="ZIP"
        ),
        context=self.context,
    )

    out_fd = io.BytesIO()
    for chunk in result.GenerateContent():
      out_fd.write(chunk)

    zip_fd = zipfile.ZipFile(out_fd, "r")
    manifest = None
    for name in zip_fd.namelist():
      if name.endswith("MANIFEST"):
        manifest = yaml.safe_load(zip_fd.read(name))

    self.assertDictContainsSubset(
        {
            "archived_files": 10,
            "failed_files": 0,
            "processed_files": 10,
            "ignored_files": 0,
        },
        manifest,
    )

  def testGeneratesTarGzArchive(self):
    result = self.handler.Handle(
        api_hunt_pb2.ApiGetHuntFilesArchiveArgs(
            hunt_id=self.hunt_id, archive_format="TAR_GZ"
        ),
        context=self.context,
    )

    with utils.TempDirectory() as temp_dir:
      tar_path = os.path.join(temp_dir, "archive.tar.gz")
      with open(tar_path, "wb") as fd:
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
      with open(manifest_file_path, "rb") as fd:
        manifest = yaml.safe_load(fd.read())

        self.assertDictContainsSubset(
            {
                "archived_files": 10,
                "failed_files": 0,
                "processed_files": 10,
                "ignored_files": 0,
            },
            manifest,
        )


class ApiGetHuntFileHandlerTest(
    api_test_lib.ApiCallHandlerTest, hunt_test_lib.StandardHuntTestMixin
):

  def setUp(self):
    super().setUp()

    self.handler = hunt_plugin.ApiGetHuntFileHandler()

    self.file_path = os.path.join(self.base_path, "test.plist")
    self.vfs_file_path = "fs/os/%s" % self.file_path

    self.hunt_id = self.StartHunt(
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=file_finder.FileFinder.__name__
        ),
        flow_args=rdf_file_finder.FileFinderArgs(
            paths=[self.file_path],
            action=rdf_file_finder.FileFinderAction(action_type="DOWNLOAD"),
        ),
        client_rate=0,
        creator=self.context.username,
    )

    self.client_id = self.SetupClient(0)
    self.RunHunt(
        client_ids=[self.client_id],
        client_mock=action_mocks.FileFinderClientMock(),
    )

  def testRaisesIfOneOfArgumentAttributesIsNone(self):
    model_args = api_hunt_pb2.ApiGetHuntFileArgs(
        hunt_id=self.hunt_id,
        client_id=self.client_id,
        vfs_path=self.vfs_file_path,
        timestamp=rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch(),
    )

    args = api_hunt_pb2.ApiGetHuntFileArgs()
    args.CopyFrom(model_args)
    args.ClearField("hunt_id")
    with self.assertRaises(ValueError):
      self.handler.Handle(args)

    args = api_hunt_pb2.ApiGetHuntFileArgs()
    args.CopyFrom(model_args)
    args.ClearField("client_id")
    with self.assertRaises(ValueError):
      self.handler.Handle(args)

    args = api_hunt_pb2.ApiGetHuntFileArgs()
    args.CopyFrom(model_args)
    args.ClearField("vfs_path")
    with self.assertRaises(ValueError):
      self.handler.Handle(args)

    args = api_hunt_pb2.ApiGetHuntFileArgs()
    args.CopyFrom(model_args)
    args.ClearField("timestamp")
    with self.assertRaises(ValueError):
      self.handler.Handle(args)

  def testRaisesIfVfsRootIsNotAllowed(self):
    args = api_hunt_pb2.ApiGetHuntFileArgs(
        hunt_id=self.hunt_id,
        client_id=self.client_id,
        vfs_path="flows/W:123456",
        timestamp=rdfvalue.RDFDatetime().Now().AsMicrosecondsSinceEpoch(),
    )

    with self.assertRaises(ValueError):
      self.handler.Handle(args)

  def testRaisesIfResultIsBeforeTimestamp(self):
    results = data_store.REL_DB.ReadHuntResults(self.hunt_id, 0, 1)

    args = api_hunt_pb2.ApiGetHuntFileArgs(
        hunt_id=self.hunt_id,
        client_id=self.client_id,
        vfs_path=self.vfs_file_path,
        timestamp=(
            rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
                results[0].timestamp
            )
            + rdfvalue.Duration.From(1, rdfvalue.SECONDS)
        ).AsMicrosecondsSinceEpoch(),
    )
    with self.assertRaises(hunt_plugin.HuntFileNotFoundError):
      self.handler.Handle(args, context=self.context)

  def testRaisesIfResultFileDoesNotExist(self):
    results = data_store.REL_DB.ReadHuntResults(self.hunt_id, 0, 1)
    original_result = results[0]

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
            original_result.timestamp
        )
        - rdfvalue.Duration.From(1, rdfvalue.SECONDS)
    ):
      wrong_result = flows_pb2.FlowResult()
      wrong_result.CopyFrom(original_result)
      payload = flows_pb2.FileFinderResult()
      wrong_result.payload.Unpack(payload)
      payload.stat_entry.pathspec.path += "blah"
      data_store.REL_DB.WriteFlowResults([wrong_result])

    args = api_hunt_pb2.ApiGetHuntFileArgs(
        hunt_id=self.hunt_id,
        client_id=self.client_id,
        vfs_path=self.vfs_file_path + "blah",
        timestamp=wrong_result.timestamp,
    )

    with self.assertRaises(hunt_plugin.HuntFileNotFoundError):
      self.handler.Handle(args, context=self.context)

  def testReturnsBinaryStreamIfResultFound(self):
    results = data_store.REL_DB.ReadHuntResults(self.hunt_id, 0, 1)
    timestamp = results[0].timestamp

    args = api_hunt_pb2.ApiGetHuntFileArgs(
        hunt_id=self.hunt_id,
        client_id=self.client_id,
        vfs_path=self.vfs_file_path,
        timestamp=timestamp,
    )

    result = self.handler.Handle(args, context=self.context)
    self.assertTrue(hasattr(result, "GenerateContent"))
    payload = flows_pb2.FileFinderResult()
    results[0].payload.Unpack(payload)
    self.assertEqual(result.content_length, payload.stat_entry.st_size)


class ApiListHuntResultsHandlerTest(
    api_test_lib.ApiCallHandlerTest, hunt_test_lib.StandardHuntTestMixin
):
  """Test for ApiListHuntResultsHandler."""

  def setUp(self):
    super().setUp()

    self.handler = hunt_plugin.ApiListHuntResultsHandler()

  def _RunHuntWithResults(self, client_count, results):
    hunt_id = self.StartHunt(description="the hunt")

    self.client_ids = self.SetupClients(client_count)
    for client_id in self.client_ids:
      self.AddResultsToHunt(hunt_id, client_id, results)

    return hunt_id

  def testReturnsAllResultsOfAllTypes(self):
    hunt_id = self._RunHuntWithResults(
        client_count=5,
        results=[
            rdf_file_finder.CollectFilesByKnownPathResult(),
            rdf_file_finder.FileFinderResult(),
        ],
    )
    result = self.handler.Handle(
        api_hunt_pb2.ApiListHuntResultsArgs(hunt_id=hunt_id),
        context=self.context,
    )
    self.assertCountEqual(
        [r.payload.TypeName() for r in result.items],
        [
            flows_pb2.CollectFilesByKnownPathResult.DESCRIPTOR.full_name,
            flows_pb2.FileFinderResult.DESCRIPTOR.full_name,
        ]
        * 5,
    )
    self.assertEqual(result.total_count, 10)

  def testCountsAllResultsWithAllTypes(self):
    hunt_id = self._RunHuntWithResults(
        client_count=5,
        results=[
            rdf_file_finder.CollectFilesByKnownPathResult(),
            rdf_file_finder.FileFinderResult(),
        ],
    )
    result = self.handler.Handle(
        api_hunt_pb2.ApiListHuntResultsArgs(hunt_id=hunt_id, count=3),
        context=self.context,
    )

    self.assertLen(result.items, 3)
    self.assertEqual(result.total_count, 10)

  def testReturnsAllResultsOfFilteredType(self):
    hunt_id = self._RunHuntWithResults(
        client_count=5,
        results=[
            rdf_file_finder.CollectFilesByKnownPathResult(),
            rdf_file_finder.FileFinderResult(),
        ],
    )
    result = self.handler.Handle(
        api_hunt_pb2.ApiListHuntResultsArgs(
            hunt_id=hunt_id, with_type=rdf_file_finder.FileFinderResult.__name__
        ),
        context=self.context,
    )

    self.assertCountEqual(
        [r.payload.TypeName() for r in result.items],
        [flows_pb2.FileFinderResult.DESCRIPTOR.full_name] * 5,
    )
    self.assertEqual(result.total_count, 5)

  def testCountsAllResultsWithType(self):
    hunt_id = self._RunHuntWithResults(
        client_count=5,
        results=[
            rdf_file_finder.CollectFilesByKnownPathResult(),
            rdf_file_finder.FileFinderResult(),
        ],
    )
    result = self.handler.Handle(
        api_hunt_pb2.ApiListHuntResultsArgs(
            hunt_id=hunt_id,
            count=3,
            with_type=rdf_file_finder.FileFinderResult.__name__,
        ),
        context=self.context,
    )
    self.assertCountEqual(
        [r.payload.TypeName() for r in result.items],
        [flows_pb2.FileFinderResult.DESCRIPTOR.full_name] * 3,
    )
    self.assertEqual(result.total_count, 5)


class ApiCountHuntResultsHandlerTest(
    api_test_lib.ApiCallHandlerTest, hunt_test_lib.StandardHuntTestMixin
):
  """Test for ApiCountHuntResultsByTypeHandler."""

  def setUp(self):
    super().setUp()

    self.handler = hunt_plugin.ApiCountHuntResultsByTypeHandler()

  def _RunHuntWithResults(self, client_count, results):
    hunt_id = self.StartHunt(description="the hunt")

    self.client_ids = self.SetupClients(client_count)
    for client_id in self.client_ids:
      self.AddResultsToHunt(hunt_id, client_id, results)

    return hunt_id

  def testCountsAllResultsOfAllTypes(self):
    hunt_id = self._RunHuntWithResults(
        client_count=5,
        results=[
            rdf_file_finder.CollectFilesByKnownPathResult(),
            rdf_file_finder.FileFinderResult(),
        ],
    )
    result = self.handler.Handle(
        api_hunt_pb2.ApiCountHuntResultsByTypeArgs(hunt_id=hunt_id),
        context=self.context,
    )

    self.assertCountEqual(
        result.items,
        [
            api_hunt_pb2.ApiTypeCount(
                type=flows_pb2.CollectFilesByKnownPathResult.__name__,
                count=5,
            ),
            api_hunt_pb2.ApiTypeCount(
                type=flows_pb2.FileFinderResult.__name__, count=5
            ),
        ],
    )


class ApiListHuntOutputPluginLogsHandlerTest(
    api_test_lib.ApiCallHandlerTest, hunt_test_lib.StandardHuntTestMixin
):
  """Test for ApiListHuntOutputPluginLogsHandler."""

  def setUp(self):
    super().setUp()

    self.client_ids = self.SetupClients(5)
    self.handler = hunt_plugin.ApiListHuntOutputPluginLogsHandler()
    self.output_plugins = [
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name=test_plugins.DummyHuntTestOutputPlugin.__name__,
            args=test_plugins.DummyHuntTestOutputPlugin.args_type(
                filename_regex="foo"
            ),
        ),
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name=test_plugins.DummyHuntTestOutputPlugin.__name__,
            args=test_plugins.DummyHuntTestOutputPlugin.args_type(
                filename_regex="bar"
            ),
        ),
    ]

  def RunHuntWithOutputPlugins(self, output_plugins):
    hunt_id = self.StartHunt(
        description="the hunt", output_plugins=output_plugins
    )

    for client_id in self.client_ids:
      self.RunHunt(client_ids=[client_id], failrate=-1)

    return hunt_id

  def testReturnsLogsWhenJustOnePlugin(self):
    hunt_id = self.RunHuntWithOutputPlugins([self.output_plugins[0]])
    result = self.handler.Handle(
        api_hunt_pb2.ApiListHuntOutputPluginLogsArgs(
            hunt_id=hunt_id,
            plugin_id=test_plugins.DummyHuntTestOutputPlugin.__name__ + "_0",
        ),
        context=self.context,
    )

    self.assertEqual(result.total_count, 5)
    self.assertLen(result.items, 5)

  def testReturnsLogsWhenMultiplePlugins(self):
    hunt_id = self.RunHuntWithOutputPlugins(self.output_plugins)
    result = self.handler.Handle(
        api_hunt_pb2.ApiListHuntOutputPluginLogsArgs(
            hunt_id=hunt_id,
            plugin_id=test_plugins.DummyHuntTestOutputPlugin.__name__ + "_1",
        ),
        context=self.context,
    )

    self.assertEqual(result.total_count, 5)
    self.assertLen(result.items, 5)

  def testSlicesLogsWhenJustOnePlugin(self):
    hunt_id = self.RunHuntWithOutputPlugins([self.output_plugins[0]])
    result = self.handler.Handle(
        api_hunt_pb2.ApiListHuntOutputPluginLogsArgs(
            hunt_id=hunt_id,
            offset=2,
            count=2,
            plugin_id=test_plugins.DummyHuntTestOutputPlugin.__name__ + "_0",
        ),
        context=self.context,
    )

    self.assertEqual(result.total_count, 5)
    self.assertLen(result.items, 2)

  def testSlicesLogsWhenMultiplePlugins(self):
    hunt_id = self.RunHuntWithOutputPlugins(self.output_plugins)
    result = self.handler.Handle(
        api_hunt_pb2.ApiListHuntOutputPluginLogsArgs(
            hunt_id=hunt_id,
            offset=2,
            count=2,
            plugin_id=test_plugins.DummyHuntTestOutputPlugin.__name__ + "_1",
        ),
        context=self.context,
    )

    self.assertEqual(result.total_count, 5)
    self.assertLen(result.items, 2)


class ApiModifyHuntHandlerTest(
    api_test_lib.ApiCallHandlerTest, hunt_test_lib.StandardHuntTestMixin
):
  """Test for ApiModifyHuntHandler."""

  def setUp(self):
    super().setUp()

    self.handler = hunt_plugin.ApiModifyHuntHandler()

    self.hunt_id = self.CreateHunt(description="the hunt")

    self.args = api_hunt_pb2.ApiModifyHuntArgs(hunt_id=self.hunt_id)

  def testDoesNothingIfArgsHaveNoChanges(self):
    hunt_obj = data_store.REL_DB.ReadHuntObject(self.hunt_id)
    before = hunt_plugin.InitApiHuntFromHuntObject(hunt_obj)

    self.handler.Handle(self.args, context=self.context)

    hunt_obj = data_store.REL_DB.ReadHuntObject(self.hunt_id)
    after = hunt_plugin.InitApiHuntFromHuntObject(hunt_obj)

    self.assertEqual(before, after)

  def testRaisesIfStateIsSetToNotStartedOrStopped(self):
    self.args.state = api_hunt_pb2.ApiHunt.State.COMPLETED
    with self.assertRaises(hunt_plugin.InvalidHuntStateError):
      self.handler.Handle(self.args, context=self.context)

  def testRaisesWhenStartingHuntInTheWrongState(self):
    hunt.StartHunt(self.hunt_id)
    hunt.StopHunt(self.hunt_id)

    self.args.state = api_hunt_pb2.ApiHunt.State.STARTED
    with self.assertRaises(hunt_plugin.HuntNotStartableError):
      self.handler.Handle(self.args, context=self.context)

  def testRaisesWhenStoppingHuntInTheWrongState(self):
    hunt.StartHunt(self.hunt_id)
    hunt.StopHunt(self.hunt_id)

    self.args.state = api_hunt_pb2.ApiHunt.State.STOPPED
    with self.assertRaises(hunt_plugin.HuntNotStoppableError):
      self.handler.Handle(self.args, context=self.context)

  def testStartsHuntCorrectly(self):
    self.args.state = api_hunt_pb2.ApiHunt.State.STARTED
    self.handler.Handle(self.args, context=self.context)

    h = data_store.REL_DB.ReadHuntObject(self.hunt_id)
    self.assertEqual(h.hunt_state, h.HuntState.STARTED)

  def testStopsHuntCorrectly(self):
    self.args.state = api_hunt_pb2.ApiHunt.State.STOPPED
    self.handler.Handle(self.args, context=self.context)

    h = data_store.REL_DB.ReadHuntObject(self.hunt_id)
    self.assertEqual(h.hunt_state, h.HuntState.STOPPED)
    self.assertEqual(
        h.hunt_state_reason,
        hunts_pb2.Hunt.HuntStateReason.TRIGGERED_BY_USER,
    )
    self.assertEqual(h.hunt_state_comment, "Cancelled by user")

  def testRaisesWhenModifyingHuntInNonPausedState(self):
    hunt.StartHunt(self.hunt_id)

    self.args.client_rate = 100
    with self.assertRaises(hunt_plugin.HuntNotModifiableError):
      self.handler.Handle(self.args, context=self.context)

  def testModifiesHuntCorrectly(self):
    self.args.client_rate = 100
    self.args.client_limit = 42
    self.args.duration = rdfvalue.Duration.From(1, rdfvalue.DAYS).ToInt(
        timeunit=rdfvalue.SECONDS
    )

    self.handler.Handle(self.args, context=self.context)

    hunt_obj = data_store.REL_DB.ReadHuntObject(self.hunt_id)
    after = hunt_plugin.InitApiHuntFromHuntObject(hunt_obj)

    self.assertEqual(after.client_rate, 100)
    self.assertEqual(after.client_limit, 42)
    self.assertEqual(
        after.duration,
        rdfvalue.Duration.From(1, rdfvalue.DAYS).ToInt(
            timeunit=rdfvalue.SECONDS
        ),
    )


class ApiDeleteHuntHandlerTest(
    api_test_lib.ApiCallHandlerTest, hunt_test_lib.StandardHuntTestMixin
):
  """Test for ApiDeleteHuntHandler."""

  def setUp(self):
    super().setUp()

    self.handler = hunt_plugin.ApiDeleteHuntHandler()

    self.hunt_id = self.CreateHunt(description="the hunt")

    self.args = api_hunt_pb2.ApiDeleteHuntArgs(hunt_id=self.hunt_id)

  def testRaisesIfHuntNotFound(self):
    with self.assertRaises(hunt_plugin.HuntNotFoundError):
      self.handler.Handle(
          api_hunt_pb2.ApiDeleteHuntArgs(hunt_id="H:123456"),
          context=self.context,
      )

  def testRaisesIfHuntIsRunning(self):
    hunt.StartHunt(self.hunt_id)

    with self.assertRaises(hunt_plugin.HuntNotDeletableError):
      self.handler.Handle(self.args, context=self.context)

  def testDeletesHunt(self):
    self.handler.Handle(self.args, context=self.context)

    with self.assertRaises(db.UnknownHuntError):
      data_store.REL_DB.ReadHuntObject(self.hunt_id)


class TestInstantOutputPluginProto(
    instant_output_plugin.InstantOutputPluginProto,
):
  """Test plugin."""

  plugin_name = "test"
  friendly_name = "test plugin"
  description = "test plugin description"

  def Start(self):
    yield f"Start: {self.source_urn}".encode("utf-8")

  def ProcessValuesOfType(
      self,
      type_url: str,
      type_url_results_generator_fn: Callable[
          [], Iterable[flows_pb2.FlowResult]
      ],
  ) -> Iterator[bytes]:
    yield f"Values of type: {type_url}".encode("utf-8")
    for flow_result in type_url_results_generator_fn():
      yield (
          "First pass:"
          f" {flow_result.payload} (client_id={flow_result.client_id})"
      ).encode("utf-8")
    for flow_result in type_url_results_generator_fn():
      yield (
          "Second pass:"
          f" {flow_result.payload} (client_id={flow_result.client_id})"
      ).encode("utf-8")

  def Finish(self):
    yield f"Finish: {self.source_urn}".encode("utf-8")


class ApiGetExportedHuntResultsHandlerTest(
    test_lib.GRRBaseTest, hunt_test_lib.StandardHuntTestMixin
):

  def setUp(self):
    super().setUp()
    self.handler = hunt_plugin.ApiGetExportedHuntResultsHandler()
    self.context = api_call_context.ApiCallContext("test")

  @test_plugins.WithInstantOutputPluginProto(TestInstantOutputPluginProto)
  def testWorksCorrectlyWithProtoPlugin(self):
    input_str = "banana"
    hunt_id = self.StartHunt(
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=flow_test_lib.EchoLogFlowProto.__name__
        ),
        flow_args=rdf_client.LogMessage(data=input_str),
        client_rate=0,
    )
    client_ids = self.SetupClients(1)
    for cid in client_ids:
      self.RunHunt(client_ids=[cid])

    result = self.handler.Handle(
        api_hunt_pb2.ApiGetExportedHuntResultsArgs(
            hunt_id=hunt_id,
            plugin_name=TestInstantOutputPluginProto.plugin_name,
        ),
        context=self.context,
    )
    chunks = list(result.GenerateContent())

    flow_result = jobs_pb2.LogMessage(data=f"echo('{input_str}')")
    packed_flow_result = any_pb2.Any()
    packed_flow_result.Pack(flow_result)

    decoded_chunks = [chunk.decode("utf-8") for chunk in chunks]
    self.assertListEqual(
        decoded_chunks,
        [
            f"Start: aff4:/hunts/{hunt_id}",
            (
                "Values of type:"
                f" type.googleapis.com/{jobs_pb2.LogMessage.DESCRIPTOR.full_name}"
            ),
            f"First pass: {packed_flow_result} (client_id={client_ids[0]})",
            f"Second pass: {packed_flow_result} (client_id={client_ids[0]})",
            f"Finish: aff4:/hunts/{hunt_id}",
        ],
    )

  def testComplainsAboutMissingPlugin(self):
    with self.assertRaises(hunt_plugin.InstantOutputPluginNotFoundError):
      self.handler.Handle(
          api_hunt_pb2.ApiGetExportedHuntResultsArgs(
              hunt_id="shouldn't be relevant", plugin_name="non-existing"
          ),
          context=self.context,
      )

  @test_plugins.WithInstantOutputPluginProto(
      csv_instant_plugin.CSVInstantOutputPluginProto
  )
  @export_test_lib.WithExportConverterProto(
      log_message.LogMessageToExportedStringConverter
  )
  def testIntegrationWithCSVAndExportConverter(self):
    hunt_id = self.StartHunt(
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=flow_test_lib.EchoLogFlowProto.__name__
        ),
        flow_args=rdf_client.LogMessage(data="yerba mate"),
        client_rate=0,
    )
    client_ids = self.SetupClients(1)
    for cid in client_ids:
      self.RunHunt(client_ids=[cid])

    result = self.handler.Handle(
        api_hunt_pb2.ApiGetExportedHuntResultsArgs(
            hunt_id=hunt_id,
            plugin_name=csv_instant_plugin.CSVInstantOutputPluginProto.plugin_name,
        ),
        context=self.context,
    )
    chunks = list(result.GenerateContent())

    fd_path = os.path.join(self.temp_dir, "csv_result.zip")
    with open(fd_path, "wb") as fd:
      for chunk in chunks:
        fd.write(chunk)
    zip_fd = zipfile.ZipFile(fd_path)
    filename_prefix = f"results_hunts_{hunt_id}"

    self.assertEqual(
        set(zip_fd.namelist()),
        {
            f"{filename_prefix}/MANIFEST",
            f"{filename_prefix}/ExportedString/from_LogMessage.csv",
        },
    )

    parsed_manifest = yaml.safe_load(zip_fd.read(f"{filename_prefix}/MANIFEST"))
    self.assertEqual(
        parsed_manifest,
        {"export_stats": {"LogMessage": {"ExportedString": 1}}},
    )

    with zip_fd.open(
        f"{filename_prefix}/ExportedString/from_LogMessage.csv"
    ) as filedesc:
      content = filedesc.read().decode("utf-8")
    parsed_output = list(csv.DictReader(io.StringIO(content)))

    self.assertLen(parsed_output, 1)
    self.assertEqual(parsed_output[0]["data"], "echo('yerba mate')")


class ListHuntErrorsHandlerTest(absltest.TestCase):

  @db_test_lib.WithDatabase
  def testWithoutFilter(self, rel_db: db.Database):
    hunt_id = db_test_utils.InitializeHunt(rel_db)

    client_id_1 = db_test_utils.InitializeClient(rel_db)
    client_id_2 = db_test_utils.InitializeClient(rel_db)

    flow_id_1 = db_test_utils.InitializeFlow(
        rel_db,
        client_id=client_id_1,
        flow_id=hunt_id,
        parent_hunt_id=hunt_id,
    )
    flow_id_2 = db_test_utils.InitializeFlow(
        rel_db,
        client_id=client_id_2,
        flow_id=hunt_id,
        parent_hunt_id=hunt_id,
    )

    flow_obj_1 = rel_db.ReadFlowObject(client_id_1, flow_id_1)
    flow_obj_1.flow_state = flows_pb2.Flow.FlowState.ERROR
    flow_obj_1.error_message = "ERROR_1"
    rel_db.UpdateFlow(client_id_1, flow_id_1, flow_obj_1)

    flow_obj_2 = rel_db.ReadFlowObject(client_id_2, flow_id_2)
    flow_obj_2.flow_state = rdf_flow_objects.Flow.FlowState.ERROR
    flow_obj_2.error_message = "ERROR_2"
    rel_db.UpdateFlow(client_id_2, flow_id_2, flow_obj_2)

    args = api_hunt_pb2.ApiListHuntErrorsArgs()
    args.hunt_id = hunt_id

    handler = hunt_plugin.ApiListHuntErrorsHandler()

    results = handler.Handle(args)
    self.assertLen(results.items, 2)

    self.assertEqual(results.items[0].client_id, client_id_1)
    self.assertEqual(results.items[0].log_message, "ERROR_1")

    self.assertEqual(results.items[1].client_id, client_id_2)
    self.assertEqual(results.items[1].log_message, "ERROR_2")

  @db_test_lib.WithDatabase
  def testWithFilterByClientID(self, rel_db: db.Database):
    hunt_id = db_test_utils.InitializeHunt(rel_db)

    client_id_1 = db_test_utils.InitializeClient(rel_db)
    client_id_2 = db_test_utils.InitializeClient(rel_db)

    flow_id_1 = db_test_utils.InitializeFlow(
        rel_db,
        client_id=client_id_1,
        flow_id=hunt_id,
        parent_hunt_id=hunt_id,
    )
    flow_id_2 = db_test_utils.InitializeFlow(
        rel_db,
        client_id=client_id_2,
        flow_id=hunt_id,
        parent_hunt_id=hunt_id,
    )

    flow_obj_1 = rel_db.ReadFlowObject(client_id_1, flow_id_1)
    flow_obj_1.flow_state = flows_pb2.Flow.FlowState.ERROR
    flow_obj_1.error_message = "ERROR_1"
    rel_db.UpdateFlow(client_id_1, flow_id_1, flow_obj_1)

    flow_obj_2 = rel_db.ReadFlowObject(client_id_2, flow_id_2)
    flow_obj_2.flow_state = flows_pb2.Flow.FlowState.ERROR
    flow_obj_2.error_message = "ERROR_2"
    rel_db.UpdateFlow(client_id_2, flow_id_2, flow_obj_2)

    args = api_hunt_pb2.ApiListHuntErrorsArgs()
    args.hunt_id = hunt_id
    args.filter = client_id_2

    handler = hunt_plugin.ApiListHuntErrorsHandler()

    results = handler.Handle(args)
    self.assertLen(results.items, 1)

    self.assertEqual(results.items[0].client_id, client_id_2)
    self.assertEqual(results.items[0].log_message, "ERROR_2")

  @db_test_lib.WithDatabase
  def testWithFilterByMessage(self, rel_db: db.Database):
    hunt_id = db_test_utils.InitializeHunt(rel_db)

    client_id_1 = db_test_utils.InitializeClient(rel_db)
    client_id_2 = db_test_utils.InitializeClient(rel_db)

    flow_id_1 = db_test_utils.InitializeFlow(
        rel_db,
        client_id=client_id_1,
        flow_id=hunt_id,
        parent_hunt_id=hunt_id,
    )
    flow_id_2 = db_test_utils.InitializeFlow(
        rel_db,
        client_id=client_id_2,
        flow_id=hunt_id,
        parent_hunt_id=hunt_id,
    )

    flow_obj_1 = rel_db.ReadFlowObject(client_id_1, flow_id_1)
    flow_obj_1.flow_state = flows_pb2.Flow.FlowState.ERROR
    flow_obj_1.error_message = "ERROR_1"
    rel_db.UpdateFlow(client_id_1, flow_id_1, flow_obj_1)

    flow_obj_2 = rel_db.ReadFlowObject(client_id_2, flow_id_2)
    flow_obj_2.flow_state = flows_pb2.Flow.FlowState.ERROR
    flow_obj_2.error_message = "ERROR_2"
    rel_db.UpdateFlow(client_id_2, flow_id_2, flow_obj_2)

    args = api_hunt_pb2.ApiListHuntErrorsArgs()
    args.hunt_id = hunt_id
    args.filter = "_1"

    handler = hunt_plugin.ApiListHuntErrorsHandler()

    results = handler.Handle(args)
    self.assertLen(results.items, 1)

    self.assertEqual(results.items[0].client_id, client_id_1)
    self.assertEqual(results.items[0].log_message, "ERROR_1")

  @db_test_lib.WithDatabase
  def testWithFilterByBacktrace(self, rel_db: db.Database):
    hunt_id = db_test_utils.InitializeHunt(rel_db)

    client_id_1 = db_test_utils.InitializeClient(rel_db)
    client_id_2 = db_test_utils.InitializeClient(rel_db)

    flow_id_1 = db_test_utils.InitializeFlow(
        rel_db,
        client_id=client_id_1,
        flow_id=hunt_id,
        parent_hunt_id=hunt_id,
    )
    flow_id_2 = db_test_utils.InitializeFlow(
        rel_db,
        client_id=client_id_2,
        flow_id=hunt_id,
        parent_hunt_id=hunt_id,
    )

    flow_obj_1 = rel_db.ReadFlowObject(client_id_1, flow_id_1)
    flow_obj_1.flow_state = flows_pb2.Flow.FlowState.ERROR
    flow_obj_1.error_message = "ERROR_1"
    flow_obj_1.backtrace = "File 'foo_1.py', line 1, in 'foo'"
    rel_db.UpdateFlow(client_id_1, flow_id_1, flow_obj_1)

    flow_obj_2 = rel_db.ReadFlowObject(client_id_2, flow_id_2)
    flow_obj_2.flow_state = flows_pb2.Flow.FlowState.ERROR
    flow_obj_2.error_message = "ERROR_2"
    flow_obj_2.backtrace = "File 'foo_2.py', line 1, in 'foo'"
    rel_db.UpdateFlow(client_id_2, flow_id_2, flow_obj_2)

    args = api_hunt_pb2.ApiListHuntErrorsArgs()
    args.hunt_id = hunt_id
    args.filter = "foo_2.py"

    handler = hunt_plugin.ApiListHuntErrorsHandler()

    results = handler.Handle(args)
    self.assertLen(results.items, 1)

    self.assertEqual(results.items[0].client_id, client_id_2)
    self.assertEqual(results.items[0].log_message, "ERROR_2")


class TestHistogram(absltest.TestCase):

  def testHistogram(self):
    timestamps = list(range(100))
    min_ts, max_ts = 0, 100
    num_buckets = 5

    histogram = hunt_plugin.Histogram(
        min_ts, max_ts, num_buckets, values=timestamps
    )

    expected_bucket_size = 20
    self.assertLen(histogram.buckets, 5)
    first_bucket = histogram.buckets[0]
    self.assertAlmostEqual(first_bucket.lower_boundary_ts, 0)
    self.assertEqual(first_bucket.count, 20)

    last_bucket = histogram.buckets[-1]
    self.assertAlmostEqual(
        last_bucket.lower_boundary_ts, max_ts - expected_bucket_size
    )
    self.assertEqual(last_bucket.count, 20)

  def testHistogramRaisesWhenInsertingOutOfRangeTimestamp(self):
    with self.assertRaises(ValueError):
      hunt_plugin.Histogram(
          min_timestamp=0, max_timestamp=100, num_buckets=5, values=[-1]
      )

  def testCumulativeHistogram(self):
    histogram = hunt_plugin.Histogram(
        min_timestamp=0,
        max_timestamp=9,
        num_buckets=3,
        values=[0, 1, 2] + [3, 4] + [6],  # Bucket 0 + Bucket 1 + Bucket 2
    )
    cumulative_histogram = histogram.GetCumulativeHistogram()
    expected_bucket_boundaries = [0, 3, 6]
    expected_bucket_counts = [3, 5, 6]

    self.assertLen(cumulative_histogram.buckets, 3)
    self.assertEqual(
        [b.lower_boundary_ts for b in cumulative_histogram.buckets],
        expected_bucket_boundaries,
    )
    self.assertEqual(
        [b.count for b in cumulative_histogram.buckets],
        expected_bucket_counts,
    )

  def testCumulativeHistogramContainsIncludesEmptyHistogramBuckets(self):
    histogram = hunt_plugin.Histogram(
        min_timestamp=0,
        max_timestamp=3,
        num_buckets=3,
        values=[1, 1],  # Bucket 1
        # Buckets 0 and 2 are empty
    )
    cumulative_histogram = histogram.GetCumulativeHistogram()
    expected_bucket_boundaries = [0, 1, 2]
    expected_bucket_counts = [0, 2, 2]

    self.assertEqual(
        [b.lower_boundary_ts for b in cumulative_histogram.buckets],
        expected_bucket_boundaries,
    )
    self.assertEqual(
        [b.count for b in cumulative_histogram.buckets],
        expected_bucket_counts,
    )


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
