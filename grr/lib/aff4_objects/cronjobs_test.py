#!/usr/bin/env python
import random
import time


import mock

from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import stats
from grr.lib import test_lib
from grr.lib.aff4_objects import cronjobs
from grr.lib.rdfvalues import grr_rdf
from grr.lib.rdfvalues import paths as rdf_paths


class FakeCronJob(flow.GRRFlow):
  """A Cron job which does nothing."""
  lifetime = rdfvalue.Duration("1d")

  @flow.StateHandler(next_state="End")
  def Start(self):
    self.CallState(next_state="End")


class FailingFakeCronJob(flow.GRRFlow):
  """A Cron job that only fails."""

  @flow.StateHandler(next_state="End")
  def Start(self):
    raise RuntimeError("Oh, no!")


class OccasionallyFailingFakeCronJob(flow.GRRFlow):
  """A Cron job that only fails."""

  @flow.StateHandler(next_state="End")
  def Start(self):
    if time.time() > 30:
      raise RuntimeError("Oh, no!")


class DummySystemCronJob(cronjobs.SystemCronFlow):
  """Dummy system cron job."""

  lifetime = rdfvalue.Duration("42h")
  frequency = rdfvalue.Duration("42d")

  @flow.StateHandler(next_state="End")
  def Start(self):
    self.CallState(next_state="End")


class DummySystemCronJobStartNow(DummySystemCronJob):
  start_time_randomization = False

  @flow.StateHandler(next_state="End")
  def Start(self):
    self.CallState(next_state="End")


class DummyStatefulSystemCronJob(cronjobs.StatefulSystemCronFlow):
  """Dummy stateful system cron job."""

  VALUES = []

  @flow.StateHandler()
  def Start(self):
    state = self.ReadCronState()
    value = state.get("value", default=0)

    DummyStatefulSystemCronJob.VALUES.append(value)

    state.Register("value", value + 1)
    self.WriteCronState(state)


class DummyDisabledSystemCronJob(DummySystemCronJob):
  """Disabled system cron job."""

  disabled = True


