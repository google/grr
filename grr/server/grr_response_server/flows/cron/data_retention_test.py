#!/usr/bin/env python
"""Tests for datastore cleaning cron flows."""

import re

from grr import config
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import cronjobs as rdf_cronjobs
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server import flow
from grr.server.grr_response_server.aff4_objects import cronjobs
from grr.server.grr_response_server.aff4_objects import standard as aff4_standard
from grr.server.grr_response_server.data_stores import fake_data_store
from grr.server.grr_response_server.flows.cron import data_retention
from grr.server.grr_response_server.hunts import implementation
from grr.server.grr_response_server.hunts import standard
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class CleanHuntsTest(flow_test_lib.FlowTestsBaseclass):
  """Test the CleanHunts flow."""

  NUM_HUNTS = 10

  def setUp(self):
    super(CleanHuntsTest, self).setUp()

    self.hunts_urns = []
    with test_lib.FakeTime(40):
      for i in range(self.NUM_HUNTS):
        hunt = implementation.GRRHunt.StartHunt(
            hunt_name=standard.SampleHunt.__name__,
            expiry_time=rdfvalue.Duration("1m") * i,
            token=self.token)
        hunt.Run()
        self.hunts_urns.append(hunt.urn)

  def testDoesNothingIfAgeLimitNotSetInConfig(self):
    with test_lib.FakeTime(40 + 60 * self.NUM_HUNTS):
      flow.GRRFlow.StartFlow(
          flow_name=data_retention.CleanHunts.__name__,
          sync=True,
          token=self.token)

    hunts_urns = list(
        aff4.FACTORY.Open("aff4:/hunts", token=self.token).ListChildren())
    self.assertEqual(len(hunts_urns), 10)

  def testDeletesHuntsWithExpirationDateOlderThanGivenAge(self):
    with test_lib.ConfigOverrider({
        "DataRetention.hunts_ttl": rdfvalue.Duration("150s")
    }):
      with test_lib.FakeTime(40 + 60 * self.NUM_HUNTS):
        flow.GRRFlow.StartFlow(
            flow_name=data_retention.CleanHunts.__name__,
            sync=True,
            token=self.token)
        latest_timestamp = rdfvalue.RDFDatetime.Now()

      hunts_urns = list(
          aff4.FACTORY.Open("aff4:/hunts", token=self.token).ListChildren())
      self.assertEqual(len(hunts_urns), 2)

      for hunt_urn in hunts_urns:
        hunt_obj = aff4.FACTORY.Open(hunt_urn, token=self.token)
        runner = hunt_obj.GetRunner()

        self.assertLess(runner.context.expires, latest_timestamp)
        self.assertGreaterEqual(runner.context.expires,
                                latest_timestamp - rdfvalue.Duration("150s"))

  def testNoTraceOfDeletedHuntIsLeftInTheDataStore(self):
    # This only works with the test data store (FakeDataStore).
    if not isinstance(data_store.DB, fake_data_store.FakeDataStore):
      self.skipTest("Only supported on FakeDataStore.")

    with test_lib.ConfigOverrider({
        "DataRetention.hunts_ttl": rdfvalue.Duration("1s")
    }):
      with test_lib.FakeTime(40 + 60 * self.NUM_HUNTS):
        flow.GRRFlow.StartFlow(
            flow_name=data_retention.CleanHunts.__name__,
            sync=True,
            token=self.token)

      for hunt_urn in self.hunts_urns:
        hunt_id = hunt_urn.Basename()

        for subject, subject_data in data_store.DB.subjects.items():
          # Foreman rules are versioned, so hunt ids will be mentioned
          # there. Ignoring audit events as well.
          if subject == "aff4:/foreman" or subject.startswith("aff4:/audit"):
            continue

          self.assertNotIn(hunt_id, subject)

          for column_name, values in subject_data.items():
            self.assertNotIn(hunt_id, column_name)

            for value, _ in values:
              self.assertNotIn(hunt_id, utils.SmartUnicode(value))

  def testKeepsHuntsWithRetainLabel(self):
    exception_label_name = config.CONFIG[
        "DataRetention.hunts_ttl_exception_label"]

    for hunt_urn in self.hunts_urns[:3]:
      with aff4.FACTORY.Open(hunt_urn, mode="rw", token=self.token) as fd:
        fd.AddLabel(exception_label_name)

    with test_lib.ConfigOverrider({
        "DataRetention.hunts_ttl": rdfvalue.Duration("10s")
    }):

      with test_lib.FakeTime(40 + 60 * self.NUM_HUNTS):
        flow.GRRFlow.StartFlow(
            flow_name=data_retention.CleanHunts.__name__,
            sync=True,
            token=self.token)

      hunts_urns = list(
          aff4.FACTORY.Open("aff4:/hunts", token=self.token).ListChildren())
      self.assertEqual(len(hunts_urns), 3)


