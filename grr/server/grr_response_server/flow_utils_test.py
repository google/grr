#!/usr/bin/env python
"""Tests for flow utils classes."""


from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib.rdfvalues import client as rdf_client
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import flow_utils
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class TestInterpolatePath(flow_test_lib.FlowTestsBaseclass):
  """Tests for path interpolation."""

  def _MakeClientRecord(self):
    # Set up client info
    client_id = self.SetupClient(0)
    client = aff4.FACTORY.Open(client_id, mode="rw", token=self.token)
    client.Set(client.Schema.SYSTEM("Windows"))
    kb = client.Get(client.Schema.KNOWLEDGE_BASE)
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
    client.Set(kb)
    client.Flush()
    return client

  def testBasicInterpolation(self):
    """Test Basic."""
    client = self._MakeClientRecord()
    path = "{systemroot}\\test"
    new_path = flow_utils.InterpolatePath(path, client, users=None)
    self.assertEqual(new_path.lower(), "c:\\windows\\test")

    new_path = flow_utils.InterpolatePath("{does_not_exist}", client)
    self.assertEqual(new_path, "")

  def testUserInterpolation(self):
    """User interpolation returns a list of paths."""
    client = self._MakeClientRecord()
    path = "{homedir}\\dir"
    new_path = flow_utils.InterpolatePath(path, client, users=["test"])
    self.assertEqual(new_path[0].lower(), "c:\\users\\test\\dir")

    path = "{systemroot}\\{last_logon}\\dir"
    new_path = flow_utils.InterpolatePath(path, client, users=["test"])
    self.assertEqual(new_path[0].lower(),
                     "c:\\windows\\2012-11-10 00:00:00\\dir")

    path = "{homedir}\\a"
    new_path = flow_utils.InterpolatePath(path, client, users=["test", "test2"])
    self.assertEqual(len(new_path), 2)
    self.assertEqual(new_path[0].lower(), "c:\\users\\test\\a")
    self.assertEqual(new_path[1].lower(), "c:\\users\\test2\\a")

    new_path = flow_utils.InterpolatePath(
        "{does_not_exist}", client, users=["test"])
    self.assertEqual(new_path, [])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
