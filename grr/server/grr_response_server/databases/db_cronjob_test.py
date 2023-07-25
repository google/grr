#!/usr/bin/env python
"""Mixin tests for storing cronjob objects in the relational db."""


from grr_response_core.lib import rdfvalue
from grr_response_core.lib.util import random
from grr_response_server.databases import db
from grr_response_server.databases import db_test_utils
from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import test_lib


class DatabaseTestCronJobMixin(object):

  def _CreateCronJob(self):
    return rdf_cronjobs.CronJob(
        cron_job_id="job_%s" % random.UInt16(), enabled=True)

  def testCronJobReading(self):
    job = self._CreateCronJob()
    self.db.WriteCronJob(job)

    res = self.db.ReadCronJob(job.cron_job_id)
    self.assertEqual(res, job)

    res = self.db.ReadCronJobs(cronjob_ids=[job.cron_job_id])
    self.assertLen(res, 1)
    self.assertEqual(res[0], job)

    res = self.db.ReadCronJobs()
    self.assertLen(res, 1)
    self.assertEqual(res[0], job)

  def testDuplicateWriting(self):
    job = self._CreateCronJob()
    self.db.WriteCronJob(job)
    self.db.WriteCronJob(job)

  def testUnknownIDs(self):
    job = self._CreateCronJob()

    with self.assertRaises(db.UnknownCronJobError):
      self.db.ReadCronJob("Does not exist")

    with self.assertRaises(db.UnknownCronJobError):
      self.db.ReadCronJobs(["Does not exist"])

    with self.assertRaises(db.UnknownCronJobError):
      self.db.ReadCronJobs([job.cron_job_id, "Does not exist"])

  def testCronJobUpdates(self):
    job = self._CreateCronJob()
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

    # To test `current_run_id` we first need to create a CronJobRun with it.
    job_run0 = rdf_cronjobs.CronJobRun(
        cron_job_id=job.cron_job_id, run_id="ABCD1234")
    self.db.WriteCronJobRun(job_run0)

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

    with self.assertRaises(db.UnknownCronJobError):
      self.db.UpdateCronJob("Does not exist", current_run_id="12345678")

  def testCronJobDeletion(self):
    job_id = "job0"
    self.db.WriteCronJob(rdf_cronjobs.CronJob(cron_job_id=job_id))
    job_run0 = rdf_cronjobs.CronJobRun(cron_job_id=job_id, run_id="a")
    job_run1 = rdf_cronjobs.CronJobRun(cron_job_id=job_id, run_id="b")
    self.db.WriteCronJobRun(job_run0)
    self.db.WriteCronJobRun(job_run1)
    self.assertLen(self.db.ReadCronJobRuns(job_id), 2)
    self.db.DeleteCronJob(job_id)
    with self.assertRaises(db.UnknownCronJobError):
      self.db.ReadCronJob(job_id)
    self.assertEmpty(self.db.ReadCronJobRuns(job_id))

  def testCronJobDeletion_UnknownJob(self):
    with self.assertRaises(db.UnknownCronJobError):
      self.db.DeleteCronJob("non-existent-id")

  def testDeleteCronJobWithApprovalRequest(self):
    creator = db_test_utils.InitializeUser(self.db)
    approver = db_test_utils.InitializeUser(self.db)
    cron_job_id = db_test_utils.InitializeCronJob(self.db)

    approval = rdf_objects.ApprovalRequest()
    approval.approval_type = (
        rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CRON_JOB
    )
    approval.requestor_username = creator
    approval.notified_users = [approver]
    approval.subject_id = cron_job_id
    approval.expiration_time = (
        rdfvalue.RDFDatetime.Now() + rdfvalue.Duration.From(1, rdfvalue.DAYS)
    )
    approval_id = self.db.WriteApprovalRequest(approval)

    self.db.DeleteCronJob(cron_job_id)

    with self.assertRaises(db.UnknownApprovalRequestError):
      self.db.ReadApprovalRequest(creator, approval_id)

  def testCronJobEnabling(self):
    job = self._CreateCronJob()
    self.db.WriteCronJob(job)

    self.assertTrue(job.enabled)

    self.db.DisableCronJob(job.cron_job_id)
    new_job = self.db.ReadCronJob(job.cron_job_id)
    self.assertFalse(new_job.enabled)

    self.db.EnableCronJob(job.cron_job_id)
    new_job = self.db.ReadCronJob(job.cron_job_id)
    self.assertTrue(new_job.enabled)

    with self.assertRaises(db.UnknownCronJobError):
      self.db.EnableCronJob("Does not exist")

    with self.assertRaises(db.UnknownCronJobError):
      self.db.DisableCronJob("Does not exist")

  def testCronJobOverwrite(self):
    job = self._CreateCronJob()
    self.db.WriteCronJob(job)

    read = self.db.ReadCronJob(job.cron_job_id)
    self.assertEqual(job.enabled, read.enabled)
    original_ca = read.created_at

    job.enabled = not job.enabled
    self.db.WriteCronJob(job)

    read = self.db.ReadCronJob(job.cron_job_id)
    self.assertEqual(job.enabled, read.enabled)

    self.assertEqual(read.created_at, original_ca)

  def testCronJobLeasing(self):
    job = self._CreateCronJob()
    self.db.WriteCronJob(job)

    current_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10000)
    lease_time = rdfvalue.Duration.From(5, rdfvalue.MINUTES)
    with test_lib.FakeTime(current_time):
      leased = self.db.LeaseCronJobs(lease_time=lease_time)
      self.assertLen(leased, 1)
      leased_job = leased[0]
      self.assertTrue(leased_job.leased_by)
      self.assertEqual(leased_job.leased_until, current_time + lease_time)

    with test_lib.FakeTime(current_time +
                           rdfvalue.Duration.From(1, rdfvalue.MINUTES)):
      leased = self.db.LeaseCronJobs(lease_time=lease_time)
      self.assertFalse(leased)

    with test_lib.FakeTime(current_time +
                           rdfvalue.Duration.From(6, rdfvalue.MINUTES)):
      leased = self.db.LeaseCronJobs(lease_time=lease_time)
      self.assertLen(leased, 1)
      leased_job = leased[0]
      self.assertTrue(leased_job.leased_by)
      self.assertEqual(
          leased_job.leased_until, current_time +
          rdfvalue.Duration.From(6, rdfvalue.MINUTES) + lease_time)

  def testCronJobLeasingByID(self):
    jobs = [self._CreateCronJob() for _ in range(3)]
    for j in jobs:
      self.db.WriteCronJob(j)

    current_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10000)
    lease_time = rdfvalue.Duration.From(5, rdfvalue.MINUTES)
    with test_lib.FakeTime(current_time):
      leased = self.db.LeaseCronJobs(
          cronjob_ids=[job.cron_job_id for job in jobs[:2]],
          lease_time=lease_time)
      self.assertLen(leased, 2)
      self.assertCountEqual([j.cron_job_id for j in leased],
                            [j.cron_job_id for j in jobs[:2]])

  def testCronJobReturning(self):
    job = self._CreateCronJob()
    self.db.WriteCronJob(job)
    leased_job = self._CreateCronJob()
    self.db.WriteCronJob(leased_job)

    with self.assertRaises(ValueError):
      self.db.ReturnLeasedCronJobs([job])

    current_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10000)
    with test_lib.FakeTime(current_time):
      leased = self.db.LeaseCronJobs(
          cronjob_ids=[leased_job.cron_job_id],
          lease_time=rdfvalue.Duration.From(5, rdfvalue.MINUTES))
      self.assertTrue(leased)

    with test_lib.FakeTime(current_time +
                           rdfvalue.Duration.From(1, rdfvalue.MINUTES)):
      self.db.ReturnLeasedCronJobs([leased[0]])

    returned_job = self.db.ReadCronJob(leased[0].cron_job_id)
    self.assertIsNone(returned_job.leased_by)
    self.assertIsNone(returned_job.leased_until)

  def testCronJobReturningMultiple(self):
    jobs = [self._CreateCronJob() for _ in range(3)]
    for job in jobs:
      self.db.WriteCronJob(job)

    current_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10000)
    with test_lib.FakeTime(current_time):
      leased = self.db.LeaseCronJobs(
          lease_time=rdfvalue.Duration.From(5, rdfvalue.MINUTES))
      self.assertLen(leased, 3)

    current_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10001)
    with test_lib.FakeTime(current_time):
      unleased_jobs = self.db.LeaseCronJobs(
          lease_time=rdfvalue.Duration.From(5, rdfvalue.MINUTES))
      self.assertEmpty(unleased_jobs)

      self.db.ReturnLeasedCronJobs(leased)

    current_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10002)
    with test_lib.FakeTime(current_time):
      leased = self.db.LeaseCronJobs(
          lease_time=rdfvalue.Duration.From(5, rdfvalue.MINUTES))
      self.assertLen(leased, 3)

  def testCronJobRuns(self):
    with self.assertRaises(db.UnknownCronJobError):
      self.db.WriteCronJobRun(
          rdf_cronjobs.CronJobRun(cron_job_id="job1", run_id="00000000"))

    before_writing = rdfvalue.RDFDatetime.Now()
    for j in range(1, 3):
      self.db.WriteCronJob(rdf_cronjobs.CronJob(cron_job_id="job%d" % j))
      for r in range(1, 3):
        run = rdf_cronjobs.CronJobRun(
            cron_job_id="job%d" % j, run_id="abcd123%d" % r)
        self.db.WriteCronJobRun(run)
    after_writing = rdfvalue.RDFDatetime.Now()

    for j in range(1, 3):
      job_id = "job%d" % j
      jobs = self.db.ReadCronJobRuns(job_id)
      self.assertLen(jobs, 2)
      for job in jobs:
        self.assertEqual(job.cron_job_id, job_id)
        self.assertBetween(job.timestamp, before_writing, after_writing)

    job = self.db.ReadCronJobRun("job1", "abcd1231")
    self.assertEqual(job.cron_job_id, "job1")
    self.assertEqual(job.run_id, "abcd1231")
    self.assertBetween(job.timestamp, before_writing, after_writing)

    with self.assertRaises(ValueError):
      self.db.ReadCronJobRun(job_id, "invalid_id")

    with self.assertRaises(db.UnknownCronJobRunError):
      self.db.ReadCronJobRun(job_id, "abcd1234")

    with self.assertRaises(db.UnknownCronJobRunError):
      self.db.ReadCronJobRun("doesntexist", "abcd1231")

    self.assertEqual(self.db.ReadCronJobRuns("doesntexist"), [])

  def testCronJobRunsOverwrite(self):
    self.db.WriteCronJob(rdf_cronjobs.CronJob(cron_job_id="job"))
    run = rdf_cronjobs.CronJobRun(cron_job_id="job", run_id="abcd1234")
    self.db.WriteCronJobRun(run)
    original_ts = self.db.ReadCronJobRun("job", "abcd1234").timestamp

    now = rdfvalue.RDFDatetime.Now()
    run.backtrace = "error"
    run.log_message = "log"
    run.started_at = now - rdfvalue.Duration.From(5, rdfvalue.SECONDS)
    run.finished_at = now
    self.db.WriteCronJobRun(run)

    read = self.db.ReadCronJobRun("job", "abcd1234")

    self.assertEqual(read.backtrace, run.backtrace)
    self.assertEqual(read.log_message, run.log_message)
    self.assertEqual(read.started_at, run.started_at)
    self.assertEqual(read.finished_at, run.finished_at)
    self.assertNotEqual(read.timestamp, original_ts)

  def testCronJobRunExpiry(self):
    job_id = "job1"
    self.db.WriteCronJob(rdf_cronjobs.CronJob(cron_job_id=job_id))

    fake_time = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration.From(
        7, rdfvalue.DAYS)
    with test_lib.FakeTime(fake_time):
      run = rdf_cronjobs.CronJobRun(
          cron_job_id=job_id, run_id="00000000", started_at=fake_time)
      self.db.WriteCronJobRun(run)

    fake_time_one_day_later = fake_time + rdfvalue.Duration.From(
        1, rdfvalue.DAYS)
    with test_lib.FakeTime(fake_time_one_day_later):
      run = rdf_cronjobs.CronJobRun(
          cron_job_id=job_id,
          run_id="00000001",
          started_at=fake_time_one_day_later)
      self.db.WriteCronJobRun(run)

    fake_time_two_days_later = fake_time + rdfvalue.Duration.From(
        2, rdfvalue.DAYS)
    with test_lib.FakeTime(fake_time_two_days_later):
      run = rdf_cronjobs.CronJobRun(
          cron_job_id=job_id,
          run_id="00000002",
          started_at=fake_time_two_days_later)
      self.db.WriteCronJobRun(run)

    self.assertLen(self.db.ReadCronJobRuns(job_id), 3)

    cutoff = fake_time + rdfvalue.Duration.From(1, rdfvalue.HOURS)
    self.db.DeleteOldCronJobRuns(cutoff)
    jobs = self.db.ReadCronJobRuns(job_id)
    self.assertLen(jobs, 2)
    for job in jobs:
      self.assertGreater(job.timestamp, cutoff)

    cutoff = fake_time + rdfvalue.Duration.From(25, rdfvalue.HOURS)
    self.db.DeleteOldCronJobRuns(cutoff)
    jobs = self.db.ReadCronJobRuns(job_id)
    self.assertLen(jobs, 1)
    for job in jobs:
      self.assertGreater(job.timestamp, cutoff)


# This file is a test library and thus does not require a __main__ block.
