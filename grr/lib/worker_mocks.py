#!/usr/bin/env python
"""GRR worker mocks for use in tests."""

import threading

from grr.client import client_stats
from grr.client import comms
from grr.lib.rdfvalues import flows as rdf_flows


class FakeClientWorker(comms.GRRClientWorker):
  """A Fake GRR client worker which just collects SendReplys."""

  # Global store of suspended actions, indexed by the unique ID of the client
  # action.
  suspended_actions = {}

  def __init__(self):
    self.responses = []
    self.sent_bytes_per_flow = {}
    self.lock = threading.RLock()
    self.stats_collector = client_stats.ClientStatsCollector(self)

  def __del__(self):
    pass

  def SendReply(self,
                rdf_value,
                message_type=rdf_flows.GrrMessage.Type.MESSAGE,
                **kw):
    message = rdf_flows.GrrMessage(type=message_type, payload=rdf_value, **kw)

    self.responses.append(message)

  def Drain(self):
    result = self.responses
    self.responses = []
    return result
