#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import functools
import threading

from absl import app
from future.builtins import range
import mock

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import compatibility
from grr_response_core.stats import stats_collector_instance
from grr_response_server import cronjobs
from grr_response_server import data_store
from grr_response_server.flows.general import transfer
from grr_response_server.hunts import standard
from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib


class DummySystemCronJobRel(cronjobs.SystemCronJobBase):
  """Dummy system cron job."""

  lifetime = rdfvalue.Duration("42h")
  frequency = rdfvalue.Duration("42d")

  def Run(self):
    pass


class DummyStatefulSystemCronJobRel(cronjobs.SystemCronJobBase):
  """Dummy stateful system cron job."""

  frequency = rdfvalue.Duration("1d")
  lifetime = rdfvalue.Duration("20h")

  VALUES = []

  def Run(self):
    state = self.ReadCronState()
    value = state.get("value", 0)

    DummyStatefulSystemCronJobRel.VALUES.append(value)

    state["value"] = value + 1
    self.WriteCronState(state)


class DummyDisabledSystemCronJobRel(DummySystemCronJobRel):
  """Disabled system cron job."""

  enabled = False


def WaitForEvent(event):
  event.wait()


def WaitAndSignal(wait_event, signal_event):
  signal_event.set()
  wait_event.wait()


