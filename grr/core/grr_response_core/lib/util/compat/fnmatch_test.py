#!/usr/bin/env python
# Lint as: python3
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl.testing import absltest

from grr_response_core.lib.util.compat import fnmatch


class FnmatchTranslateTest(absltest.TestCase):

  def testProducesExpectedPython2CompatibleOutput(self):
    self.assertEqual(fnmatch.translate("*"), "(?ms).*\\Z")
    self.assertEqual(fnmatch.translate("bar.*"), "(?ms)bar\\..*\\Z")
    self.assertEqual(fnmatch.translate("*.bar.*"), "(?ms).*\\.bar\\..*\\Z")


if __name__ == "__main__":
  absltest.main()
