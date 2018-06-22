#!/usr/bin/env python
"""This module contains tests for cron-related API handlers."""


from grr.lib import flags
from grr.lib.rdfvalues import cronjobs as rdf_cronjobs
from grr.lib.rdfvalues import flows as rdf_flows

from grr.server.grr_response_server.aff4_objects import cronjobs
from grr.server.grr_response_server.flows.cron import system as cron_system
from grr.server.grr_response_server.gui import api_test_lib
from grr.server.grr_response_server.gui.api_plugins import cron as cron_plugin
from grr.server.grr_response_server.hunts import standard
from grr.test_lib import test_lib


class CronJobsTestMixin(object):

  def CreateCronJob(self,
                    flow_name,
                    periodicity="1d",
                    lifetime="7d",
                    description="",
                    disabled=False,
                    token=None):
    cron_args = rdf_cronjobs.CreateCronJobFlowArgs(
        periodicity=periodicity, lifetime=lifetime, description=description)
    cron_args.flow_runner_args.flow_name = flow_name

    return cronjobs.GetCronManager().CreateJob(
        cron_args, job_id=flow_name, disabled=disabled, token=token)


class ApiCreateCronJobHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiCreateCronJobHandler."""

  def setUp(self):
    super(ApiCreateCronJobHandlerTest, self).setUp()
    self.handler = cron_plugin.ApiCreateCronJobHandler()

  def testBaseSessionIdFlowRunnerArgumentIsNotRespected(self):
    args = cron_plugin.ApiCronJob(
        flow_name=standard.CreateAndRunGenericHuntFlow.__name__,
        flow_runner_args=rdf_flows.FlowRunnerArgs(base_session_id="aff4:/foo"))
    result = self.handler.Handle(args, token=self.token)
    self.assertFalse(result.flow_runner_args.HasField("base_session_id"))


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


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
