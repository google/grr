#!/usr/bin/env python
"""Fleetspeak-related helpers for use in tests."""

from grr_response_server import fleetspeak_connector


class ConnectionOverrider(object):
  """Context manager used to override the active Fleetspeak connector."""

  def __init__(self, conn):
    self._previous_conn = None
    self._previous_label_map = None
    self._previous_unknown_label = None
    self._conn = conn

  def __enter__(self):
    self.Start()

  def Start(self):
    self._previous_conn = fleetspeak_connector.CONN
    self._previous_label_map = fleetspeak_connector.label_map
    self._previous_unknown_label = fleetspeak_connector.unknown_label
    fleetspeak_connector.Init(self._conn)

  def __exit__(self, *args):
    self.Stop()

  def Stop(self):
    fleetspeak_connector.CONN = self._previous_conn
    fleetspeak_connector.label_map = self._previous_label_map
    fleetspeak_connector.unknown_label = self._previous_unknown_label
