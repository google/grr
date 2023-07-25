#!/usr/bin/env python
"""The MySQL database methods for cron job handling."""

import MySQLdb

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import mysql_utils
from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs
from grr_response_server.rdfvalues import objects as rdf_objects


class MySQLDBCronJobMixin(object):
  """MySQLDB mixin for cronjob related functions."""

  @mysql_utils.WithTransaction()
  def WriteCronJob(self, cronjob, cursor=None):
    """Writes a cronjob to the database."""
    query = ("INSERT INTO cron_jobs "
             "(job_id, job, create_time, enabled) "
             "VALUES (%s, %s, FROM_UNIXTIME(%s), %s) "
             "ON DUPLICATE KEY UPDATE "
             "enabled=VALUES(enabled)")

    create_time_str = mysql_utils.RDFDatetimeToTimestamp(
        cronjob.created_at or rdfvalue.RDFDatetime.Now())
    cursor.execute(query, [
        cronjob.cron_job_id,
        cronjob.SerializeToBytes(), create_time_str, cronjob.enabled
    ])

  def _CronJobFromRow(self, row):
    """Creates a cronjob object from a database result row."""
    (job, create_time, enabled, forced_run_requested, last_run_status,
     last_run_time, current_run_id, state, leased_until, leased_by) = row

    job = rdf_cronjobs.CronJob.FromSerializedBytes(job)
    job.current_run_id = db_utils.IntToCronJobRunID(current_run_id)
    job.enabled = enabled
    job.forced_run_requested = forced_run_requested
    job.last_run_status = last_run_status
    job.last_run_time = mysql_utils.TimestampToRDFDatetime(last_run_time)
    if state:
      job.state = rdf_protodict.AttributedDict.FromSerializedBytes(state)
    job.created_at = mysql_utils.TimestampToRDFDatetime(create_time)
    job.leased_until = mysql_utils.TimestampToRDFDatetime(leased_until)
    job.leased_by = leased_by
    return job

  @mysql_utils.WithTransaction(readonly=True)
  def ReadCronJobs(self, cronjob_ids=None, cursor=None):
    """Reads all cronjobs from the database."""
    query = ("SELECT job, UNIX_TIMESTAMP(create_time), enabled, "
             "forced_run_requested, last_run_status, "
             "UNIX_TIMESTAMP(last_run_time), current_run_id, state, "
             "UNIX_TIMESTAMP(leased_until), leased_by "
             "FROM cron_jobs")
    if cronjob_ids is None:
      cursor.execute(query)
      return [self._CronJobFromRow(row) for row in cursor.fetchall()]

    query += " WHERE job_id IN (%s)" % ", ".join(["%s"] * len(cronjob_ids))
    cursor.execute(query, cronjob_ids)
    res = []
    for row in cursor.fetchall():
      res.append(self._CronJobFromRow(row))

    if len(res) != len(cronjob_ids):
      missing = set(cronjob_ids) - set([c.cron_job_id for c in res])
      raise db.UnknownCronJobError("CronJob(s) with id(s) %s not found." %
                                   missing)
    return res

  def _SetCronEnabledBit(self, cronjob_id, enabled, cursor=None):
    res = cursor.execute(
        "UPDATE cron_jobs SET enabled=%d WHERE job_id=%%s" % int(enabled),
        [cronjob_id])
    if res != 1:
      raise db.UnknownCronJobError("CronJob with id %s not found." % cronjob_id)

  @mysql_utils.WithTransaction()
  def EnableCronJob(self, cronjob_id, cursor=None):
    self._SetCronEnabledBit(cronjob_id, True, cursor=cursor)

  @mysql_utils.WithTransaction()
  def DisableCronJob(self, cronjob_id, cursor=None):
    self._SetCronEnabledBit(cronjob_id, False, cursor=cursor)

  @mysql_utils.WithTransaction()
  def DeleteCronJob(self, cronjob_id, cursor=None):
    """Deletes a cronjob along with all its runs."""
    res = cursor.execute("DELETE FROM cron_jobs WHERE job_id=%s", [cronjob_id])
    if res != 1:
      raise db.UnknownCronJobError("CronJob with id %s not found." % cronjob_id)

    query = """
    DELETE
      FROM approval_request
     WHERE approval_type = %(approval_type)s
       AND subject_id = %(cron_job_id)s
    """
    args = {
        "approval_type": int(
            rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CRON_JOB
        ),
        "cron_job_id": cronjob_id,
    }
    cursor.execute(query, args)

  @mysql_utils.WithTransaction()
  def UpdateCronJob(self,
                    cronjob_id,
                    last_run_status=db.Database.unchanged,
                    last_run_time=db.Database.unchanged,
                    current_run_id=db.Database.unchanged,
                    state=db.Database.unchanged,
                    forced_run_requested=db.Database.unchanged,
                    cursor=None):
    """Updates run information for an existing cron job."""
    updates = []
    args = []
    if last_run_status != db.Database.unchanged:
      updates.append("last_run_status=%s")
      args.append(int(last_run_status))
    if last_run_time != db.Database.unchanged:
      updates.append("last_run_time=FROM_UNIXTIME(%s)")
      args.append(mysql_utils.RDFDatetimeToTimestamp(last_run_time))
    if current_run_id != db.Database.unchanged:
      updates.append("current_run_id=%s")
      args.append(db_utils.CronJobRunIDToInt(current_run_id))
    if state != db.Database.unchanged:
      updates.append("state=%s")
      args.append(state.SerializeToBytes())
    if forced_run_requested != db.Database.unchanged:
      updates.append("forced_run_requested=%s")
      args.append(forced_run_requested)

    if not updates:
      return

    query = "UPDATE cron_jobs SET "
    query += ", ".join(updates)
    query += " WHERE job_id=%s"
    res = cursor.execute(query, args + [cronjob_id])
    if res != 1:
      raise db.UnknownCronJobError("CronJob with id %s not found." % cronjob_id)

  @mysql_utils.WithTransaction()
  def LeaseCronJobs(self, cronjob_ids=None, lease_time=None, cursor=None):
    """Leases all available cron jobs."""
    now = rdfvalue.RDFDatetime.Now()
    now_str = mysql_utils.RDFDatetimeToTimestamp(now)
    expiry_str = mysql_utils.RDFDatetimeToTimestamp(now + lease_time)
    id_str = utils.ProcessIdString()

    query = ("UPDATE cron_jobs "
             "SET leased_until=FROM_UNIXTIME(%s), leased_by=%s "
             "WHERE (leased_until IS NULL OR leased_until < FROM_UNIXTIME(%s))")
    args = [expiry_str, id_str, now_str]

    if cronjob_ids:
      query += " AND job_id in (%s)" % ", ".join(["%s"] * len(cronjob_ids))
      args += cronjob_ids

    updated = cursor.execute(query, args)

    if updated == 0:
      return []

    cursor.execute(
        "SELECT job, UNIX_TIMESTAMP(create_time), enabled,"
        "forced_run_requested, last_run_status, UNIX_TIMESTAMP(last_run_time), "
        "current_run_id, state, UNIX_TIMESTAMP(leased_until), leased_by "
        "FROM cron_jobs "
        "FORCE INDEX (cron_jobs_by_lease) "
        "WHERE leased_until=FROM_UNIXTIME(%s) AND leased_by=%s",
        [expiry_str, id_str])
    return [self._CronJobFromRow(row) for row in cursor.fetchall()]

  @mysql_utils.WithTransaction()
  def ReturnLeasedCronJobs(self, jobs, cursor=None):
    """Makes leased cron jobs available for leasing again."""
    if not jobs:
      return

    unleased_jobs = []

    conditions = []
    args = []
    for job in jobs:
      if not job.leased_by or not job.leased_until:
        unleased_jobs.append(job)
        continue

      conditions.append("""
      (job_id = %s AND leased_until = FROM_UNIXTIME(%s) AND leased_by = %s)
      """)
      args += [
          job.cron_job_id,
          mysql_utils.RDFDatetimeToTimestamp(job.leased_until), job.leased_by
      ]

    if conditions:
      query = ("UPDATE cron_jobs "
               "SET leased_until=NULL, leased_by=NULL "
               "WHERE ") + " OR ".join(conditions)
      returned = cursor.execute(query, args)

    if unleased_jobs:
      raise ValueError("CronJobs to return are not leased: %s" % unleased_jobs)
    if returned != len(jobs):
      raise ValueError("%d cronjobs in %s could not be returned." %
                       ((len(jobs) - returned), jobs))

  @mysql_utils.WithTransaction()
  def WriteCronJobRun(self, run_object, cursor=None):
    """Stores a cron job run object in the database."""
    query = ("INSERT INTO cron_job_runs "
             "(job_id, run_id, write_time, run) "
             "VALUES (%s, %s, FROM_UNIXTIME(%s), %s) "
             "ON DUPLICATE KEY UPDATE "
             "run=VALUES(run), write_time=VALUES(write_time)")

    write_time_str = mysql_utils.RDFDatetimeToTimestamp(
        rdfvalue.RDFDatetime.Now())
    try:
      cursor.execute(query, [
          run_object.cron_job_id,
          db_utils.CronJobRunIDToInt(run_object.run_id),
          write_time_str,
          run_object.SerializeToBytes(),
      ])
    except MySQLdb.IntegrityError as e:
      raise db.UnknownCronJobError(
          "CronJob with id %s not found." % run_object.cron_job_id, cause=e)

  def _CronJobRunFromRow(self, row):
    serialized_run, timestamp = row
    res = rdf_cronjobs.CronJobRun.FromSerializedBytes(serialized_run)
    res.timestamp = mysql_utils.TimestampToRDFDatetime(timestamp)
    return res

  @mysql_utils.WithTransaction()
  def ReadCronJobRuns(self, job_id, cursor=None):
    """Reads all cron job runs for a given job id."""
    query = """
    SELECT run, UNIX_TIMESTAMP(write_time)
      FROM cron_job_runs
     WHERE job_id = %s
    """
    cursor.execute(query, [job_id])
    runs = [self._CronJobRunFromRow(row) for row in cursor.fetchall()]
    return sorted(runs, key=lambda run: run.started_at or 0, reverse=True)

  @mysql_utils.WithTransaction()
  def ReadCronJobRun(self, job_id, run_id, cursor=None):
    """Reads a single cron job run from the db."""
    query = ("SELECT run, UNIX_TIMESTAMP(write_time) FROM cron_job_runs "
             "WHERE job_id = %s AND run_id = %s")
    num_runs = cursor.execute(
        query, [job_id, db_utils.CronJobRunIDToInt(run_id)])
    if num_runs == 0:
      raise db.UnknownCronJobRunError(
          "Run with job id %s and run id %s not found." % (job_id, run_id))

    return self._CronJobRunFromRow(cursor.fetchall()[0])

  @mysql_utils.WithTransaction()
  def DeleteOldCronJobRuns(self, cutoff_timestamp, cursor=None):
    """Deletes cron job runs that are older then the given timestamp."""
    query = "DELETE FROM cron_job_runs WHERE write_time < FROM_UNIXTIME(%s)"
    cursor.execute(query,
                   [mysql_utils.RDFDatetimeToTimestamp(cutoff_timestamp)])
