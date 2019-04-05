#!/usr/bin/env python
"""Abstract base test for serving statistics."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc

from future.utils import with_metaclass

import portpicker
import requests

from grr_response_server import base_stats_server


class StatsServerTestMixin(with_metaclass(abc.ABCMeta, object)):

  def __init__(self, *args, **kwargs):
    super(StatsServerTestMixin, self).__init__(*args, **kwargs)
    self.server = None

  def setUp(self):
    super(StatsServerTestMixin, self).setUp()
    self.server = self.setUpStatsServer(portpicker.pick_unused_port())
    self.server.Start()
    self.addCleanup(self.server.Stop)

  @abc.abstractmethod
  def setUpStatsServer(self, port):
    raise NotImplementedError()

  def url(self, path="/"):
    return "http://localhost:{}{}".format(self.server.port, path)

  def testHealth(self):
    response = requests.get(self.url("/healthz"))
    self.assertEqual(response.status_code, 200)

  def testRaisesPortInUseError(self):
    port = self.server.port
    duplicate = self.setUpStatsServer(port)
    with self.assertRaises(base_stats_server.PortInUseError) as context:
      duplicate.Start()
    self.assertEqual(context.exception.port, port)


# This file is a test library and thus does not require a __main__ block.
