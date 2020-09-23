#!/usr/bin/env python
# Lint as: python3
"""Cron Job objects that get stored in the relational db."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import collections
import logging
import threading
import time
import traceback

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.registry import CronJobRegistry
from grr_response_core.lib.registry import SystemCronJobRegistry
from grr_response_core.lib.util import random
from grr_response_core.stats import metrics
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server import hunt
from grr_response_server import threadpool
from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs


# The maximum number of log-messages to store in the DB for a given cron-job
# run.
_MAX_LOG_MESSAGES = 20


CRON_JOB_FAILURE = metrics.Counter(
    "cron_job_failure", fields=[("cron_job_id", str)])
CRON_JOB_TIMEOUT = metrics.Counter(
    "cron_job_timeout", fields=[("cron_job_id", str)])
CRON_JOB_LATENCY = metrics.Event(
    "cron_job_latency", fields=[("cron_job_id", str)])

CRON_JOB_USERNAME = "GRRCron"


class Error(Exception):
  pass


class OneOrMoreCronJobsFailedError(Error):

  def __init__(self, failure_map):
    message = "One or more cron jobs failed unexpectedly: " + ", ".join(
        "%s=%s" % (k, v) for k, v in failure_map.items())
    super().__init__(message)
    self.failure_map = failure_map


class LockError(Error):
  pass


class LifetimeExceededError(Error):
  """Exception raised when a cronjob exceeds its max allowed runtime."""


class CronJobBase(metaclass=CronJobRegistry):
  """The base class for all cron jobs."""

  __abstract = True  # pylint: disable=g-bad-name

  def __init__(self, run_state, job):
    self.run_state = run_state
    self.job = job
    self.token = access_control.ACLToken(username=CRON_JOB_USERNAME)

  @abc.abstractmethod
  def Run(self):
    """The actual cron job logic goes into this method."""

  def StartRun(self, wait_for_start_event, signal_event, wait_for_write_event):
    """Starts a new run for the given cron job."""
    # Signal that the cron thread has started. This way the cron scheduler
    # will know that the task is not sitting in a threadpool queue, but is
    # actually executing.
    wait_for_start_event.set()
    # Wait until the cron scheduler acknowledges the run. If it doesn't
    # acknowledge, just return (it means that the cron scheduler considers
    # this task as "not started" and has returned the lease so that another
    # worker can pick it up).
    if not signal_event.wait(TASK_STARTUP_WAIT):
      return

    try:
      logging.info("Processing cron job: %s", self.job.cron_job_id)
      self.run_state.started_at = rdfvalue.RDFDatetime.Now()
      self.run_state.status = "RUNNING"

      data_store.REL_DB.WriteCronJobRun(self.run_state)
      data_store.REL_DB.UpdateCronJob(
          self.job.cron_job_id,
          last_run_time=rdfvalue.RDFDatetime.Now(),
          current_run_id=self.run_state.run_id,
          forced_run_requested=False)
    finally:
      # Notify the cron scheduler that all the DB updates are done. At this
      # point the cron scheduler can safely return this job's lease.
      wait_for_write_event.set()

    try:
      self.Run()
      self.run_state.status = "FINISHED"
    except LifetimeExceededError:
      self.run_state.status = "LIFETIME_EXCEEDED"
      CRON_JOB_FAILURE.Increment(fields=[self.job.cron_job_id])
    except Exception as e:  # pylint: disable=broad-except
      logging.exception("Cronjob %s failed with an error: %s",
                        self.job.cron_job_id, e)
      CRON_JOB_FAILURE.Increment(fields=[self.job.cron_job_id])
      self.run_state.status = "ERROR"
      self.run_state.backtrace = "{}\n\n{}".format(e, traceback.format_exc())

    finally:
      self.run_state.finished_at = rdfvalue.RDFDatetime.Now()
      elapsed = self.run_state.finished_at - self.run_state.started_at
      CRON_JOB_LATENCY.RecordEvent(
          elapsed.ToFractional(rdfvalue.SECONDS), fields=[self.job.cron_job_id])
      if self.job.lifetime:
        expiration_time = self.run_state.started_at + self.job.lifetime
        if self.run_state.finished_at > expiration_time:
          self.run_state.status = "LIFETIME_EXCEEDED"
          CRON_JOB_TIMEOUT.Increment(fields=[self.job.cron_job_id])
      data_store.REL_DB.WriteCronJobRun(self.run_state)

    current_job = data_store.REL_DB.ReadCronJob(self.job.cron_job_id)
    # If no other job was started while we were running, update last status
    # information.
    if current_job.current_run_id == self.run_state.run_id:
      data_store.REL_DB.UpdateCronJob(
          self.job.cron_job_id,
          current_run_id=None,
          last_run_status=self.run_state.status)


class SystemCronJobBase(CronJobBase, metaclass=SystemCronJobRegistry):
  """The base class for all system cron jobs."""

  __abstract = True  # pylint: disable=g-bad-name

  frequency = None
  lifetime = None

  allow_overruns = False
  enabled = True

  def __init__(self, *args, **kw):
    super().__init__(*args, **kw)

    if self.frequency is None or self.lifetime is None:
      raise ValueError(
          "SystemCronJob without frequency or lifetime encountered: %s" % self)
    self._log_messages = collections.deque(maxlen=_MAX_LOG_MESSAGES)

  # TODO(user): Cronjobs shouldn't have to call Heartbeat() in order to
  # enforce max-runtime limits.
  def HeartBeat(self):
    """Terminates a cronjob-run if it has exceeded its maximum runtime.

    This is a no-op for cronjobs that allow overruns.

    Raises:
      LifetimeExceededError: If the cronjob has exceeded its maximum runtime.
    """
    # In prod, self.job.lifetime is guaranteed to always be set, and is
    # always equal to self.__class__.lifetime. Some tests however, do not
    # set the job lifetime, which isn't great.
    if self.allow_overruns or not self.job.lifetime:
      return

    runtime = rdfvalue.RDFDatetime.Now() - self.run_state.started_at
    if runtime > self.lifetime:
      raise LifetimeExceededError(
          "Cronjob run has exceeded the maximum runtime of %s." % self.lifetime)

  def Log(self, message, *args):
    # Arrange messages in reverse chronological order.
    self._log_messages.appendleft(message % args)
    self.run_state.log_message = "\n".join(self._log_messages)
    # TODO(user): Fix tests that do not set self.run_state.run_id. The field
    # is guaranteed to always be set in prod.
    if self.run_state.run_id:
      data_store.REL_DB.WriteCronJobRun(self.run_state)

  def ReadCronState(self):
    return self.job.state

  def WriteCronState(self, state):
    self.job.state = state
    data_store.REL_DB.UpdateCronJob(self.job.cron_job_id, state=self.job.state)


TASK_STARTUP_WAIT = 10


class CronManager(object):
  """CronManager is used to schedule/terminate cron jobs."""

  def __init__(self, max_threads=10):
    super().__init__()

    if max_threads <= 0:
      raise ValueError("max_threads should be >= 1")

    self.max_threads = max_threads

  def CreateJob(self, cron_args=None, job_id=None, enabled=True):
    """Creates a cron job that runs given flow with a given frequency.

    Args:
      cron_args: A protobuf of type rdf_cronjobs.CreateCronJobArgs.
      job_id: Use this job_id instead of an autogenerated unique name (used for
        system cron jobs - we want them to have well-defined persistent name).
      enabled: If False, the job object will be created, but will be disabled.

    Returns:
      URN of the cron job created.

    Raises:
      ValueError: This function expects an arg protobuf that starts a
                  CreateAndRunGenericHuntFlow flow. If the args specify
                  something else, ValueError is raised.
    """
    if not job_id:
      # TODO: UInt16 is too small for randomly generated IDs.
      uid = random.UInt16()
      job_id = "%s_%s" % (cron_args.flow_name, uid)

    args = rdf_cronjobs.CronJobAction(
        action_type=rdf_cronjobs.CronJobAction.ActionType.HUNT_CRON_ACTION,
        hunt_cron_action=rdf_cronjobs.HuntCronAction(
            flow_name=cron_args.flow_name,
            flow_args=cron_args.flow_args,
            hunt_runner_args=cron_args.hunt_runner_args))

    job = rdf_cronjobs.CronJob(
        cron_job_id=job_id,
        description=cron_args.description,
        frequency=cron_args.frequency,
        lifetime=cron_args.lifetime,
        allow_overruns=cron_args.allow_overruns,
        args=args,
        enabled=enabled)
    data_store.REL_DB.WriteCronJob(job)

    return job_id

  def ListJobs(self):
    """Returns a list of ids of all currently running cron jobs."""
    return [job.cron_job_id for job in data_store.REL_DB.ReadCronJobs()]

  def ReadJob(self, job_id):
    return data_store.REL_DB.ReadCronJob(job_id)

  def ReadJobs(self):
    """Returns a list of all currently running cron jobs."""
    return data_store.REL_DB.ReadCronJobs()

  def ReadJobRun(self, job_id, run_id):
    return data_store.REL_DB.ReadCronJobRun(job_id, run_id)

  def ReadJobRuns(self, job_id):
    return data_store.REL_DB.ReadCronJobRuns(job_id)

  def EnableJob(self, job_id):
    """Enable cron job with the given id."""
    return data_store.REL_DB.EnableCronJob(job_id)

  def DisableJob(self, job_id):
    """Disable cron job with the given id."""
    return data_store.REL_DB.DisableCronJob(job_id)

  def DeleteJob(self, job_id):
    """Deletes cron job with the given URN."""
    return data_store.REL_DB.DeleteCronJob(job_id)

  def RequestForcedRun(self, job_id):
    data_store.REL_DB.UpdateCronJob(job_id, forced_run_requested=True)

  def RunOnce(self, names=None):
    """Tries to lock and run cron jobs.

    Args:
      names: List of cron jobs to run.  If unset, run them all.

    Raises:
      OneOrMoreCronJobsFailedError: if one or more individual cron jobs fail.
      Note: a failure of a single cron job doesn't preclude other cron jobs
      from running.
    """
    leased_jobs = data_store.REL_DB.LeaseCronJobs(
        cronjob_ids=names,
        lease_time=rdfvalue.Duration.From(10, rdfvalue.MINUTES))
    logging.info("Leased %d cron jobs for processing.", len(leased_jobs))
    if not leased_jobs:
      return

    errors = {}
    processed_count = 0
    for job in sorted(leased_jobs, key=lambda j: j.cron_job_id):
      if self.TerminateStuckRunIfNeeded(job):
        continue

      if not self.JobDueToRun(job):
        continue

      try:
        if self.RunJob(job):
          processed_count += 1
        else:
          logging.info(
              "Can't schedule cron job %s on a thread pool "
              "(all threads are busy or CPU load is high)", job.cron_job_id)
          break
      except Exception as e:  # pylint: disable=broad-except
        logging.exception("Cron job %s has failed: %s", job.cron_job_id, e)
        errors[job.cron_job_id] = e

    logging.info("Processed %d cron jobs.", processed_count)
    data_store.REL_DB.ReturnLeasedCronJobs(leased_jobs)

    if errors:
      raise OneOrMoreCronJobsFailedError(errors)

  def _GetThreadPool(self):
    pool = threadpool.ThreadPool.Factory(
        "CronJobPool", min_threads=1, max_threads=self.max_threads)
    pool.Start()
    return pool

  def TerminateStuckRunIfNeeded(self, job):
    """Cleans up job state if the last run is stuck."""
    if job.current_run_id and job.last_run_time and job.lifetime:
      now = rdfvalue.RDFDatetime.Now()
      # We add additional 10 minutes to give the job run a chance to kill itself
      # during one of the HeartBeat calls (HeartBeat checks if a cron job is
      # run is running too long and raises if it is).
      expiration_time = (
          job.last_run_time + job.lifetime +
          rdfvalue.Duration.From(10, rdfvalue.MINUTES))
      if now > expiration_time:
        run = data_store.REL_DB.ReadCronJobRun(job.cron_job_id,
                                               job.current_run_id)
        run.status = "LIFETIME_EXCEEDED"
        run.finished_at = now
        data_store.REL_DB.WriteCronJobRun(run)
        data_store.REL_DB.UpdateCronJob(
            job.cron_job_id, current_run_id=None, last_run_status=run.status)
        CRON_JOB_LATENCY.RecordEvent(
            (now - job.last_run_time).ToFractional(rdfvalue.SECONDS),
            fields=[job.cron_job_id])
        CRON_JOB_TIMEOUT.Increment(fields=[job.cron_job_id])

        return True

    return False

  def RunJob(self, job):
    """Does the actual work of the Cron, if the job is due to run.

    Args:
      job: The cronjob rdfvalue that should be run. Must be leased.

    Returns:
      A boolean indicating if this cron job was started or not. False may
      be returned when the threadpool is already full.

    Raises:
      LockError: if the object is not locked.
      ValueError: If the job argument is invalid.
    """
    if not job.leased_until:
      raise LockError("CronJob must be leased for Run() to be called.")
    if job.leased_until < rdfvalue.RDFDatetime.Now():
      raise LockError("CronJob lease expired for %s." % job.cron_job_id)

    logging.info("Starting cron job: %s", job.cron_job_id)

    if job.args.action_type == job.args.ActionType.SYSTEM_CRON_ACTION:
      cls_name = job.args.system_cron_action.job_class_name
      job_cls = SystemCronJobRegistry.CronJobClassByName(cls_name)
      name = "%s runner" % cls_name
    elif job.args.action_type == job.args.ActionType.HUNT_CRON_ACTION:
      job_cls = CronJobRegistry.CronJobClassByName("RunHunt")
      name = "Hunt runner"
    else:
      raise ValueError("CronJob %s doesn't have a valid args type set." %
                       job.cron_job_id)

    run_state = rdf_cronjobs.CronJobRun(
        cron_job_id=job.cron_job_id, status="RUNNING")
    run_state.GenerateRunId()

    run_obj = job_cls(run_state, job)
    wait_for_start_event, signal_event, wait_for_write_event = (
        threading.Event(), threading.Event(), threading.Event())
    try:
      self._GetThreadPool().AddTask(
          target=run_obj.StartRun,
          args=(wait_for_start_event, signal_event, wait_for_write_event),
          name=name,
          blocking=False,
          inline=False)
      if not wait_for_start_event.wait(TASK_STARTUP_WAIT):
        logging.error("Cron job run task for %s is too slow to start.",
                      job.cron_job_id)
        # Most likely the thread pool is full and the task is sitting on the
        # queue. Make sure we don't put more things on the queue by returning
        # False.
        return False

      # We know that the cron job task has started, unblock it by setting
      # the signal event. If signal_event is not set (this happens if the
      # task sits on a ThreadPool's queue doing nothing, see the
      # if-statement above) the task will just be a no-op when ThreadPool
      # finally gets to it. This way we can ensure that we can safely return
      # the lease and let another worker schedule the same job.
      signal_event.set()

      wait_for_write_event.wait(TASK_STARTUP_WAIT)

      return True
    except threadpool.Full:
      return False

  def JobIsRunning(self, job):
    """Returns True if there's a currently running iteration of this job."""
    return bool(job.current_run_id)

  def JobDueToRun(self, job):
    """Determines if the given job is due for another run.

    Args:
      job: The cron job rdfvalue object.

    Returns:
      True if it is time to run based on the specified frequency.
    """
    if not job.enabled:
      return False

    if job.forced_run_requested:
      return True

    now = rdfvalue.RDFDatetime.Now()

    if (job.last_run_time is not None and
        job.last_run_time + job.frequency > now):
      return False

    # No currently executing job - lets go.
    if not job.current_run_id:
      return True

    # There is a job executing but we allow overruns.
    if job.allow_overruns:
      return True

    return False

  def DeleteOldRuns(self, cutoff_timestamp=None):
    """Deletes runs that were started before the timestamp given."""
    if cutoff_timestamp is None:
      raise ValueError("cutoff_timestamp can't be None")

    return data_store.REL_DB.DeleteOldCronJobRuns(
        cutoff_timestamp=cutoff_timestamp)


