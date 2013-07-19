#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.

"""Tests for flow utils classes."""


# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow_utils
from grr.lib import rdfvalue
from grr.lib import test_lib


class TestInterpolatePath(test_lib.FlowTestsBaseclass):
  """Tests for path interpolation."""

  def setUp(self):
    super(TestInterpolatePath, self).setUp()
    # Set up client info
    self.client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    self.client.Set(self.client.Schema.SYSTEM("Windows"))
    user_list = self.client.Schema.USER()
    user_list.Append(username="test",
                     domain="TESTDOMAIN",
                     full_name="test user",
                     homedir="c:\\Users\\test",
                     last_logon=rdfvalue.RDFDatetime("2012-11-10"))

    user_list.Append(username="test2",
                     domain="TESTDOMAIN",
                     full_name="test user 2",
                     homedir="c:\\Users\\test2",
                     last_logon=100)

    self.client.AddAttribute(self.client.Schema.USER, user_list)
    self.client.Close()
    self.client = aff4.FACTORY.Open(self.client_id, token=self.token)

  def testBasicInterpolation(self):
    """Test Basic."""
    path = "{systemroot}\\test"
    new_path = flow_utils.InterpolatePath(path, self.client, users=None)
    self.assertEqual(new_path.lower(), "c:\\windows\\test")

    new_path = flow_utils.InterpolatePath("{does_not_exist}", self.client)
    self.assertEqual(new_path, "")

  def testUserInterpolation(self):
    """User interpolation returns a list of paths."""
    path = "{homedir}\\dir"
    new_path = flow_utils.InterpolatePath(path, self.client, users=["test"])
    self.assertEqual(new_path[0].lower(), "c:\\users\\test\\dir")

    path = "{systemroot}\\{last_logon}\\dir"
    new_path = flow_utils.InterpolatePath(path, self.client, users=["test"])
    self.assertEqual(new_path[0].lower(),
                     "c:\\windows\\2012-11-10 00:00:00\\dir")

    path = "{homedir}\\a"
    new_path = flow_utils.InterpolatePath(path, self.client,
                                          users=["test", "test2"])
    self.assertEqual(len(new_path), 2)
    self.assertEqual(new_path[0].lower(), "c:\\users\\test\\a")
    self.assertEqual(new_path[1].lower(), "c:\\users\\test2\\a")

    new_path = flow_utils.InterpolatePath("{does_not_exist}", self.client,
                                          users=["test"])
    self.assertEqual(new_path, [])


class TestClientPathHelper(test_lib.GRRBaseTest):
  """Tests for ClientPathHelper class."""

  def testClientPathHelper(self):
    """Test ClientPathHelper."""
    client_id = "C.%016X" % 0

    # Set up a test client
    root_urn = aff4.ROOT_URN.Add(client_id)

    client = aff4.FACTORY.Create(root_urn, "VFSGRRClient", token=self.token)

    # Set up the operating system information
    client.Set(client.Schema.SYSTEM("Windows"))

    client.Set(client.Schema.OS_RELEASE("7"))

    client.Set(client.Schema.OS_VERSION("6.1.7600"))

    # Add a user account to the client
    users_list = client.Schema.USER()
    users_list.Append(
        username="Administrator",
        comment="Built-in account for administering the computer/domain",
        last_logon=1296205801,
        domain="MYDOMAIN",
        homedir="C:\\Users\\Administrator")

    client.AddAttribute(client.Schema.USER, users_list)
    client.Close()

    # Run tests
    path_helper = flow_utils.ClientPathHelper(client_id, token=self.token)

    self.assertEqual(path_helper.GetPathSeparator(),
                     u"\\")

    self.assertEqual(path_helper.GetDefaultUsersPath(),
                     u"C:\\Users")

    self.assertEqual(path_helper.GetHomeDirectory("Administrator"),
                     u"C:\\Users\\Administrator")


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
