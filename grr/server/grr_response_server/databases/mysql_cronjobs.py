#!/usr/bin/env python
"""The MySQL database methods for cron job handling."""

from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.server.grr_response_server import db
from grr.server.grr_response_server.databases import mysql_utils
from grr.server.grr_response_server.rdfvalues import cronjobs as rdf_cronjobs


class MySQLDBCronjobMixin(object):
  """MySQLDBC mixin for cronjob related functions."""

  @mysql_utils.WithTransaction()
  def WriteCronJob(self, cronjob, cursor=None):
    query = ("INSERT IGNORE INTO cron_jobs "
             "(job_id, job, create_time, disabled) "
             "VALUES (%s, %s, %s, %s)")

    create_time_str = mysql_utils.RDFDatetimeToMysqlString(
        cronjob.create_time or rdfvalue.RDFDatetime.Now())
    cursor.execute(query, [
        cronjob.job_id,
        cronjob.SerializeToString(), create_time_str, cronjob.disabled
    ])

  def _CronjobFromRow(self, row):
    """Creates a cronjob object from a database result row."""
    (job, create_time, disabled, last_run_status, last_run_time, current_run_id,
     state, leased_until, leased_by) = row
    job = rdf_cronjobs.CronJob.FromSerializedString(job)
    job.current_run_id = current_run_id
    job.disabled = disabled
    job.last_run_status = last_run_status
    job.last_run_time = mysql_utils.MysqlToRDFDatetime(last_run_time)
    if state:
      job.state = rdf_protodict.AttributedDict.FromSerializedString(state)
    job.create_time = mysql_utils.MysqlToRDFDatetime(create_time)
    job.leased_until = mysql_utils.MysqlToRDFDatetime(leased_until)
    job.leased_by = leased_by
    return job

  @mysql_utils.WithTransaction(readonly=True)
  def ReadCronJobs(self, cronjob_ids=None, cursor=None):
    """Reads all cronjobs from the database."""
    query = ("SELECT job, create_time, disabled, "
             "last_run_status, last_run_time, current_run_id, state, "
             "leased_until, leased_by "
             "FROM cron_jobs")
    if cronjob_ids is None:
      cursor.execute(query)
      return [self._CronjobFromRow(row) for row in cursor.fetchall()]

    query += " WHERE job_id IN (%s)" % ", ".join(["%s"] * len(cronjob_ids))
    cursor.execute(query, cronjob_ids)
    res = []
    for row in cursor.fetchall():
      res.append(self._CronjobFromRow(row))

    if len(res) != len(cronjob_ids):
      missing = set(cronjob_ids) - set([c.job_id for c in res])
      raise db.UnknownCronjobError(
          "Cronjob(s) with id(s) %s not found." % missing)
    return res

  def _SetCronDisabledBit(self, cronjob_id, disabled, cursor=None):
    res = cursor.execute(
        "UPDATE cron_jobs SET disabled=%d WHERE job_id=%%s" % int(disabled),
        [cronjob_id])
    if res != 1:
      raise db.UnknownCronjobError("Cronjob with id %s not found." % cronjob_id)

  @mysql_utils.WithTransaction()
  def EnableCronJob(self, cronjob_id, cursor=None):
    self._SetCronDisabledBit(cronjob_id, False, cursor=cursor)

  @mysql_utils.WithTransaction()
  def DisableCronJob(self, cronjob_id, cursor=None):
    self._SetCronDisabledBit(cronjob_id, True, cursor=cursor)

  @mysql_utils.WithTransaction()
  def DeleteCronJob(self, cronjob_id, cursor=None):
    res = cursor.execute("DELETE FROM cron_jobs WHERE job_id=%s", [cronjob_id])
    if res != 1:
      raise db.UnknownCronjobError("Cronjob with id %s not found." % cronjob_id)

  @mysql_utils.WithTransaction()
  def UpdateCronJob(self,
                    cronjob_id,
                    last_run_status=db.Database.unchanged,
                    last_run_time=db.Database.unchanged,
                    current_run_id=db.Database.unchanged,
                    state=db.Database.unchanged,
                    cursor=None):
    """Updates run information for an existing cron job."""
    updates = []
    args = []
    if last_run_status != db.Database.unchanged:
      updates.append("last_run_status=%s")
      args.append(int(last_run_status))
    if last_run_time != db.Database.unchanged:
      updates.append("last_run_time=%s")
      args.append(mysql_utils.RDFDatetimeToMysqlString(last_run_time))
    if current_run_id != db.Database.unchanged:
      updates.append("current_run_id=%s")
      args.append(current_run_id or 0)
    if state != db.Database.unchanged:
      updates.append("state=%s")
      args.append(state.SerializeToString())

    if not updates:
      return

    query = "UPDATE cron_jobs SET "
    query += ", ".join(updates)
    query += " WHERE job_id=%s"
    res = cursor.execute(query, args + [cronjob_id])
    if res != 1:
      raise db.UnknownCronjobError("Cronjob with id %s not found." % cronjob_id)

  @mysql_utils.WithTransaction()
  def LeaseCronJobs(self, cronjob_ids=None, lease_time=None, cursor=None):
    """Leases all available cron jobs."""
    now = rdfvalue.RDFDatetime.Now()
    now_str = mysql_utils.RDFDatetimeToMysqlString(now)
    expiry_str = mysql_utils.RDFDatetimeToMysqlString(now + lease_time)
    id_str = utils.ProcessIdString()

    query = ("UPDATE cron_jobs "
             "SET leased_until=%s, leased_by=%s "
             "WHERE (leased_until IS NULL OR leased_until < %s)")
    args = [expiry_str, id_str, now_str]

    if cronjob_ids:
      query += " AND job_id in (%s)" % ", ".join(["%s"] * len(cronjob_ids))
      args += cronjob_ids

    updated = cursor.execute(query, args)

    if updated == 0:
      return []

    cursor.execute(
        "SELECT job, create_time, disabled, "
        "last_run_status, last_run_time, current_run_id, state, "
        "leased_until, leased_by "
        "FROM cron_jobs WHERE leased_until=%s AND leased_by=%s",
        [expiry_str, id_str])
    return [self._CronjobFromRow(row) for row in cursor.fetchall()]

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

      conditions.append("(job_id=%s AND leased_until=%s AND leased_by=%s)")
      args += [
          job.job_id,
          mysql_utils.RDFDatetimeToMysqlString(job.leased_until), job.leased_by
      ]

    if conditions:
      query = ("UPDATE cron_jobs "
               "SET leased_until=NULL, leased_by=NULL "
               "WHERE ") + " OR ".join(conditions)
      returned = cursor.execute(query, args)

    if unleased_jobs:
      raise ValueError("Cronjobs to return are not leased: %s" % unleased_jobs)
    if returned != len(jobs):
      raise ValueError("%d cronjobs in %s could not be returned." % (
          (len(jobs) - returned), jobs))
