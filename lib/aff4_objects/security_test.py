#!/usr/bin/env python
"""Tests for grr.lib.aff4_objects.security."""

from grr.lib import flags
from grr.lib import test_lib
from grr.lib.aff4_objects import security


class ApprovalWithReasonTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(ApprovalWithReasonTest, self).setUp()
    self.approval_obj = security.AbstractApprovalWithReason()

  def _CreateReason(self, reason, result):
    self.assertEqual(self.approval_obj.CreateReasonHTML(reason), result)

  def testCreateReasonHTML(self):
    self._CreateReason("Nothing happens if no regex set i/1234",
                       "Nothing happens if no regex set i/1234")

    # %{} is used here to tell the config system this is a literal that
    # shouldn't be expanded/filtered.
    with test_lib.ConfigOverrider({
        "Email.link_regex_list":
        [r"%{(?P<link>(incident|ir|jira)\/\d+)}"]}):
      test_pairs = [
          ("Investigating jira/1234 (incident/1234)...incident/bug",
           "Investigating <a href=\"jira/1234\">jira/1234</a> "
           "(<a href=\"incident/1234\">incident/1234</a>)...incident/bug"),
          ("\"jira/1234\" == (incident/1234)",
           "\"<a href=\"jira/1234\">jira/1234</a>\" == "
           "(<a href=\"incident/1234\">incident/1234</a>)"),
          ("Checking /var/lib/i/123/blah file",
           "Checking /var/lib/i/123/blah file")
          ]

      for reason, result in test_pairs:
        self._CreateReason(reason, result)


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
