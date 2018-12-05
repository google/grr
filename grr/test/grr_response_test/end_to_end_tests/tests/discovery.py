#!/usr/bin/env python
"""End to end tests for GRR discovery flows."""
from __future__ import absolute_import
from __future__ import division

from grr_response_test.end_to_end_tests import test_base


class TestClientInterrogate(test_base.EndToEndTest):
  """Test for the Interrogate flow on all platforms."""

  platforms = test_base.EndToEndTest.Platform.ALL

  # Intentionally excluded:
  # userdomain: too slow to collect, not in lightweight interrogate
  user_win_kb_attributes = [
      "sid", "userprofile", "appdata", "localappdata", "internet_cache",
      "cookies", "recent", "personal", "startup", "localappdata_low"
  ]

  def _IsCompleteWindowsUser(self, u):
    return all(
        getattr(u, attribute)
        for attribute in self.__class__.user_win_kb_attributes)

  def _CheckUser(self, u):
    if self.platform == test_base.EndToEndTest.Platform.WINDOWS:
      # The amount of information collected per user can vary wildly on
      # Windows depending on the type of user, whether they have logged in,
      # whether they are local/domain etc.  We expect to find at least one
      # user with all of these fields filled out.
      return self._IsCompleteWindowsUser(u)
    elif self.platform == test_base.EndToEndTest.Platform.LINUX:
      return u.HasField("uid")
    elif self.platform == test_base.EndToEndTest.Platform.DARWIN:
      # No uid collection on Darwin.
      return True
    else:
      raise ValueError("Unknown client platform: %s" % self.platform)

  def runTest(self):
    f = self.RunFlowAndWait("Interrogate")

    results = list(f.ListResults())
    self.assertLen(results, 1)

    csummary = results[0].payload
    for u in csummary.users:
      self.assertTrue(u.username, "username is empty for user: %s" % u)

    self.assertTrue(
        any(self._CheckUser(u) for u in csummary.users),
        "No users with complete user attributes: %s" % ",".join(
            u.username for u in csummary.users))
