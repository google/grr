#!/usr/bin/env python
"""Tests for grr.lib.signing."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import platform
import tempfile
import unittest


import mock
import pexpect

from grr_response_core.lib import flags
from grr_response_core.lib.builders import signing
from grr.test_lib import test_lib


class WindowsOsslsigncodeCodeSignerTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(WindowsOsslsigncodeCodeSignerTest, self).setUp()
    self.winsign = signing.WindowsOsslsigncodeCodeSigner("", "", "", "")

  @unittest.skipUnless(platform.system() == "Linux",
                       "We only have pexpect for signing on Linux")
  def testSignBuffer(self):
    intemp = tempfile.NamedTemporaryFile()

    # Simulate osslsign writing the signed file
    outname = "%s.signed" % intemp.name
    open(outname, "wb").write("content")

    with mock.patch.object(pexpect, "spawn"):
      with mock.patch.object(signing.subprocess, "check_call"):
        with mock.patch.object(
            tempfile, "NamedTemporaryFile", return_value=intemp):
          output = self.winsign.SignBuffer("asdflkjlaksjdf")

    self.assertEqual(output, "content")

    with mock.patch.object(
        pexpect, "spawn", side_effect=pexpect.ExceptionPexpect("blah")):
      with self.assertRaises(pexpect.ExceptionPexpect):
        output = self.winsign.SignBuffer("asdflkjlaksjdf")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
