#!/usr/bin/env python
"""A module with cronjobs methods of the Spanner backend."""

import datetime
from typing import Any, Mapping, Optional, Sequence

from google.api_core.exceptions import NotFound
from google.cloud import spanner as spanner_lib

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import spanner_utils

_UNCHANGED = db.Database.UNCHANGED


class CronJobsMixin:
  """A Spanner database mixin with implementation of cronjobs."""

  db: spanner_utils.Database

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteCronJob(self, cronjob: flows_pb2.CronJob) -> None:
    """Writes a cronjob to the database.

    Args:
      cronjob: A flows_pb2.CronJob object.
    """
    # We currently expect to reuse `created_at` if set.
    rdf_created_at = rdfvalue.RDFDatetime().FromMicrosecondsSinceEpoch(
        cronjob.created_at
    )
    creation_time = rdf_created_at.AsDatetime() or spanner_lib.COMMIT_TIMESTAMP

    row = {
        "JobId": cronjob.cron_job_id,
        "Job": cronjob,
        "Enabled": bool(cronjob.enabled),
        "CreationTime": creation_time,
    }

    self.db.InsertOrUpdate(table="CronJobs", row=row, txn_tag="WriteCronJob")

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadCronJobs(
      self, cronjob_ids: Optional[Sequence[str]] = None
  ) -> Sequence[flows_pb2.CronJob]:
    """Reads all cronjobs from the database.

    Args:
      cronjob_ids: A list of cronjob ids to read. If not set, returns all cron
        jobs in the database.

    Returns:
      A list of flows_pb2.CronJob objects.

    Raises:
      UnknownCronJobError: A cron job for at least one of the given ids
                           does not exist.
    """
    where_ids = ""
    params = {}
    if cronjob_ids:
      where_ids = " WHERE cj.JobId IN UNNEST(@cronjob_ids)"
      params["cronjob_ids"] = cronjob_ids

    def Transaction(txn) -> Sequence[flows_pb2.CronJob]:
      return self._SelectCronJobsWith(txn, where_ids, params)

    res = self.db.Transact(Transaction, txn_tag="ReadCronJobs")

    if cronjob_ids and len(res) != len(cronjob_ids):
      missing = set(cronjob_ids) - set([c.cron_job_id for c in res])
      raise db.UnknownCronJobError(
          "CronJob(s) with id(s) %s not found." % missing
      )
    return res

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def UpdateCronJob(  # pytype: disable=annotation-type-mismatch
      self,
      cronjob_id: str,
      last_run_status: Optional[
          "flows_pb2.CronJobRun.CronJobRunStatus"
      ] = _UNCHANGED,
      last_run_time: Optional[rdfvalue.RDFDatetime] = _UNCHANGED,
      current_run_id: Optional[str] = _UNCHANGED,
      state: Optional[jobs_pb2.AttributedDict] = _UNCHANGED,
      forced_run_requested: Optional[bool] = _UNCHANGED,
  ):
    """Updates run information for an existing cron job.

    Args:
      cronjob_id: The id of the cron job to update.
      last_run_status: A CronJobRunStatus object.
      last_run_time: The last time a run was started for this cron job.
      current_run_id: The id of the currently active run.
      state: The state dict for stateful cron jobs.
      forced_run_requested: A boolean indicating if a forced run is pending for
        this job.

    Raises:
      UnknownCronJobError: A cron job with the given id does not exist.
    """
    row = {"JobId": cronjob_id}
    if last_run_status is not _UNCHANGED:
      row["LastRunStatus"] = int(last_run_status)
    if last_run_time is not _UNCHANGED:
      row["LastRunTime"] = (
          last_run_time.AsDatetime() if last_run_time else last_run_time
      )
    if current_run_id is not _UNCHANGED:
      row["CurrentRunId"] = current_run_id
    if state is not _UNCHANGED:
      row["State"] = state if state is not None else None
    if forced_run_requested is not _UNCHANGED:
      row["ForcedRunRequested"] = forced_run_requested

    try:
      self.db.Update("CronJobs", row=row, txn_tag="UpdateCronJob")
    except NotFound as error:
      raise db.UnknownCronJobError(cronjob_id) from error

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def EnableCronJob(self, cronjob_id: str) -> None:
    """Enables a cronjob.

    Args:
      cronjob_id: The id of the cron job to enable.

    Raises:
      UnknownCronJobError: A cron job with the given id does not exist.
    """
    row = {
        "JobId": cronjob_id,
        "Enabled": True,
    }
    try:
      self.db.Update("CronJobs", row=row, txn_tag="EnableCronJob")
    except NotFound as error:
      raise db.UnknownCronJobError(cronjob_id) from error


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DisableCronJob(self, cronjob_id: str) -> None:
    """Deletes a cronjob along with all its runs.

    Args:
      cronjob_id: The id of the cron job to delete.

    Raises:
      UnknownCronJobError: A cron job with the given id does not exist.
    """
    row = {
        "JobId": cronjob_id,
        "Enabled": False,
    }
    try:
      self.db.Update("CronJobs", row=row, txn_tag="DisableCronJob")
    except NotFound as error:
      raise db.UnknownCronJobError(cronjob_id) from error

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DeleteCronJob(self, cronjob_id: str) -> None:
    """Deletes a cronjob along with all its runs.

    Args:
      cronjob_id: The id of the cron job to delete.

    Raises:
      UnknownCronJobError: A cron job with the given id does not exist.
    """
    def Transaction(txn) -> None:
      # Spanner does not raise if we attempt to delete a non-existing row so
      # we check it exists ourselves.
      keyset = spanner_lib.KeySet(keys=[[cronjob_id]])
      try:
        txn.read(table="CronJobs", keyset=keyset, columns=['JobId']).one()
      except NotFound as error:
        raise db.UnknownCronJobError(cronjob_id) from error

      txn.delete(table="CronJobs", keyset=keyset)

    self.db.Transact(Transaction, txn_tag="DeleteCronJob")


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def LeaseCronJobs(
      self,
      cronjob_ids: Optional[Sequence[str]] = None,
      lease_time: Optional[rdfvalue.Duration] = None,
  ) -> Sequence[flows_pb2.CronJob]:
    """Leases all available cron jobs.

    Args:
      cronjob_ids: A list of cronjob ids that should be leased. If None, all
        available cronjobs will be leased.
      lease_time: rdfvalue.Duration indicating how long the lease should be
        valid.

    Returns:
      A list of cronjobs.CronJob objects that were leased.
    """

    # We can't simply Update the rows because `UPDATE ... SET` will not return
    # the affected rows. So, this transaction is broken up in three parts:
    # 1. Identify the rows that will be updated
    # 2. Update these rows with the new lease information
    # 3. Read back the affected rows and return them
    def Transaction(txn) -> Sequence[flows_pb2.CronJob]:
      now = rdfvalue.RDFDatetime.Now()
      lease_end_time = now + lease_time
      lease_owner = utils.ProcessIdString()

      # ---------------------------------------------------------------------
      # Query IDs to be updated on this transaction
      # ---------------------------------------------------------------------
      query_ids_to_update = """
      SELECT cj.JobId
        FROM CronJobs as cj
       WHERE (cj.LeaseEndTime IS NULL OR cj.LeaseEndTime < @now)
      """
      params_ids_to_update = {"now": now.AsDatetime()}

      if cronjob_ids:
        query_ids_to_update += "AND cj.JobId IN UNNEST(@cronjob_ids)"
        params_ids_to_update["cronjob_ids"] = cronjob_ids

      response = txn.execute_sql(sql=query_ids_to_update, params=params_ids_to_update,
                                request_options={"request_tag": "LeaseCronJobs:CronJobs:execute_sql"})

      ids_to_update = []
      for (job_id,) in response:
        ids_to_update.append(job_id)

      if not ids_to_update:
        return []

      # ---------------------------------------------------------------------
      # Effectively update them with this process as owner
      # ---------------------------------------------------------------------
      update_query = """
      UPDATE CronJobs as cj
      SET cj.LeaseEndTime = @lease_end_time, cj.LeaseOwner = @lease_owner
      WHERE cj.JobId IN UNNEST(@ids_to_update)
      """
      update_params = {
          "lease_end_time": lease_end_time.AsDatetime(),
          "lease_owner": lease_owner,
          "ids_to_update": ids_to_update,
      }

      txn.execute_update(update_query, update_params,
                         request_options={"request_tag": "LeaseCronJobs:CronJobs:execute_update"})

      # ---------------------------------------------------------------------
      # Query (and return) jobs that were updated
      # ---------------------------------------------------------------------
      where_updated = """
       WHERE (cj.LeaseOwner = @lease_owner)
         AND cj.JobId IN UNNEST(@updated_ids)
      """
      updated_params = {
          "lease_owner": lease_owner,
          "updated_ids": ids_to_update,
      }

      return self._SelectCronJobsWith(txn, where_updated, updated_params)

    return self.db.Transact(Transaction, txn_tag="LeaseCronJobs")

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReturnLeasedCronJobs(self, jobs: Sequence[flows_pb2.CronJob]) -> None:
    """Makes leased cron jobs available for leasing again.

    Args:
      jobs: A list of leased cronjobs.

    Raises:
      ValueError: If not all of the cronjobs are leased.
    """
    if not jobs:
      return

    # Identify jobs that are not lease (cannot be returned). If there are any
    # leased jobs that need returning, then we'll go ahead and try to update
    # them anyway.
    unleased_jobs = []
    conditions = []
    jobs_to_update_args = {}
    for i, job in enumerate(jobs):
      if not job.leased_by or not job.leased_until:
        unleased_jobs.append(job)
        continue

      conditions.append(
          "(cj.JobId=@job_%d AND "
          "cj.LeaseEndTime=@ld_%d AND "
          "cj.LeaseOwner=@lo_%d)" % (i, i, i)
      )
      dt_leased_until = (
          rdfvalue.RDFDatetime()
          .FromMicrosecondsSinceEpoch(job.leased_until)
          .AsDatetime()
      )
      jobs_to_update_args[i] = (
          job.cron_job_id,
          dt_leased_until,
          job.leased_by,
      )

    if not conditions:  # all jobs are unleased.
      raise ValueError("CronJobs to return are not leased: %s" % unleased_jobs)

    # We can't simply Update the rows because `UPDATE ... SET` will not return
    # the affected rows. We need both the _already_ disabled jobs and the
    # updated rows in order to raise the appropriate exceptions.
    # 1. Identify the rows that need to be updated
    # 2. Update the relevant rows with the new unlease information
    # 3. Read back the affected rows and return them
    def Transaction(txn) -> Sequence[flows_pb2.CronJob]:
      # ---------------------------------------------------------------------
      # Query IDs to be updated on this transaction
      # ---------------------------------------------------------------------
      query_job_ids_to_return = """
      SELECT cj.JobId
        FROM CronJobs as cj
      """
      params_job_ids_to_return = {}
      query_job_ids_to_return += "WHERE" + " OR ".join(conditions)
      for i, (job_id, ld, lo) in jobs_to_update_args.items():
        params_job_ids_to_return["job_%d" % i] = job_id
        params_job_ids_to_return["ld_%d" % i] = ld
        params_job_ids_to_return["lo_%d" % i] = lo

      response = txn.execute_sql(
          query_job_ids_to_return, params_job_ids_to_return
      )

      ids_to_return = []
      for (job_id,) in response:
        ids_to_return.append(job_id)

      if not ids_to_return:
        return []

      # ---------------------------------------------------------------------
      # Effectively update them, removing owners
      # ---------------------------------------------------------------------
      update_query = """
      UPDATE CronJobs as cj
      SET cj.LeaseEndTime = NULL, cj.LeaseOwner = NULL
      WHERE cj.JobId IN UNNEST(@ids_to_return)
      """
      update_params = {
          "ids_to_return": ids_to_return,
      }

      txn.execute_update(update_query, update_params,
                         request_options={"request_tag": "ReturnLeasedCronJobs:CronJobs:execute_update"})

      # ---------------------------------------------------------------------
      # Query (and return) jobs that were updated
      # ---------------------------------------------------------------------
      where_returned = """
       WHERE cj.JobId IN UNNEST(@updated_ids)
      """
      returned_params = {
          "updated_ids": ids_to_return,
      }

      returned_jobs = self._SelectCronJobsWith(
          txn, where_returned, returned_params
      )

      return returned_jobs

    returned_jobs = self.db.Transact(
        Transaction, txn_tag="ReturnLeasedCronJobs"
    )
    if unleased_jobs:
      raise ValueError("CronJobs to return are not leased: %s" % unleased_jobs)
    if len(returned_jobs) != len(jobs):
      raise ValueError(
          "%d cronjobs in %s could not be returned. Successfully returned: %s"
          % ((len(jobs) - len(returned_jobs)), jobs, returned_jobs)
      )

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteCronJobRun(self, run_object: flows_pb2.CronJobRun) -> None:
    """Stores a cron job run object in the database.

    Args:
      run_object: A flows_pb2.CronJobRun object to store.
    """
    # If created_at is set, we use that instead of the commit timestamp.
    # This is important for overriding timestamps in testing. Ideally, we would
    # have a better/easier way to mock CommitTimestamp instead.
    if run_object.started_at:
      creation_time = (
          rdfvalue.RDFDatetime()
          .FromMicrosecondsSinceEpoch(run_object.started_at)
          .AsDatetime()
      )
    else:
      creation_time = spanner_lib.COMMIT_TIMESTAMP

    row = {
        "JobId": run_object.cron_job_id,
        "RunId": run_object.run_id,
        "CreationTime": creation_time,
        "Payload": run_object,
        "Status": int(run_object.status) or 0,
    }
    if run_object.finished_at:
      row["FinishTime"] = (
          rdfvalue.RDFDatetime()
          .FromMicrosecondsSinceEpoch(run_object.finished_at)
          .AsDatetime()
      )
    if run_object.log_message:
      row["LogMessage"] = run_object.log_message
    if run_object.backtrace:
      row["Backtrace"] = run_object.backtrace

    try:
      self.db.InsertOrUpdate(
          table="CronJobRuns", row=row, txn_tag="WriteCronJobRun"
      )
    except Exception as error:
      if "Parent row for row [" in str(error):
        # This error can be raised only when the parent cron job does not exist.
        message = f"Cron job with id '{run_object.cron_job_id}' not found."
        raise db.UnknownCronJobError(message) from error
      else:
        raise

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadCronJobRuns(self, job_id: str) -> Sequence[flows_pb2.CronJobRun]:
    """Reads all cron job runs for a given job id.

    Args:
      job_id: Runs will be returned for the job with the given id.

    Returns:
      A list of flows_pb2.CronJobRun objects.
    """
    cols = [
        "Payload",
        "JobId",
        "RunId",
        "CreationTime",
        "FinishTime",
        "Status",
        "LogMessage",
        "Backtrace",
    ]
    rowrange = spanner_lib.KeyRange(start_closed=[job_id], end_closed=[job_id])
    rows = spanner_lib.KeySet(ranges=[rowrange])

    res = []
    for row in self.db.ReadSet(table="CronJobRuns",
                               rows=rows,
                               cols=cols,
                               txn_tag="ReadCronJobRuns"):
      res.append(
          _CronJobRunFromRow(
              job_run=row[0],
              job_id=row[1],
              run_id=row[2],
              creation_time=row[3],
              finish_time=row[4],
              status=row[5],
              log_message=row[6],
              backtrace=row[7],
          )
      )

    return sorted(res, key=lambda run: run.started_at or 0, reverse=True)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadCronJobRun(self, job_id: str, run_id: str) -> flows_pb2.CronJobRun:
    """Reads a single cron job run from the db.

    Args:
      job_id: The job_id of the run to be read.
      run_id: The run_id of the run to be read.

    Returns:
      An flows_pb2.CronJobRun object.
    """
    cols = [
        "Payload",
        "JobId",
        "RunId",
        "CreationTime",
        "FinishTime",
        "Status",
        "LogMessage",
        "Backtrace",
    ]
    try:
      row = self.db.Read(table="CronJobRuns",
                         key=(job_id, run_id),
                         cols=cols,
                         txn_tag="ReadCronJobRun")
    except NotFound as error:
      raise db.UnknownCronJobRunError(
          "Run with job id %s and run id %s not found." % (job_id, run_id)
      ) from error

    return _CronJobRunFromRow(
        job_run=row[0],
        job_id=row[1],
        run_id=row[2],
        creation_time=row[3],
        finish_time=row[4],
        status=row[5],
        log_message=row[6],
        backtrace=row[7],
    )

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DeleteOldCronJobRuns(self, cutoff_timestamp: rdfvalue.RDFDatetime) -> int:
    """Deletes cron job runs that are older than cutoff_timestamp.

    Args:
      cutoff_timestamp: This method deletes all runs that were started before
        cutoff_timestamp.

    Returns:
      The number of deleted runs.
    """
    query = """
    SELECT cjr.JobId, cjr.RunId
      FROM CronJobRuns AS cjr
     WHERE cjr.CreationTime < @cutoff_timestamp
    """
    params = {"cutoff_timestamp": cutoff_timestamp.AsDatetime()}

    def Transaction(txn) -> int:
      rows = list(txn.execute_sql(sql=query, params=params))

      for job_id, run_id in rows:
        keyset = spanner_lib.KeySet(keys=[[job_id, run_id]])
        
        txn.delete(table="CronJobRuns", keyset=keyset,
                   request_options={"request_tag": "DeleteOldCronJobRuns:CronJobRuns:delete"})

      return len(rows)

    return self.db.Transact(Transaction, txn_tag="DeleteOldCronJobRuns").value

  def _SelectCronJobsWith(
      self,
      txn,
      where_clause: str,
      params: Mapping[str, Any],
  ) -> Sequence[flows_pb2.CronJob]:
    """Reads rows within the transaction and converts results into CronJobs.

    Args:
      txn: a transaction that will param query and return a cursor for the rows.
      where_clause: where clause for filtering the rows.
      params: params to be applied to the where_clause.

    Returns:
      A list of CronJobs read from the database.
    """

    query = """
    SELECT cj.Job, cj.JobId, cj.CreationTime, cj.Enabled,
           cj.ForcedRunRequested, cj.LastRunStatus, cj.LastRunTime,
           cj.CurrentRunId, cj.State, cj.LeaseEndTime, cj.LeaseOwner
      FROM CronJobs as cj
    """
    query += where_clause

    response = txn.execute_sql(sql=query, params=params)

    res = []
    for row in response:
      (
          job,
          job_id,
          creation_time,
          enabled,
          forced_run_requested,
          last_run_status,
          last_run_time,
          current_run_id,
          state,
          lease_end_time,
          lease_owner,
      ) = row
      res.append(
          _CronJobFromRow(
              job=job,
              job_id=job_id,
              creation_time=creation_time,
              enabled=enabled,
              forced_run_requested=forced_run_requested,
              last_run_status=last_run_status,
              last_run_time=last_run_time,
              current_run_id=current_run_id,
              state=state,
              lease_end_time=lease_end_time,
              lease_owner=lease_owner,
          )
      )

    return res