def ScheduleSystemCronJobs(names=None):
  """Schedules all system cron jobs."""

  errors = []
  disabled_classes = config.CONFIG["Cron.disabled_cron_jobs"]
  for name in disabled_classes:
    try:
      SystemCronJobRegistry.CronJobClassByName(name)
    except ValueError:
      errors.append("Cron job not found: %s." % name)
      continue

  if names is None:
    names = SystemCronJobRegistry.SYSTEM_CRON_REGISTRY.keys()

  for name in names:
    cls = SystemCronJobRegistry.CronJobClassByName(name)

    enabled = cls.enabled and name not in disabled_classes
    system = rdf_cronjobs.CronJobAction.ActionType.SYSTEM_CRON_ACTION
    args = rdf_cronjobs.CronJobAction(
        action_type=system,
        system_cron_action=rdf_cronjobs.SystemCronAction(job_class_name=name))

    job = rdf_cronjobs.CronJob(
        cron_job_id=name,
        args=args,
        enabled=enabled,
        frequency=cls.frequency,
        lifetime=cls.lifetime,
        allow_overruns=cls.allow_overruns)
    data_store.REL_DB.WriteCronJob(job)

  if errors:
    raise ValueError("Error(s) while parsing Cron.disabled_cron_jobs: %s" %
                     errors)


