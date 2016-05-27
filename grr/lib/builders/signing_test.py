#!/usr/bin/env python
"""Tests for grr.lib.signing."""

import tempfile


import mock
import pexpect

from grr.lib import flags
from grr.lib import test_lib
from grr.lib.builders import signing


class WindowsCodeSignerTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(WindowsCodeSignerTest, self).setUp()
    self.winsign = signing.WindowsCodeSigner("", "", "", "")

  def testSignBuffer(self):
    intemp = tempfile.NamedTemporaryFile()

    # Simulate osslsign writing the signed file
    outname = "%s.signed" % intemp.name
    open(outname, "w").write("content")

    with mock.patch.object(pexpect, "spawn"):
      with mock.patch.object(signing.subprocess, "check_call"):
        with mock.patch.object(tempfile,
                               "NamedTemporaryFile",
                               return_value=intemp):
          output = self.winsign.SignBuffer("asdflkjlaksjdf")

    self.assertEqual(output, "content")

    with mock.patch.object(pexpect,
                           "spawn",
                           side_effect=pexpect.ExceptionPexpect("blah")):
      with self.assertRaises(pexpect.ExceptionPexpect):
        output = self.winsign.SignBuffer("asdflkjlaksjdf")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
