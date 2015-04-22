#!/usr/bin/env python
"""Tests for grr.lib.console_utils."""


# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import aff4
from grr.lib import console_utils
from grr.lib import test_lib


class ConsoleUtilsTest(test_lib.FlowTestsBaseclass):
  """Test the console utils library."""

  def testClientIdToHostname(self):
    client_ids = self.SetupClients(1)
    client1 = aff4.FACTORY.Open(client_ids[0], token=self.token, mode="rw")
    client1.Set(client1.Schema.HOSTNAME("test1"))
    client1.Flush()
    self.assertEquals(console_utils.ClientIdToHostname(str(client1)),
                      "test1")
