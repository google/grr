#!/usr/bin/env python
"""Cron Job objects that get stored in the relational db."""

import logging

from grr.lib import rdfvalue
from grr.lib import stats
from grr.lib import utils
from grr.lib.rdfvalues import cronjobs as rdf_cronjobs
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server import flow
from grr.server.grr_response_server import queue_manager


class Error(Exception):
  pass


class LockError(Error):
  pass


class CronJob(object):
  """The cron job class."""

  def __init__(self,
               job_id=None,
               cron_args=None,
               current_run_id=None,
               disabled=None,
               last_run_status=None,
               last_run_time=None,
               start_time=None,
               state=None,
               token=None):
    self.job_id = job_id
    self.cron_args = cron_args
    self.current_run_id = current_run_id
    self.disabled = disabled
    self.last_run_status = last_run_status
    self.last_run_time = last_run_time
    self.start_time = start_time
    self.state = state
    self.token = token
    self.leased_until = None
    self.leased_by = None

  def DeleteRuns(self, age=None):
    """Deletes runs that were started before the age given."""
    if age is None:
      raise ValueError("age can't be None")

    runs_base = rdfvalue.RDFURN("aff4:/cron").Add(self.job_id)
    runs_base_obj = aff4.FACTORY.Open(runs_base, token=self.token)
    child_flows = list(runs_base_obj.ListChildren(age=age))
    with queue_manager.QueueManager(token=self.token) as queuemanager:
      queuemanager.MultiDestroyFlowStates(child_flows)

    aff4.FACTORY.MultiDelete(child_flows, token=self.token)

  def IsRunning(self):
    """Returns True if there's a currently running iteration of this job."""
    if not self.current_run_id:
      return False

    runs_base = rdfvalue.RDFURN("aff4:/cron").Add(self.job_id)
    run_urn = runs_base.Add("F:%X" % self.current_run_id)
    try:
      current_flow = aff4.FACTORY.Open(
          urn=run_urn, aff4_type=flow.GRRFlow, token=self.token, mode="r")
      return current_flow.GetRunner().IsRunning()

    except aff4.InstantiationError:
      # This isn't a flow, something went really wrong, clear it out.
      logging.error("Unable to open cron job run: %s", run_urn)
      data_store.REL_DB.UpdateCronJob(self.job_id, current_run_id=None)
      self.current_run_id = None
      return False

  def DueToRun(self):
    """Called periodically by the cron daemon, if True Run() will be called.

    Returns:
        True if it is time to run based on the specified frequency.
    """
    if self.disabled:
      return False

    now = rdfvalue.RDFDatetime.Now()

    # Its time to run.
    if (self.last_run_time is None or
        now > self.cron_args.periodicity.Expiry(self.last_run_time)):

      # Not due to start yet.
      if now < self.cron_args.start_time:
        return False

      # Do we allow overruns?
      if self.cron_args.allow_overruns:
        return True

      # No currently executing job - lets go.
      if self.current_run_id is None:
        return True

    return False

  def StopCurrentRun(self, reason="Cron lifetime exceeded.", force=True):
    """Stops the currently active run if there is one."""
    if not self.current_run_id:
      return

    runs_base = rdfvalue.RDFURN("aff4:/cron").Add(self.job_id)
    current_run_urn = runs_base.Add("F:%X" % self.current_run_id)
    flow.GRRFlow.TerminateFlow(
        current_run_urn, reason=reason, force=force, token=self.token)

    status = rdf_cronjobs.CronJobRunStatus(
        status=rdf_cronjobs.CronJobRunStatus.Status.TIMEOUT)
    data_store.REL_DB.UpdateCronJob(
        self.job_id, last_run_status=status, current_run_id=None)

  def TerminateExpiredRun(self):
    """Terminates the current run if it has exceeded CRON_ARGS.lifetime.

    Returns:
      bool: True if the run was terminate.
    """
    if not self.IsRunning():
      return False

    lifetime = self.cron_args.lifetime
    if not lifetime:
      return False

    elapsed = rdfvalue.RDFDatetime.Now() - self.last_run_time

    if elapsed > lifetime.seconds:
      self.StopCurrentRun()
      stats.STATS.IncrementCounter("cron_job_timeout", fields=[self.job_id])
      stats.STATS.RecordEvent("cron_job_latency", elapsed, fields=[self.job_id])
      return True

    return False

  def Run(self, force=False):
    """Do the actual work of the Cron. Will first check if DueToRun is True.

    CronJob object must be leased for Run() to be called.

    Args:
      force: If True, the job will run even if DueToRun() returns False.

    Raises:
      LockError: if the object is not locked.
    """
    if not self.leased_until or self.leased_until < rdfvalue.RDFDatetime.Now():
      raise LockError("CronJob must be leased for Run() to be called.")

    self.TerminateExpiredRun()

    # If currently running flow has finished, update our state.
    runs_base = rdfvalue.RDFURN("aff4:/cron").Add(self.job_id)
    if self.current_run_id:
      current_run_urn = runs_base.Add("F:%X" % self.current_run_id)
      current_flow = aff4.FACTORY.Open(current_run_urn, token=self.token)
      runner = current_flow.GetRunner()
      if not runner.IsRunning():
        if runner.context.state == "ERROR":
          status = rdf_cronjobs.CronJobRunStatus(
              status=rdf_cronjobs.CronJobRunStatus.Status.ERROR)
          stats.STATS.IncrementCounter("cron_job_failure", fields=[self.job_id])
        else:
          status = rdf_cronjobs.CronJobRunStatus(
              status=rdf_cronjobs.CronJobRunStatus.Status.OK)
          elapsed = rdfvalue.RDFDatetime.Now() - self.last_run_time
          stats.STATS.RecordEvent(
              "cron_job_latency", elapsed, fields=[self.job_id])

        data_store.REL_DB.UpdateCronJob(
            self.job_id, last_run_status=status, current_run_id=None)

    if not force and not self.DueToRun():
      return

    # Make sure the flow is created with cron job as a parent folder.
    self.cron_args.flow_runner_args.base_session_id = runs_base

    flow_urn = flow.GRRFlow.StartFlow(
        runner_args=self.cron_args.flow_runner_args,
        args=self.cron_args.flow_args,
        token=self.token,
        sync=False)

    self.current_run_id = int(flow_urn.Basename()[2:], 16)
    data_store.REL_DB.UpdateCronJob(
        self.job_id,
        last_run_time=rdfvalue.RDFDatetime.Now(),
        current_run_id=self.current_run_id)


