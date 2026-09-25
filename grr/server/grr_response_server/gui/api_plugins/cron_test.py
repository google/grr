#!/usr/bin/env python
"""This module contains tests for cron-related API handlers."""

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import mig_protodict
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.util import random
from grr_response_proto import flows_pb2
from grr_response_proto.api import cron_pb2
from grr_response_server import cronjobs
from grr_response_server import data_store
from grr_response_server.flows.general import file_finder
from grr_response_server.gui import api_test_lib
from grr_response_server.gui import mig_api_call_handler_utils
from grr_response_server.gui.api_plugins import cron as cron_plugin
from grr_response_server.models import hunts as models_hunts
from grr.test_lib import test_lib


class ApiCronJobTest(test_lib.GRRBaseTest):

  _DATETIME = rdfvalue.RDFDatetime.FromHumanReadable

  def testInitFromCronObject(self):
    state = rdf_protodict.AttributedDict()
    state["quux"] = "norf"
    state["thud"] = "blargh"

    cron_job = flows_pb2.CronJob(
        created_at=int(rdfvalue.RDFDatetime.Now()),
    )
    cron_job.cron_job_id = "foo"
    cron_job.current_run_id = "bar"
    cron_job.last_run_time = int(self._DATETIME("2001-01-01"))
    cron_job.last_run_status = flows_pb2.CronJobRun.CronJobRunStatus.FINISHED
    cron_job.frequency = rdfvalue.Duration.From(1, rdfvalue.DAYS).ToInt(
        timeunit=rdfvalue.MICROSECONDS
    )
    cron_job.lifetime = rdfvalue.Duration.From(30, rdfvalue.DAYS).ToInt(
        timeunit=rdfvalue.MICROSECONDS
    )
    cron_job.enabled = False
    cron_job.forced_run_requested = True
    cron_job.state.CopyFrom(mig_protodict.ToProtoAttributedDict(state))
    cron_job.description = "testdescription"

    api_cron_job = cron_plugin.InitApiCronJobFromCronJob(cron_job)

    self.assertEqual(api_cron_job.cron_job_id, "foo")
    self.assertEqual(api_cron_job.current_run_id, "bar")
    self.assertEqual(api_cron_job.description, "testdescription")
    self.assertEqual(
        api_cron_job.last_run_time, int(self._DATETIME("2001-01-01"))
    )
    self.assertEqual(
        api_cron_job.last_run_status,
        flows_pb2.CronJobRun.CronJobRunStatus.FINISHED,
    )
    self.assertEqual(
        api_cron_job.frequency,
        rdfvalue.Duration.From(1, rdfvalue.DAYS).ToInt(
            timeunit=rdfvalue.MICROSECONDS
        ),
    )
    self.assertEqual(
        api_cron_job.lifetime,
        rdfvalue.Duration.From(30, rdfvalue.DAYS).ToInt(
            timeunit=rdfvalue.MICROSECONDS
        ),
    )
    self.assertFalse(api_cron_job.enabled)
    self.assertTrue(api_cron_job.forced_run_requested)

    state = mig_api_call_handler_utils.ToRDFApiDataObject(api_cron_job.state)
    api_state_items = {_.key: _.value for _ in state.items}
    self.assertEqual(api_state_items, {"quux": "norf", "thud": "blargh"})


