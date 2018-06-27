#!/usr/bin/env python
"""The in memory database methods for cron job handling."""

from grr.lib import rdfvalue
from grr.lib import utils
from grr.server.grr_response_server import db


class InMemoryDBCronjobMixin(object):
  """InMemoryDB mixin for cronjob related functions."""

  @utils.Synchronized
  def WriteCronJob(self, cronjob):
    """Writes a cronjob to the database."""
    self.cronjobs[cronjob.job_id] = cronjob.Copy()

  @utils.Synchronized
  def ReadCronJobs(self, cronjob_ids=None):
    """Reads a cronjob from the database."""
    if cronjob_ids is None:
      res = [job.Copy() for job in self.cronjobs.values()]

    else:
      res = []
      for job_id in cronjob_ids:
        try:
          res.append(self.cronjobs[job_id].Copy())
        except KeyError:
          raise db.UnknownCronjobError(
              "Cron job with id %s not found." % job_id)

    for job in res:
      lease = self.cronjob_leases.get(job.job_id)
      if lease:
        job.leased_until, job.leased_by = lease
    return res

  @utils.Synchronized
  def UpdateCronJob(self,
                    cronjob_id,
                    last_run_status=db.Database.unchanged,
                    last_run_time=db.Database.unchanged,
                    current_run_id=db.Database.unchanged,
                    state=db.Database.unchanged):
    """Updates run information for an existing cron job."""
    job = self.cronjobs.get(cronjob_id)
    if job is None:
      raise db.UnknownCronjobError("Cron job %s not known." % cronjob_id)

    if last_run_status != db.Database.unchanged:
      job.last_run_status = last_run_status
    if last_run_time != db.Database.unchanged:
      job.last_run_time = last_run_time
    if current_run_id != db.Database.unchanged:
      job.current_run_id = current_run_id
    if state != db.Database.unchanged:
      job.state = state

  @utils.Synchronized
  def EnableCronJob(self, cronjob_id):
    """Enables a cronjob."""
    job = self.cronjobs.get(cronjob_id)
    if job is None:
      raise db.UnknownCronjobError("Cron job %s not known." % cronjob_id)
    job.disabled = False

  @utils.Synchronized
  def DisableCronJob(self, cronjob_id):
    """Disables a cronjob."""
    job = self.cronjobs.get(cronjob_id)
    if job is None:
      raise db.UnknownCronjobError("Cron job %s not known." % cronjob_id)
    job.disabled = True

  @utils.Synchronized
  def DeleteCronJob(self, cronjob_id):
    """Deletes a cronjob."""
    if cronjob_id not in self.cronjobs:
      raise db.UnknownCronjobError("Cron job %s not known." % cronjob_id)
    del self.cronjobs[cronjob_id]
    try:
      del self.cronjob_leases[cronjob_id]
    except KeyError:
      pass

  @utils.Synchronized
  def LeaseCronJobs(self, cronjob_ids=None, lease_time=None):
    """Leases all available cron jobs."""
    leased_jobs = []

    now = rdfvalue.RDFDatetime.Now()
    expiration_time = now + lease_time

    for job in self.cronjobs.values():
      if cronjob_ids and job.job_id not in cronjob_ids:
        continue
      existing_lease = self.cronjob_leases.get(job.job_id)
      if existing_lease is None or existing_lease[0] < now:
        self.cronjob_leases[job.job_id] = (expiration_time,
                                           utils.ProcessIdString())
        job = job.Copy()
        job.leased_until, job.leased_by = self.cronjob_leases[job.job_id]
        leased_jobs.append(job)

    return leased_jobs

  @utils.Synchronized
  def ReturnLeasedCronJobs(self, jobs):
    """Makes leased cron jobs available for leasing again."""
    errored_jobs = []

    for returned_job in jobs:
      existing_lease = self.cronjob_leases.get(returned_job.job_id)
      if existing_lease is None:
        errored_jobs.append(returned_job)
        continue

      if (returned_job.leased_until != existing_lease[0] or
          returned_job.leased_by != existing_lease[1]):
        errored_jobs.append(returned_job)
        continue

      del self.cronjob_leases[returned_job.job_id]

    if errored_jobs:
      raise ValueError("Some jobs could not be returned: %s" % ",".join(
          job.job_id for job in errored_jobs))
