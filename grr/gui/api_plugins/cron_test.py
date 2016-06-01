#!/usr/bin/env python
"""This module contains tests for cron-related API handlers."""




from grr.gui import api_test_lib
from grr.gui.api_plugins import cron as cron_plugin

from grr.lib import aff4
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.aff4_objects import cronjobs
from grr.lib.flows.cron import system as cron_system
from grr.lib.rdfvalues import grr_rdf


class CronJobsTestMixin(object):

  def CreateCronJob(self,
                    flow_name,
                    periodicity="1d",
                    lifetime="7d",
                    description="",
                    disabled=False,
                    token=None):
    cron_args = cronjobs.CreateCronJobFlowArgs(periodicity=periodicity,
                                               lifetime=lifetime,
                                               description=description)
    cron_args.flow_runner_args.flow_name = flow_name

    return cronjobs.CRON_MANAGER.ScheduleFlow(cron_args,
                                              job_name=flow_name,
                                              disabled=disabled,
                                              token=token)


class ApiListCronJobsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest, CronJobsTestMixin):
  """Test cron jobs list handler."""

  handler = "ApiListCronJobsHandler"

  def Run(self):
    # Add one "normal" cron job...
    with test_lib.FakeTime(42):
      self.CreateCronJob(flow_name=cron_system.GRRVersionBreakDown.__name__,
                         periodicity="1d",
                         lifetime="2h",
                         description="foo",
                         disabled=True,
                         token=self.token)

    # ...one disabled cron job,
    with test_lib.FakeTime(84):
      self.CreateCronJob(flow_name=cron_system.OSBreakDown.__name__,
                         periodicity="7d",
                         lifetime="1d",
                         description="bar",
                         token=self.token)

    # ...and one failing cron job.
    with test_lib.FakeTime(126):
      cron_urn = self.CreateCronJob(
          flow_name=cron_system.LastAccessStats.__name__,
          periodicity="7d",
          lifetime="1d",
          token=self.token)

      for i in range(4):
        with test_lib.FakeTime(200 + i * 10):
          with aff4.FACTORY.OpenWithLock(cron_urn, token=self.token) as job:
            job.Set(job.Schema.LAST_RUN_TIME(rdfvalue.RDFDatetime().Now()))
            job.Set(job.Schema.LAST_RUN_STATUS(
                status=grr_rdf.CronJobRunStatus.Status.ERROR))

    self.Check("GET", "/api/cron-jobs")


class ApiCreateCronJobHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Test handler that creates a new cron job."""

  handler = "ApiCreateCronJobHandler"

  def Run(self):

    def ReplaceCronJobUrn():
      jobs = list(cronjobs.CRON_MANAGER.ListJobs(token=self.token))
      return {jobs[0].Basename(): "CreateAndRunGeneicHuntFlow_1234"}

    self.Check("POST",
               "/api/cron-jobs",
               {"flow_name": "CreateAndRunGenericHuntFlow",
                "periodicity": 604800,
                "lifetime": 3600,
                "flow_args": {
                    "hunt_args": {
                        "flow_runner_args": {
                            "flow_name": "FileFinder"
                        },
                        "flow_args": {
                            "paths": ["c:\\windows\\system32\\notepad.*"]
                        },
                    },
                    "hunt_runner_args": {
                        "client_rule_set": {
                            "rules": [
                                {
                                    "os": {
                                        "os_windows": True
                                    }
                                }
                            ]
                        },
                        "description": "Foobar! (cron)"
                    }
                },
                "description": "Foobar!"},
               replace=ReplaceCronJobUrn)


class ApiDeleteCronJobHandlerTest(test_lib.GRRBaseTest, CronJobsTestMixin):
  """Test delete cron job handler."""

  def setUp(self):
    super(ApiDeleteCronJobHandlerTest, self).setUp()
    self.handler = cron_plugin.ApiDeleteCronJobHandler()

    self.cron_job_urn = self.CreateCronJob(
        flow_name=cron_system.OSBreakDown.__name__,
        token=self.token)

  def testDeletesCronFromCollection(self):
    jobs = list(cronjobs.CRON_MANAGER.ListJobs(token=self.token))
    self.assertEqual(len(jobs), 1)
    self.assertEqual(jobs[0], self.cron_job_urn)

    args = cron_plugin.ApiDeleteCronJobArgs(
        cron_job_id=self.cron_job_urn.Basename())
    self.handler.Handle(args, token=self.token)

    jobs = list(cronjobs.CRON_MANAGER.ListJobs(token=self.token))
    self.assertEqual(len(jobs), 0)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
