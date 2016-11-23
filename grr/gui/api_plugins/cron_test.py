#!/usr/bin/env python
"""This module contains tests for cron-related API handlers."""




from grr.gui import api_test_lib
from grr.gui.api_plugins import cron as cron_plugin

from grr.lib import flags
from grr.lib import test_lib
from grr.lib.aff4_objects import cronjobs
from grr.lib.flows.cron import system as cron_system


class CronJobsTestMixin(object):

  def CreateCronJob(self,
                    flow_name,
                    periodicity="1d",
                    lifetime="7d",
                    description="",
                    disabled=False,
                    token=None):
    cron_args = cronjobs.CreateCronJobFlowArgs(
        periodicity=periodicity, lifetime=lifetime, description=description)
    cron_args.flow_runner_args.flow_name = flow_name

    return cronjobs.CRON_MANAGER.ScheduleFlow(
        cron_args, job_name=flow_name, disabled=disabled, token=token)


class ApiDeleteCronJobHandlerTest(api_test_lib.ApiCallHandlerTest,
                                  CronJobsTestMixin):
  """Test delete cron job handler."""

  def setUp(self):
    super(ApiDeleteCronJobHandlerTest, self).setUp()
    self.handler = cron_plugin.ApiDeleteCronJobHandler()

    self.cron_job_urn = self.CreateCronJob(
        flow_name=cron_system.OSBreakDown.__name__, token=self.token)

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
