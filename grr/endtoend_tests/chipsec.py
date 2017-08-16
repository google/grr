#!/usr/bin/env python
"""End to end tests for lib.flows.general.hardware."""

from grr.endtoend_tests import base
from grr.lib.rdfvalues import client as rdf_client
from grr.server import aff4
from grr.server.flows.general import hardware


class TestDumpFlashImage(base.AutomatedTest):
  """Test DumpFlashImage (Chipsec).

  This flow returns a StatEntry to the flash image should it be successful.
  In some cases (deprecated chipset), this might not be possible. Verify
  the logs and, if applicable, the image.
  """

  platforms = ["Linux"]
  flow = hardware.DumpFlashImage.__name__

  def CheckFlow(self):
    flow = aff4.FACTORY.Open(self.session_id, token=self.token)

    # On older systems, the flow may returns no result at all. If this is
    # mentioned in the logs, skip further testing.
    for log in flow.GetLog():
      if "No path returned. Skipping host" in log.log_message:
        return

    flash_list = self.CheckResultCollectionNotEmptyWithRetry(self.session_id)

    # There should be exactly one path
    self.assertEqual(len(flash_list), 1)
    flash_entry = flash_list[0]
    self.assertIsInstance(flash_entry, rdf_client.StatEntry)

    # Images are usually a few megabytes in size.
    # Check that it is at least 1MB.
    self.assertGreater(flash_entry.st_size, 1 * 1000 * 1000)
