#!/usr/bin/env python
"""Tests for datastore cleaning cron flows."""



from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import flags
from grr.lib import flow
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.aff4_objects import cronjobs
from grr.lib.flows.cron import data_retention
from grr.lib.hunts import standard


class CleanHuntsTest(test_lib.FlowTestsBaseclass):
  """Test the CleanOldHunts flow."""

  NUM_HUNTS = 10

  def setUp(self):
    super(CleanHuntsTest, self).setUp()

    self.hunts_urns = []
    with test_lib.FakeTime(40):
      for i in range(self.NUM_HUNTS):
        hunt = hunts.GRRHunt.StartHunt(
            hunt_name=standard.SampleHunt.__name__,
            expiry_time=rdfvalue.Duration("1m") * i)
        hunt.Run()
        self.hunts_urns.append(hunt.urn)

  def testDoesNothingIfAgeLimitNotSetInConfig(self):
    with test_lib.FakeTime(40 + 60 * self.NUM_HUNTS):
      flow.GRRFlow.StartFlow(
          flow_name=data_retention.CleanHunts.__name__,
          sync=True, token=self.token)

    hunts_urns = list(aff4.FACTORY.Open("aff4:/hunts",
                                        token=self.token).ListChildren())
    self.assertEqual(len(hunts_urns), 10)

  def testDeletesHuntsWithExpirationDateOlderThanGivenAge(self):
    config_lib.CONFIG.Set("DataRetention.hunts_ttl",
                          rdfvalue.Duration("150s"))

    with test_lib.FakeTime(40 + 60 * self.NUM_HUNTS):
      flow.GRRFlow.StartFlow(
          flow_name=data_retention.CleanHunts.__name__,
          sync=True, token=self.token)
      latest_timestamp = rdfvalue.RDFDatetime().Now()

    hunts_urns = list(aff4.FACTORY.Open("aff4:/hunts",
                                        token=self.token).ListChildren())
    self.assertEqual(len(hunts_urns), 2)

    for hunt_urn in hunts_urns:
      hunt_obj = aff4.FACTORY.Open(hunt_urn, token=self.token)
      runner = hunt_obj.GetRunner()

      self.assertTrue(runner.context.expires < latest_timestamp)
      self.assertTrue(runner.context.expires >
                      latest_timestamp - rdfvalue.Duration("150s"))

  def testNoTraceOfDeletedHuntIsLeftInTheDataStore(self):
    config_lib.CONFIG.Set("DataRetention.hunts_ttl",
                          rdfvalue.Duration("1s"))

    with test_lib.FakeTime(40 + 60 * self.NUM_HUNTS):
      flow.GRRFlow.StartFlow(
          flow_name=data_retention.CleanHunts.__name__,
          sync=True, token=self.token)

    for hunt_urn in self.hunts_urns:
      hunt_id = hunt_urn.Basename()

      # NOTE: We assume that tests are running with FakeDataStore.
      for subject, subject_data in data_store.DB.subjects.items():
        # Foreman rules are versioned, so hunt ids will be mentioned
        # there. Ignoring audit events as well.
        if subject == "aff4:/foreman" or subject.startswith("aff4:/audit"):
          continue

        self.assertFalse(hunt_id in subject)

        for column_name, values in subject_data.items():
          self.assertFalse(hunt_id in column_name)

          for value, _ in values:
            self.assertFalse(hunt_id in utils.SmartUnicode(value))

  def testKeepsHuntsWithRetainLabel(self):
    exception_label_name = config_lib.CONFIG[
        "DataRetention.hunts_ttl_exception_label"]

    for hunt_urn in self.hunts_urns[:3]:
      with aff4.FACTORY.Open(hunt_urn, mode="rw", token=self.token) as fd:
        fd.AddLabels(exception_label_name)

    config_lib.CONFIG.Set("DataRetention.hunts_ttl",
                          rdfvalue.Duration("10s"))

    with test_lib.FakeTime(40 + 60 * self.NUM_HUNTS):
      flow.GRRFlow.StartFlow(
          flow_name=data_retention.CleanHunts.__name__,
          sync=True, token=self.token)

    hunts_urns = list(aff4.FACTORY.Open("aff4:/hunts",
                                        token=self.token).ListChildren())
    self.assertEqual(len(hunts_urns), 3)


class DummySystemCronJob(cronjobs.SystemCronFlow):
  """Dummy system cron job."""

  lifetime = rdfvalue.Duration("30m")
  frequency = rdfvalue.Duration("1h")

  @flow.StateHandler(next_state="End")
  def Start(self):
    self.CallState(next_state="End")


class CleanCronJobsTest(test_lib.FlowTestsBaseclass):
  """Test the CleanCronJobs flow."""

  NUM_CRON_RUNS = 10

  def setUp(self):
    super(CleanCronJobsTest, self).setUp()

    with test_lib.FakeTime(40):
      cron_args = cronjobs.CreateCronJobFlowArgs(
          periodicity=DummySystemCronJob.frequency)
      cron_args.flow_runner_args.flow_name = DummySystemCronJob.__name__
      cron_args.lifetime = DummySystemCronJob.lifetime

      self.cron_jobs_urns = []
      self.cron_jobs_urns.append(cronjobs.CRON_MANAGER.ScheduleFlow(
          cron_args=cron_args, job_name="Foo", token=self.token,
          disabled=False))
      self.cron_jobs_urns.append(cronjobs.CRON_MANAGER.ScheduleFlow(
          cron_args=cron_args, job_name="Bar", token=self.token,
          disabled=False))

    for i in range(self.NUM_CRON_RUNS):
      with test_lib.FakeTime(40 + 60 * i):
        cronjobs.CRON_MANAGER.RunOnce(token=self.token, force=True)

  def testDoesNothingIfAgeLimitNotSetInConfig(self):
    with test_lib.FakeTime(40 + 60 * self.NUM_CRON_RUNS):
      flow.GRRFlow.StartFlow(
          flow_name=data_retention.CleanCronJobs.__name__,
          sync=True, token=self.token)

    for cron_urn in self.cron_jobs_urns:
      fd = aff4.FACTORY.Open(cron_urn, token=self.token)
      self.assertEqual(len(list(fd.ListChildren())), self.NUM_CRON_RUNS)

  def testDeletesFlowsOlderThanGivenAge(self):
    config_lib.CONFIG.Set("DataRetention.cron_jobs_flows_ttl",
                          rdfvalue.Duration("150s"))
    # Only two iterations are supposed to survive, as they were running
    # every minute.
    with test_lib.FakeTime(40 + 60 * self.NUM_CRON_RUNS):
      flow.GRRFlow.StartFlow(
          flow_name=data_retention.CleanCronJobs.__name__,
          sync=True, token=self.token)
      latest_timestamp = rdfvalue.RDFDatetime().Now()

    for cron_urn in self.cron_jobs_urns:
      fd = aff4.FACTORY.Open(cron_urn, token=self.token)
      children = list(fd.ListChildren())
      self.assertEqual(len(children), 2)

      for child_urn in children:
        self.assertTrue(child_urn.age < latest_timestamp)
        self.assertTrue(child_urn.age >
                        latest_timestamp - rdfvalue.Duration("150s"))


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
