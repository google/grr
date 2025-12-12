#!/usr/bin/env python
"""The in memory database methods for cron job handling."""

from collections.abc import Sequence
from typing import Optional

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_proto import flows_pb2
from grr_response_proto import objects_pb2
from grr_response_server.databases import db


class InMemoryDBCronJobMixin(object):
  """InMemoryDB mixin for cronjob related functions."""

  # Maps cron_job_id to cron_job
  cronjobs: dict[str, flows_pb2.CronJob]
  # Maps cron_job_id to (leased_until_ms, leased_by)
  cronjob_leases: dict[str, tuple[int, str]]
  # Maps (cron_job_id, run_id) to cron_job_run
  cronjob_runs: dict[tuple[str, str], flows_pb2.CronJobRun]
  approvals_by_username: dict[str, dict[str, objects_pb2.ApprovalRequest]]

  @utils.Synchronized
  def WriteCronJob(self, cronjob: flows_pb2.CronJob) -> None:
    """Writes a cronjob to the database."""
    proto_clone = flows_pb2.CronJob()
    proto_clone.CopyFrom(cronjob)
    self.cronjobs[cronjob.cron_job_id] = proto_clone

  @utils.Synchronized
  def ReadCronJobs(
      self, cronjob_ids: Optional[Sequence[str]] = None
  ) -> Sequence[flows_pb2.CronJob]:
    """Reads a cronjob from the database."""
    if cronjob_ids is None:
      res = []
      for job in self.cronjobs.values():
        job_copy = flows_pb2.CronJob()
        job_copy.CopyFrom(job)
        res.append(job_copy)
    else:
      res = []
      for job_id in cronjob_ids:
        try:
          job_copy = flows_pb2.CronJob()
          job_copy.CopyFrom(self.cronjobs[job_id])
          res.append(job_copy)
        except KeyError as e:
          raise db.UnknownCronJobError(
              f"Cron job with id {job_id} not found."
          ) from e

    for job in res:
      lease = self.cronjob_leases.get(job.cron_job_id)
      if lease:
        job.leased_until, job.leased_by = lease
    return res

  @utils.Synchronized
  def UpdateCronJob(
      self,
      cronjob_id,
      last_run_status=db.Database.UNCHANGED,
      last_run_time=db.Database.UNCHANGED,
      current_run_id=db.Database.UNCHANGED,
      state=db.Database.UNCHANGED,
      forced_run_requested=db.Database.UNCHANGED,
  ):
    """Updates run information for an existing cron job."""
    job = self.cronjobs.get(cronjob_id)
    if job is None:
      raise db.UnknownCronJobError(f"Cron job {cronjob_id} not known.")

    if last_run_status != db.Database.UNCHANGED:
      job.last_run_status = last_run_status
    if last_run_time != db.Database.UNCHANGED:
      job.last_run_time = last_run_time.AsMicrosecondsSinceEpoch()
    if current_run_id != db.Database.UNCHANGED:
      if current_run_id is None:
        job.ClearField("current_run_id")
      else:
        job.current_run_id = current_run_id
    if state != db.Database.UNCHANGED:
      job.state.CopyFrom(state)
    if forced_run_requested != db.Database.UNCHANGED:
      job.forced_run_requested = forced_run_requested

  @utils.Synchronized
  def EnableCronJob(self, cronjob_id: str) -> None:
    """Enables a cronjob."""
    job = self.cronjobs.get(cronjob_id)
    if job is None:
      raise db.UnknownCronJobError(f"Cron job {cronjob_id} not known.")
    job.enabled = True

  @utils.Synchronized
  def DisableCronJob(self, cronjob_id: str) -> None:
    """Disables a cronjob."""
    job = self.cronjobs.get(cronjob_id)
    if job is None:
      raise db.UnknownCronJobError(f"Cron job {cronjob_id} not known.")
    job.enabled = False

  @utils.Synchronized
  def DeleteCronJob(self, cronjob_id: str) -> None:
    """Deletes a cronjob along with all its runs."""
    if cronjob_id not in self.cronjobs:
      raise db.UnknownCronJobError(f"Cron job {cronjob_id} not known.")
    del self.cronjobs[cronjob_id]
    try:
      del self.cronjob_leases[cronjob_id]
    except KeyError:
      pass
    for job_run in self.ReadCronJobRuns(cronjob_id):
      del self.cronjob_runs[(cronjob_id, job_run.run_id)]

    # TODO: Use protos in approvals.
    for approvals in self.approvals_by_username.values():
      # We use `list` around dictionary items iterator to avoid errors about
      # dictionary modification during iteration.
      for approval_id, approval in list(approvals.items()):
        if (
            approval.approval_type
            != objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CRON_JOB
        ):
          continue
        if approval.subject_id != cronjob_id:
          continue
        del approvals[approval_id]

  @utils.Synchronized
  def LeaseCronJobs(
      self,
      cronjob_ids: Optional[Sequence[str]] = None,
      lease_time: Optional[rdfvalue.Duration] = None,
  ) -> Sequence[flows_pb2.CronJob]:
    """Leases all available cron jobs."""
    leased_jobs = []

    now = rdfvalue.RDFDatetime.Now()
    expiration_time = now + lease_time

    for job in self.cronjobs.values():
      if cronjob_ids and job.cron_job_id not in cronjob_ids:
        continue
      existing_lease = self.cronjob_leases.get(job.cron_job_id)
      if (
          existing_lease is None
          or existing_lease[0] < now.AsMicrosecondsSinceEpoch()
      ):
        self.cronjob_leases[job.cron_job_id] = (
            expiration_time.AsMicrosecondsSinceEpoch(),
            utils.ProcessIdString(),
        )
        clone = flows_pb2.CronJob()
        clone.CopyFrom(job)
        clone.leased_until, clone.leased_by = self.cronjob_leases[
            job.cron_job_id
        ]
        leased_jobs.append(clone)

    return leased_jobs

  @utils.Synchronized
  def ReturnLeasedCronJobs(self, jobs: Sequence[flows_pb2.CronJob]) -> None:
    """Makes leased cron jobs available for leasing again."""
    errored_jobs = []

    for returned_job in jobs:
      existing_lease = self.cronjob_leases.get(returned_job.cron_job_id)
      if existing_lease is None:
        errored_jobs.append(returned_job)
        continue

      if (
          returned_job.leased_until != existing_lease[0]
          or returned_job.leased_by != existing_lease[1]
      ):
        errored_jobs.append(returned_job)
        continue

      del self.cronjob_leases[returned_job.cron_job_id]

    if errored_jobs:
      raise ValueError(
          "Some jobs could not be returned: %s"
          % ",".join(job.cron_job_id for job in errored_jobs)
      )

  @utils.Synchronized
  def WriteCronJobRun(self, run_object: flows_pb2.CronJobRun) -> None:
    """Stores a cron job run object in the database."""
    if run_object.cron_job_id not in self.cronjobs:
      raise db.UnknownCronJobError(
          f"Job with id {run_object.cron_job_id} not found."
      )

    clone = flows_pb2.CronJobRun()
    clone.CopyFrom(run_object)
    clone.created_at = rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()
    self.cronjob_runs[(clone.cron_job_id, clone.run_id)] = clone

  @utils.Synchronized
  def ReadCronJobRuns(self, job_id: str) -> Sequence[flows_pb2.CronJobRun]:
    """Reads all cron job runs for a given job id."""
    runs = []
    for run in self.cronjob_runs.values():
      if run.cron_job_id == job_id:
        clone = flows_pb2.CronJobRun()
        clone.CopyFrom(run)
        runs.append(clone)
    return sorted(runs, key=lambda run: run.created_at, reverse=True)

  @utils.Synchronized
  def ReadCronJobRun(self, job_id: str, run_id: str) -> flows_pb2.CronJobRun:
    """Reads a single cron job run from the db."""
    for run in self.cronjob_runs.values():
      if run.cron_job_id == job_id and run.run_id == run_id:
        return run
    raise db.UnknownCronJobRunError(
        f"Run with job id {job_id} and run id {run_id} not found."
    )

  @utils.Synchronized
  def DeleteOldCronJobRuns(self, cutoff_timestamp):
    """Deletes cron job runs for a given job id."""
    deleted = 0
    for run in list(self.cronjob_runs.values()):
      if run.created_at < cutoff_timestamp:
        del self.cronjob_runs[(run.cron_job_id, run.run_id)]
        deleted += 1

    return deleted