def _CronJobFromRow(
    job: Optional[bytes] = None,
    job_id: Optional[str] = None,
    creation_time: Optional[datetime.datetime] = None,
    enabled: Optional[bool] = None,
    forced_run_requested: Optional[bool] = None,
    last_run_status: Optional[int] = None,
    last_run_time: Optional[datetime.datetime] = None,
    current_run_id: Optional[str] = None,
    state: Optional[bytes] = None,
    lease_end_time: Optional[datetime.datetime] = None,
    lease_owner: Optional[str] = None,
) -> flows_pb2.CronJob:
  """Creates a CronJob object from a database result row."""

  if job is not None:
    parsed = flows_pb2.CronJob()
    parsed.ParseFromString(job)
    job = parsed
  else:
    job = flows_pb2.CronJob(
        created_at=rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch(),
    )

  if job_id is not None:
    job.cron_job_id = job_id
  if current_run_id is not None:
    job.current_run_id = current_run_id
  if enabled is not None:
    job.enabled = enabled
  if forced_run_requested is not None:
    job.forced_run_requested = forced_run_requested
  if last_run_status is not None:
    job.last_run_status = last_run_status
  if last_run_time is not None:
    job.last_run_time = rdfvalue.RDFDatetime.FromDatetime(
        last_run_time
    ).AsMicrosecondsSinceEpoch()
  if state is not None:
    read_state = jobs_pb2.AttributedDict()
    read_state.ParseFromString(state)
    job.state.CopyFrom(read_state)
  if creation_time is not None:
    job.created_at = rdfvalue.RDFDatetime.FromDatetime(
        creation_time
    ).AsMicrosecondsSinceEpoch()
  if lease_end_time is not None:
    job.leased_until = rdfvalue.RDFDatetime.FromDatetime(
        lease_end_time
    ).AsMicrosecondsSinceEpoch()
  if lease_owner is not None:
    job.leased_by = lease_owner

  return job

