#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import time

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.stats import stats_collector_instance
from grr_response_server import flow
from grr_response_server.aff4_objects import cronjobs as aff4_cronjobs
from grr_response_server.flows.general import transfer
from grr_response_server.hunts import standard
from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs
from grr.test_lib import aff4_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class FakeCronJob(flow.GRRFlow):
  """A Cron job which does nothing."""
  lifetime = rdfvalue.Duration("1d")

  def Start(self):
    self.CallState(next_state="End")


class FailingFakeCronJob(aff4_cronjobs.SystemCronFlow):
  """A Cron job that only fails."""

  def Start(self):
    raise RuntimeError("Oh, no!")


class OccasionallyFailingFakeCronJob(aff4_cronjobs.SystemCronFlow):
  """A Cron job that only fails."""

  frequency = rdfvalue.Duration("30s")

  def Start(self):
    if time.time() > 30:
      raise RuntimeError("Oh, no!")


class DummySystemCronJob(aff4_cronjobs.SystemCronFlow):
  """Dummy system cron job."""

  lifetime = rdfvalue.Duration("42h")
  frequency = rdfvalue.Duration("42d")

  def Start(self):
    self.CallState(next_state="End")


class DummyStatefulSystemCronJob(aff4_cronjobs.StatefulSystemCronFlow):
  """Dummy stateful system cron job."""

  VALUES = []

  def Start(self):
    state = self.ReadCronState()
    value = state.get("value", 0)

    DummyStatefulSystemCronJob.VALUES.append(value)

    state["value"] = value + 1
    self.WriteCronState(state)


class DummyDisabledSystemCronJob(DummySystemCronJob):
  """Disabled system cron job."""

  enabled = False


class TestSystemCron(aff4_cronjobs.SystemCronFlow):
  frequency = rdfvalue.Duration("10m")
  lifetime = rdfvalue.Duration("12h")


