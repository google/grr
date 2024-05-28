#!/usr/bin/env python
"""GCP Pub/Sub subscriber for fleetspeak messages."""

import logging
from typing import Callable

from google.cloud import pubsub_v1

from grr_response_core import config
from fleetspeak.src.common.proto.fleetspeak import common_pb2


class ConfigError(Exception):
  """Raised when the Cloud Pub/Sub config is invalid."""


class Subscriber:
  """Cloud Pub/Sub subscriber, receiving messages from Fleetspeak."""

  def __init__(self) -> None:
    for var in (
        "Server.fleetspeak_cps_project",
        "Server.fleetspeak_cps_subscription",
    ):
      if not config.CONFIG[var]:
        raise ConfigError(f"Missing config value for {var}")

    self._project = config.CONFIG["Server.fleetspeak_cps_project"]
    self._subscription = config.CONFIG["Server.fleetspeak_cps_subscription"]
    self._concurrency = config.CONFIG["Server.fleetspeak_cps_concurrency"]
    self._client = None
    self._sub_futures = []

  def Start(self, process_fn: Callable[[common_pb2.Message], None]) -> None:
    """Start the (asynchronous) subscriber.

    Args:
      process_fn: message-processing callback; all messages received from
        Fleetspeak are passed to this function.

    Multiple message-receiving and processing threads will be spawned in the
    background, as per the config var `Server.fleetspeak_cps_concurrency.
    """

    def _PubsubCallback(cps_msg: pubsub_v1.subscriber.message.Message) -> None:
      # Using broad Exception catching here because, at this point, any error
      # is unrecoverable. This code is run by some thread spawned by the
      # google-cloud lib; any uncaught exception would just crash that thread.
      try:
        fs_msg = common_pb2.Message.FromString(cps_msg.data)
      except Exception as e:  # pylint: disable=broad-exception-caught
        # Any error in message deserialization is final - we don't know how to
        # handle the message. Log the error and drop the message permanently.
        logging.exception(
            "Dropping malformed CPS message from Fleetspeak: %s", e
        )
        cps_msg.ack()
        return
      try:
        process_fn(fs_msg)
      except Exception as e:  # pylint: disable=broad-exception-caught
        # A message processing error might be temporary (i.e. may be caused by
        # some temporary condition). Mark the message as NACK, so that it will
        # be redelivered at a later time.
        logging.exception("Exception during CPS message processing: %s", e)
        cps_msg.nack()
      else:
        cps_msg.ack()

    self._client = pubsub_v1.SubscriberClient()
    sub_path = self._client.subscription_path(self._project, self._subscription)

    for i in range(self._concurrency):
      logging.info(
          "Starting Cloud Pub/Sub subscriber %d/%d", i + 1, self._concurrency
      )
      fut = self._client.subscribe(sub_path, callback=_PubsubCallback)
      self._sub_futures.append(fut)

  def Stop(self) -> None:
    """Stop the (asynchronous) subscriber.

    This will block until all message-processing threads shut down.
    """
    for fut in self._sub_futures:
      fut.cancel()
    for fut in self._sub_futures:
      fut.result()
    self._client = None
    self._sub_futures = []
