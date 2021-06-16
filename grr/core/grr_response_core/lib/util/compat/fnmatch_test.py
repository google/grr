#!/usr/bin/env python

from absl.testing import absltest

from grr_response_core.lib.util.compat import fnmatch


class FnmatchTranslateTest(absltest.TestCase):

  def testProducesExpectedPython2CompatibleOutput(self):
    self.assertEqual(fnmatch.translate("*"), "(?ms).*\\Z")
    self.assertEqual(fnmatch.translate("bar.*"), "(?ms)bar\\..*\\Z")
    self.assertEqual(fnmatch.translate("*.bar.*"), "(?ms).*\\.bar\\..*\\Z")


if __name__ == "__main__":
  absltest.main()
