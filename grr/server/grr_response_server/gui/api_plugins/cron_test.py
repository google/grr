#!/usr/bin/env python
"""This module contains tests for cron-related API handlers."""

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_server import data_store
from grr_response_server.aff4_objects import cronjobs
from grr_response_server.flows.cron import system as cron_system
from grr_response_server.gui import api_test_lib
from grr_response_server.gui.api_plugins import cron as cron_plugin
from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs
from grr_response_server.rdfvalues import hunts as rdf_hunts
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class CronJobsTestMixin(object):

  def CreateCronJob(self,
                    flow_name,
                    periodicity="1d",
                    lifetime="7d",
                    description="",
                    enabled=True,
                    token=None):
    args = rdf_cronjobs.CreateCronJobArgs(
        flow_name=flow_name,
        description=description,
        frequency=periodicity,
        lifetime=lifetime)
    return cronjobs.GetCronManager().CreateJob(
        args, enabled=enabled, token=token)


class ApiCreateCronJobHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiCreateCronJobHandler."""

  def setUp(self):
    super(ApiCreateCronJobHandlerTest, self).setUp()
    self.handler = cron_plugin.ApiCreateCronJobHandler()

  def testAddForemanRulesHuntRunnerArgumentIsNotRespected(self):
    args = cron_plugin.ApiCreateCronJobArgs(
        flow_name=flow_test_lib.FlowWithOneNestedFlow.__name__,
        hunt_runner_args=rdf_hunts.HuntRunnerArgs(
            # Default is True.
            add_foreman_rules=False))
    result = self.handler.Handle(args, token=self.token)
    self.assertTrue(
        result.args.hunt_cron_action.hunt_runner_args.add_foreman_rules)


class ApiDeleteCronJobHandlerTest(api_test_lib.ApiCallHandlerTest,
                                  CronJobsTestMixin):
  """Test delete cron job handler."""

  def setUp(self):
    super(ApiDeleteCronJobHandlerTest, self).setUp()
    self.handler = cron_plugin.ApiDeleteCronJobHandler()

    self.cron_job_id = self.CreateCronJob(
        flow_name=cron_system.OSBreakDown.__name__, token=self.token)

  def testDeletesCronFromCollection(self):
    jobs = list(cronjobs.GetCronManager().ListJobs(token=self.token))
    self.assertEqual(len(jobs), 1)
    self.assertEqual(jobs[0], self.cron_job_id)

    args = cron_plugin.ApiDeleteCronJobArgs(cron_job_id=self.cron_job_id)
    self.handler.Handle(args, token=self.token)

    jobs = list(cronjobs.GetCronManager().ListJobs(token=self.token))
    self.assertEqual(len(jobs), 0)


class ApiGetCronJobHandlerTest(db_test_lib.RelationalDBEnabledMixin,
                               api_test_lib.ApiCallHandlerTest):
  """Tests the ApiGetCronJobHandler."""

  def setUp(self):
    super(ApiGetCronJobHandlerTest, self).setUp()
    self.handler = cron_plugin.ApiGetCronJobHandler()

  def testHandler(self):
    now = rdfvalue.RDFDatetime.Now()
    with test_lib.FakeTime(now):
      job = rdf_cronjobs.CronJob(
          cron_job_id="job_id",
          enabled=True,
          last_run_status="FINISHED",
          frequency=rdfvalue.Duration("7d"),
          lifetime=rdfvalue.Duration("1h"),
          allow_overruns=True)
      data_store.REL_DB.WriteCronJob(job)

    state = rdf_protodict.AttributedDict()
    state["item"] = "key"
    data_store.REL_DB.UpdateCronJob(
        job.cron_job_id,
        current_run_id="ABCD1234",
        state=state,
        forced_run_requested=True)

    args = cron_plugin.ApiGetCronJobArgs(cron_job_id=job.cron_job_id)
    result = self.handler.Handle(args)

    self.assertEqual(result.cron_job_id, job.cron_job_id)
    # TODO(amoser): The aff4 implementation does not store the create time so we
    # can't return it yet.
    # self.assertEqual(result.created_at, now)
    self.assertEqual(result.enabled, job.enabled)
    self.assertEqual(result.current_run_id, "ABCD1234")
    self.assertEqual(result.forced_run_requested, True)
    self.assertEqual(result.frequency, job.frequency)
    self.assertEqual(result.is_failing, False)
    self.assertEqual(result.last_run_status, job.last_run_status)
    self.assertEqual(result.lifetime, job.lifetime)
    state_entries = list(result.state.items)
    self.assertEqual(len(state_entries), 1)
    state_entry = state_entries[0]
    self.assertEqual(state_entry.key, "item")
    self.assertEqual(state_entry.value, "key")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