class RelationalCronTest(db_test_lib.RelationalDBEnabledMixin,
                         test_lib.GRRBaseTest):
  """Tests for cron functionality."""

  def tearDown(self):
    # Make sure all pending cronjobs have been processed before we wipe the db.
    cronjobs.CronManager()._GetThreadPool().Stop()
    super(RelationalCronTest, self).tearDown()

  def testCronJobPreservesFlowNameAndArguments(self):
    pathspec = rdf_paths.PathSpec(
        path="/foo", pathtype=rdf_paths.PathSpec.PathType.TSK)

    cron_manager = cronjobs.CronManager()

    flow_name = transfer.GetFile.__name__

    cron_args = rdf_cronjobs.CreateCronJobArgs(
        frequency="1d", allow_overruns=False, flow_name=flow_name)

    cron_args.flow_args.pathspec = pathspec

    job_id = cron_manager.CreateJob(cron_args=cron_args)

    # Check that CronJob definition is saved properly
    jobs = cron_manager.ListJobs(token=self.token)
    self.assertLen(jobs, 1)
    self.assertEqual(jobs[0], job_id)

    cron_job = cron_manager.ReadJob(job_id, token=self.token)
    hunt_args = cron_job.args.hunt_cron_action
    self.assertEqual(hunt_args.flow_name, flow_name)

    self.assertEqual(hunt_args.flow_args.pathspec, pathspec)

    self.assertEqual(cron_job.frequency, rdfvalue.Duration("1d"))
    self.assertEqual(cron_job.allow_overruns, False)

  def testCronJobStartsRun(self):
    cron_manager = cronjobs.CronManager()
    create_flow_args = rdf_cronjobs.CreateCronJobArgs()

    job_id = cron_manager.CreateJob(cron_args=create_flow_args)

    cron_job = cron_manager.ReadJob(job_id, token=self.token)
    self.assertFalse(cron_manager.JobIsRunning(cron_job, token=self.token))
    # The job never ran, so JobDueToRun() should return true.
    self.assertTrue(cron_manager.JobDueToRun(cron_job))

    cron_manager.RunOnce(token=self.token)
    cron_manager._GetThreadPool().Join()

    runs = cron_manager.ReadJobRuns(job_id, token=self.token)
    self.assertLen(runs, 1)
    run = runs[0]
    self.assertTrue(run.run_id)
    self.assertTrue(run.started_at)
    self.assertTrue(run.finished_at)
    self.assertEqual(run.status, "FINISHED")

  def testDisabledCronJobDoesNotCreateJobs(self):
    cron_manager = cronjobs.CronManager()
    create_flow_args = rdf_cronjobs.CreateCronJobArgs()

    job_id1 = cron_manager.CreateJob(cron_args=create_flow_args)
    job_id2 = cron_manager.CreateJob(cron_args=create_flow_args)

    cron_manager.DisableJob(job_id1, token=self.token)

    event = threading.Event()
    waiting_func = functools.partial(WaitForEvent, event)
    try:
      with mock.patch.object(standard.RunHunt, "Run", wraps=waiting_func):
        cron_manager.RunOnce(token=self.token)

      cron_job1 = cron_manager.ReadJob(job_id1, token=self.token)
      cron_job2 = cron_manager.ReadJob(job_id2, token=self.token)

      # Disabled flow shouldn't be running, while not-disabled flow should run
      # as usual.
      self.assertFalse(cron_manager.JobIsRunning(cron_job1, token=self.token))
      self.assertTrue(cron_manager.JobIsRunning(cron_job2, token=self.token))
    finally:
      event.set()

  @mock.patch.object(cronjobs, "TASK_STARTUP_WAIT", 1)
  def testCronMaxThreadsLimitIsRespectedAndCorrectlyHandled(self):
    cron_manager = cronjobs.CronManager()

    event = threading.Event()
    waiting_func = functools.partial(WaitForEvent, event)

    try:
      create_flow_args = rdf_cronjobs.CreateCronJobArgs(
          frequency="1h", lifetime="1h")
      with mock.patch.object(standard.RunHunt, "Run", wraps=waiting_func):
        job_ids = []
        for _ in range(cron_manager.max_threads * 2):
          job_ids.append(cron_manager.CreateJob(cron_args=create_flow_args))

        cron_manager.RunOnce(token=self.token)

        count_scheduled = 0
        for job_id in job_ids:
          count_scheduled += len(cron_manager.ReadJobRuns(job_id))

        self.assertEqual(count_scheduled, cron_manager.max_threads)
    finally:
      event.set()

    cron_manager._GetThreadPool().Join()

    count_scheduled = 0
    for job_id in job_ids:
      count_scheduled += len(cron_manager.ReadJobRuns(job_id))
    # Check that tasks that were not scheduled due to max_threads limit
    # run later.
    self.assertEqual(count_scheduled, cron_manager.max_threads)

    # Now all the cron jobs that weren't scheduled in previous RunOnce call
    # due to max_threads limit should get scheduled.
    cron_manager.RunOnce(token=self.token)

    count_scheduled = 0
    for job_id in job_ids:
      count_scheduled += len(cron_manager.ReadJobRuns(job_id))
    self.assertEqual(count_scheduled, cron_manager.max_threads * 2)

  def testNonExistingSystemCronJobDoesNotPreventOtherCronJobsFromRunning(self):
    cron_manager = cronjobs.CronManager()

    # Have a fake non-existing cron job. We assume that cron jobs are going
    # to be processed in alphabetical order, according to their cron job ids.
    args = rdf_cronjobs.CronJobAction(
        action_type=rdf_cronjobs.CronJobAction.ActionType.SYSTEM_CRON_ACTION,
        system_cron_action=rdf_cronjobs.SystemCronAction(
            job_class_name="__AbstractFakeCronJob__"))

    job = rdf_cronjobs.CronJob(
        cron_job_id="cron_1",
        args=args,
        enabled=True,
        frequency=rdfvalue.Duration("2h"),
        lifetime=rdfvalue.Duration("1h"),
        allow_overruns=False)
    data_store.REL_DB.WriteCronJob(job)

    # Have a proper cron job.
    cron_manager = cronjobs.CronManager()
    args = rdf_cronjobs.CronJobAction(
        action_type=rdf_cronjobs.CronJobAction.ActionType.SYSTEM_CRON_ACTION,
        system_cron_action=rdf_cronjobs.SystemCronAction(
            job_class_name="DummyStatefulSystemCronJobRel"))

    job = rdf_cronjobs.CronJob(
        cron_job_id="cron_2",
        args=args,
        enabled=True,
        frequency=rdfvalue.Duration("2h"),
        lifetime=rdfvalue.Duration("1h"),
        allow_overruns=False)
    data_store.REL_DB.WriteCronJob(job)

    with self.assertRaises(cronjobs.OneOrMoreCronJobsFailedError):
      cron_manager.RunOnce()
    cron_manager._GetThreadPool().Join()

    self.assertEmpty(cron_manager.ReadJobRuns("cron_1"))
    self.assertLen(cron_manager.ReadJobRuns("cron_2"), 1)

  def testCronJobRunDoesNothingIfCurrentFlowIsRunning(self):
    event = threading.Event()
    waiting_func = functools.partial(WaitForEvent, event)
    cron_manager = cronjobs.CronManager()
    with mock.patch.object(standard.RunHunt, "Run", wraps=waiting_func):
      try:
        fake_time = rdfvalue.RDFDatetime.Now()
        with test_lib.FakeTime(fake_time):
          create_flow_args = rdf_cronjobs.CreateCronJobArgs(
              allow_overruns=False, frequency="1h")

          job_id = cron_manager.CreateJob(cron_args=create_flow_args)
          cron_manager.RunOnce(token=self.token)

          cron_job_runs = cron_manager.ReadJobRuns(job_id, token=self.token)
          self.assertLen(cron_job_runs, 1)

          job = cron_manager.ReadJob(job_id)
          self.assertTrue(cron_manager.JobIsRunning(job))

        fake_time += rdfvalue.Duration("2h")
        with test_lib.FakeTime(fake_time):
          cron_manager.RunOnce(token=self.token)

          cron_job_runs = cron_manager.ReadJobRuns(job_id, token=self.token)
          self.assertLen(cron_job_runs, 1)

      finally:
        event.set()
        cron_manager._GetThreadPool().Join()

  def testForceRun(self):
    event = threading.Event()
    waiting_func = functools.partial(WaitForEvent, event)
    cron_manager = cronjobs.CronManager()
    with mock.patch.object(standard.RunHunt, "Run", wraps=waiting_func):
      try:
        fake_time = rdfvalue.RDFDatetime.Now()
        with test_lib.FakeTime(fake_time):
          create_flow_args = rdf_cronjobs.CreateCronJobArgs(
              allow_overruns=False, frequency="1h")

          job_id = cron_manager.CreateJob(cron_args=create_flow_args)
          cron_manager.RunOnce(token=self.token)

          cron_job_runs = cron_manager.ReadJobRuns(job_id, token=self.token)
          self.assertLen(cron_job_runs, 1)

          job = cron_manager.ReadJob(job_id)
          self.assertTrue(cron_manager.JobIsRunning(job))

          # At this point, there is a run currently executing and also the job
          # is not due to run for another hour. We can still force execute the
          # job.
          cron_manager.RunOnce(token=self.token)
          cron_job_runs = cron_manager.ReadJobRuns(job_id, token=self.token)
          self.assertLen(cron_job_runs, 1)

          cron_manager.RequestForcedRun(job_id)
          cron_manager.RunOnce(token=self.token)
          cron_job_runs = cron_manager.ReadJobRuns(job_id, token=self.token)
          self.assertLen(cron_job_runs, 2)

          # The only way to prevent a forced run is to disable the job.
          cron_manager.DisableJob(job_id)
          cron_manager.RequestForcedRun(job_id)
          cron_manager.RunOnce(token=self.token)
          cron_job_runs = cron_manager.ReadJobRuns(job_id, token=self.token)
          self.assertLen(cron_job_runs, 2)

          # And enable again.
          cron_manager.EnableJob(job_id)
          cron_manager.RequestForcedRun(job_id)
          cron_manager.RunOnce(token=self.token)
          cron_job_runs = cron_manager.ReadJobRuns(job_id, token=self.token)
          self.assertLen(cron_job_runs, 3)

      finally:
        event.set()
        cron_manager._GetThreadPool().Join()

  def testCronJobRunDoesNothingIfDueTimeHasNotComeYet(self):
    fake_time = rdfvalue.RDFDatetime.Now()
    with test_lib.FakeTime(fake_time):
      cron_manager = cronjobs.CronManager()
      create_flow_args = rdf_cronjobs.CreateCronJobArgs(
          allow_overruns=False, frequency="1h")

      job_id = cron_manager.CreateJob(cron_args=create_flow_args)

      cron_manager.RunOnce(token=self.token)

      cron_job_runs = cron_manager.ReadJobRuns(job_id, token=self.token)
      self.assertLen(cron_job_runs, 1)

    # Let 59 minutes pass. Frequency is 1 hour, so new flow is not
    # supposed to start.
    fake_time += rdfvalue.Duration("59m")
    with test_lib.FakeTime(fake_time):

      cron_manager.RunOnce(token=self.token)

      cron_job_runs = cron_manager.ReadJobRuns(job_id, token=self.token)
      self.assertLen(cron_job_runs, 1)

  def testCronJobRunPreventsOverrunsWhenAllowOverrunsIsFalse(self):
    event = threading.Event()
    waiting_func = functools.partial(WaitForEvent, event)
    cron_manager = cronjobs.CronManager()
    try:
      with mock.patch.object(standard.RunHunt, "Run", wraps=waiting_func):
        fake_time = rdfvalue.RDFDatetime.Now()
        with test_lib.FakeTime(fake_time):
          create_flow_args = rdf_cronjobs.CreateCronJobArgs(
              allow_overruns=False, frequency="1h")

          job_id = cron_manager.CreateJob(cron_args=create_flow_args)

          cron_manager.RunOnce(token=self.token)

          cron_job_runs = cron_manager.ReadJobRuns(job_id, token=self.token)
          self.assertLen(cron_job_runs, 1)

        # Let two hours pass. Frequency is 1h (i.e. cron job iterations are
        # supposed to be started every hour), so the new flow should be started
        # by RunOnce(). However, as allow_overruns is False, and previous
        # iteration flow hasn't finished yet, no flow will be started.
        fake_time += rdfvalue.Duration("2h")
        with test_lib.FakeTime(fake_time):

          cron_manager.RunOnce(token=self.token)

          cron_job_runs = cron_manager.ReadJobRuns(job_id, token=self.token)
          self.assertLen(cron_job_runs, 1)

    finally:
      event.set()
      cron_manager._GetThreadPool().Join()

  def testCronJobRunPreventsOverrunsWhenAllowOverrunsIsTrue(self):
    event = threading.Event()
    waiting_func = functools.partial(WaitForEvent, event)
    cron_manager = cronjobs.CronManager()
    try:
      with mock.patch.object(standard.RunHunt, "Run", wraps=waiting_func):
        fake_time = rdfvalue.RDFDatetime.Now()
        with test_lib.FakeTime(fake_time):
          create_flow_args = rdf_cronjobs.CreateCronJobArgs(
              allow_overruns=True, frequency="1h")

          job_id = cron_manager.CreateJob(cron_args=create_flow_args)

          cron_manager.RunOnce(token=self.token)

          cron_job_runs = cron_manager.ReadJobRuns(job_id, token=self.token)
          self.assertLen(cron_job_runs, 1)

        # Let two hours pass. Frequency is 1h (i.e. cron job iterations are
        # supposed to be started every hour), so the new flow should be started
        # by RunOnce(). However, as allow_overruns is False, and previous
        # iteration flow hasn't finished yet, no flow will be started.
        fake_time += rdfvalue.Duration("2h")
        with test_lib.FakeTime(fake_time):

          cron_manager.RunOnce(token=self.token)

          cron_job_runs = cron_manager.ReadJobRuns(job_id, token=self.token)
          self.assertLen(cron_job_runs, 2)

    finally:
      event.set()
      cron_manager._GetThreadPool().Join()

  def testCronManagerListJobsDoesNotListDeletedJobs(self):
    cron_manager = cronjobs.CronManager()

    create_flow_args = rdf_cronjobs.CreateCronJobArgs()

    cron_job_id = cron_manager.CreateJob(cron_args=create_flow_args)

    self.assertLen(cron_manager.ListJobs(), 1)

    cron_manager.DeleteJob(cron_job_id)

    self.assertEmpty(cron_manager.ListJobs())

  def testRunningJobs(self):
    event = threading.Event()
    waiting_func = functools.partial(WaitForEvent, event)

    with mock.patch.object(standard.RunHunt, "Run", wraps=waiting_func):
      cron_manager = cronjobs.CronManager()
      create_flow_args = rdf_cronjobs.CreateCronJobArgs(
          frequency="1w", lifetime="1d")

      job_id = cron_manager.CreateJob(cron_args=create_flow_args)

      prev_timeout_value = stats_collector_instance.Get().GetMetricValue(
          "cron_job_timeout", fields=[job_id])
      prev_latency_value = stats_collector_instance.Get().GetMetricValue(
          "cron_job_latency", fields=[job_id])

      cron_manager.RunOnce(token=self.token)

      cron_job = cron_manager.ReadJob(job_id, token=self.token)
      self.assertTrue(cron_manager.JobIsRunning(cron_job))
      runs = cron_manager.ReadJobRuns(job_id)
      self.assertLen(runs, 1)
      run = runs[0]

      self.assertEqual(cron_job.current_run_id, run.run_id)
      self.assertEqual(run.status, "RUNNING")

      event.set()
      cron_manager._GetThreadPool().Join()

      cron_job = cron_manager.ReadJob(job_id, token=self.token)
      self.assertFalse(cron_manager.JobIsRunning(cron_job))
      runs = cron_manager.ReadJobRuns(job_id)
      self.assertLen(runs, 1)
      run = runs[0]

      self.assertFalse(cron_job.current_run_id)
      self.assertEqual(run.status, "FINISHED")

      # Check that timeout counter got updated.
      current_timeout_value = stats_collector_instance.Get().GetMetricValue(
          "cron_job_timeout", fields=[job_id])
      self.assertEqual(current_timeout_value, prev_timeout_value)

      # Check that latency stat got updated.
      current_latency_value = stats_collector_instance.Get().GetMetricValue(
          "cron_job_latency", fields=[job_id])
      self.assertEqual(current_latency_value.count - prev_latency_value.count,
                       1)

  def testTimeoutOfCrashedCronJobIsHandledCorrectly(self):
    wait_event = threading.Event()
    signal_event = threading.Event()
    waiting_func = functools.partial(WaitAndSignal, wait_event, signal_event)

    fake_time = rdfvalue.RDFDatetime.Now()
    with mock.patch.object(standard.RunHunt, "Run", wraps=waiting_func):
      with test_lib.FakeTime(fake_time):
        cron_manager = cronjobs.CronManager()
        create_flow_args = rdf_cronjobs.CreateCronJobArgs()
        create_flow_args.frequency = "1h"
        create_flow_args.lifetime = "1h"

        job_id = cron_manager.CreateJob(cron_args=create_flow_args)

        cron_manager.RunOnce(token=self.token)
        # Make sure the cron job has actually been started.
        signal_event.wait(10)

        cron_job = cron_manager.ReadJob(job_id, token=self.token)
        self.assertTrue(cron_manager.JobIsRunning(cron_job))
        runs = cron_manager.ReadJobRuns(job_id)
        self.assertLen(runs, 1)
        run = runs[0]
        self.assertEqual(cron_job.current_run_id, run.run_id)
        self.assertEqual(run.status, "RUNNING")

      try:
        prev_timeout_value = stats_collector_instance.Get().GetMetricValue(
            "cron_job_timeout", fields=[job_id])
        prev_latency_value = stats_collector_instance.Get().GetMetricValue(
            "cron_job_latency", fields=[job_id])

        fake_time += rdfvalue.Duration("2h")
        with test_lib.FakeTime(fake_time):
          signal_event.clear()
          # First RunOnce call will mark the stuck job as failed.
          cron_manager.RunOnce(token=self.token)
          cron_job = cron_manager.ReadJob(job_id, token=self.token)
          self.assertEqual(cron_job.last_run_status, "LIFETIME_EXCEEDED")
          runs = cron_manager.ReadJobRuns(job_id)
          self.assertLen(runs, 1)
          self.assertEqual(runs[0].status, "LIFETIME_EXCEEDED")

          # Second RunOnce call will schedule a new invocation.
          cron_manager.RunOnce(token=self.token)
          signal_event.wait(10)

          # Previous job run should be considered stuck by now. A new one
          # has to be started.
          cron_job = cron_manager.ReadJob(job_id, token=self.token)
          runs = cron_manager.ReadJobRuns(job_id)
          self.assertLen(runs, 2)

          old_run, new_run = sorted(runs, key=lambda r: r.started_at)
          self.assertIsNotNone(new_run.started_at)

          self.assertEqual(new_run.status, "RUNNING")
          self.assertEqual(cron_job.current_run_id, new_run.run_id)
          self.assertIsNotNone(old_run.started_at)
          self.assertIsNotNone(old_run.finished_at)
          self.assertEqual(old_run.status, "LIFETIME_EXCEEDED")

          self.assertEqual(cron_job.last_run_status, "LIFETIME_EXCEEDED")

          # Check that timeout counter got updated.
          current_timeout_value = stats_collector_instance.Get().GetMetricValue(
              "cron_job_timeout", fields=[job_id])
          self.assertEqual(current_timeout_value - prev_timeout_value, 1)

          # Check that latency stat got updated.
          current_latency_value = stats_collector_instance.Get().GetMetricValue(
              "cron_job_latency", fields=[job_id])
          self.assertEqual(
              current_latency_value.count - prev_latency_value.count, 1)
          self.assertEqual(current_latency_value.sum - prev_latency_value.sum,
                           rdfvalue.Duration("2h").seconds)

      finally:
        # Make sure that the cron job thread actually finishes.
        wait_event.set()
        cron_manager._GetThreadPool().Join()

      # Make sure cron job got updated correctly after stuck job as finished.
      cron_job = cron_manager.ReadJob(job_id, token=self.token)
      self.assertEqual(cron_job.last_run_status, "FINISHED")

  def testTimeoutOfLongRunningJobIsHandledCorrectly(self):
    wait_event = threading.Event()
    signal_event = threading.Event()
    waiting_func = functools.partial(WaitAndSignal, wait_event, signal_event)

    fake_time = rdfvalue.RDFDatetime.Now()
    with mock.patch.object(standard.RunHunt, "Run", wraps=waiting_func):
      with test_lib.FakeTime(fake_time):
        cron_manager = cronjobs.CronManager()
        create_flow_args = rdf_cronjobs.CreateCronJobArgs()
        create_flow_args.lifetime = "1h"

        job_id = cron_manager.CreateJob(cron_args=create_flow_args)

        cron_manager.RunOnce(token=self.token)
        # Make sure the cron job has actually been started.
        signal_event.wait(10)

        cron_job = cron_manager.ReadJob(job_id, token=self.token)
        self.assertTrue(cron_manager.JobIsRunning(cron_job))
        runs = cron_manager.ReadJobRuns(job_id)
        self.assertLen(runs, 1)
        run = runs[0]
        self.assertEqual(cron_job.current_run_id, run.run_id)
        self.assertEqual(run.status, "RUNNING")

      prev_timeout_value = stats_collector_instance.Get().GetMetricValue(
          "cron_job_timeout", fields=[job_id])
      prev_latency_value = stats_collector_instance.Get().GetMetricValue(
          "cron_job_latency", fields=[job_id])

      fake_time += rdfvalue.Duration("2h")
      with test_lib.FakeTime(fake_time):
        wait_event.set()
        cron_manager._GetThreadPool().Join()

        cron_job = cron_manager.ReadJob(job_id, token=self.token)
        runs = cron_manager.ReadJobRuns(job_id)
        self.assertLen(runs, 1)
        run = runs[0]

        self.assertEqual(cron_job.last_run_status, "LIFETIME_EXCEEDED")
        self.assertEqual(run.status, "LIFETIME_EXCEEDED")

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
                         rdfvalue.Duration("2h").seconds)

  def testError(self):
    with mock.patch.object(
        standard.RunHunt,
        "Run",
        side_effect=ValueError("Random cron job error.")):
      cron_manager = cronjobs.CronManager()
      create_flow_args = rdf_cronjobs.CreateCronJobArgs()

      job_id = cron_manager.CreateJob(cron_args=create_flow_args)

      prev_failure_value = stats_collector_instance.Get().GetMetricValue(
          "cron_job_failure", fields=[job_id])
      prev_latency_value = stats_collector_instance.Get().GetMetricValue(
          "cron_job_latency", fields=[job_id])

      cron_manager.RunOnce(token=self.token)
      cron_manager._GetThreadPool().Join()

      cron_job = cron_manager.ReadJob(job_id, token=self.token)
      self.assertFalse(cron_manager.JobIsRunning(cron_job))
      runs = cron_manager.ReadJobRuns(job_id)
      self.assertLen(runs, 1)
      run = runs[0]
      self.assertEqual(cron_job.last_run_status, "ERROR")
      self.assertEqual(run.status, "ERROR")

      self.assertTrue(run.backtrace)
      self.assertIn("cron job error", run.backtrace)

      current_failure_value = stats_collector_instance.Get().GetMetricValue(
          "cron_job_failure", fields=[job_id])
      current_latency_value = stats_collector_instance.Get().GetMetricValue(
          "cron_job_latency", fields=[job_id])

      self.assertEqual(current_failure_value, prev_failure_value + 1)
      self.assertEqual(current_latency_value.count,
                       prev_latency_value.count + 1)

  def testSchedulingJobWithFixedNamePreservesTheName(self):
    cron_manager = cronjobs.CronManager()
    create_flow_args = rdf_cronjobs.CreateCronJobArgs()

    job_id = cron_manager.CreateJob(cron_args=create_flow_args, job_id="TheJob")
    self.assertEqual("TheJob", job_id)

  def testSystemCronJobsGetScheduledAutomatically(self):
    cronjobs.ScheduleSystemCronJobs(names=[DummySystemCronJobRel.__name__])

    jobs = cronjobs.CronManager().ListJobs()
    self.assertIn("DummySystemCronJobRel", jobs)

    # System cron job should be enabled by default.
    job = cronjobs.CronManager().ReadJob("DummySystemCronJobRel")
    self.assertTrue(job.enabled)

  def testSystemCronJobsWithDisabledAttributeDoNotGetScheduled(self):
    cronjobs.ScheduleSystemCronJobs(
        names=[DummyDisabledSystemCronJobRel.__name__])

    jobs = cronjobs.CronManager().ListJobs()
    self.assertIn("DummyDisabledSystemCronJobRel", jobs)

    # System cron job should be enabled by default.
    job = cronjobs.CronManager().ReadJob("DummyDisabledSystemCronJobRel")
    self.assertFalse(job.enabled)

  def testSystemCronJobsMayBeDisabledViaConfig(self):
    with test_lib.ConfigOverrider(
        {"Cron.disabled_cron_jobs": ["DummySystemCronJobRel"]}):
      cronjobs.ScheduleSystemCronJobs()

      cron_manager = cronjobs.CronManager()

      jobs = cron_manager.ListJobs()
      self.assertIn("DummySystemCronJobRel", jobs)

      # This cron job should be disabled, because it's listed in
      # Cron.disabled_cron_jobs config variable.
      job = cron_manager.ReadJob("DummySystemCronJobRel")
      self.assertFalse(job.enabled)

    # Now remove the cron job from the list and check that it gets disabled
    # after next ScheduleSystemCronJobs() call.
    with test_lib.ConfigOverrider({"Cron.disabled_cron_jobs": []}):

      cronjobs.ScheduleSystemCronJobs()

      # System cron job should be enabled.
      job = cron_manager.ReadJob("DummySystemCronJobRel")
      self.assertTrue(job.enabled)

  def testScheduleSystemCronJobsRaisesWhenFlowCanNotBeFound(self):
    with test_lib.ConfigOverrider({"Cron.disabled_cron_jobs": ["NonExistent"]}):
      self.assertRaises(ValueError, cronjobs.ScheduleSystemCronJobs)

  def testSystemCronJobsGetScheduledWhenDisabledListInvalid(self):
    with test_lib.ConfigOverrider({"Cron.disabled_cron_jobs": ["NonExistent"]}):
      with self.assertRaises(ValueError):
        cronjobs.ScheduleSystemCronJobs(names=[DummySystemCronJobRel.__name__])

    jobs = cronjobs.CronManager().ListJobs()
    self.assertIn("DummySystemCronJobRel", jobs)

  def testStatefulSystemCronJobMaintainsState(self):
    DummyStatefulSystemCronJobRel.VALUES = []

    # We need to have a cron job started to have a place to maintain
    # state.
    cron_manager = cronjobs.CronManager()
    args = rdf_cronjobs.CronJobAction(
        action_type=rdf_cronjobs.CronJobAction.ActionType.SYSTEM_CRON_ACTION,
        system_cron_action=rdf_cronjobs.SystemCronAction(
            job_class_name="DummyStatefulSystemCronJobRel"))

    job = rdf_cronjobs.CronJob(
        cron_job_id="test_cron",
        args=args,
        enabled=True,
        frequency=rdfvalue.Duration("2h"),
        lifetime=rdfvalue.Duration("1h"),
        allow_overruns=False)
    data_store.REL_DB.WriteCronJob(job)

    fake_time = rdfvalue.RDFDatetime.Now()
    for i in range(3):
      with test_lib.FakeTime(fake_time + rdfvalue.Duration("%dh" % (3 * i))):
        cron_manager.RunOnce()
        cron_manager._GetThreadPool().Join()
      runs = cron_manager.ReadJobRuns("test_cron")
      self.assertLen(runs, i + 1)
      for run in runs:
        self.assertEqual(run.status, "FINISHED")

    self.assertListEqual(DummyStatefulSystemCronJobRel.VALUES, [0, 1, 2])

  def testHeartbeat_EnforceMaxRuntime(self):
    cron_started_event = threading.Event()
    heartbeat_event = threading.Event()

    class HeartbeatingCronJob(cronjobs.SystemCronJobBase):
      lifetime = rdfvalue.Duration("1h")
      frequency = rdfvalue.Duration("2h")
      allow_overruns = False

      def Run(self):
        cron_started_event.set()
        heartbeat_event.wait()
        fake_time = self.run_state.started_at + rdfvalue.Duration("3h")
        with test_lib.FakeTime(fake_time):
          self.HeartBeat()

    self._TestHeartBeat(HeartbeatingCronJob, cron_started_event,
                        heartbeat_event)

  def testHeartbeat_AllowOverruns(self):
    cron_started_event = threading.Event()
    heartbeat_event = threading.Event()

    class HeartbeatingOverruningCronJob(cronjobs.SystemCronJobBase):
      lifetime = rdfvalue.Duration("1h")
      frequency = rdfvalue.Duration("2h")
      allow_overruns = True

      def Run(self):
        cron_started_event.set()
        heartbeat_event.wait()
        fake_time = self.run_state.started_at + rdfvalue.Duration("3h")
        with test_lib.FakeTime(fake_time):
          self.HeartBeat()

    self._TestHeartBeat(HeartbeatingOverruningCronJob, cron_started_event,
                        heartbeat_event)

  def _TestHeartBeat(self, cron_class, cron_started_event, heartbeat_event):
    """Helper for heartbeat tests."""
    cron_name = compatibility.GetName(cron_class)
    cronjobs.ScheduleSystemCronJobs(names=[cron_name])
    cron_manager = cronjobs.CronManager()
    jobs = cronjobs.CronManager().ListJobs()
    self.assertIn(cron_name, jobs)

    try:
      cron_manager.RunOnce()
      cron_started_event.wait()
      runs = cron_manager.ReadJobRuns(cron_name)
      self.assertLen(runs, 1)
      self.assertEqual(runs[0].status,
                       rdf_cronjobs.CronJobRun.CronJobRunStatus.RUNNING)
    finally:
      heartbeat_event.set()
      cron_manager._GetThreadPool().Join()
      runs = cron_manager.ReadJobRuns(cron_name)
      self.assertLen(runs, 1)
      if cron_class.allow_overruns:
        expected_status = rdf_cronjobs.CronJobRun.CronJobRunStatus.FINISHED
      else:
        expected_status = (
            rdf_cronjobs.CronJobRun.CronJobRunStatus.LIFETIME_EXCEEDED)
      self.assertEqual(runs[0].status, expected_status)

  @mock.patch.object(cronjobs, "_MAX_LOG_MESSAGES", 5)
  def testLogging(self):

    class LoggingCronJob(cronjobs.SystemCronJobBase):
      lifetime = rdfvalue.Duration("1h")
      frequency = rdfvalue.Duration("2h")

      def Run(self):
        for i in range(7):
          self.Log("Log message %d." % i)

    cron_name = compatibility.GetName(LoggingCronJob)
    cronjobs.ScheduleSystemCronJobs(names=[cron_name])
    cron_manager = cronjobs.CronManager()
    try:
      cron_manager.RunOnce()
    finally:
      cron_manager._GetThreadPool().Join()
      runs = cron_manager.ReadJobRuns(cron_name)
      self.assertLen(runs, 1)
      self.assertEmpty(runs[0].backtrace)
      self.assertEqual(runs[0].status,
                       rdf_cronjobs.CronJobRun.CronJobRunStatus.FINISHED)
      # The first two log messages should be discarded since
      # _MAX_LOG_MESSAGES is 5.
      self.assertMultiLineEqual(
          runs[0].log_message,
          "Log message 6.\nLog message 5.\nLog message 4.\nLog message 3.\n"
          "Log message 2.")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
