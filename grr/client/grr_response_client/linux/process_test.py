#!/usr/bin/env python
"""Tests for the Linux process memory reading."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import __builtin__
import os

from grr_response_client import process_error
from grr_response_client.linux import process
from grr_response_core.lib import flags
from grr_response_core.lib import utils
from grr.test_lib import test_lib


class ProcessTest(test_lib.GRRBaseTest):
  """Tests the Linux process reading."""

  def testUnknownPID(self):

    def FailingOpen(requested_path, mode="rb"):
      del requested_path, mode
      raise OSError("Error in open64.")

    with utils.Stubber(process, "open64", FailingOpen):
      with self.assertRaises(process_error.ProcessError):
        process.Process(pid=1).Open()

  def testRegions(self):

    def MockedOpen64(requested_path, mode="rb"):
      del mode
      if "proc/100/mem" in requested_path._obj.value:
        return True

      raise OSError("Error in open64.")

    def MockedOpen(requested_path, mode="rb"):
      if "proc/100/maps" in requested_path:
        return open.old_target(os.path.join(self.base_path, "maps"), mode=mode)

      raise OSError("Error in open.")

    with utils.MultiStubber((__builtin__, "open", MockedOpen),
                            (process, "open64", MockedOpen64)):
      with process.Process(pid=100) as proc:
        self.assertLen(list(proc.Regions()), 32)
        self.assertLen(list(proc.Regions(skip_mapped_files=True)), 10)
        self.assertLen(list(proc.Regions(skip_shared_regions=True)), 31)
        self.assertEqual(
            len(list(proc.Regions(skip_executable_regions=True))), 27)
        self.assertEqual(
            len(list(proc.Regions(skip_readonly_regions=True))), 10)
        self.assertEqual(
            len(
                list(
                    proc.Regions(
                        skip_executable_regions=True,
                        skip_shared_regions=True))), 26)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