class CronManager(object):
  """CronManager is used to schedule/terminate cron jobs."""

  def CreateJob(self, cron_args=None, job_id=None, token=None, disabled=False):
    """Creates a cron job that runs given flow with a given frequency.

    Args:
      cron_args: A protobuf of type CreateCronJobFlowArgs.

      job_id: Use this job_id instead of an autogenerated unique name (used
              for system cron jobs - we want them to have well-defined
              persistent name).

      token: Security token used for data store access.

      disabled: If True, the job object will be created, but will be disabled.

    Returns:
      URN of the cron job created.
    """
    if not job_id:
      uid = utils.PRNG.GetUInt16()
      job_id = "%s_%s" % (cron_args.flow_runner_args.flow_name, uid)

    job = CronJob(
        job_id=job_id,
        cron_args=cron_args,
        disabled=disabled,
        start_time=cron_args.start_time,
        token=token)
    data_store.REL_DB.WriteCronJob(job)

    return job_id

  def ListJobs(self, token=None):
    """Returns a list of ids of all currently running cron jobs."""
    del token
    return [job.job_id for job in data_store.REL_DB.ReadCronJobs()]

  def ReadJob(self, job_id, token=None):
    del token
    return data_store.REL_DB.ReadCronJob(job_id)

  def ReadJobs(self, token=None):
    """Returns a list of all currently running cron jobs."""
    del token
    return data_store.REL_DB.ReadCronJobs()

  def ReadJobRuns(self, job_id, token=None):
    runs_base = rdfvalue.RDFURN("aff4:/cron").Add(job_id)
    fd = aff4.FACTORY.Open(runs_base, token=token)
    return list(fd.OpenChildren())

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

  def RunOnce(self, token=None, force=False, names=None):
    """Tries to lock and run cron jobs.

    Args:
      token: security token.
      force: If True, force a run.
      names: List of cron jobs to run.  If unset, run them all.
    """
    leased_jobs = data_store.REL_DB.LeaseCronJobs(
        cronjob_ids=names, lease_time=600)
    if not leased_jobs:
      return

    for job in leased_jobs:
      job.token = token
      try:
        logging.info("Running cron job: %s", job.job_id)
        job.Run(force=force)
      except Exception:  # pylint: disable=broad-except
        logging.exception("Error processing cron job %s", job.job_id)
        stats.STATS.IncrementCounter("cron_internal_error")

    data_store.REL_DB.ReturnLeasedCronJobs(leased_jobs)