class RetentionTestSystemCronJob(cronjobs.SystemCronFlow):
  """Dummy system cron job."""

  lifetime = rdfvalue.Duration("30m")
  frequency = rdfvalue.Duration("1h")

  @flow.StateHandler()
  def Start(self):
    self.CallState(next_state="End")


class CleanCronJobsTest(flow_test_lib.FlowTestsBaseclass):
  """Test the CleanCronJobs flow."""

  NUM_CRON_RUNS = 10

  def setUp(self):
    super(CleanCronJobsTest, self).setUp()

    with test_lib.FakeTime(40):
      cron_args = rdf_cronjobs.CreateCronJobFlowArgs(
          periodicity=RetentionTestSystemCronJob.frequency)
      cron_args.flow_runner_args.flow_name = RetentionTestSystemCronJob.__name__
      cron_args.lifetime = RetentionTestSystemCronJob.lifetime

      self.cron_jobs_names = []
      self.cron_jobs_names.append(cronjobs.GetCronManager().CreateJob(
          cron_args=cron_args, job_id="Foo", token=self.token, disabled=False))
      self.cron_jobs_names.append(cronjobs.GetCronManager().CreateJob(
          cron_args=cron_args, job_id="Bar", token=self.token, disabled=False))

    for i in range(self.NUM_CRON_RUNS):
      with test_lib.FakeTime(40 + 60 * i):
        cronjobs.GetCronManager().RunOnce(token=self.token, force=True)

  def testDoesNothingIfAgeLimitNotSetInConfig(self):
    with test_lib.FakeTime(40 + 60 * self.NUM_CRON_RUNS):
      flow.GRRFlow.StartFlow(
          flow_name=data_retention.CleanCronJobs.__name__,
          sync=True,
          token=self.token)

    for name in self.cron_jobs_names:
      runs = cronjobs.GetCronManager().ReadJobRuns(name, token=self.token)
      self.assertEqual(len(runs), self.NUM_CRON_RUNS)

  def testDeletesFlowsOlderThanGivenAge(self):
    all_children = []
    for cron_name in self.cron_jobs_names:
      all_children.extend(cronjobs.GetCronManager().ReadJobRuns(
          cron_name, token=self.token))

    with test_lib.ConfigOverrider({
        "DataRetention.cron_jobs_flows_ttl": rdfvalue.Duration("150s")
    }):

      # Only two iterations are supposed to survive, as they were running
      # every minute.
      with test_lib.FakeTime(40 + 60 * self.NUM_CRON_RUNS):
        flow.GRRFlow.StartFlow(
            flow_name=data_retention.CleanCronJobs.__name__,
            sync=True,
            token=self.token)
        latest_timestamp = rdfvalue.RDFDatetime.Now()

      remaining_children = []

      for cron_name in self.cron_jobs_names:
        children = cronjobs.GetCronManager().ReadJobRuns(
            cron_name, token=self.token)
        self.assertEqual(len(children), 2)
        remaining_children.extend(children)

        for child in children:
          create_time = child.context.create_time
          self.assertLess(create_time, latest_timestamp)
          self.assertGreater(create_time,
                             latest_timestamp - rdfvalue.Duration("150s"))

      # Only works with the test data store.
      if isinstance(data_store.DB, fake_data_store.FakeDataStore):
        # Check that no subjects are left behind that have anything to do with
        # the deleted flows (requests, responses, ...).
        deleted_flows = set(all_children) - set(remaining_children)
        for subject in data_store.DB.subjects:
          for flow_urn in deleted_flows:
            self.assertNotIn(str(flow_urn), subject)


class CleanTempTest(flow_test_lib.FlowTestsBaseclass):
  """Test the CleanTemp flow."""

  NUM_TMP = 10

  def setUp(self):
    super(CleanTempTest, self).setUp()

    self.tmp_urns = []
    for i in range(self.NUM_TMP):
      with test_lib.FakeTime(40 + 60 * i):
        tmp_obj = aff4.FACTORY.Create(
            "aff4:/tmp/%s" % i,
            aff4_standard.TempMemoryFile,
            mode="rw",
            token=self.token)
        self.tmp_urns.append(tmp_obj.urn)
        tmp_obj.Close()

  def testDoesNothingIfAgeLimitNotSetInConfig(self):
    with test_lib.FakeTime(40 + 60 * self.NUM_TMP):
      flow.GRRFlow.StartFlow(
          flow_name=data_retention.CleanTemp.__name__,
          sync=True,
          token=self.token)

    tmp_urns = list(
        aff4.FACTORY.Open("aff4:/tmp", token=self.token).ListChildren())
    self.assertEqual(len(tmp_urns), 10)

  def testDeletesTempWithAgeOlderThanGivenAge(self):
    with test_lib.ConfigOverrider({
        "DataRetention.tmp_ttl": rdfvalue.Duration("300s")
    }):

      with test_lib.FakeTime(40 + 60 * self.NUM_TMP):
        flow.GRRFlow.StartFlow(
            flow_name=data_retention.CleanTemp.__name__,
            sync=True,
            token=self.token)
        latest_timestamp = rdfvalue.RDFDatetime.Now()

      tmp_urns = list(
          aff4.FACTORY.Open("aff4:/tmp", token=self.token).ListChildren())
      self.assertEqual(len(tmp_urns), 5)

      for tmp_urn in tmp_urns:
        self.assertLess(tmp_urn.age, latest_timestamp)
        self.assertGreaterEqual(tmp_urn.age,
                                latest_timestamp - rdfvalue.Duration("300s"))

  def testKeepsTempWithRetainLabel(self):
    exception_label_name = config.CONFIG[
        "DataRetention.tmp_ttl_exception_label"]

    for tmp_urn in self.tmp_urns[:3]:
      with aff4.FACTORY.Open(tmp_urn, mode="rw", token=self.token) as fd:
        fd.AddLabel(exception_label_name)

    with test_lib.ConfigOverrider({
        "DataRetention.tmp_ttl": rdfvalue.Duration("10s")
    }):

      with test_lib.FakeTime(40 + 60 * self.NUM_TMP):
        flow.GRRFlow.StartFlow(
            flow_name=data_retention.CleanTemp.__name__,
            sync=True,
            token=self.token)

      tmp_urns = list(
          aff4.FACTORY.Open("aff4:/tmp", token=self.token).ListChildren())
      self.assertEqual(len(tmp_urns), 3)


