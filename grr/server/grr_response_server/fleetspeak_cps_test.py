#!/usr/bin/env python
"""Unit tests for GCP Pub/Sub subscriber for fleetspeak messages."""

import os
import time
from typing import Callable
import unittest

from absl import app
from google.cloud import pubsub_v1

from grr_response_server import fleetspeak_cps
from grr.test_lib import test_lib
from fleetspeak.src.common.proto.fleetspeak import common_pb2


_TEST_PROJECT = "test-project"
_TEST_TOPIC = "test-topic"
_TEST_SUB = "test-sub"


class FleetspeakCPSTest(test_lib.GRRBaseTest):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()

    if not os.getenv("PUBSUB_EMULATOR_HOST"):
      raise unittest.SkipTest(
          "Cloud Pub/Sub emulation not found (PUBSUB_EMULATOR_HOST is not set)."
      )

    cls._cps_config_overrider = test_lib.ConfigOverrider({
        "Server.fleetspeak_cps_enabled": True,
        "Server.fleetspeak_cps_project": _TEST_PROJECT,
        "Server.fleetspeak_cps_subscription": _TEST_SUB,
        "Server.fleetspeak_cps_concurrency": 1,
    })
    cls._cps_config_overrider.Start()

  @classmethod
  def tearDownClass(cls):
    cls._cps_config_overrider.Stop()
    super().tearDownClass()

  def setUp(self):
    super().setUp()
    self._topic = f"projects/{_TEST_PROJECT}/topics/{_TEST_TOPIC}"
    self._sub = f"projects/{_TEST_PROJECT}/subscriptions/{_TEST_SUB}"
    pubsub_v1.PublisherClient().create_topic(name=self._topic)
    pubsub_v1.SubscriberClient().create_subscription(
        name=self._sub, topic=self._topic
    )

  def tearDown(self):
    pubsub_v1.SubscriberClient().delete_subscription(subscription=self._sub)
    pubsub_v1.PublisherClient().delete_topic(topic=self._topic)
    super().tearDown()

  def _publishAndProcess(
      self,
      fs_msg: common_pb2.Message,
      process_fn: Callable[common_pb2.Message, None],
  ):
    subscriber = fleetspeak_cps.Subscriber()
    subscriber.Start(process_fn)
    pubsub_v1.PublisherClient().publish(
        topic=self._topic, data=fs_msg.SerializeToString()
    )
    time.sleep(2)
    subscriber.Stop()

  def testSuccessfulMessageProcessing(self):
    delivered = False

    def _Process(fs_msg: common_pb2.Message):
      del fs_msg
      nonlocal delivered
      delivered = True

    fs_msg = common_pb2.Message(message_type="GrrMessage")
    self._publishAndProcess(fs_msg, _Process)

    self.assertTrue(delivered)

  def testMessageRedeliveryOnFailure(self):
    delivery_count = 0

    def _Process(fs_msg: common_pb2.Message):
      del fs_msg
      nonlocal delivery_count
      delivery_count += 1
      if delivery_count == 1:
        raise KeyError("failing first processing attempt")

    fs_msg = common_pb2.Message(message_type="GrrMessage")
    self._publishAndProcess(fs_msg, _Process)

    self.assertEqual(delivery_count, 2)


if __name__ == "__main__":
  app.run(test_lib.main)