def _CronJobRunFromRow(
    job_run: Optional[bytes] = None,
    job_id: Optional[str] = None,
    run_id: Optional[str] = None,
    creation_time: Optional[datetime.datetime] = None,
    finish_time: Optional[datetime.datetime] = None,
    status: Optional[int] = None,
    log_message: Optional[str] = None,
    backtrace: Optional[str] = None,
) -> flows_pb2.CronJobRun:
  """Creates a CronJobRun object from a database result row."""

  if job_run is not None:
    parsed = flows_pb2.CronJobRun()
    parsed.ParseFromString(job_run)
    job_run = parsed
  else:
    job_run = flows_pb2.CronJobRun()

  if job_id is not None:
    job_run.cron_job_id = job_id
  if run_id is not None:
    job_run.run_id = run_id
  if creation_time is not None:
    job_run.created_at = rdfvalue.RDFDatetime.FromDatetime(
        creation_time
    ).AsMicrosecondsSinceEpoch()
  if finish_time is not None:
    job_run.finished_at = rdfvalue.RDFDatetime.FromDatetime(
        finish_time
    ).AsMicrosecondsSinceEpoch()
  if status is not None:
    job_run.status = status
  if log_message is not None:
    job_run.log_message = log_message
  if backtrace is not None:
    job_run.backtrace = backtrace

  return job_run