class CleanInactiveClientsTest(flow_test_lib.FlowTestsBaseclass):
  """Test the CleanTemp flow."""

  NUM_CLIENT = 10
  CLIENT_URN_PATTERN = "aff4:/C." + "[0-9a-fA-F]" * 16

  def setUp(self):
    super(CleanInactiveClientsTest, self).setUp()
    self.client_regex = re.compile(self.CLIENT_URN_PATTERN)
    self.client_urns = self.SetupClients(self.NUM_CLIENT)
    for i in range(len(self.client_urns)):
      with test_lib.FakeTime(40 + 60 * i):
        with aff4.FACTORY.Open(
            self.client_urns[i], mode="rw", token=self.token) as client:
          client.Set(client.Schema.LAST(rdfvalue.RDFDatetime.Now()))

  def testDoesNothingIfAgeLimitNotSetInConfig(self):
    with test_lib.FakeTime(40 + 60 * self.NUM_CLIENT):
      flow.GRRFlow.StartFlow(
          flow_name=data_retention.CleanInactiveClients.__name__,
          sync=True,
          token=self.token)

    aff4_root = aff4.FACTORY.Open("aff4:/", mode="r", token=self.token)
    aff4_urns = list(aff4_root.ListChildren())
    client_urns = [x for x in aff4_urns if re.match(self.client_regex, str(x))]

    self.assertEqual(len(client_urns), 10)

  def testDeletesInactiveClientsWithAgeOlderThanGivenAge(self):
    with test_lib.ConfigOverrider({
        "DataRetention.inactive_client_ttl": rdfvalue.Duration("300s")
    }):

      with test_lib.FakeTime(40 + 60 * self.NUM_CLIENT):
        flow.GRRFlow.StartFlow(
            flow_name=data_retention.CleanInactiveClients.__name__,
            sync=True,
            token=self.token)
        latest_timestamp = rdfvalue.RDFDatetime.Now()

      aff4_root = aff4.FACTORY.Open("aff4:/", mode="r", token=self.token)
      aff4_urns = list(aff4_root.ListChildren())
      client_urns = [
          x for x in aff4_urns if re.match(self.client_regex, str(x))
      ]

      self.assertEqual(len(client_urns), 5)

      for client_urn in client_urns:
        client = aff4.FACTORY.Open(client_urn, mode="r", token=self.token)
        self.assertLess(client.Get(client.Schema.LAST), latest_timestamp)
        self.assertGreaterEqual(
            client.Get(client.Schema.LAST),
            latest_timestamp - rdfvalue.Duration("300s"))

  def testKeepsClientsWithRetainLabel(self):
    exception_label_name = config.CONFIG[
        "DataRetention.inactive_client_ttl_exception_label"]

    for client_urn in self.client_urns[:3]:
      with aff4.FACTORY.Open(client_urn, mode="rw", token=self.token) as fd:
        fd.AddLabel(exception_label_name)

    with test_lib.ConfigOverrider({
        "DataRetention.inactive_client_ttl": rdfvalue.Duration("10s")
    }):

      with test_lib.FakeTime(40 + 60 * self.NUM_CLIENT):
        flow.GRRFlow.StartFlow(
            flow_name=data_retention.CleanInactiveClients.__name__,
            sync=True,
            token=self.token)

      aff4_root = aff4.FACTORY.Open("aff4:/", mode="r", token=self.token)
      aff4_urns = list(aff4_root.ListChildren())
      client_urns = [
          x for x in aff4_urns if re.match(self.client_regex, str(x))
      ]

      self.assertEqual(len(client_urns), 3)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
