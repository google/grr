#!/usr/bin/env python
"""GRR worker mocks for use in tests."""

import threading

from grr_response_client import client_stats
from grr_response_client import comms
from grr_response_core.lib.rdfvalues import flows as rdf_flows


class FakeMixin(object):
  """Worker methods that just collect SendReplys."""

  def __init__(self, *args, **kw):
    super().__init__(*args, **kw)
    self.responses = []
    self.sent_bytes_per_flow = {}
    self.lock = threading.RLock()
    self.stats_collector = client_stats.ClientStatsCollector(self)

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


class ClientWorker(comms.GRRClientWorker):
  """A GRR client worker with disabled threads."""

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.stats_collector = client_stats.ClientStatsCollector(self)

  def StartStatsCollector(self):
    # Don't start any threads in tests.
    pass

  def start(self):
    # Don't start any threads in tests.
    pass


class FakeClientWorker(FakeMixin, ClientWorker):
  """A Fake GRR client worker which just collects SendReplys."""