class CronTest(aff4_test_lib.AFF4ObjectTest):
  """Tests for cron functionality."""

  def testCronJobPreservesFlowNameAndArguments(self):
    """Testing initialization of a ConfigManager."""
    pathspec = rdf_paths.PathSpec(
        path="/foo", pathtype=rdf_paths.PathSpec.PathType.TSK)

    cron_manager = aff4_cronjobs.GetCronManager()

    cron_args = rdf_cronjobs.CreateCronJobArgs(
        frequency="1d",
        allow_overruns=False,
        flow_name=transfer.GetFile.__name__)
    cron_args.flow_args.pathspec = pathspec

    job_id = cron_manager.CreateJob(cron_args=cron_args, token=self.token)

    # Check that CronJob definition is saved properly
    jobs = cron_manager.ListJobs(token=self.token)
    self.assertLen(jobs, 1)
    self.assertEqual(jobs[0], job_id)

    cron_job = cron_manager.ReadJob(job_id, token=self.token)
    cron_args = cron_job.Get(cron_job.Schema.CRON_ARGS)
    # CreateJob creates a cronjob that runs the CreateAndRunGenericHuntFlow
    # which in turn starts a hunt with the flow that we passed in.
    self.assertEqual(cron_args.flow_runner_args.flow_name,
                     standard.CreateAndRunGenericHuntFlow.__name__)
    self.assertEqual(cron_args.flow_args.hunt_args.flow_runner_args.flow_name,
                     transfer.GetFile.__name__)

    self.assertEqual(cron_args.flow_args.hunt_args.flow_args.pathspec, pathspec)

    self.assertEqual(cron_args.periodicity, rdfvalue.Duration("1d"))
    self.assertEqual(cron_args.allow_overruns, False)

  def testCronJobStartsFlowAndCreatesSymlinkOnRun(self):
    cron_manager = aff4_cronjobs.GetCronManager()
    cron_args = rdf_cronjobs.CreateCronJobArgs(flow_name="FakeCronJob")

    job_id = cron_manager.CreateJob(cron_args=cron_args, token=self.token)

    cron_job = cron_manager.ReadJob(job_id, token=self.token)
    self.assertFalse(cron_job.IsRunning())
    # The job never ran, so DueToRun() should return true.
    self.assertTrue(cron_job.DueToRun())

    cron_manager.RunOnce(token=self.token)

    cron_job = cron_manager.ReadJob(job_id, token=self.token)
    self.assertTrue(cron_job.IsRunning())

    # Check that a link to the flow is created under job object.
    runs = cron_manager.ReadJobRuns(job_id, token=self.token)
    self.assertLen(runs, 1)
    # Check that the link points to the correct flow.
    self.assertEqual(runs[0].args.hunt_args.flow_runner_args.flow_name,
                     "FakeCronJob")

  def testDisabledCronJobDoesNotCreateJobs(self):
    cron_manager = aff4_cronjobs.GetCronManager()
    cron_args = rdf_cronjobs.CreateCronJobArgs(flow_name="FakeCronJob")

    job_id1 = cron_manager.CreateJob(cron_args, token=self.token)
    job_id2 = cron_manager.CreateJob(cron_args, token=self.token)

    cron_manager.DisableJob(job_id1, token=self.token)

    cron_manager.RunOnce(token=self.token)

    cron_job1 = cron_manager.ReadJob(job_id1, token=self.token)
    cron_job2 = cron_manager.ReadJob(job_id2, token=self.token)

    # Disabled flow shouldn't be running, while not-disabled flow should run
    # as usual.
    self.assertFalse(cron_job1.IsRunning())
    self.assertTrue(cron_job2.IsRunning())

  def testCronJobRunMonitorsRunningFlowState(self):
    cron_manager = aff4_cronjobs.GetCronManager()
    cron_args = rdf_cronjobs.CreateCronJobArgs(
        allow_overruns=False, frequency="1d", flow_name="FakeCronJob")

    job_id = cron_manager.CreateJob(cron_args, token=self.token)

    # Run() wasn't called, so nothing is supposed to be running
    cron_job = cron_manager.ReadJob(job_id, token=self.token)
    self.assertFalse(cron_job.IsRunning())

    cron_manager.RunOnce(token=self.token)

    # Run() was called and flow was started, so the job should be
    # considered running.
    cron_job = cron_manager.ReadJob(job_id, token=self.token)
    self.assertTrue(cron_job.IsRunning())

    # Find the flow that is currently running for the job and terminate it.
    cron_job = cron_manager.ReadJob(job_id, token=self.token)
    self.assertTrue(cron_job.IsRunning())
    cron_job_flow_urn = cron_job.Get(cron_job.Schema.CURRENT_FLOW_URN)
    self.assertTrue(cron_job_flow_urn is not None)
    flow.GRRFlow.TerminateAFF4Flow(cron_job_flow_urn, token=self.token)

    # Check we're dead
    cron_job = cron_manager.ReadJob(job_id, token=self.token)
    self.assertFalse(cron_job.IsRunning())

    # This will understand that current flow has terminated. New flow won't be
    # started, because iterations are supposed to be started once per day
    # (frequency=1d).
    cron_manager.RunOnce(token=self.token)

    # Still dead
    cron_job = cron_manager.ReadJob(job_id, token=self.token)
    self.assertFalse(cron_job.IsRunning())

  def testCronJobRunDoesNothingIfCurrentFlowIsRunning(self):
    cron_manager = aff4_cronjobs.GetCronManager()
    cron_args = rdf_cronjobs.CreateCronJobArgs(
        allow_overruns=False, frequency="1d", flow_name="FakeCronJob")

    job_id = cron_manager.CreateJob(cron_args=cron_args, token=self.token)

    cron_manager.RunOnce(token=self.token)

    cron_job_runs = cron_manager.ReadJobRuns(job_id, token=self.token)
    self.assertLen(cron_job_runs, 1)

    cron_manager.RunOnce(token=self.token)

    cron_job_runs = cron_manager.ReadJobRuns(job_id, token=self.token)
    self.assertLen(cron_job_runs, 1)

  def testCronJobRunDoesNothingIfDueTimeHasNotComeYet(self):
    with test_lib.FakeTime(0):
      cron_manager = aff4_cronjobs.GetCronManager()
      cron_args = rdf_cronjobs.CreateCronJobArgs(
          allow_overruns=False, frequency="1h", flow_name="FakeCronJob")

      job_id = cron_manager.CreateJob(cron_args=cron_args, token=self.token)

      cron_manager.RunOnce(token=self.token)

      cron_job_runs = cron_manager.ReadJobRuns(job_id, token=self.token)
      self.assertLen(cron_job_runs, 1)

      # Let 59 minutes pass. Frequency is 1 hour, so new flow is not
      # supposed to start.
      time.time = lambda: 59 * 60

      cron_manager.RunOnce(token=self.token)

      cron_job_runs = cron_manager.ReadJobRuns(job_id, token=self.token)
      self.assertLen(cron_job_runs, 1)

  def testCronJobRunPreventsOverrunsWhenAllowOverrunsIsFalse(self):
    with test_lib.FakeTime(0):
      cron_manager = aff4_cronjobs.GetCronManager()
      cron_args = rdf_cronjobs.CreateCronJobArgs(
          allow_overruns=False, frequency="1h", flow_name="FakeCronJob")

      job_id = cron_manager.CreateJob(cron_args=cron_args, token=self.token)

      cron_manager.RunOnce(token=self.token)

      cron_job_runs = cron_manager.ReadJobRuns(job_id, token=self.token)
      self.assertLen(cron_job_runs, 1)

      # Let an hour pass. Frequency is 1h (i.e. cron job iterations are
      # supposed to be started every hour), so the new flow should be started
      # by RunOnce(). However, as allow_overruns is False, and previous
      # iteration flow hasn't finished yet, no flow will be started.
      time.time = lambda: 60 * 60 + 1

      cron_manager.RunOnce(token=self.token)

      cron_job_runs = cron_manager.ReadJobRuns(job_id, token=self.token)
      self.assertLen(cron_job_runs, 1)

  def testCronJobRunAllowsOverrunsWhenAllowOverrunsIsTrue(self):
    with test_lib.FakeTime(0):
      cron_manager = aff4_cronjobs.GetCronManager()
      cron_args = rdf_cronjobs.CreateCronJobArgs(
          allow_overruns=True, frequency="1h", flow_name="FakeCronJob")

      job_id = cron_manager.CreateJob(cron_args=cron_args, token=self.token)

      cron_manager.RunOnce(token=self.token)

      cron_job_runs = cron_manager.ReadJobRuns(job_id, token=self.token)
      self.assertLen(cron_job_runs, 1)

      # Let an hour pass. Frequency is 1h (i.e. cron job iterations are
      # supposed to be started every hour), so the new flow should be started
      # by RunOnce(). Previous iteration flow hasn't finished yet, but
      # allow_overruns is True, so it's ok to start new iteration.
      time.time = lambda: 60 * 60 + 1

      cron_manager.RunOnce(token=self.token)

      cron_job_runs = cron_manager.ReadJobRuns(job_id, token=self.token)
      self.assertLen(cron_job_runs, 2)

  def testCronManagerListJobsDoesNotListDeletedJobs(self):
    cron_manager = aff4_cronjobs.GetCronManager()

    cron_args = rdf_cronjobs.CreateCronJobArgs(
        allow_overruns=True, frequency="1d", flow_name="FakeCronJob")

    cron_job_urn = cron_manager.CreateJob(cron_args=cron_args, token=self.token)

    cron_jobs = list(cron_manager.ListJobs(token=self.token))
    self.assertLen(cron_jobs, 1)

    cron_manager.DeleteJob(cron_job_urn, token=self.token)

    cron_jobs = list(cron_manager.ListJobs(token=self.token))
    self.assertEmpty(cron_jobs)

  def testKillOldFlows(self):
    with test_lib.FakeTime(0):
      cron_manager = aff4_cronjobs.GetCronManager()
      cron_args = rdf_cronjobs.CreateCronJobArgs(
          flow_name="FakeCronJob",
          frequency="1w",
          lifetime=FakeCronJob.lifetime)
      job_id = cron_manager.CreateJob(cron_args=cron_args, token=self.token)

      cron_manager.RunOnce(token=self.token)

      cron_job = cron_manager.ReadJob(job_id, token=self.token)
      self.assertTrue(cron_job.IsRunning())
      self.assertFalse(cron_job.KillOldFlows())

    prev_timeout_value = stats_collector_instance.Get().GetMetricValue(
        "cron_job_timeout", fields=[job_id])
    prev_latency_value = stats_collector_instance.Get().GetMetricValue(
        "cron_job_latency", fields=[job_id])

    # Fast forward one day
    with test_lib.FakeTime(24 * 60 * 60 + 1):
      flow_urn = cron_job.Get(cron_job.Schema.CURRENT_FLOW_URN)

      cron_manager.RunOnce(token=self.token)
      cron_job = cron_manager.ReadJob(job_id, token=self.token)
      self.assertFalse(cron_job.IsRunning())

      # Check the termination log
      log_collection = flow.GRRFlow.LogCollectionForFID(flow_urn)

      for line in log_collection:
        if line.urn == flow_urn:
          self.assertIn("lifetime exceeded", str(line.log_message))

      # Check that timeout counter got updated.
      current_timeout_value = stats_collector_instance.Get().GetMetricValue(
          "cron_job_timeout", fields=[job_id])
      self.assertEqual(current_timeout_value - prev_timeout_value, 1)

      # Check that latency stat got updated.
      current_latency_value = stats_collector_instance.Get().GetMetricValue(
          "cron_job_latency", fields=[job_id])
      self.assertEqual(current_latency_value.count - prev_latency_value.count,
                       1)
      self.assertEqual(current_latency_value.sum - prev_latency_value.sum,
                       24 * 60 * 60 + 1)

  def testFailedFlowUpdatesStats(self):
    job_id = "FailingFakeCronJob"
    aff4_cronjobs.ScheduleSystemCronFlows(names=[job_id], token=self.token)

    prev_metric_value = stats_collector_instance.Get().GetMetricValue(
        "cron_job_failure", fields=[job_id])

    cron_manager = aff4_cronjobs.GetCronManager()
    cron_manager.RunOnce(token=self.token)
    cron_job = cron_manager.ReadJob(job_id, token=self.token)
    cron_flow_urn = cron_job.Get(cron_job.Schema.CURRENT_FLOW_URN)
    flow_test_lib.TestFlowHelper(
        cron_flow_urn, check_flow_errors=False, token=self.token)
    # This RunOnce call should determine that the flow has failed
    cron_manager.RunOnce(token=self.token)

    # Check that stats got updated
    current_metric_value = stats_collector_instance.Get().GetMetricValue(
        "cron_job_failure", fields=[job_id])
    self.assertEqual(current_metric_value - prev_metric_value, 1)

  def testLatencyStatsAreCorrectlyRecorded(self):
    with test_lib.FakeTime(0):
      cron_manager = aff4_cronjobs.GetCronManager()
      cron_args = rdf_cronjobs.CreateCronJobArgs(
          flow_name="FakeCronJob", frequency="1w")

      cron_job_id = cron_manager.CreateJob(
          cron_args=cron_args, token=self.token)

      cron_manager.RunOnce(token=self.token)

    prev_metric_value = stats_collector_instance.Get().GetMetricValue(
        "cron_job_latency", fields=[cron_job_id])

    # Fast forward one minute
    with test_lib.FakeTime(60):
      cron_manager.RunOnce(token=self.token)
      cron_job = cron_manager.ReadJob(cron_job_id, token=self.token)
      cron_flow_urn = cron_job.Get(cron_job.Schema.CURRENT_FLOW_URN)
      flow_test_lib.TestFlowHelper(
          cron_flow_urn, check_flow_errors=False, token=self.token)

      # This RunOnce call should determine that the flow has finished
      cron_manager.RunOnce(token=self.token)

    # Check that stats got updated
    current_metric_value = stats_collector_instance.Get().GetMetricValue(
        "cron_job_latency", fields=[cron_job_id])
    self.assertEqual(current_metric_value.count - prev_metric_value.count, 1)
    self.assertEqual(current_metric_value.sum - prev_metric_value.sum, 60)

  def testSchedulingJobWithFixedNamePreservesTheName(self):
    cron_manager = aff4_cronjobs.GetCronManager()
    cron_args = rdf_cronjobs.CreateCronJobArgs(
        allow_overruns=True, frequency="1d", flow_name="FakeCronJob")

    job_id = cron_manager.CreateJob(
        cron_args=cron_args, token=self.token, job_id="TheJob")
    self.assertEqual("TheJob", job_id)

  def testReschedulingJobWithFixedNameDoesNotCreateNewObjectVersion(self):
    cron_manager = aff4_cronjobs.GetCronManager()

    cron_args = rdf_cronjobs.CreateCronJobArgs(
        allow_overruns=True, frequency="1d", flow_name="FakeCronJob")

    # Schedule cron job with a fixed name. Check that we have 1 version
    # of "TYPE" attribute.
    cron_manager.CreateJob(
        cron_args=cron_args, token=self.token, job_id="TheJob")
    cron_job = cron_manager.ReadJob("TheJob", token=self.token)
    attr_values = list(cron_job.GetValuesForAttribute(cron_job.Schema.TYPE))
    self.assertTrue(len(attr_values) == 1)

    # Reschedule the job. Check that we still have only one "TYPE" version.
    cron_manager.CreateJob(
        cron_args=cron_args, token=self.token, job_id="TheJob")
    cron_job = cron_manager.ReadJob("TheJob", token=self.token)
    attr_values = list(cron_job.GetValuesForAttribute(cron_job.Schema.TYPE))
    self.assertTrue(len(attr_values) == 1)

  def testLastRunStatusGetsUpdatedOnEveryRun(self):
    job_id = "OccasionallyFailingFakeCronJob"
    aff4_cronjobs.ScheduleSystemCronFlows(names=[job_id], token=self.token)

    cron_manager = aff4_cronjobs.GetCronManager()

    for fake_time in [0, 60]:
      with test_lib.FakeTime(fake_time):
        # This call should start a new cron job flow
        cron_manager.RunOnce(token=self.token)
        cron_job = cron_manager.ReadJob(job_id, token=self.token)
        cron_flow_urn = cron_job.Get(cron_job.Schema.CURRENT_FLOW_URN)

        flow_test_lib.TestFlowHelper(
            cron_flow_urn, check_flow_errors=False, token=self.token)
        # This RunOnce call should determine that the flow has finished
        cron_manager.RunOnce(token=self.token)

    cron_job = cron_manager.ReadJob(job_id, token=self.token)
    statuses = list(
        cron_job.GetValuesForAttribute(cron_job.Schema.LAST_RUN_STATUS))

    statuses = sorted(statuses, key=lambda x: x.age)
    self.assertLen(statuses, 2)

    self.assertEqual(statuses[0].age,
                     rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0))
    self.assertEqual(statuses[1].age,
                     rdfvalue.RDFDatetime.FromSecondsSinceEpoch(60))
    self.assertEqual(statuses[0].status,
                     rdf_cronjobs.CronJobRunStatus.Status.OK)
    self.assertEqual(statuses[1].status,
                     rdf_cronjobs.CronJobRunStatus.Status.ERROR)

  def testSystemCronFlowsGetScheduledAutomatically(self):
    aff4_cronjobs.ScheduleSystemCronFlows(
        names=[DummySystemCronJob.__name__], token=self.token)

    jobs = aff4_cronjobs.GetCronManager().ListJobs(token=self.token)
    self.assertIn("DummySystemCronJob", jobs)

    # System cron job should be enabled by default.
    job = aff4_cronjobs.GetCronManager().ReadJob(
        "DummySystemCronJob", token=self.token)
    self.assertFalse(job.Get(job.Schema.DISABLED))

  def testSystemCronFlowsWithDisabledAttributeDoNotGetScheduled(self):
    aff4_cronjobs.ScheduleSystemCronFlows(
        names=[DummyDisabledSystemCronJob.__name__], token=self.token)

    jobs = aff4_cronjobs.GetCronManager().ListJobs(token=self.token)
    self.assertIn("DummyDisabledSystemCronJob", jobs)

    # System cron job should be enabled by default.
    job = aff4_cronjobs.GetCronManager().ReadJob(
        "DummyDisabledSystemCronJob", token=self.token)
    self.assertTrue(job.Get(job.Schema.DISABLED))

  def testSystemCronFlowsMayBeDisabledViaConfig(self):
    with test_lib.ConfigOverrider(
        {"Cron.disabled_system_jobs": ["DummySystemCronJob"]}):
      aff4_cronjobs.ScheduleSystemCronFlows(token=self.token)

      jobs = aff4_cronjobs.GetCronManager().ListJobs(token=self.token)
      self.assertIn("DummySystemCronJob", jobs)

      # This cron job should be disabled, because it's listed in
      # Cron.disabled_system_jobs config variable.
      job = aff4_cronjobs.GetCronManager().ReadJob(
          "DummySystemCronJob", token=self.token)
      self.assertTrue(job.Get(job.Schema.DISABLED))

    # Now remove the cron job from the list and check that it gets disabled
    # after next ScheduleSystemCronFlows() call.
    with test_lib.ConfigOverrider({"Cron.disabled_system_jobs": []}):

      aff4_cronjobs.ScheduleSystemCronFlows(token=self.token)

      # System cron job should be enabled.
      job = aff4_cronjobs.GetCronManager().ReadJob(
          "DummySystemCronJob", token=self.token)
      self.assertFalse(job.Get(job.Schema.DISABLED))

  def testScheduleSystemCronFlowsRaisesWhenFlowCanNotBeFound(self):
    with test_lib.ConfigOverrider(
        {"Cron.disabled_system_jobs": ["NonExistent"]}):
      self.assertRaises(
          ValueError, aff4_cronjobs.ScheduleSystemCronFlows, token=self.token)

  def testSystemCronJobsGetScheduledWhenDisabledListInvalid(self):
    with test_lib.ConfigOverrider(
        {"Cron.disabled_system_jobs": ["NonExistent"]}):
      with self.assertRaises(ValueError):
        aff4_cronjobs.ScheduleSystemCronFlows(
            names=[DummySystemCronJob.__name__], token=self.token)

    jobs = aff4_cronjobs.GetCronManager().ListJobs(token=self.token)
    self.assertIn("DummySystemCronJob", jobs)

  def testStatefulSystemCronFlowRaisesWhenRunningWithoutCronJob(self):
    self.assertRaises(
        aff4_cronjobs.StateReadError,
        flow.StartAFF4Flow,
        flow_name="DummyStatefulSystemCronJob",
        token=self.token)

  def testStatefulSystemCronFlowMaintainsState(self):
    DummyStatefulSystemCronJob.VALUES = []

    # We need to have a cron job started to have a place to maintain
    # state.
    aff4_cronjobs.ScheduleSystemCronFlows(
        names=[DummyStatefulSystemCronJob.__name__], token=self.token)

    flow.StartAFF4Flow(flow_name="DummyStatefulSystemCronJob", token=self.token)
    flow.StartAFF4Flow(flow_name="DummyStatefulSystemCronJob", token=self.token)
    flow.StartAFF4Flow(flow_name="DummyStatefulSystemCronJob", token=self.token)

    self.assertListEqual(DummyStatefulSystemCronJob.VALUES, [0, 1, 2])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
