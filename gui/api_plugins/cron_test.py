#!/usr/bin/env python
"""This module contains tests for cron-related API handlers."""




from grr.gui import api_test_lib

from grr.lib import aff4
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.aff4_objects import cronjobs
from grr.lib.flows.cron import system as cron_system
from grr.lib.rdfvalues import grr_rdf


class ApiListCronJobsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Test cron jobs list handler."""

  handler = "ApiListCronJobsHandler"

  def Run(self):
    # Add one "normal" cron job...
    with test_lib.FakeTime(42):
      flow_name = cron_system.GRRVersionBreakDown.__name__

      cron_args = cronjobs.CreateCronJobFlowArgs(periodicity="1d",
                                                 lifetime="2h",
                                                 description="foo")
      cron_args.flow_runner_args.flow_name = flow_name
      cronjobs.CRON_MANAGER.ScheduleFlow(cron_args, job_name=flow_name,
                                         disabled=True, token=self.token)

    # ...one disabled cron job,
    with test_lib.FakeTime(84):
      flow_name = cron_system.OSBreakDown.__name__

      cron_args = cronjobs.CreateCronJobFlowArgs(periodicity="7d",
                                                 lifetime="1d",
                                                 description="bar")
      cron_args.flow_runner_args.flow_name = flow_name
      cronjobs.CRON_MANAGER.ScheduleFlow(cron_args, job_name=flow_name,
                                         token=self.token)

    # ...and one failing cron job.
    with test_lib.FakeTime(126):
      flow_name = cron_system.LastAccessStats.__name__

      cron_args = cronjobs.CreateCronJobFlowArgs(periodicity="7d",
                                                 lifetime="1d")
      cron_args.flow_runner_args.flow_name = flow_name
      cron_urn = cronjobs.CRON_MANAGER.ScheduleFlow(cron_args,
                                                    job_name=flow_name,
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

    self.Check("POST", "/api/cron-jobs",
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
                        "regex_rules": [{"attribute_name": "System",
                                         "attribute_regex": "Windows"}],
                        "description": "Foobar! (cron)"
                        }
                    },
                "description": "Foobar!"}, replace=ReplaceCronJobUrn)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
