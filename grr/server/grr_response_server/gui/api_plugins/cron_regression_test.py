#!/usr/bin/env python
"""This module contains regression tests for cron-related API handlers."""


from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue

from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import foreman_rules
from grr_response_server.aff4_objects import cronjobs
from grr_response_server.flows.cron import system as cron_system
from grr_response_server.flows.general import file_finder
from grr_response_server.gui import api_regression_test_lib
from grr_response_server.gui.api_plugins import cron as cron_plugin
from grr_response_server.gui.api_plugins import cron_test as cron_plugin_test
from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs
from grr_response_server.rdfvalues import hunts as rdf_hunts
from grr.test_lib import test_lib


class ApiListCronJobsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    cron_plugin_test.CronJobsTestMixin):
  """Test cron jobs list handler."""

  api_method = "ListCronJobs"
  handler = cron_plugin.ApiListCronJobsHandler

  def Run(self):
    # Add one "normal" cron job...
    with test_lib.FakeTime(42):
      self.CreateCronJob(
          flow_name=cron_system.GRRVersionBreakDown.__name__,
          periodicity="1d",
          lifetime="2h",
          description="foo",
          disabled=True,
          token=self.token)

    # ...one disabled cron job,
    with test_lib.FakeTime(84):
      self.CreateCronJob(
          flow_name=cron_system.OSBreakDown.__name__,
          periodicity="7d",
          lifetime="1d",
          description="bar",
          token=self.token)

    # ...and one failing cron job.
    with test_lib.FakeTime(126):
      cron_id = self.CreateCronJob(
          flow_name=cron_system.LastAccessStats.__name__,
          periodicity="7d",
          lifetime="1d",
          token=self.token)

    with test_lib.FakeTime(230):
      if data_store.RelationalDBReadEnabled(category="cronjobs"):
        data_store.REL_DB.UpdateCronJob(
            cron_id,
            last_run_time=rdfvalue.RDFDatetime.Now(),
            last_run_status=rdf_cronjobs.CronJobRunStatus.Status.ERROR)
      else:
        cron_urn = cronjobs.GetCronManager().CRON_JOBS_PATH.Add(cron_id)
        with aff4.FACTORY.OpenWithLock(cron_urn, token=self.token) as job:
          job.Set(job.Schema.LAST_RUN_TIME(rdfvalue.RDFDatetime.Now()))
          job.Set(
              job.Schema.LAST_RUN_STATUS(
                  status=rdf_cronjobs.CronJobRunStatus.Status.ERROR))

    self.Check("ListCronJobs", args=cron_plugin.ApiListCronJobsArgs())


class ApiCreateCronJobHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):
  """Test handler that creates a new cron job."""

  api_method = "CreateCronJob"
  handler = cron_plugin.ApiCreateCronJobHandler

  # ApiCronJob references CreateAndRunGenericHuntFlow that contains
  # some legacy dynamic fields, that can't be serialized in JSON-proto3-friendly
  # way.
  uses_legacy_dynamic_protos = True

  def Run(self):

    def ReplaceCronJobUrn():
      jobs = list(cronjobs.GetCronManager().ListJobs(token=self.token))
      return {jobs[0]: "CreateAndRunGeneicHuntFlow_1234"}

    flow_name = file_finder.FileFinder.__name__
    flow_args = rdf_file_finder.FileFinderArgs(
        paths=["c:\\windows\\system32\\notepad.*"])

    hunt_runner_args = rdf_hunts.HuntRunnerArgs()
    hunt_runner_args.client_rule_set.rules = [
        foreman_rules.ForemanClientRule(
            os=foreman_rules.ForemanOsClientRule(os_windows=True))
    ]
    hunt_runner_args.description = "Foobar! (cron)"

    self.Check(
        "CreateCronJob",
        args=cron_plugin.ApiCreateCronJobArgs(
            description="Foobar!",
            flow_name=flow_name,
            flow_args=flow_args,
            hunt_runner_args=hunt_runner_args,
            periodicity=604800,
            lifetime=3600),
        replace=ReplaceCronJobUrn)


class ApiListCronJobRunsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):
  """Test cron job runs list handler."""

  api_method = "ListCronJobRuns"
  handler = cron_plugin.ApiListCronJobRunsHandler

  flow_name = cron_system.GRRVersionBreakDown.__name__

  def setUp(self):
    super(ApiListCronJobRunsHandlerRegressionTest, self).setUp()

    with test_lib.FakeTime(44):
      cron_args = rdf_cronjobs.CreateCronJobFlowArgs(
          periodicity="7d", lifetime="1d")
      cron_args.flow_runner_args.flow_name = self.flow_name
      cronjobs.GetCronManager().CreateJob(
          cron_args, job_id=self.flow_name, token=self.token)

      cronjobs.GetCronManager().RunOnce(token=self.token)

  def _GetRunId(self):
    runs = cronjobs.GetCronManager().ReadJobRuns(
        self.flow_name, token=self.token)

    return runs[0].urn.Basename()

  def Run(self):
    run_id = self._GetRunId()

    self.Check(
        "ListCronJobRuns",
        args=cron_plugin.ApiListCronJobRunsArgs(cron_job_id=self.flow_name),
        replace={run_id: "F:ABCDEF11"})


class ApiGetCronJobRunHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):
  """Test cron job run getter handler."""

  api_method = "GetCronJobRun"
  handler = cron_plugin.ApiGetCronJobRunHandler

  def setUp(self):
    super(ApiGetCronJobRunHandlerRegressionTest, self).setUp()

    self.flow_name = cron_system.GRRVersionBreakDown.__name__

    with test_lib.FakeTime(44):
      cron_args = rdf_cronjobs.CreateCronJobFlowArgs(
          periodicity="7d", lifetime="1d")
      cron_args.flow_runner_args.flow_name = self.flow_name
      cronjobs.GetCronManager().CreateJob(
          cron_args, job_id=self.flow_name, token=self.token)

      cronjobs.GetCronManager().RunOnce(token=self.token)

  def _GetRunId(self):
    runs = cronjobs.GetCronManager().ReadJobRuns(
        self.flow_name, token=self.token)

    return runs[0].urn.Basename()

  def Run(self):
    run_id = self._GetRunId()

    self.Check(
        "GetCronJobRun",
        args=cron_plugin.ApiGetCronJobRunArgs(
            cron_job_id=self.flow_name, run_id=run_id),
        replace={run_id: "F:ABCDEF11"})


class ApiForceRunCronJobRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    cron_plugin_test.CronJobsTestMixin):
  """Test cron job flow getter handler."""

  api_method = "ForceRunCronJob"
  handler = cron_plugin.ApiForceRunCronJobHandler

  def Run(self):
    self.CreateCronJob(
        flow_name=cron_system.OSBreakDown.__name__, token=self.token)

    self.Check(
        "ForceRunCronJob",
        args=cron_plugin.ApiForceRunCronJobArgs(
            cron_job_id=cron_system.OSBreakDown.__name__))


class ApiModifyCronJobRegressionTest(api_regression_test_lib.ApiRegressionTest,
                                     cron_plugin_test.CronJobsTestMixin):
  """Test cron job flow getter handler."""

  api_method = "ModifyCronJob"
  handler = cron_plugin.ApiModifyCronJobHandler

  def Run(self):
    self.CreateCronJob(
        flow_name=cron_system.OSBreakDown.__name__, token=self.token)
    self.CreateCronJob(
        flow_name=cron_system.GRRVersionBreakDown.__name__, token=self.token)

    self.Check(
        "ModifyCronJob",
        args=cron_plugin.ApiModifyCronJobArgs(
            cron_job_id=cron_system.OSBreakDown.__name__, state="ENABLED"))
    self.Check(
        "ModifyCronJob",
        args=cron_plugin.ApiModifyCronJobArgs(
            cron_job_id=cron_system.GRRVersionBreakDown.__name__,
            state="DISABLED"))


def main(argv):
  api_regression_test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
