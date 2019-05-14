#!/usr/bin/env python
"""Cron Job objects that get stored in the relational db."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import collections
import logging
import threading
import traceback

from future.utils import iterkeys

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib.util import random
from grr_response_core.stats import stats_collector_instance
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server import threadpool
from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs

# The maximum number of log-messages to store in the DB for a given cron-job
# run.
_MAX_LOG_MESSAGES = 20


class Error(Exception):
  pass


class OneOrMoreCronJobsFailedError(Error):

  def __init__(self, failure_map):
    message = "One or more cron jobs failed unexpectedly: " + ", ".join(
        "%s=%s" % (k, v) for k, v in failure_map.items())
    super(OneOrMoreCronJobsFailedError, self).__init__(message)
    self.failure_map = failure_map


class LockError(Error):
  pass


class LifetimeExceededError(Error):
  """Exception raised when a cronjob exceeds its max allowed runtime."""


class CronJobBase(object):
  """The base class for all cron jobs."""

  __metaclass__ = registry.CronJobRegistry

  __abstract = True  # pylint: disable=g-bad-name

  def __init__(self, run_state, job):
    self.run_state = run_state
    self.job = job
    self.token = access_control.ACLToken(username="Cron")

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
      stats_collector_instance.Get().IncrementCounter(
          "cron_job_failure", fields=[self.job.cron_job_id])
    except Exception as e:  # pylint: disable=broad-except
      logging.exception("Cronjob %s failed with an error: %s",
                        self.job.cron_job_id, e)
      stats_collector_instance.Get().IncrementCounter(
          "cron_job_failure", fields=[self.job.cron_job_id])
      self.run_state.status = "ERROR"
      self.run_state.backtrace = "{}\n\n{}".format(e, traceback.format_exc())

    finally:
      self.run_state.finished_at = rdfvalue.RDFDatetime.Now()
      elapsed = self.run_state.finished_at - self.run_state.started_at
      stats_collector_instance.Get().RecordEvent(
          "cron_job_latency", elapsed.seconds, fields=[self.job.cron_job_id])
      if self.job.lifetime:
        expiration_time = self.run_state.started_at + self.job.lifetime
        if self.run_state.finished_at > expiration_time:
          self.run_state.status = "LIFETIME_EXCEEDED"
          stats_collector_instance.Get().IncrementCounter(
              "cron_job_timeout", fields=[self.job.cron_job_id])
      data_store.REL_DB.WriteCronJobRun(self.run_state)

    current_job = data_store.REL_DB.ReadCronJob(self.job.cron_job_id)
    # If no other job was started while we were running, update last status
    # information.
    if current_job.current_run_id == self.run_state.run_id:
      data_store.REL_DB.UpdateCronJob(
          self.job.cron_job_id,
          current_run_id=None,
          last_run_status=self.run_state.status)


class SystemCronJobBase(CronJobBase):
  """The base class for all system cron jobs."""

  __metaclass__ = registry.SystemCronJobRegistry

  __abstract = True  # pylint: disable=g-bad-name

  frequency = None
  lifetime = None

  allow_overruns = False
  enabled = True

  def __init__(self, *args, **kw):
    super(SystemCronJobBase, self).__init__(*args, **kw)

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
    super(CronManager, self).__init__()

    if max_threads <= 0:
      raise ValueError("max_threads should be >= 1")

    self.max_threads = max_threads

  def CreateJob(self, cron_args=None, job_id=None, enabled=True, token=None):
    """Creates a cron job that runs given flow with a given frequency.

    Args:
      cron_args: A protobuf of type rdf_cronjobs.CreateCronJobArgs.
      job_id: Use this job_id instead of an autogenerated unique name (used for
        system cron jobs - we want them to have well-defined persistent name).
      enabled: If False, the job object will be created, but will be disabled.
      token: Security token used for data store access. Unused.

    Returns:
      URN of the cron job created.

    Raises:
      ValueError: This function expects an arg protobuf that starts a
                  CreateAndRunGenericHuntFlow flow. If the args specify
                  something else, ValueError is raised.
    """
    # TODO(amoser): Remove the token from this method once the aff4
    # cronjobs are gone.
    del token
    if not job_id:
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

  def ListJobs(self, token=None):
    """Returns a list of ids of all currently running cron jobs."""
    del token
    return [job.cron_job_id for job in data_store.REL_DB.ReadCronJobs()]

  def ReadJob(self, job_id, token=None):
    del token
    return data_store.REL_DB.ReadCronJob(job_id)

  def ReadJobs(self, token=None):
    """Returns a list of all currently running cron jobs."""
    del token
    return data_store.REL_DB.ReadCronJobs()

  def ReadJobRun(self, job_id, run_id, token=None):
    del token
    return data_store.REL_DB.ReadCronJobRun(job_id, run_id)

  def ReadJobRuns(self, job_id, token=None):
    del token
    return data_store.REL_DB.ReadCronJobRuns(job_id)

  def EnableJob(self, job_id, token=None):
    """Enable cron job with the given id."""
    del token
    return data_store.REL_DB.EnableCronJob(job_id)

  def DisableJob(self, job_id, token=None):
    """Disable cron job with the given id."""
    del token
    return data_store.REL_DB.DisableCronJob(job_id)

  def DeleteJob(self, job_id, token=None):
    """Deletes cron job with the given URN."""
    del token
    return data_store.REL_DB.DeleteCronJob(job_id)

  def RequestForcedRun(self, job_id):
    data_store.REL_DB.UpdateCronJob(job_id, forced_run_requested=True)

  def RunOnce(self, names=None, token=None):
    """Tries to lock and run cron jobs.

    Args:
      names: List of cron jobs to run.  If unset, run them all.
      token: security token.

    Raises:
      OneOrMoreCronJobsFailedError: if one or more individual cron jobs fail.
      Note: a failure of a single cron job doesn't preclude other cron jobs
      from running.
    """
    del token

    leased_jobs = data_store.REL_DB.LeaseCronJobs(
        cronjob_ids=names, lease_time=rdfvalue.Duration("10m"))
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
          job.last_run_time + job.lifetime + rdfvalue.Duration("10m"))
      if now > expiration_time:
        run = data_store.REL_DB.ReadCronJobRun(job.cron_job_id,
                                               job.current_run_id)
        run.status = "LIFETIME_EXCEEDED"
        run.finished_at = now
        data_store.REL_DB.WriteCronJobRun(run)
        data_store.REL_DB.UpdateCronJob(
            job.cron_job_id, current_run_id=None, last_run_status=run.status)
        stats_collector_instance.Get().RecordEvent(
            "cron_job_latency", (now - job.last_run_time).seconds,
            fields=[job.cron_job_id])
        stats_collector_instance.Get().IncrementCounter(
            "cron_job_timeout", fields=[job.cron_job_id])

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
      job_cls = registry.SystemCronJobRegistry.CronJobClassByName(cls_name)
      name = "%s runner" % cls_name
    elif job.args.action_type == job.args.ActionType.HUNT_CRON_ACTION:
      job_cls = registry.CronJobRegistry.CronJobClassByName("RunHunt")
      name = "Hunt runner"
    else:
      raise ValueError(
          "CronJob %s doesn't have a valid args type set." % job.cron_job_id)

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

  def JobIsRunning(self, job, token=None):
    """Returns True if there's a currently running iteration of this job."""
    del token
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
      cls = registry.SystemCronJobRegistry.CronJobClassByName(name)
    except ValueError:
      errors.append("Cron job not found: %s." % name)
      continue

  if names is None:
    names = iterkeys(registry.SystemCronJobRegistry.SYSTEM_CRON_REGISTRY)

  for name in names:

    cls = registry.SystemCronJobRegistry.CronJobClassByName(name)

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
    raise ValueError(
        "Error(s) while parsing Cron.disabled_cron_jobs: %s" % errors)
