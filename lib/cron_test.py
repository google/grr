#!/usr/bin/env python
import time


# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import aff4
from grr.lib import cron
from grr.lib import flags
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import test_lib


class FakeCronJob(flow.GRRFlow):
  """A Cron job which does nothing."""

  @flow.StateHandler(next_state="End")
  def Start(self):
    self.CallState(next_state="End")


class CronTest(test_lib.GRRBaseTest):
  """Tests for cron functionality."""

  def testCronJobPreservesFlowNameAndArguments(self):
    """Testing initialization of a ConfigManager."""
    pathspec = rdfvalue.PathSpec(path="/foo",
                                 pathtype=rdfvalue.PathSpec.PathType.TSK)

    cron_manager = cron.CronManager()
    cron_job_urn = cron_manager.ScheduleFlow(
        "GetFile", flow_args={"pathspec": pathspec},
        frequency=rdfvalue.Duration("1d"), allow_overruns=False,
        token=self.token)

    # Check that CronJob definition is saved properly
    cron_root = aff4.FACTORY.Open(cron_manager.CRON_JOBS_PATH, token=self.token)
    cron_jobs = list(cron_root.ListChildren())
    self.assertEqual(len(cron_jobs), 1)
    self.assertEqual(cron_jobs[0], cron_job_urn)

    cron_job = aff4.FACTORY.Open(cron_jobs[0], token=self.token)
    self.assertEqual(cron_job.Get(cron_job.Schema.FLOW_NAME), "GetFile")

    flow_args = cron_job.Get(cron_job.Schema.FLOW_ARGS)
    self.assertEqual(flow_args["pathspec"], pathspec)

    self.assertEqual(cron_job.Get(cron_job.Schema.FREQUENCY),
                     rdfvalue.Duration("1d"))
    self.assertEqual(cron_job.Get(cron_job.Schema.ALLOW_OVERRUNS), False)

  def testCronJobStartsFlowAndCreatesSymlinkOnRun(self):
    cron_manager = cron.CronManager()
    cron_job_urn = cron_manager.ScheduleFlow("FakeCronJob", flow_args={},
                                             token=self.token)

    cron_job = aff4.FACTORY.Open(cron_job_urn, aff4_type="CronJob",
                                 token=self.token)
    self.assertFalse(cron_job.IsRunning())
    # The job never ran, so DueToRun() should return true.
    self.assertTrue(cron_job.DueToRun())

    cron_manager.RunOnce(token=self.token)

    cron_job = aff4.FACTORY.Open(cron_job_urn, aff4_type="CronJob",
                                 token=self.token)
    self.assertTrue(cron_job.IsRunning())

    # Check that a link to the flow is created under job object.
    cron_job_flows = list(cron_job.ListChildren())
    self.assertEqual(len(cron_job_flows), 1)

    # Check that the link points to the correct flow.
    cron_job_flow = aff4.FACTORY.Open(cron_job_flows[0], token=self.token)
    self.assertEqual(cron_job_flow.state.context.flow_name, "FakeCronJob")

  def testDisabledCronJobDoesNotScheduleFlows(self):
    cron_manager = cron.CronManager()
    cron_job_urn1 = cron_manager.ScheduleFlow("FakeCronJob", flow_args={},
                                              token=self.token)
    cron_job_urn2 = cron_manager.ScheduleFlow("FakeCronJob", flow_args={},
                                              token=self.token)

    cron_job1 = aff4.FACTORY.Open(cron_job_urn1, aff4_type="CronJob",
                                  mode="rw", token=self.token)
    cron_job1.Set(cron_job1.Schema.DISABLED(1))
    cron_job1.Close()

    cron_manager.RunOnce(token=self.token)

    cron_job1 = aff4.FACTORY.Open(cron_job_urn1, aff4_type="CronJob",
                                  token=self.token)
    cron_job2 = aff4.FACTORY.Open(cron_job_urn2, aff4_type="CronJob",
                                  token=self.token)

    # Disabled flow shouldn't be running, while not-disabled flow should run
    # as usual.
    self.assertFalse(cron_job1.IsRunning())
    self.assertTrue(cron_job2.IsRunning())

  def testCronJobRunMonitorsRunningFlowState(self):
    cron_manager = cron.CronManager()
    cron_job_urn = cron_manager.ScheduleFlow("FakeCronJob", flow_args={},
                                             allow_overruns=False,
                                             frequency=rdfvalue.Duration("1d"),
                                             token=self.token)

    # Run() wasn't called, so nothing is supposed to be running
    cron_job = aff4.FACTORY.Open(cron_job_urn, aff4_type="CronJob",
                                 token=self.token)
    self.assertFalse(cron_job.IsRunning())

    cron_manager.RunOnce(token=self.token)

    # Run() was called and flow was started, so the job should be
    # considered running.
    cron_job = aff4.FACTORY.Open(cron_job_urn, aff4_type="CronJob",
                                 token=self.token)
    self.assertTrue(cron_job.IsRunning())

    # Find the flow that is currently running for the job and terminate it.
    cron_job = aff4.FACTORY.Open(cron_job_urn, aff4_type="CronJob",
                                 token=self.token)
    self.assertTrue(cron_job.IsRunning())
    cron_job_flow_urn = cron_job.Get(cron_job.Schema.CURRENT_FLOW_URN)
    self.assertTrue(cron_job_flow_urn is not None)
    flow.GRRFlow.TerminateFlow(cron_job_flow_urn, token=self.token)

    # We're still running, becasue Run() wasn't called and therefore
    # current flow status wasn't checked.
    cron_job = aff4.FACTORY.Open(cron_job_urn, aff4_type="CronJob",
                                 token=self.token)
    self.assertTrue(cron_job.IsRunning())

    # This will understand that current flow has terminated. New flow won't be
    # started, because iterations are supposed to be started once per day
    # (frequency=1d).
    cron_manager.RunOnce(token=self.token)

    # RunOnce was called, so state should be marked as not running now.
    cron_job = aff4.FACTORY.Open(cron_job_urn, aff4_type="CronJob",
                                 token=self.token)
    self.assertFalse(cron_job.IsRunning())

  def testCronJobRunDoesNothingIfCurrentFlowIsRunning(self):
    cron_manager = cron.CronManager()
    cron_job_urn = cron_manager.ScheduleFlow("FakeCronJob", flow_args={},
                                             frequency=rdfvalue.Duration("1d"),
                                             token=self.token)

    cron_job = aff4.FACTORY.Open(cron_job_urn, aff4_type="CronJob",
                                 token=self.token)
    cron_manager.RunOnce(token=self.token)

    cron_job = aff4.FACTORY.Open(cron_job_urn, aff4_type="CronJob",
                                 token=self.token)
    cron_job_flows = list(cron_job.ListChildren())
    self.assertEqual(len(cron_job_flows), 1)

    cron_manager.RunOnce(token=self.token)

    cron_job = aff4.FACTORY.Open(cron_job_urn, aff4_type="CronJob",
                                 token=self.token)
    cron_job_flows = list(cron_job.ListChildren())
    self.assertEqual(len(cron_job_flows), 1)

  def testCronJobRunDoesNothingIfDueTimeHasNotComeYet(self):
    old_time = time.time
    try:
      time.time = lambda: 0

      cron_manager = cron.CronManager()
      cron_job_urn = cron_manager.ScheduleFlow(
          "FakeCronJob", flow_args={}, allow_overruns=False,
          frequency=rdfvalue.Duration("1h"), token=self.token)

      cron_manager.RunOnce(token=self.token)

      cron_job = aff4.FACTORY.Open(cron_job_urn, aff4_type="CronJob",
                                   token=self.token)
      cron_job_flows = list(cron_job.ListChildren())
      self.assertEqual(len(cron_job_flows), 1)

      # Let 59 minutes pass. Frequency is 1 hour, so new flow is not
      # supposed to start.
      time.time = lambda: 59 * 60

      cron_manager.RunOnce(token=self.token)

      cron_job = aff4.FACTORY.Open(cron_job_urn, aff4_type="CronJob",
                                   token=self.token)
      cron_job_flows = list(cron_job.ListChildren())
      self.assertEqual(len(cron_job_flows), 1)

    finally:
      time.time = old_time

  def testCronJobRunPreventsOverrunsWhenAllowOverrunsIsFalse(self):
    old_time = time.time
    try:
      time.time = lambda: 0

      cron_manager = cron.CronManager()
      cron_job_urn = cron_manager.ScheduleFlow(
          "FakeCronJob", flow_args={}, allow_overruns=False,
          frequency=rdfvalue.Duration("1h"), token=self.token)

      cron_manager.RunOnce(token=self.token)

      cron_job = aff4.FACTORY.Open(cron_job_urn, aff4_type="CronJob",
                                   token=self.token)
      cron_job_flows = list(cron_job.ListChildren())
      self.assertEqual(len(cron_job_flows), 1)

      # Let an hour pass. Frequency is 1h (i.e. cron job iterations are
      # supposed to be started every hour), so the new flow should be started
      # by RunOnce(). However, as allow_overruns is False, and previous
      # iteration flow hasn't finished yet, no flow will be started.
      time.time = lambda: 60*60 + 1

      cron_manager.RunOnce(token=self.token)

      cron_job = aff4.FACTORY.Open(cron_job_urn, aff4_type="CronJob",
                                   token=self.token)
      cron_job_flows = list(cron_job.ListChildren())
      self.assertEqual(len(cron_job_flows), 1)

    finally:
      time.time = old_time

  def testCronJobRunAllowsOverrunsWhenAllowOverrunsIsTrue(self):
    old_time = time.time
    try:
      time.time = lambda: 0

      cron_manager = cron.CronManager()
      cron_job_urn = cron_manager.ScheduleFlow(
          "FakeCronJob", flow_args={}, allow_overruns=True,
          frequency=rdfvalue.Duration("1h"), token=self.token)

      cron_manager.RunOnce(token=self.token)

      cron_job = aff4.FACTORY.Open(cron_job_urn, aff4_type="CronJob",
                                   token=self.token)
      cron_job_flows = list(cron_job.ListChildren())
      self.assertEqual(len(cron_job_flows), 1)

      # Let an hour pass. Frequency is 1h (i.e. cron job iterations are
      # supposed to be started every hour), so the new flow should be started
      # by RunOnce(). Previous iteration flow hasn't finished yet, but
      # allow_overruns is True, so it's ok to start new iteration.
      time.time = lambda: 60*60 + 1

      cron_manager.RunOnce(token=self.token)

      cron_job = aff4.FACTORY.Open(cron_job_urn, aff4_type="CronJob",
                                   token=self.token)
      cron_job_flows = list(cron_job.ListChildren())
      self.assertEqual(len(cron_job_flows), 2)

    finally:
      time.time = old_time

  def testCronManagerListJobsDoesNotListDeletedJobs(self):
    cron_manager = cron.CronManager()
    cron_job_urn = cron_manager.ScheduleFlow("FakeCronJob", flow_args={},
                                             frequency=rdfvalue.Duration("1d"),
                                             token=self.token)

    cron_jobs = list(cron_manager.ListJobs(token=self.token))
    self.assertEqual(len(cron_jobs), 1)

    cron_manager.DeleteJob(cron_job_urn, token=self.token)

    cron_jobs = list(cron_manager.ListJobs(token=self.token))
    self.assertEqual(len(cron_jobs), 0)


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