class CronTest(test_lib.AFF4ObjectTest):
  """Tests for cron functionality."""

  def testCronJobPreservesFlowNameAndArguments(self):
    """Testing initialization of a ConfigManager."""
    pathspec = rdf_paths.PathSpec(path="/foo",
                                  pathtype=rdf_paths.PathSpec.PathType.TSK)

    cron_manager = cronjobs.CronManager()

    cron_args = cronjobs.CreateCronJobFlowArgs(periodicity="1d",
                                               allow_overruns=False)

    cron_args.flow_runner_args.flow_name = "GetFile"
    cron_args.flow_args.pathspec = pathspec

    cron_job_urn = cron_manager.ScheduleFlow(cron_args=cron_args,
                                             token=self.token)

    # Check that CronJob definition is saved properly
    cron_root = aff4.FACTORY.Open(cron_manager.CRON_JOBS_PATH, token=self.token)
    cron_jobs = list(cron_root.ListChildren())
    self.assertEqual(len(cron_jobs), 1)
    self.assertEqual(cron_jobs[0], cron_job_urn)

    cron_job = aff4.FACTORY.Open(cron_jobs[0], token=self.token)
    cron_args = cron_job.Get(cron_job.Schema.CRON_ARGS)
    self.assertEqual(cron_args.flow_runner_args.flow_name, "GetFile")

    self.assertEqual(cron_args.flow_args.pathspec, pathspec)

    self.assertEqual(cron_args.periodicity, rdfvalue.Duration("1d"))
    self.assertEqual(cron_args.allow_overruns, False)

  def testCronJobStartsFlowAndCreatesSymlinkOnRun(self):
    cron_manager = cronjobs.CronManager()
    cron_args = cronjobs.CreateCronJobFlowArgs()
    cron_args.flow_runner_args.flow_name = "FakeCronJob"

    cron_job_urn = cron_manager.ScheduleFlow(cron_args=cron_args,
                                             token=self.token)

    cron_job = aff4.FACTORY.Open(cron_job_urn,
                                 aff4_type=cronjobs.CronJob,
                                 token=self.token)
    self.assertFalse(cron_job.IsRunning())
    # The job never ran, so DueToRun() should return true.
    self.assertTrue(cron_job.DueToRun())

    cron_manager.RunOnce(token=self.token)

    cron_job = aff4.FACTORY.Open(cron_job_urn,
                                 aff4_type=cronjobs.CronJob,
                                 token=self.token)
    self.assertTrue(cron_job.IsRunning())

    # Check that a link to the flow is created under job object.
    cron_job_flows = list(cron_job.ListChildren())
    self.assertEqual(len(cron_job_flows), 1)

    # Check that the link points to the correct flow.
    cron_job_flow = aff4.FACTORY.Open(cron_job_flows[0], token=self.token)
    self.assertEqual(cron_job_flow.state.context.args.flow_name, "FakeCronJob")

  def testDisabledCronJobDoesNotScheduleFlows(self):
    cron_manager = cronjobs.CronManager()
    cron_args = cronjobs.CreateCronJobFlowArgs()
    cron_args.flow_runner_args.flow_name = "FakeCronJob"

    cron_job_urn1 = cron_manager.ScheduleFlow(cron_args, token=self.token)
    cron_job_urn2 = cron_manager.ScheduleFlow(cron_args, token=self.token)

    cron_job1 = aff4.FACTORY.Open(cron_job_urn1,
                                  aff4_type=cronjobs.CronJob,
                                  mode="rw",
                                  token=self.token)
    cron_job1.Set(cron_job1.Schema.DISABLED(1))
    cron_job1.Close()

    cron_manager.RunOnce(token=self.token)

    cron_job1 = aff4.FACTORY.Open(cron_job_urn1,
                                  aff4_type=cronjobs.CronJob,
                                  token=self.token)
    cron_job2 = aff4.FACTORY.Open(cron_job_urn2,
                                  aff4_type=cronjobs.CronJob,
                                  token=self.token)

    # Disabled flow shouldn't be running, while not-disabled flow should run
    # as usual.
    self.assertFalse(cron_job1.IsRunning())
    self.assertTrue(cron_job2.IsRunning())

  def testCronJobRespectsStartTime(self):
    with test_lib.FakeTime(0):
      cron_manager = cronjobs.CronManager()
      start_time1 = rdfvalue.RDFDatetime(100 * 1000 * 1000)
      cron_args1 = cronjobs.CreateCronJobFlowArgs(start_time=start_time1)
      cron_args1.flow_runner_args.flow_name = "FakeCronJob"

      cron_args2 = cronjobs.CreateCronJobFlowArgs()
      cron_args2.flow_runner_args.flow_name = "FakeCronJob"

      cron_job_urn1 = cron_manager.ScheduleFlow(cron_args1, token=self.token)
      cron_job_urn2 = cron_manager.ScheduleFlow(cron_args2, token=self.token)

      cron_manager.RunOnce(token=self.token)

      cron_job1 = aff4.FACTORY.Open(cron_job_urn1,
                                    aff4_type=cronjobs.CronJob,
                                    token=self.token)
      cron_job2 = aff4.FACTORY.Open(cron_job_urn2,
                                    aff4_type=cronjobs.CronJob,
                                    token=self.token)

      self.assertEqual(
          cron_job1.Get(cron_job1.Schema.CRON_ARGS).start_time, start_time1)

      # Flow without a start time should now be running
      self.assertFalse(cron_job1.IsRunning())
      self.assertTrue(cron_job2.IsRunning())

    # Move the clock past the start time
    with test_lib.FakeTime(500):

      cron_manager.RunOnce(token=self.token)

      cron_job1 = aff4.FACTORY.Open(cron_job_urn1,
                                    aff4_type=cronjobs.CronJob,
                                    token=self.token)
      cron_job2 = aff4.FACTORY.Open(cron_job_urn2,
                                    aff4_type=cronjobs.CronJob,
                                    token=self.token)

      # Start time should be the same
      self.assertEqual(
          cron_job1.Get(cron_job1.Schema.CRON_ARGS).start_time, start_time1)

      # Now both should be running
      self.assertTrue(cron_job1.IsRunning())
      self.assertTrue(cron_job2.IsRunning())

      # Check setting a bad flow urn is handled and removed
      with aff4.FACTORY.OpenWithLock(cron_job_urn2,
                                     aff4_type=cronjobs.CronJob,
                                     token=self.token) as cron_job2:

        cron_job2.Set(cron_job2.Schema.CURRENT_FLOW_URN("aff4:/does/not/exist"))
        self.assertFalse(cron_job2.IsRunning())

      cron_job2 = aff4.FACTORY.Open(cron_job_urn2,
                                    aff4_type=cronjobs.CronJob,
                                    token=self.token)
      self.assertFalse(cron_job2.Get(cron_job2.Schema.CURRENT_FLOW_URN))

  def testGetStartTime(self):

    class TestSystemCron(cronjobs.SystemCronFlow):
      frequency = rdfvalue.Duration("10m")
      lifetime = rdfvalue.Duration("12h")

    class NoRandom(cronjobs.SystemCronFlow):
      frequency = rdfvalue.Duration("1d")
      lifetime = rdfvalue.Duration("12h")
      start_time_randomization = False

    with test_lib.FakeTime(100):
      now = rdfvalue.RDFDatetime().Now()

      with mock.patch.object(
          random,
          "randint",
          side_effect=[100 * 1000 * 1000, 123 * 1000 * 1000]):
        start1 = cronjobs.GetStartTime(TestSystemCron)
        start2 = cronjobs.GetStartTime(TestSystemCron)

      self.assertEqual(start1.AsSecondsFromEpoch(), 100)
      self.assertEqual(start2.AsSecondsFromEpoch(), 123)

      self.assertTrue(now <= start1 <= (now + TestSystemCron.frequency))
      self.assertTrue(now <= start2 <= (now + TestSystemCron.frequency))

      # Check disabling gives us a start time of now()
      now = rdfvalue.RDFDatetime().Now()
      start1 = cronjobs.GetStartTime(NoRandom)
      start2 = cronjobs.GetStartTime(NoRandom)

      self.assertEqual(start1.AsSecondsFromEpoch(), now.AsSecondsFromEpoch())
      self.assertEqual(start1.AsSecondsFromEpoch(), start2.AsSecondsFromEpoch())

  def testSystemCronJobSetsStartTime(self):
    with test_lib.FakeTime(100):
      now = rdfvalue.RDFDatetime().Now()
      cronjobs.ScheduleSystemCronFlows(
          names=[DummySystemCronJob.__name__,
                 DummySystemCronJobStartNow.__name__],
          token=self.token)
      random_time = "aff4:/cron/DummySystemCronJob"
      no_random_time = "aff4:/cron/DummySystemCronJobStartNow"

      random_time_job = aff4.FACTORY.Open(random_time,
                                          aff4_type=cronjobs.CronJob,
                                          token=self.token)

      no_random_time_job = aff4.FACTORY.Open(no_random_time,
                                             aff4_type=cronjobs.CronJob,
                                             token=self.token)

      start_time_now = no_random_time_job.Get(
          no_random_time_job.Schema.CRON_ARGS).start_time
      self.assertEqual(start_time_now, now)

      random_start_time = random_time_job.Get(
          random_time_job.Schema.CRON_ARGS).start_time
      self.assertTrue(now < random_start_time < (now +
                                                 DummySystemCronJob.frequency))

  def testCronJobRunMonitorsRunningFlowState(self):
    cron_manager = cronjobs.CronManager()
    cron_args = cronjobs.CreateCronJobFlowArgs(allow_overruns=False,
                                               periodicity="1d")
    cron_args.flow_runner_args.flow_name = "FakeCronJob"

    cron_job_urn = cron_manager.ScheduleFlow(cron_args, token=self.token)

    # Run() wasn't called, so nothing is supposed to be running
    cron_job = aff4.FACTORY.Open(cron_job_urn,
                                 aff4_type=cronjobs.CronJob,
                                 token=self.token)
    self.assertFalse(cron_job.IsRunning())

    cron_manager.RunOnce(token=self.token)

    # Run() was called and flow was started, so the job should be
    # considered running.
    cron_job = aff4.FACTORY.Open(cron_job_urn,
                                 aff4_type=cronjobs.CronJob,
                                 token=self.token)
    self.assertTrue(cron_job.IsRunning())

    # Find the flow that is currently running for the job and terminate it.
    cron_job = aff4.FACTORY.Open(cron_job_urn,
                                 aff4_type=cronjobs.CronJob,
                                 token=self.token)
    self.assertTrue(cron_job.IsRunning())
    cron_job_flow_urn = cron_job.Get(cron_job.Schema.CURRENT_FLOW_URN)
    self.assertTrue(cron_job_flow_urn is not None)
    flow.GRRFlow.TerminateFlow(cron_job_flow_urn, token=self.token)

    # Check we're dead
    cron_job = aff4.FACTORY.Open(cron_job_urn,
                                 aff4_type=cronjobs.CronJob,
                                 token=self.token)
    self.assertFalse(cron_job.IsRunning())

    # This will understand that current flow has terminated. New flow won't be
    # started, because iterations are supposed to be started once per day
    # (frequency=1d).
    cron_manager.RunOnce(token=self.token)

    # Still dead
    cron_job = aff4.FACTORY.Open(cron_job_urn,
                                 aff4_type=cronjobs.CronJob,
                                 token=self.token)
    self.assertFalse(cron_job.IsRunning())

  def testCronJobRunDoesNothingIfCurrentFlowIsRunning(self):
    cron_manager = cronjobs.CronManager()
    cron_args = cronjobs.CreateCronJobFlowArgs(allow_overruns=False,
                                               periodicity="1d")
    cron_args.flow_runner_args.flow_name = "FakeCronJob"

    cron_job_urn = cron_manager.ScheduleFlow(cron_args=cron_args,
                                             token=self.token)

    cron_job = aff4.FACTORY.Open(cron_job_urn,
                                 aff4_type=cronjobs.CronJob,
                                 token=self.token)
    cron_manager.RunOnce(token=self.token)

    cron_job = aff4.FACTORY.Open(cron_job_urn,
                                 aff4_type=cronjobs.CronJob,
                                 token=self.token)
    cron_job_flows = list(cron_job.ListChildren())
    self.assertEqual(len(cron_job_flows), 1)

    cron_manager.RunOnce(token=self.token)

    cron_job = aff4.FACTORY.Open(cron_job_urn,
                                 aff4_type=cronjobs.CronJob,
                                 token=self.token)
    cron_job_flows = list(cron_job.ListChildren())
    self.assertEqual(len(cron_job_flows), 1)

  def testCronJobRunDoesNothingIfDueTimeHasNotComeYet(self):
    with test_lib.FakeTime(0):
      cron_manager = cronjobs.CronManager()
      cron_args = cronjobs.CreateCronJobFlowArgs(allow_overruns=False,
                                                 periodicity="1h")

      cron_args.flow_runner_args.flow_name = "FakeCronJob"

      cron_job_urn = cron_manager.ScheduleFlow(cron_args=cron_args,
                                               token=self.token)

      cron_manager.RunOnce(token=self.token)

      cron_job = aff4.FACTORY.Open(cron_job_urn,
                                   aff4_type=cronjobs.CronJob,
                                   token=self.token)
      cron_job_flows = list(cron_job.ListChildren())
      self.assertEqual(len(cron_job_flows), 1)

      # Let 59 minutes pass. Frequency is 1 hour, so new flow is not
      # supposed to start.
      time.time = lambda: 59 * 60

      cron_manager.RunOnce(token=self.token)

      cron_job = aff4.FACTORY.Open(cron_job_urn,
                                   aff4_type=cronjobs.CronJob,
                                   token=self.token)
      cron_job_flows = list(cron_job.ListChildren())
      self.assertEqual(len(cron_job_flows), 1)

  def testCronJobRunPreventsOverrunsWhenAllowOverrunsIsFalse(self):
    with test_lib.FakeTime(0):
      cron_manager = cronjobs.CronManager()
      cron_args = cronjobs.CreateCronJobFlowArgs(allow_overruns=False,
                                                 periodicity="1h")

      cron_args.flow_runner_args.flow_name = "FakeCronJob"

      cron_job_urn = cron_manager.ScheduleFlow(cron_args=cron_args,
                                               token=self.token)

      cron_manager.RunOnce(token=self.token)

      cron_job = aff4.FACTORY.Open(cron_job_urn,
                                   aff4_type=cronjobs.CronJob,
                                   token=self.token)
      cron_job_flows = list(cron_job.ListChildren())
      self.assertEqual(len(cron_job_flows), 1)

      # Let an hour pass. Frequency is 1h (i.e. cron job iterations are
      # supposed to be started every hour), so the new flow should be started
      # by RunOnce(). However, as allow_overruns is False, and previous
      # iteration flow hasn't finished yet, no flow will be started.
      time.time = lambda: 60 * 60 + 1

      cron_manager.RunOnce(token=self.token)

      cron_job = aff4.FACTORY.Open(cron_job_urn,
                                   aff4_type=cronjobs.CronJob,
                                   token=self.token)
      cron_job_flows = list(cron_job.ListChildren())
      self.assertEqual(len(cron_job_flows), 1)

  def testCronJobRunAllowsOverrunsWhenAllowOverrunsIsTrue(self):
    with test_lib.FakeTime(0):
      cron_manager = cronjobs.CronManager()
      cron_args = cronjobs.CreateCronJobFlowArgs(allow_overruns=True,
                                                 periodicity="1h")

      cron_args.flow_runner_args.flow_name = "FakeCronJob"

      cron_job_urn = cron_manager.ScheduleFlow(cron_args=cron_args,
                                               token=self.token)

      cron_manager.RunOnce(token=self.token)

      cron_job = aff4.FACTORY.Open(cron_job_urn,
                                   aff4_type=cronjobs.CronJob,
                                   token=self.token)
      cron_job_flows = list(cron_job.ListChildren())
      self.assertEqual(len(cron_job_flows), 1)

      # Let an hour pass. Frequency is 1h (i.e. cron job iterations are
      # supposed to be started every hour), so the new flow should be started
      # by RunOnce(). Previous iteration flow hasn't finished yet, but
      # allow_overruns is True, so it's ok to start new iteration.
      time.time = lambda: 60 * 60 + 1

      cron_manager.RunOnce(token=self.token)

      cron_job = aff4.FACTORY.Open(cron_job_urn,
                                   aff4_type=cronjobs.CronJob,
                                   token=self.token)
      cron_job_flows = list(cron_job.ListChildren())
      self.assertEqual(len(cron_job_flows), 2)

  def testCronManagerListJobsDoesNotListDeletedJobs(self):
    cron_manager = cronjobs.CronManager()

    cron_args = cronjobs.CreateCronJobFlowArgs(allow_overruns=True,
                                               periodicity="1d")

    cron_args.flow_runner_args.flow_name = "FakeCronJob"

    cron_job_urn = cron_manager.ScheduleFlow(cron_args=cron_args,
                                             token=self.token)

    cron_jobs = list(cron_manager.ListJobs(token=self.token))
    self.assertEqual(len(cron_jobs), 1)

    cron_manager.DeleteJob(cron_job_urn, token=self.token)

    cron_jobs = list(cron_manager.ListJobs(token=self.token))
    self.assertEqual(len(cron_jobs), 0)

  def testKillOldFlows(self):
    with test_lib.FakeTime(0):
      cron_manager = cronjobs.CronManager()
      cron_args = cronjobs.CreateCronJobFlowArgs()
      cron_args.flow_runner_args.flow_name = "FakeCronJob"
      cron_args.periodicity = "1w"
      cron_args.lifetime = FakeCronJob.lifetime

      cron_job_urn = cron_manager.ScheduleFlow(cron_args=cron_args,
                                               token=self.token)

      cron_manager.RunOnce(token=self.token)

      cron_job = aff4.FACTORY.Open(cron_job_urn,
                                   aff4_type=cronjobs.CronJob,
                                   token=self.token)
      self.assertTrue(cron_job.IsRunning())
      self.assertFalse(cron_job.KillOldFlows())

    prev_timeout_value = stats.STATS.GetMetricValue(
        "cron_job_timeout", fields=[cron_job_urn.Basename()])
    prev_latency_value = stats.STATS.GetMetricValue(
        "cron_job_latency", fields=[cron_job_urn.Basename()])

    # Fast foward one day
    with test_lib.FakeTime(24 * 60 * 60 + 1):
      flow_urn = cron_job.Get(cron_job.Schema.CURRENT_FLOW_URN)

      cron_manager.RunOnce(token=self.token)
      cron_job = aff4.FACTORY.Open(cron_job_urn,
                                   aff4_type=cronjobs.CronJob,
                                   token=self.token)
      self.assertFalse(cron_job.IsRunning())

      # Check the termination log
      log_collection = aff4.FACTORY.Open(urn=flow_urn.Add("Logs"),
                                         token=self.token,
                                         mode="r")

      for line in log_collection:
        if line.urn == flow_urn:
          self.assertTrue("lifetime exceeded" in str(line.log_message))

      # Check that timeout counter got updated.
      current_timeout_value = stats.STATS.GetMetricValue(
          "cron_job_timeout",
          fields=[cron_job_urn.Basename()])
      self.assertEqual(current_timeout_value - prev_timeout_value, 1)

      # Check that latency stat got updated.
      current_latency_value = stats.STATS.GetMetricValue(
          "cron_job_latency",
          fields=[cron_job_urn.Basename()])
      self.assertEqual(current_latency_value.count - prev_latency_value.count,
                       1)
      self.assertEqual(current_latency_value.sum - prev_latency_value.sum,
                       24 * 60 * 60 + 1)

  def testFailedFlowUpdatesStats(self):
    cron_manager = cronjobs.CronManager()
    cron_args = cronjobs.CreateCronJobFlowArgs(allow_overruns=False,
                                               periodicity="1d")
    cron_args.flow_runner_args.flow_name = "FailingFakeCronJob"

    cron_job_urn = cron_manager.ScheduleFlow(cron_args=cron_args,
                                             token=self.token)

    prev_metric_value = stats.STATS.GetMetricValue(
        "cron_job_failure", fields=[cron_job_urn.Basename()])

    cron_manager.RunOnce(token=self.token)
    cron_job = aff4.FACTORY.Open(cron_job_urn, token=self.token)
    cron_flow_urn = cron_job.Get(cron_job.Schema.CURRENT_FLOW_URN)
    for _ in test_lib.TestFlowHelper(cron_flow_urn,
                                     check_flow_errors=False,
                                     token=self.token):
      pass
    # This RunOnce call should determine that the flow has failed
    cron_manager.RunOnce(token=self.token)

    # Check that stats got updated
    current_metric_value = stats.STATS.GetMetricValue(
        "cron_job_failure", fields=[cron_job_urn.Basename()])
    self.assertEqual(current_metric_value - prev_metric_value, 1)

  def testLatencyStatsAreCorrectlyRecorded(self):
    with test_lib.FakeTime(0):
      cron_manager = cronjobs.CronManager()
      cron_args = cronjobs.CreateCronJobFlowArgs()
      cron_args.flow_runner_args.flow_name = "FakeCronJob"
      cron_args.periodicity = "1w"

      cron_job_urn = cron_manager.ScheduleFlow(cron_args=cron_args,
                                               token=self.token)

      cron_manager.RunOnce(token=self.token)

    prev_metric_value = stats.STATS.GetMetricValue(
        "cron_job_latency", fields=[cron_job_urn.Basename()])

    # Fast foward one minute
    with test_lib.FakeTime(60):
      cron_manager.RunOnce(token=self.token)
      cron_job = aff4.FACTORY.Open(cron_job_urn,
                                   aff4_type=cronjobs.CronJob,
                                   token=self.token)
      cron_flow_urn = cron_job.Get(cron_job.Schema.CURRENT_FLOW_URN)
      for _ in test_lib.TestFlowHelper(cron_flow_urn,
                                       check_flow_errors=False,
                                       token=self.token):
        pass

      # This RunOnce call should determine that the flow has finished
      cron_manager.RunOnce(token=self.token)

    # Check that stats got updated
    current_metric_value = stats.STATS.GetMetricValue(
        "cron_job_latency", fields=[cron_job_urn.Basename()])
    self.assertEqual(current_metric_value.count - prev_metric_value.count, 1)
    self.assertEqual(current_metric_value.sum - prev_metric_value.sum, 60)

  def testSchedulingJobWithFixedNamePreservesTheName(self):
    cron_manager = cronjobs.CronManager()
    cron_args = cronjobs.CreateCronJobFlowArgs(allow_overruns=True,
                                               periodicity="1d")

    cron_args.flow_runner_args.flow_name = "FakeCronJob"

    cron_job_urn = cron_manager.ScheduleFlow(cron_args=cron_args,
                                             token=self.token,
                                             job_name="TheJob")
    self.assertEqual("TheJob", cron_job_urn.Basename())

  def testReschedulingJobWithFixedNameDoesNotCreateNewObjectVersion(self):
    cron_manager = cronjobs.CronManager()

    cron_args = cronjobs.CreateCronJobFlowArgs(allow_overruns=True,
                                               periodicity="1d")
    cron_args.flow_runner_args.flow_name = "FakeCronJob"

    # Schedule cron job with a fixed name. Check that we have 1 version
    # of "TYPE" attribute.
    cron_job_urn = cron_manager.ScheduleFlow(cron_args=cron_args,
                                             token=self.token,
                                             job_name="TheJob")
    cron_job = aff4.FACTORY.Open(cron_job_urn,
                                 age=aff4.ALL_TIMES,
                                 token=self.token)
    attr_values = list(cron_job.GetValuesForAttribute(cron_job.Schema.TYPE))
    self.assertTrue(len(attr_values) == 1)

    # Reschedule the job. Check that we still have only one "TYPE" version.
    cron_job_urn = cron_manager.ScheduleFlow(cron_args=cron_args,
                                             token=self.token,
                                             job_name="TheJob")
    cron_job = aff4.FACTORY.Open(cron_job_urn,
                                 age=aff4.ALL_TIMES,
                                 token=self.token)
    attr_values = list(cron_job.GetValuesForAttribute(cron_job.Schema.TYPE))
    self.assertTrue(len(attr_values) == 1)

  def testLastRunStatusGetsUpdatedOnEveryRun(self):
    cron_manager = cronjobs.CronManager()
    cron_args = cronjobs.CreateCronJobFlowArgs()
    cron_args.flow_runner_args.flow_name = "OccasionallyFailingFakeCronJob"
    cron_args.periodicity = "30s"

    cron_job_urn = cron_manager.ScheduleFlow(cron_args=cron_args,
                                             token=self.token)

    for fake_time in [0, 60]:
      with test_lib.FakeTime(fake_time):
        # This call should start a new cron job flow
        cron_manager.RunOnce(token=self.token)
        cron_job = aff4.FACTORY.Open(cron_job_urn,
                                     aff4_type=cronjobs.CronJob,
                                     token=self.token)
        cron_flow_urn = cron_job.Get(cron_job.Schema.CURRENT_FLOW_URN)
        for _ in test_lib.TestFlowHelper(cron_flow_urn,
                                         check_flow_errors=False,
                                         token=self.token):
          pass
        # This RunOnce call should determine that the flow has finished
        cron_manager.RunOnce(token=self.token)

    cron_job = aff4.FACTORY.Open(cron_job_urn,
                                 age=aff4.ALL_TIMES,
                                 token=self.token)
    statuses = list(cron_job.GetValuesForAttribute(
        cron_job.Schema.LAST_RUN_STATUS))

    statuses = sorted(statuses, key=lambda x: x.age)
    self.assertEqual(len(statuses), 2)

    self.assertEqual(statuses[0].age,
                     rdfvalue.RDFDatetime().FromSecondsFromEpoch(0))
    self.assertEqual(statuses[1].age,
                     rdfvalue.RDFDatetime().FromSecondsFromEpoch(60))
    self.assertEqual(statuses[0].status, grr_rdf.CronJobRunStatus.Status.OK)
    self.assertEqual(statuses[1].status, grr_rdf.CronJobRunStatus.Status.ERROR)

  def testSystemCronFlowsGetScheduledAutomatically(self):
    cronjobs.ScheduleSystemCronFlows(names=[DummySystemCronJob.__name__],
                                     token=self.token)

    jobs = cronjobs.CRON_MANAGER.ListJobs(token=self.token)
    dummy_jobs = [j for j in jobs if j.Basename() == "DummySystemCronJob"]
    self.assertTrue(dummy_jobs)

    # System cron job should be enabled by default.
    job = aff4.FACTORY.Open(dummy_jobs[0],
                            aff4_type=cronjobs.CronJob,
                            token=self.token)
    self.assertFalse(job.Get(job.Schema.DISABLED))

  def testSystemCronFlowsWithDisabledAttributeDoNotGetScheduled(self):
    cronjobs.ScheduleSystemCronFlows(
        names=[DummyDisabledSystemCronJob.__name__],
        token=self.token)

    jobs = cronjobs.CRON_MANAGER.ListJobs(token=self.token)
    dummy_jobs = [j for j in jobs
                  if j.Basename() == "DummyDisabledSystemCronJob"]
    self.assertTrue(dummy_jobs)

    # System cron job should be enabled by default.
    job = aff4.FACTORY.Open(dummy_jobs[0],
                            aff4_type=cronjobs.CronJob,
                            token=self.token)
    self.assertTrue(job.Get(job.Schema.DISABLED))

  def testSystemCronFlowsMayBeDisabledViaConfig(self):
    with test_lib.ConfigOverrider({
        "Cron.disabled_system_jobs": ["DummySystemCronJob"]
    }):
      cronjobs.ScheduleSystemCronFlows(token=self.token)

      jobs = cronjobs.CRON_MANAGER.ListJobs(token=self.token)
      dummy_jobs = [j for j in jobs if j.Basename() == "DummySystemCronJob"]
      self.assertTrue(dummy_jobs)

      # This cron job should be disabled, because it's listed in
      # Cron.disabled_system_jobs config variable.
      job = aff4.FACTORY.Open(dummy_jobs[0],
                              aff4_type=cronjobs.CronJob,
                              token=self.token)
      self.assertTrue(job.Get(job.Schema.DISABLED))

    # Now remove the cron job from the list and check that it gets disabled
    # after next ScheduleSystemCronFlows() call.
    with test_lib.ConfigOverrider({"Cron.disabled_system_jobs": []}):

      cronjobs.ScheduleSystemCronFlows(token=self.token)

      # System cron job should be enabled.
      job = aff4.FACTORY.Open(dummy_jobs[0],
                              aff4_type=cronjobs.CronJob,
                              token=self.token)
      self.assertFalse(job.Get(job.Schema.DISABLED))

  def testScheduleSystemCronFlowsRaisesWhenFlowCanNotBeFound(self):
    with test_lib.ConfigOverrider({
        "Cron.disabled_system_jobs": ["NonExistent"]
    }):
      self.assertRaises(KeyError,
                        cronjobs.ScheduleSystemCronFlows,
                        token=self.token)

  def testStatefulSystemCronFlowRaisesWhenRunningWithoutCronJob(self):
    self.assertRaises(cronjobs.StateReadError,
                      flow.GRRFlow.StartFlow,
                      flow_name="DummyStatefulSystemCronJob",
                      token=self.token)

  def testStatefulSystemCronFlowMaintainsState(self):
    DummyStatefulSystemCronJob.VALUES = []

    # We need to have a cron job started to have a place to maintain
    # state.
    cronjobs.ScheduleSystemCronFlows(
        names=[DummyStatefulSystemCronJob.__name__],
        token=self.token)

    flow.GRRFlow.StartFlow(flow_name="DummyStatefulSystemCronJob",
                           token=self.token)
    flow.GRRFlow.StartFlow(flow_name="DummyStatefulSystemCronJob",
                           token=self.token)
    flow.GRRFlow.StartFlow(flow_name="DummyStatefulSystemCronJob",
                           token=self.token)

    self.assertListEqual(DummyStatefulSystemCronJob.VALUES, [0, 1, 2])


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
