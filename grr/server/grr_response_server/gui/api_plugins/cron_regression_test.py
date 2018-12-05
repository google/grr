#!/usr/bin/env python
"""This module contains regression tests for cron-related API handlers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.util import compatibility
from grr_response_server import aff4
from grr_response_server import cronjobs
from grr_response_server import data_store
from grr_response_server import foreman_rules
from grr_response_server.aff4_objects import cronjobs as aff4_cronjobs
from grr_response_server.flows.cron import system as cron_system
from grr_response_server.flows.general import file_finder
from grr_response_server.gui import api_regression_test_lib
from grr_response_server.gui.api_plugins import cron as cron_plugin
from grr_response_server.gui.api_plugins import cron_test as cron_plugin_test
from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs
from grr_response_server.rdfvalues import hunts as rdf_hunts
from grr.test_lib import flow_test_lib
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
      cron_id_1 = self.CreateCronJob(
          flow_name=cron_system.GRRVersionBreakDown.__name__,
          periodicity="1d",
          lifetime="2h",
          description="foo",
          enabled=False,
          token=self.token)

    # ...one disabled cron job,
    with test_lib.FakeTime(84):
      cron_id_2 = self.CreateCronJob(
          flow_name=cron_system.OSBreakDown.__name__,
          periodicity="7d",
          lifetime="1d",
          description="bar",
          token=self.token)

    # ...and one failing cron job.
    with test_lib.FakeTime(126):
      cron_id_3 = self.CreateCronJob(
          flow_name=cron_system.LastAccessStats.__name__,
          periodicity="7d",
          lifetime="1d",
          token=self.token)

    with test_lib.FakeTime(230):
      if data_store.RelationalDBReadEnabled(category="cronjobs"):
        data_store.REL_DB.UpdateCronJob(
            cron_id_3,
            last_run_time=rdfvalue.RDFDatetime.Now(),
            last_run_status=rdf_cronjobs.CronJobRun.CronJobRunStatus.ERROR)
      else:
        cron_urn = aff4_cronjobs.GetCronManager().CRON_JOBS_PATH.Add(cron_id_3)
        with aff4.FACTORY.OpenWithLock(cron_urn, token=self.token) as job:
          job.Set(job.Schema.LAST_RUN_TIME(rdfvalue.RDFDatetime.Now()))
          job.Set(
              job.Schema.LAST_RUN_STATUS(
                  status=rdf_cronjobs.CronJobRunStatus.Status.ERROR))

    self.Check(
        "ListCronJobs",
        args=cron_plugin.ApiListCronJobsArgs(),
        replace={
            cron_id_1: "GRRVersionBreakDown",
            cron_id_2: "OSBreakDown",
            cron_id_3: "LastAccessStats"
        })


def _GetRunId(cron_job_name, token=None):
  runs = aff4_cronjobs.GetCronManager().ReadJobRuns(cron_job_name, token=token)

  try:
    return runs[0].run_id
  except AttributeError:
    return runs[0].urn.Basename()


def _SetupAndRunVersionBreakDownCronjob(token=None):
  with test_lib.FakeTime(44):
    manager = aff4_cronjobs.GetCronManager()

    if data_store.RelationalDBReadEnabled("cronjobs"):
      cron_job_name = compatibility.GetName(
          cron_system.GRRVersionBreakDownCronJob)
      cronjobs.ScheduleSystemCronJobs(names=[cron_job_name])
      manager.RunOnce()
      manager._GetThreadPool().Stop()
    else:
      cron_job_name = compatibility.GetName(cron_system.GRRVersionBreakDown)
      aff4_cronjobs.ScheduleSystemCronFlows(names=[cron_job_name], token=token)
      manager.RunOnce(token=token)
      run_id = _GetRunId(cron_job_name, token=token)
      flow_test_lib.TestFlowHelper(
          rdfvalue.RDFURN("aff4:/cron/%s/%s" % (cron_job_name, run_id)),
          token=token)
      manager.RunOnce(token=token)

    return cron_job_name


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
      jobs = list(aff4_cronjobs.GetCronManager().ListJobs(token=self.token))
      return {jobs[0]: "CreateAndRunGenericHuntFlow_1234"}

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
    api_regression_test_lib.ApiRegressionTest,
    cron_plugin_test.CronJobsTestMixin):
  """Test cron job runs list handler."""

  api_method = "ListCronJobRuns"
  handler = cron_plugin.ApiListCronJobRunsHandler

  def Run(self):
    cron_job_id = _SetupAndRunVersionBreakDownCronjob(token=self.token)
    run_id = _GetRunId(cron_job_id, token=self.token)

    self.Check(
        "ListCronJobRuns",
        args=cron_plugin.ApiListCronJobRunsArgs(cron_job_id=cron_job_id),
        replace={
            run_id: "F:ABCDEF11",
            cron_job_id: "GRRVersionBreakDown"
        })


class ApiGetCronJobRunHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):
  """Test cron job run getter handler."""

  api_method = "GetCronJobRun"
  handler = cron_plugin.ApiGetCronJobRunHandler

  def Run(self):
    cron_job_id = _SetupAndRunVersionBreakDownCronjob(token=self.token)
    run_id = _GetRunId(cron_job_id, token=self.token)

    self.Check(
        "GetCronJobRun",
        args=cron_plugin.ApiGetCronJobRunArgs(
            cron_job_id=cron_job_id, run_id=run_id),
        replace={
            run_id: "F:ABCDEF11",
            cron_job_id: "GRRVersionBreakDown"
        })


class ApiForceRunCronJobRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    cron_plugin_test.CronJobsTestMixin):
  """Test cron job flow getter handler."""

  api_method = "ForceRunCronJob"
  handler = cron_plugin.ApiForceRunCronJobHandler

  def Run(self):
    cron_job_id = self.CreateCronJob(
        flow_name=cron_system.OSBreakDown.__name__, token=self.token)

    self.Check(
        "ForceRunCronJob",
        args=cron_plugin.ApiForceRunCronJobArgs(cron_job_id=cron_job_id),
        replace={cron_job_id: "OSBreakDown"})


class ApiModifyCronJobRegressionTest(api_regression_test_lib.ApiRegressionTest,
                                     cron_plugin_test.CronJobsTestMixin):
  """Test cron job flow getter handler."""

  api_method = "ModifyCronJob"
  handler = cron_plugin.ApiModifyCronJobHandler

  def Run(self):
    with test_lib.FakeTime(44):
      cron_job_id1 = self.CreateCronJob(
          flow_name=cron_system.OSBreakDown.__name__, token=self.token)
      cron_job_id2 = self.CreateCronJob(
          flow_name=cron_system.GRRVersionBreakDown.__name__, token=self.token)

    self.Check(
        "ModifyCronJob",
        args=cron_plugin.ApiModifyCronJobArgs(
            cron_job_id=cron_job_id1, enabled=True),
        replace={
            cron_job_id1: "OSBreakDown",
            cron_job_id2: "GRRVersionBreakDown"
        })
    self.Check(
        "ModifyCronJob",
        args=cron_plugin.ApiModifyCronJobArgs(
            cron_job_id=cron_job_id2, enabled=False),
        replace={
            cron_job_id1: "OSBreakDown",
            cron_job_id2: "GRRVersionBreakDown"
        })


def main(argv):
  api_regression_test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
