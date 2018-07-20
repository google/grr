#!/usr/bin/env python
"""Mixin tests for storing cronjob objects in the relational db."""

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_server import db
from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs
from grr.test_lib import test_lib


class DatabaseTestCronjobMixin(object):

  def _CreateCronjob(self):
    return rdf_cronjobs.CronJob(
        cron_job_id="job_%s" % utils.PRNG.GetUInt16(), enabled=True)

  def testCronjobReading(self):
    job = self._CreateCronjob()
    self.db.WriteCronJob(job)

    res = self.db.ReadCronJob(job.cron_job_id)
    self.assertEqual(res, job)

    res = self.db.ReadCronJobs(cronjob_ids=[job.cron_job_id])
    self.assertEqual(len(res), 1)
    self.assertEqual(res[0], job)

    res = self.db.ReadCronJobs()
    self.assertEqual(len(res), 1)
    self.assertEqual(res[0], job)

  def testDuplicateWriting(self):
    job = self._CreateCronjob()
    self.db.WriteCronJob(job)
    self.db.WriteCronJob(job)

  def testUnknownIDs(self):
    job = self._CreateCronjob()

    with self.assertRaises(db.UnknownCronjobError):
      self.db.ReadCronJob("Does not exist")

    with self.assertRaises(db.UnknownCronjobError):
      self.db.ReadCronJobs(["Does not exist"])

    with self.assertRaises(db.UnknownCronjobError):
      self.db.ReadCronJobs([job.cron_job_id, "Does not exist"])

  def testCronjobUpdates(self):
    job = self._CreateCronjob()
    job.last_run_status = rdf_cronjobs.CronJobRun.CronJobRunStatus.FINISHED
    self.db.WriteCronJob(job)

    err = rdf_cronjobs.CronJobRun.CronJobRunStatus.ERROR
    self.db.UpdateCronJob(job.cron_job_id, last_run_status=err)

    new_job = self.db.ReadCronJob(job.cron_job_id)
    self.assertEqual(job.last_run_status, "FINISHED")
    self.assertEqual(new_job.last_run_status, "ERROR")

    t = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1000000)
    self.db.UpdateCronJob(job.cron_job_id, last_run_time=t)
    new_job = self.db.ReadCronJob(job.cron_job_id)
    self.assertEqual(new_job.last_run_time, t)

    self.db.UpdateCronJob(job.cron_job_id, current_run_id="ABCD1234")
    new_job = self.db.ReadCronJob(job.cron_job_id)
    self.assertEqual(new_job.current_run_id, "ABCD1234")

    # None is accepted to clear the current_run_id.
    self.db.UpdateCronJob(job.cron_job_id, current_run_id=None)
    new_job = self.db.ReadCronJob(job.cron_job_id)
    self.assertFalse(new_job.current_run_id)

    state = job.state
    self.assertNotIn("test", state)
    state["test"] = 12345
    self.db.UpdateCronJob(job.cron_job_id, state=state)
    new_job = self.db.ReadCronJob(job.cron_job_id)
    self.assertEqual(new_job.state.get("test"), 12345)

    self.db.UpdateCronJob(job.cron_job_id, forced_run_requested=True)
    new_job = self.db.ReadCronJob(job.cron_job_id)
    self.assertEqual(new_job.forced_run_requested, True)

    with self.assertRaises(db.UnknownCronjobError):
      self.db.UpdateCronJob("Does not exist", current_run_id="12345678")

  def testCronjobDeletion(self):
    job = self._CreateCronjob()
    self.db.WriteCronJob(job)

    self.db.ReadCronJob(job.cron_job_id)
    self.db.DeleteCronJob(job.cron_job_id)
    with self.assertRaises(db.UnknownCronjobError):
      self.db.ReadCronJob(job.cron_job_id)

  def testCronjobEnabling(self):
    job = self._CreateCronjob()
    self.db.WriteCronJob(job)

    self.assertTrue(job.enabled)

    self.db.DisableCronJob(job.cron_job_id)
    new_job = self.db.ReadCronJob(job.cron_job_id)
    self.assertFalse(new_job.enabled)

    self.db.EnableCronJob(job.cron_job_id)
    new_job = self.db.ReadCronJob(job.cron_job_id)
    self.assertTrue(new_job.enabled)

    with self.assertRaises(db.UnknownCronjobError):
      self.db.EnableCronJob("Does not exist")

    with self.assertRaises(db.UnknownCronjobError):
      self.db.DisableCronJob("Does not exist")

  def testCronjobLeasing(self):
    job = self._CreateCronjob()
    self.db.WriteCronJob(job)

    current_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10000)
    lease_time = rdfvalue.Duration("5m")
    with test_lib.FakeTime(current_time):
      leased = self.db.LeaseCronJobs(lease_time=lease_time)
      self.assertEqual(len(leased), 1)
      leased_job = leased[0]
      self.assertTrue(leased_job.leased_by)
      self.assertEqual(leased_job.leased_until, current_time + lease_time)

    with test_lib.FakeTime(current_time + rdfvalue.Duration("1m")):
      leased = self.db.LeaseCronJobs(lease_time=lease_time)
      self.assertFalse(leased)

    with test_lib.FakeTime(current_time + rdfvalue.Duration("6m")):
      leased = self.db.LeaseCronJobs(lease_time=lease_time)
      self.assertEqual(len(leased), 1)
      leased_job = leased[0]
      self.assertTrue(leased_job.leased_by)
      self.assertEqual(leased_job.leased_until,
                       current_time + rdfvalue.Duration("6m") + lease_time)

  def testCronjobLeasingByID(self):
    jobs = [self._CreateCronjob() for _ in range(3)]
    for j in jobs:
      self.db.WriteCronJob(j)

    current_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10000)
    lease_time = rdfvalue.Duration("5m")
    with test_lib.FakeTime(current_time):
      leased = self.db.LeaseCronJobs(
          cronjob_ids=[job.cron_job_id for job in jobs[:2]],
          lease_time=lease_time)
      self.assertEqual(len(leased), 2)
      self.assertEqual(
          sorted([j.cron_job_id for j in leased]),
          sorted([j.cron_job_id for j in jobs[:2]]))

  def testCronjobReturning(self):
    job = self._CreateCronjob()
    self.db.WriteCronJob(job)
    leased_job = self._CreateCronjob()
    self.db.WriteCronJob(leased_job)

    with self.assertRaises(ValueError):
      self.db.ReturnLeasedCronJobs([job])

    current_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10000)
    with test_lib.FakeTime(current_time):
      leased = self.db.LeaseCronJobs(
          cronjob_ids=[leased_job.cron_job_id],
          lease_time=rdfvalue.Duration("5m"))
      self.assertTrue(leased)

    with test_lib.FakeTime(current_time + rdfvalue.Duration("1m")):
      self.db.ReturnLeasedCronJobs([leased[0]])

    returned_job = self.db.ReadCronJob(leased[0].cron_job_id)
    self.assertIsNone(returned_job.leased_by)
    self.assertIsNone(returned_job.leased_until)

  def testCronjobReturningMultiple(self):
    jobs = [self._CreateCronjob() for _ in range(3)]
    for job in jobs:
      self.db.WriteCronJob(job)

    current_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10000)
    with test_lib.FakeTime(current_time):
      leased = self.db.LeaseCronJobs(lease_time=rdfvalue.Duration("5m"))
      self.assertEqual(len(leased), 3)

    current_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10001)
    with test_lib.FakeTime(current_time):
      unleased_jobs = self.db.LeaseCronJobs(lease_time=rdfvalue.Duration("5m"))
      self.assertEqual(len(unleased_jobs), 0)

      self.db.ReturnLeasedCronJobs(leased)

    current_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10002)
    with test_lib.FakeTime(current_time):
      leased = self.db.LeaseCronJobs(lease_time=rdfvalue.Duration("5m"))
      self.assertEqual(len(leased), 3)
