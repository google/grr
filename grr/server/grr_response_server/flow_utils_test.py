#!/usr/bin/env python
"""Tests for flow utils classes."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_server import flow_utils
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class TestInterpolatePath(flow_test_lib.FlowTestsBaseclass):
  """Tests for path interpolation."""

  def _MakeKnowledgeBase(self):
    kb = rdf_client.KnowledgeBase()
    kb.users.Append(
        rdf_client.User(
            username="test",
            userdomain="TESTDOMAIN",
            full_name="test user",
            homedir="c:\\Users\\test",
            last_logon=rdfvalue.RDFDatetime.FromHumanReadable("2012-11-10")))
    kb.users.Append(
        rdf_client.User(
            username="test2",
            userdomain="TESTDOMAIN",
            full_name="test user 2",
            homedir="c:\\Users\\test2",
            last_logon=100))
    return kb

  def testBasicInterpolation(self):
    """Test Basic."""
    kb = self._MakeKnowledgeBase()
    path = "{systemroot}\\test"
    new_path = flow_utils.InterpolatePath(path, kb, users=None)
    self.assertEqual(new_path.lower(), "c:\\windows\\test")

    new_path = flow_utils.InterpolatePath("{does_not_exist}", kb)
    self.assertEqual(new_path, "")

  def testUserInterpolation(self):
    """User interpolation returns a list of paths."""
    kb = self._MakeKnowledgeBase()
    path = "{homedir}\\dir"
    new_path = flow_utils.InterpolatePath(path, kb, users=["test"])
    self.assertEqual(new_path[0].lower(), "c:\\users\\test\\dir")

    path = "{systemroot}\\{last_logon}\\dir"
    new_path = flow_utils.InterpolatePath(path, kb, users=["test"])
    self.assertEqual(new_path[0].lower(),
                     "c:\\windows\\2012-11-10 00:00:00\\dir")

    path = "{homedir}\\a"
    new_path = flow_utils.InterpolatePath(path, kb, users=["test", "test2"])
    self.assertLen(new_path, 2)
    self.assertEqual(new_path[0].lower(), "c:\\users\\test\\a")
    self.assertEqual(new_path[1].lower(), "c:\\users\\test2\\a")

    new_path = flow_utils.InterpolatePath(
        "{does_not_exist}", kb, users=["test"])
    self.assertEqual(new_path, [])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
