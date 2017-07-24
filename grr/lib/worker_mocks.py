#!/usr/bin/env python
"""GRR worker mocks for use in tests."""

import threading

from grr.client import client_stats
from grr.client import comms
from grr.lib.rdfvalues import flows as rdf_flows


class FakeMixin(object):
  """Worker methods that just collect SendReplys."""

  def __init__(self, *args, **kw):
    super(FakeMixin, self).__init__(*args, **kw)
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


class FakeClientWorker(FakeMixin, comms.GRRClientWorker):
  """A Fake GRR client worker which just collects SendReplys."""


class FakeThreadedWorker(FakeMixin, comms.GRRThreadedWorker):
  """A Fake GRR client worker based on the actual threaded worker."""
