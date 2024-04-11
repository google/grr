#!/usr/bin/env python
"""Mixin tests for storing cronjob objects in the relational db."""

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import mig_protodict
from grr_response_core.lib.util import random
from grr_response_proto import flows_pb2
from grr_response_server.databases import db
from grr_response_server.databases import db_test_utils
from grr_response_server.rdfvalues import mig_objects
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import test_lib


class DatabaseTestCronJobMixin(object):

  def _CreateCronJob(self):
    return flows_pb2.CronJob(
        cron_job_id=f"job_{random.UInt16()}",
        enabled=True,
        created_at=rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch(),
    )

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
    job.last_run_status = flows_pb2.CronJobRun.CronJobRunStatus.FINISHED
    self.db.WriteCronJob(job)

    err = flows_pb2.CronJobRun.CronJobRunStatus.ERROR
    self.db.UpdateCronJob(job.cron_job_id, last_run_status=err)

    new_job = self.db.ReadCronJob(job.cron_job_id)
    self.assertEqual(
        job.last_run_status, flows_pb2.CronJobRun.CronJobRunStatus.FINISHED
    )
    self.assertEqual(
        new_job.last_run_status, flows_pb2.CronJobRun.CronJobRunStatus.ERROR
    )

    t = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1000000)
    self.db.UpdateCronJob(job.cron_job_id, last_run_time=t)
    new_job = self.db.ReadCronJob(job.cron_job_id)
    self.assertEqual(new_job.last_run_time, t.AsMicrosecondsSinceEpoch())

    # To test `current_run_id` we first need to create a CronJobRun with it.
    job_run0 = flows_pb2.CronJobRun(
        cron_job_id=job.cron_job_id, run_id="ABCD1234"
    )
    self.db.WriteCronJobRun(job_run0)

    self.db.UpdateCronJob(job.cron_job_id, current_run_id="ABCD1234")
    new_job = self.db.ReadCronJob(job.cron_job_id)
    self.assertEqual(new_job.current_run_id, "ABCD1234")

    # None is accepted to clear the current_run_id.
    self.db.UpdateCronJob(job.cron_job_id, current_run_id=None)
    new_job = self.db.ReadCronJob(job.cron_job_id)
    self.assertFalse(new_job.current_run_id)

    # TODO: Stop using rdf_protodict.Dict below.
    state = mig_protodict.FromProtoAttributedDictToNativeDict(job.state)
    self.assertNotIn("test", state)
    state["test"] = 12345
    proto_state = mig_protodict.FromNativeDictToProtoAttributedDict(state)
    self.db.UpdateCronJob(job.cron_job_id, state=proto_state)
    new_job = self.db.ReadCronJob(job.cron_job_id)
    new_dict = mig_protodict.FromProtoAttributedDictToNativeDict(new_job.state)
    self.assertEqual(new_dict.get("test"), 12345)

    self.db.UpdateCronJob(job.cron_job_id, forced_run_requested=True)
    new_job = self.db.ReadCronJob(job.cron_job_id)
    self.assertEqual(new_job.forced_run_requested, True)

    with self.assertRaises(db.UnknownCronJobError):
      self.db.UpdateCronJob("Does not exist", current_run_id="12345678")

  def testCronJobDeletion(self):
    job_id = "job0"
    job = flows_pb2.CronJob(
        cron_job_id=job_id,
        created_at=rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch(),
    )
    self.db.WriteCronJob(job)
    job_run0 = flows_pb2.CronJobRun(cron_job_id=job_id, run_id="a")
    job_run1 = flows_pb2.CronJobRun(cron_job_id=job_id, run_id="b")
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
    # TODO: Stop using `mig_objects`.
    proto_approval = mig_objects.ToProtoApprovalRequest(approval)
    approval_id = self.db.WriteApprovalRequest(proto_approval)

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
    self.assertTrue(job.enabled)

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
      want_time = current_time + lease_time
      self.assertEqual(
          leased_job.leased_until,
          want_time.AsMicrosecondsSinceEpoch(),
      )

    with test_lib.FakeTime(
        current_time + rdfvalue.Duration.From(1, rdfvalue.MINUTES)
    ):
      leased = self.db.LeaseCronJobs(lease_time=lease_time)
      self.assertFalse(leased)

    with test_lib.FakeTime(
        current_time + rdfvalue.Duration.From(6, rdfvalue.MINUTES)
    ):
      leased = self.db.LeaseCronJobs(lease_time=lease_time)
      self.assertLen(leased, 1)
      leased_job = leased[0]
      self.assertTrue(leased_job.leased_by)
      want_time = (
          current_time
          + rdfvalue.Duration.From(6, rdfvalue.MINUTES)
          + lease_time
      )
      self.assertEqual(
          leased_job.leased_until,
          want_time.AsMicrosecondsSinceEpoch(),
      )

  def testCronJobLeasingByID(self):
    jobs = [self._CreateCronJob() for _ in range(3)]
    for j in jobs:
      self.db.WriteCronJob(j)

    current_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10000)
    lease_time = rdfvalue.Duration.From(5, rdfvalue.MINUTES)
    with test_lib.FakeTime(current_time):
      leased = self.db.LeaseCronJobs(
          cronjob_ids=[job.cron_job_id for job in jobs[:2]],
          lease_time=lease_time,
      )
      self.assertLen(leased, 2)
      self.assertCountEqual(
          [j.cron_job_id for j in leased], [j.cron_job_id for j in jobs[:2]]
      )

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
          lease_time=rdfvalue.Duration.From(5, rdfvalue.MINUTES),
      )
      self.assertTrue(leased)

    with test_lib.FakeTime(
        current_time + rdfvalue.Duration.From(1, rdfvalue.MINUTES)
    ):
      self.db.ReturnLeasedCronJobs([leased[0]])

    returned_job = self.db.ReadCronJob(leased[0].cron_job_id)
    self.assertFalse(returned_job.HasField("leased_by"))
    self.assertFalse(returned_job.HasField("leased_until"))

  def testCronJobReturningMultiple(self):
    jobs = [self._CreateCronJob() for _ in range(3)]
    for j in jobs:
      self.db.WriteCronJob(j)

    current_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10000)
    with test_lib.FakeTime(current_time):
      leased = self.db.LeaseCronJobs(
          lease_time=rdfvalue.Duration.From(5, rdfvalue.MINUTES)
      )
      self.assertLen(leased, 3)

    current_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10001)
    with test_lib.FakeTime(current_time):
      unleased_jobs = self.db.LeaseCronJobs(
          lease_time=rdfvalue.Duration.From(5, rdfvalue.MINUTES)
      )
      self.assertEmpty(unleased_jobs)

      self.db.ReturnLeasedCronJobs(leased)

    current_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10002)
    with test_lib.FakeTime(current_time):
      leased = self.db.LeaseCronJobs(
          lease_time=rdfvalue.Duration.From(5, rdfvalue.MINUTES)
      )
      self.assertLen(leased, 3)

  def testCronJobRuns(self):
    with self.assertRaises(db.UnknownCronJobError):
      self.db.WriteCronJobRun(
          flows_pb2.CronJobRun(cron_job_id="job1", run_id="00000000")
      )

    before_writing = rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()
    for j in range(1, 3):
      job = flows_pb2.CronJob(
          cron_job_id=f"job{j}",
          created_at=rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch(),
      )
      self.db.WriteCronJob(job)
      for r in range(1, 3):
        run = flows_pb2.CronJobRun(cron_job_id=f"job{j}", run_id=f"abcd123{r}")
        self.db.WriteCronJobRun(run)
    after_writing = rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()

    for j in range(1, 3):
      job_id = f"job{j}"
      runs = self.db.ReadCronJobRuns(job_id)
      self.assertLen(runs, 2)
      for run in runs:
        self.assertEqual(run.cron_job_id, job_id)
        self.assertBetween(run.created_at, before_writing, after_writing)

    run = self.db.ReadCronJobRun("job1", "abcd1231")
    self.assertEqual(run.cron_job_id, "job1")
    self.assertEqual(run.run_id, "abcd1231")
    self.assertBetween(run.created_at, before_writing, after_writing)

    with self.assertRaises(ValueError):
      self.db.ReadCronJobRun(job_id, "invalid_id")

    with self.assertRaises(db.UnknownCronJobRunError):
      self.db.ReadCronJobRun(job_id, "abcd1234")

    with self.assertRaises(db.UnknownCronJobRunError):
      self.db.ReadCronJobRun("doesntexist", "abcd1231")

    self.assertEqual(self.db.ReadCronJobRuns("doesntexist"), [])

  def testCronJobRunsOverwrite(self):
    job = flows_pb2.CronJob(
        cron_job_id="job",
        created_at=rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch(),
    )
    self.db.WriteCronJob(job)
    run = flows_pb2.CronJobRun(cron_job_id="job", run_id="abcd1234")
    self.db.WriteCronJobRun(run)
    original_ts = self.db.ReadCronJobRun("job", "abcd1234").created_at

    now = rdfvalue.RDFDatetime.Now()
    run.backtrace = "error"
    run.log_message = "log"
    run.started_at = (
        now - rdfvalue.Duration.From(5, rdfvalue.SECONDS)
    ).AsMicrosecondsSinceEpoch()
    run.finished_at = now.AsMicrosecondsSinceEpoch()
    self.db.WriteCronJobRun(run)

    read = self.db.ReadCronJobRun("job", "abcd1234")

    self.assertEqual(read.backtrace, run.backtrace)
    self.assertEqual(read.log_message, run.log_message)
    self.assertEqual(read.started_at, run.started_at)
    self.assertEqual(read.finished_at, run.finished_at)
    self.assertNotEqual(read.created_at, original_ts)

  def testCronJobRunExpiry(self):
    job_id = "job1"
    job = flows_pb2.CronJob(
        cron_job_id=job_id,
        created_at=rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch(),
    )
    self.db.WriteCronJob(job)

    fake_time = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration.From(
        7, rdfvalue.DAYS
    )
    with test_lib.FakeTime(fake_time):
      run = flows_pb2.CronJobRun(
          cron_job_id=job_id,
          run_id="00000000",
          started_at=fake_time.AsMicrosecondsSinceEpoch(),
      )
      self.db.WriteCronJobRun(run)

    fake_time_one_day_later = fake_time + rdfvalue.Duration.From(
        1, rdfvalue.DAYS
    )
    with test_lib.FakeTime(fake_time_one_day_later):
      run = flows_pb2.CronJobRun(
          cron_job_id=job_id,
          run_id="00000001",
          started_at=fake_time_one_day_later.AsMicrosecondsSinceEpoch(),
      )
      self.db.WriteCronJobRun(run)

    fake_time_two_days_later = fake_time + rdfvalue.Duration.From(
        2, rdfvalue.DAYS
    )
    with test_lib.FakeTime(fake_time_two_days_later):
      run = flows_pb2.CronJobRun(
          cron_job_id=job_id,
          run_id="00000002",
          started_at=fake_time_two_days_later.AsMicrosecondsSinceEpoch(),
      )
      self.db.WriteCronJobRun(run)

    self.assertLen(self.db.ReadCronJobRuns(job_id), 3)

    cutoff = fake_time + rdfvalue.Duration.From(1, rdfvalue.HOURS)
    self.db.DeleteOldCronJobRuns(cutoff)
    runs = self.db.ReadCronJobRuns(job_id)
    self.assertLen(runs, 2)
    for run in runs:
      self.assertGreater(run.created_at, cutoff.AsMicrosecondsSinceEpoch())

    cutoff = fake_time + rdfvalue.Duration.From(25, rdfvalue.HOURS)
    self.db.DeleteOldCronJobRuns(cutoff)
    runs = self.db.ReadCronJobRuns(job_id)
    self.assertLen(runs, 1)
    for run in runs:
      self.assertGreater(run.created_at, cutoff.AsMicrosecondsSinceEpoch())


# This file is a test library and thus does not require a __main__ block.
