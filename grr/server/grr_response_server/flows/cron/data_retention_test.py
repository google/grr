#!/usr/bin/env python
"""Tests for datastore cleaning cron flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re


from builtins import range  # pylint: disable=redefined-builtin
from future.utils import iteritems

from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server.aff4_objects import cronjobs
from grr_response_server.data_stores import fake_data_store
from grr_response_server.flows.cron import data_retention
from grr_response_server.hunts import implementation
from grr_response_server.hunts import standard
from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class CleanHuntsFlowTest(flow_test_lib.FlowTestsBaseclass):
  """Test the CleanHunts flow."""

  NUM_HUNTS = 10

  def setUp(self):
    super(CleanHuntsFlowTest, self).setUp()

    self.hunts_urns = []
    with test_lib.FakeTime(40):
      for i in range(self.NUM_HUNTS):
        hunt = implementation.StartHunt(
            hunt_name=standard.SampleHunt.__name__,
            expiry_time=rdfvalue.Duration("1m") * i,
            token=self.token)
        hunt.Run()
        self.hunts_urns.append(hunt.urn)

  def _RunCleanup(self):
    self.cleaner_flow = flow.StartAFF4Flow(
        flow_name=data_retention.CleanHunts.__name__,
        sync=True,
        token=self.token)

  def _CheckLog(self, msg):
    flow_obj = aff4.FACTORY.Open(self.cleaner_flow)
    log_collection = flow_obj.GetLog()
    for log_item in log_collection:
      if msg in log_item.log_message:
        return
    raise ValueError("Log message '%s' not found in the flow log." % msg)

  def testDoesNothingIfAgeLimitNotSetInConfig(self):
    with test_lib.FakeTime(40 + 60 * self.NUM_HUNTS):
      self._RunCleanup()

    hunts_urns = list(
        aff4.FACTORY.Open("aff4:/hunts", token=self.token).ListChildren())
    self.assertLen(hunts_urns, 10)

  def testDeletesHuntsWithExpirationDateOlderThanGivenAge(self):
    with test_lib.ConfigOverrider(
        {"DataRetention.hunts_ttl": rdfvalue.Duration("150s")}):
      with test_lib.FakeTime(40 + 60 * self.NUM_HUNTS):
        self._RunCleanup()
        latest_timestamp = rdfvalue.RDFDatetime.Now()

      hunts_urns = list(
          aff4.FACTORY.Open("aff4:/hunts", token=self.token).ListChildren())
      self.assertLen(hunts_urns, 2)

      for hunt_urn in hunts_urns:
        hunt_obj = aff4.FACTORY.Open(hunt_urn, token=self.token)
        runner = hunt_obj.GetRunner()

        self.assertLess(runner.context.expires, latest_timestamp)
        self.assertGreaterEqual(runner.context.expires,
                                latest_timestamp - rdfvalue.Duration("150s"))
    self._CheckLog("Deleted 8")

  def testNoTraceOfDeletedHuntIsLeftInTheDataStore(self):
    # This only works with the test data store (FakeDataStore).
    if not isinstance(data_store.DB, fake_data_store.FakeDataStore):
      self.skipTest("Only supported on FakeDataStore.")

    with test_lib.ConfigOverrider(
        {"DataRetention.hunts_ttl": rdfvalue.Duration("1s")}):
      with test_lib.FakeTime(40 + 60 * self.NUM_HUNTS):
        self._RunCleanup()

      for hunt_urn in self.hunts_urns:
        hunt_id = hunt_urn.Basename()

        for subject, subject_data in iteritems(data_store.DB.subjects):
          # Foreman rules are versioned, so hunt ids will be mentioned
          # there. Ignoring audit events as well.
          if subject == "aff4:/foreman" or subject.startswith("aff4:/audit"):
            continue

          self.assertNotIn(hunt_id, subject)

          for column_name, values in iteritems(subject_data):
            self.assertNotIn(hunt_id, column_name)

            for value, _ in values:
              self.assertNotIn(hunt_id, utils.SmartUnicode(value))

  def testKeepsHuntsWithRetainLabel(self):
    exception_label_name = config.CONFIG[
        "DataRetention.hunts_ttl_exception_label"]

    for hunt_urn in self.hunts_urns[:3]:
      with aff4.FACTORY.Open(hunt_urn, mode="rw", token=self.token) as fd:
        fd.AddLabel(exception_label_name)

    with test_lib.ConfigOverrider(
        {"DataRetention.hunts_ttl": rdfvalue.Duration("10s")}):

      with test_lib.FakeTime(40 + 60 * self.NUM_HUNTS):
        self._RunCleanup()

      hunts_urns = list(
          aff4.FACTORY.Open("aff4:/hunts", token=self.token).ListChildren())
      self.assertLen(hunts_urns, 3)


class CleanHuntsJobTest(db_test_lib.RelationalDBEnabledMixin,
                        CleanHuntsFlowTest):
  """Test the CleanHunts cron job."""

  def _RunCleanup(self):
    run = rdf_cronjobs.CronJobRun()
    job = rdf_cronjobs.CronJob()
    self.cleaner_job = data_retention.CleanHuntsCronJob(run, job)
    self.cleaner_job.Run()

  def _CheckLog(self, msg):
    self.assertIn(msg, self.cleaner_job.run_state.log_message)


class RetentionTestSystemCronJob(cronjobs.SystemCronFlow):
  """Dummy system cron job."""

  lifetime = rdfvalue.Duration("30s")
  frequency = rdfvalue.Duration("30s")

  def Start(self):
    self.CallState(next_state="End")


class CleanCronJobsFlowTest(flow_test_lib.FlowTestsBaseclass):
  """Test the CleanCronJobs flow."""

  NUM_CRON_RUNS = 10

  def setUp(self):
    super(CleanCronJobsFlowTest, self).setUp()

    with test_lib.FakeTime(40):
      cron_args = rdf_cronjobs.CreateCronJobArgs(
          frequency=RetentionTestSystemCronJob.frequency,
          flow_name=RetentionTestSystemCronJob.__name__,
          lifetime=RetentionTestSystemCronJob.lifetime)

      self.cron_jobs_names = []
      self.cron_jobs_names.append(cronjobs.GetCronManager().CreateJob(
          cron_args=cron_args, job_id="Foo", token=self.token, enabled=True))
      self.cron_jobs_names.append(cronjobs.GetCronManager().CreateJob(
          cron_args=cron_args, job_id="Bar", token=self.token, enabled=True))

    manager = cronjobs.GetCronManager()
    for i in range(self.NUM_CRON_RUNS):
      with test_lib.FakeTime(40 + 60 * i):
        manager.RunOnce(token=self.token)
        if data_store.RelationalDBReadEnabled(category="cronjobs"):
          manager._GetThreadPool().Join()

    if data_store.RelationalDBReadEnabled(category="cronjobs"):
      manager._GetThreadPool().Stop()

  def _RunCleanup(self):
    self.cleaner_flow = flow.StartAFF4Flow(
        flow_name=data_retention.CleanCronJobs.__name__,
        sync=True,
        token=self.token)

  def _CheckLog(self, msg):
    flow_obj = aff4.FACTORY.Open(self.cleaner_flow)
    log_collection = flow_obj.GetLog()
    for log_item in log_collection:
      if msg in log_item.log_message:
        return
    raise ValueError("Log message '%s' not found in the flow log." % msg)

  def testDoesNothingIfAgeLimitNotSetInConfig(self):
    with test_lib.FakeTime(40 + 60 * self.NUM_CRON_RUNS):
      self._RunCleanup()

    for name in self.cron_jobs_names:
      runs = cronjobs.GetCronManager().ReadJobRuns(name, token=self.token)
      self.assertLen(runs, self.NUM_CRON_RUNS)

  def testDeletesRunsOlderThanGivenAge(self):
    all_children = []
    for cron_name in self.cron_jobs_names:
      all_children.extend(cronjobs.GetCronManager().ReadJobRuns(
          cron_name, token=self.token))

    with test_lib.ConfigOverrider(
        {"DataRetention.cron_jobs_flows_ttl": rdfvalue.Duration("150s")}):

      # Only two iterations are supposed to survive, as they were running
      # every minute.
      with test_lib.FakeTime(40 + 60 * self.NUM_CRON_RUNS):
        self._RunCleanup()
        latest_timestamp = rdfvalue.RDFDatetime.Now()

      remaining_children = []

      for cron_name in self.cron_jobs_names:
        children = cronjobs.GetCronManager().ReadJobRuns(
            cron_name, token=self.token)
        self.assertLen(children, 2)
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

    self._CheckLog("Deleted 16")


class CleanCronJobsJobTest(db_test_lib.RelationalDBEnabledMixin,
                           CleanCronJobsFlowTest):
  """Test the CleanCronJobs cron job."""

  def _RunCleanup(self):
    run = rdf_cronjobs.CronJobRun()
    job = rdf_cronjobs.CronJob()
    self.cleaner_job = data_retention.CleanCronJobsCronJob(run, job)
    self.cleaner_job.Run()

  def testDeletesRunsOlderThanGivenAge(self):
    all_children = []
    for cron_name in self.cron_jobs_names:
      all_children.extend(cronjobs.GetCronManager().ReadJobRuns(cron_name))

    with test_lib.ConfigOverrider(
        {"DataRetention.cron_jobs_flows_ttl": rdfvalue.Duration("150s")}):

      # Only two iterations are supposed to survive, as they were running
      # every minute.
      with test_lib.FakeTime(40 + 60 * self.NUM_CRON_RUNS):
        self._RunCleanup()
        latest_timestamp = rdfvalue.RDFDatetime.Now()

      for cron_name in self.cron_jobs_names:
        children = cronjobs.GetCronManager().ReadJobRuns(cron_name)
        self.assertLen(children, 2)

        for child in children:
          self.assertLess(child.started_at, latest_timestamp)
          self.assertGreater(child.started_at,
                             latest_timestamp - rdfvalue.Duration("150s"))

    self.assertIn("Deleted 16", self.cleaner_job.run_state.log_message)


class CleanInactiveClientsFlowTest(flow_test_lib.FlowTestsBaseclass):
  """Tests the client cleanup flow."""

  NUM_CLIENT = 10
  CLIENT_URN_PATTERN = "aff4:/C." + "[0-9a-fA-F]" * 16

  def setUp(self):
    super(CleanInactiveClientsFlowTest, self).setUp()
    self.client_regex = re.compile(self.CLIENT_URN_PATTERN)
    self.client_urns = self.SetupClients(self.NUM_CLIENT)
    for i in range(len(self.client_urns)):
      with test_lib.FakeTime(40 + 60 * i):
        with aff4.FACTORY.Open(
            self.client_urns[i], mode="rw", token=self.token) as client:
          client.Set(client.Schema.LAST(rdfvalue.RDFDatetime.Now()))

  def _RunCleanup(self):
    self.cleaner_flow = flow.StartAFF4Flow(
        flow_name=data_retention.CleanInactiveClients.__name__,
        sync=True,
        token=self.token)

  def _CheckLog(self, msg):
    flow_obj = aff4.FACTORY.Open(self.cleaner_flow)
    log_collection = flow_obj.GetLog()
    for log_item in log_collection:
      if msg in log_item.log_message:
        return
    raise ValueError("Log message '%s' not found in the flow log." % msg)

  def testDoesNothingIfAgeLimitNotSetInConfig(self):
    with test_lib.FakeTime(40 + 60 * self.NUM_CLIENT):
      self._RunCleanup()

    aff4_root = aff4.FACTORY.Open("aff4:/", mode="r", token=self.token)
    aff4_urns = list(aff4_root.ListChildren())
    client_urns = [x for x in aff4_urns if re.match(self.client_regex, str(x))]

    self.assertLen(client_urns, 10)

  def testDeletesInactiveClientsWithAgeOlderThanGivenAge(self):
    with test_lib.ConfigOverrider(
        {"DataRetention.inactive_client_ttl": rdfvalue.Duration("300s")}):

      with test_lib.FakeTime(40 + 60 * self.NUM_CLIENT):
        self._RunCleanup()
        latest_timestamp = rdfvalue.RDFDatetime.Now()

      aff4_root = aff4.FACTORY.Open("aff4:/", mode="r", token=self.token)
      aff4_urns = list(aff4_root.ListChildren())
      client_urns = [
          x for x in aff4_urns if re.match(self.client_regex, str(x))
      ]

      self.assertLen(client_urns, 5)

      for client_urn in client_urns:
        client = aff4.FACTORY.Open(client_urn, mode="r", token=self.token)
        self.assertLess(client.Get(client.Schema.LAST), latest_timestamp)
        self.assertGreaterEqual(
            client.Get(client.Schema.LAST),
            latest_timestamp - rdfvalue.Duration("300s"))

    self._CheckLog("Deleted 5")

  def testKeepsClientsWithRetainLabel(self):
    exception_label_name = config.CONFIG[
        "DataRetention.inactive_client_ttl_exception_label"]

    for client_urn in self.client_urns[:3]:
      with aff4.FACTORY.Open(client_urn, mode="rw", token=self.token) as fd:
        fd.AddLabel(exception_label_name)

    with test_lib.ConfigOverrider(
        {"DataRetention.inactive_client_ttl": rdfvalue.Duration("10s")}):

      with test_lib.FakeTime(40 + 60 * self.NUM_CLIENT):
        self._RunCleanup()

      aff4_root = aff4.FACTORY.Open("aff4:/", mode="r", token=self.token)
      aff4_urns = list(aff4_root.ListChildren())
      client_urns = [
          x for x in aff4_urns if re.match(self.client_regex, str(x))
      ]

      self.assertLen(client_urns, 3)


class CleanInactiveClientsJobTest(db_test_lib.RelationalDBEnabledMixin,
                                  CleanInactiveClientsFlowTest):

  def _RunCleanup(self):
    run = rdf_cronjobs.CronJobRun()
    job = rdf_cronjobs.CronJob()
    self.cleaner_job = data_retention.CleanInactiveClientsCronJob(run, job)
    self.cleaner_job.Run()

  def _CheckLog(self, msg):
    self.assertIn(msg, self.cleaner_job.run_state.log_message)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