class CronWorker(object):
  """CronWorker runs a thread that periodically executes cron jobs."""

  def __init__(self, thread_name="grr_cron", sleep=60 * 5):
    self.thread_name = thread_name
    self.sleep = sleep

  def _RunLoop(self):
    ScheduleSystemCronJobs()

    while True:
      try:
        CronManager().RunOnce()
      except Exception as e:  # pylint: disable=broad-except
        logging.error("CronWorker uncaught exception: %s", e)

      time.sleep(self.sleep)

  def Run(self):
    """Runs a working thread and waits for it to finish."""
    self.RunAsync().join()

  def RunAsync(self):
    """Runs a working thread and returns immediately."""
    self.running_thread = threading.Thread(
        name=self.thread_name, target=self._RunLoop)
    self.running_thread.daemon = True
    self.running_thread.start()
    return self.running_thread


_cron_worker = None


@utils.RunOnce
def InitializeCronWorkerOnce():
  """Init hook for cron job worker."""
  global _cron_worker
  # Start the cron thread if configured to.
  if config.CONFIG["Cron.active"]:
    _cron_worker = CronWorker()
    _cron_worker.RunAsync()


class RunHunt(CronJobBase):
  """A cron job that starts a hunt."""

  def Run(self):
    hra = self.job.args.hunt_cron_action.hunt_runner_args
    anbpcl = hra.avg_network_bytes_per_client_limit
    hunt.CreateAndStartHunt(
        self.job.args.hunt_cron_action.flow_name,
        self.job.args.hunt_cron_action.flow_args,
        CRON_JOB_USERNAME,
        avg_cpu_seconds_per_client_limit=hra.avg_cpu_seconds_per_client_limit,
        avg_network_bytes_per_client_limit=anbpcl,
        avg_results_per_client_limit=hra.avg_results_per_client_limit,
        client_limit=hra.client_limit,
        client_rate=hra.client_rate,
        client_rule_set=hra.client_rule_set,
        crash_limit=hra.crash_limit,
        description=hra.description,
        duration=rdfvalue.Duration(hra.expiry_time),
        original_object=hra.original_object,
        output_plugins=hra.output_plugins,
        per_client_cpu_limit=hra.per_client_cpu_limit,
        per_client_network_bytes_limit=hra.per_client_network_limit_bytes,
    )