class CronJobsTestMixin(object):

  def CreateCronJob(
      self,
      flow_name,
      job_id=None,
      flow_args=None,
      periodicity="1d",
      lifetime="7d",
      description="",
      enabled=True,
      allow_overruns=False,
  ):
    if not flow_name:
      raise ValueError("Unspecified flow name")

    if not job_id:
      # TODO - UInt16 is too small for randomly generated IDs.
      uid = random.UInt16()
      job_id = "%s_%s" % (flow_name, uid)

    frequency = rdfvalue.DurationSeconds.FromHumanReadable(
        periodicity
    ).SerializeToWireFormat()
    lifetime = rdfvalue.DurationSeconds.FromHumanReadable(
        lifetime
    ).SerializeToWireFormat()

    args = flows_pb2.CronJobAction(
        action_type=flows_pb2.CronJobAction.ActionType.HUNT_CRON_ACTION,
        hunt_cron_action=flows_pb2.HuntCronAction(
            flow_name=flow_name,
            hunt_runner_args=models_hunts.CreateDefaultHuntRunnerArgs(),
        ),
    )
    # This is bad, we're deprecating it so nothing to do at the moment.
    if flow_args:
      args.hunt_cron_action.flow_args = flow_args.SerializeToString()

    job = flows_pb2.CronJob(
        cron_job_id=job_id,
        description=description,
        enabled=enabled,
        frequency=frequency,
        lifetime=lifetime,
        allow_overruns=allow_overruns,
        created_at=int(rdfvalue.RDFDatetime.Now()),
        args=args,
    )
    data_store.REL_DB.WriteCronJob(job)

    return job_id


class ApiDeleteCronJobHandlerTest(
    api_test_lib.ApiCallHandlerTest, CronJobsTestMixin
):
  """Test delete cron job handler."""

  def setUp(self):
    super().setUp()
    self.handler = cron_plugin.ApiDeleteCronJobHandler()

    self.cron_job_id = self.CreateCronJob(
        flow_name=file_finder.FileFinder.__name__
    )

  def testDeletesCronFromCollection(self):
    jobs = list(cronjobs.CronManager().ListJobs())
    self.assertLen(jobs, 1)
    self.assertEqual(jobs[0], self.cron_job_id)

    args = cron_pb2.ApiDeleteCronJobArgs(cron_job_id=self.cron_job_id)
    self.handler.Handle(args, context=self.context)

    jobs = list(cronjobs.CronManager().ListJobs())
    self.assertEmpty(jobs)


class ApiGetCronJobHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Tests the ApiGetCronJobHandler."""

  def setUp(self):
    super().setUp()
    self.handler = cron_plugin.ApiGetCronJobHandler()

  def testHandler(self):
    now = rdfvalue.RDFDatetime.Now()
    with test_lib.FakeTime(now):
      job = flows_pb2.CronJob(
          cron_job_id="job_id",
          enabled=True,
          last_run_status=flows_pb2.CronJobRun.CronJobRunStatus.FINISHED,
          frequency=rdfvalue.Duration.From(7, rdfvalue.DAYS).ToInt(
              timeunit=rdfvalue.MICROSECONDS
          ),
          lifetime=rdfvalue.Duration.From(1, rdfvalue.HOURS).ToInt(
              timeunit=rdfvalue.MICROSECONDS
          ),
          allow_overruns=True,
          created_at=int(rdfvalue.RDFDatetime.Now()),
      )
      data_store.REL_DB.WriteCronJob(job)

    state = rdf_protodict.AttributedDict()
    state["item"] = "key"
    data_store.REL_DB.UpdateCronJob(
        job.cron_job_id,
        current_run_id="ABCD1234",
        state=mig_protodict.ToProtoAttributedDict(state),
        forced_run_requested=True,
    )

    args = cron_pb2.ApiGetCronJobArgs(cron_job_id=job.cron_job_id)
    result = self.handler.Handle(args)

    self.assertEqual(result.cron_job_id, job.cron_job_id)
    # TODO(amoser): The aff4 implementation does not store the create time so we
    # can't return it yet.
    # self.assertEqual(result.created_at, now)
    self.assertEqual(result.enabled, job.enabled)
    self.assertEqual(result.current_run_id, "ABCD1234")
    self.assertEqual(result.forced_run_requested, True)
    self.assertEqual(result.frequency, job.frequency)
    self.assertEqual(result.is_failing, False)
    self.assertEqual(result.last_run_status, job.last_run_status)
    self.assertEqual(result.lifetime, job.lifetime)
    state = mig_api_call_handler_utils.ToRDFApiDataObject(result.state)
    state_entries = list(state.items)
    self.assertLen(state_entries, 1)
    state_entry = state_entries[0]
    self.assertEqual(state_entry.key, "item")
    self.assertEqual(state_entry.value, "key")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
