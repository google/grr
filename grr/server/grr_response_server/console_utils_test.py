#!/usr/bin/env python
"""Tests for grr.lib.console_utils."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_server import aff4
from grr_response_server import console_utils
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class ConsoleUtilsTest(flow_test_lib.FlowTestsBaseclass):
  """Test the console utils library."""

  def testFindClonedClients(self):
    client_ids = self.SetupClients(2)
    client = aff4.FACTORY.Open(client_ids[0], token=self.token, mode="rw")

    # A changing serial number is not enough indication for a cloned client.
    client.Set(client.Schema.HARDWARE_INFO(serial_number="aaa"))
    client.Set(client.Schema.HARDWARE_INFO(serial_number="aaa"))
    client.Set(client.Schema.HARDWARE_INFO(serial_number="aaa"))
    client.Set(client.Schema.HARDWARE_INFO(serial_number="bbb"))
    client.Set(client.Schema.HARDWARE_INFO(serial_number="bbb"))
    client.Set(client.Schema.HARDWARE_INFO(serial_number="bbb"))
    client.Close()

    res = console_utils.FindClonedClients(token=self.token)
    self.assertFalse(res)

    client = aff4.FACTORY.Open(client_ids[1], token=self.token, mode="rw")

    # Here, the serial number alternates back and forth between two values. This
    # is definitely two machines using the same client_id.
    client.Set(client.Schema.HARDWARE_INFO(serial_number="aaa"))
    client.Set(client.Schema.HARDWARE_INFO(serial_number="aaa"))
    client.Set(client.Schema.HARDWARE_INFO(serial_number="aaa"))
    client.Set(client.Schema.HARDWARE_INFO(serial_number="bbb"))
    client.Set(client.Schema.HARDWARE_INFO(serial_number="bbb"))
    client.Set(client.Schema.HARDWARE_INFO(serial_number="bbb"))
    client.Set(client.Schema.HARDWARE_INFO(serial_number="aaa"))
    client.Set(client.Schema.HARDWARE_INFO(serial_number="bbb"))
    client.Close()

    res = console_utils.FindClonedClients(token=self.token)
    self.assertLen(res, 1)
    self.assertEqual(res[0].urn, client.urn)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
