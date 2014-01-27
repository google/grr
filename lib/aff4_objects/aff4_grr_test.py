#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""Test the grr aff4 objects."""


from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import test_lib


class MockChangeEvent(flow.EventListener):
  EVENTS = ["MockChangeEvent"]

  well_known_session_id = rdfvalue.SessionID(
      "aff4:/flows/W:MockChangeEventHandler")

  CHANGED_URNS = []

  @flow.EventHandler(allow_client_access=True)
  def ProcessMessage(self, message=None, event=None):
    _ = event
    if (message.auth_state !=
        rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED):
      return

    urn = rdfvalue.RDFURN(message.args)
    MockChangeEvent.CHANGED_URNS.append(urn)


class AFF4GRRTest(test_lib.AFF4ObjectTest):
  """Test the client aff4 implementation."""

  def setUp(self):
    super(AFF4GRRTest, self).setUp()
    MockChangeEvent.CHANGED_URNS = []

  def testPathspecToURN(self):
    """Test the pathspec to URN conversion function."""
    pathspec = rdfvalue.PathSpec(
        path="\\\\.\\Volume{1234}\\", pathtype=rdfvalue.PathSpec.PathType.OS,
        mount_point="/c:/").Append(
            path="/windows",
            pathtype=rdfvalue.PathSpec.PathType.TSK)

    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
        pathspec, "C.1234567812345678")
    self.assertEqual(
        urn, rdfvalue.RDFURN(
            r"aff4:/C.1234567812345678/fs/tsk/\\.\Volume{1234}\/windows"))

    # Test an ADS
    pathspec = rdfvalue.PathSpec(
        path="\\\\.\\Volume{1234}\\", pathtype=rdfvalue.PathSpec.PathType.OS,
        mount_point="/c:/").Append(
            pathtype=rdfvalue.PathSpec.PathType.TSK,
            path="/Test Directory/notes.txt:ads",
            inode=66,
            ntfs_type=128,
            ntfs_id=2)

    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
        pathspec, "C.1234567812345678")
    self.assertEqual(
        urn, rdfvalue.RDFURN(
            r"aff4:/C.1234567812345678/fs/tsk/\\.\Volume{1234}\/"
            "Test Directory/notes.txt:ads"))

  def testClientSubfieldGet(self):
    """Test we can get subfields of the client."""

    fd = aff4.FACTORY.Create("C.0000000000000000", "VFSGRRClient",
                             token=self.token, age=aff4.ALL_TIMES)

    users = fd.Schema.USER()
    for i in range(5):
      folder = "C:/Users/user%s" % i
      user = rdfvalue.User(username="user%s" % i)
      user.special_folders.app_data = folder
      users.Append(user)

    fd.AddAttribute(users)
    fd.Close()

    # Check the repeated Users array.
    for i, folder in enumerate(
        fd.GetValuesForAttribute("Users.special_folders.app_data")):
      self.assertEqual(folder, "C:/Users/user%s" % i)

  def testRegexChangeNotification(self):
    """Test the AFF4RegexNotificationRule rule."""
    client_name = "C." + "0" * 16

    # Create the notification rule.
    rule_fd = aff4.FACTORY.Create("aff4:/config/aff4_rules/new_rule",
                                  aff4_type="AFF4RegexNotificationRule",
                                  token=self.token)
    rule_fd.Set(rule_fd.Schema.CLIENT_PATH_REGEX("b.*"))
    rule_fd.Set(rule_fd.Schema.EVENT_NAME("MockChangeEvent"))
    rule_fd.Set(rule_fd.Schema.NOTIFY_ONLY_IF_NEW(0))
    rule_fd.Close()

    # Force notification rules to be reloaded.
    aff4.FACTORY.UpdateNotificationRules()

    fd = aff4.FACTORY.Create(rdfvalue.ClientURN(client_name).Add("a"),
                             token=self.token,
                             aff4_type="AFF4Object")
    fd.Close()

    worker_mock = test_lib.MockWorker(token=self.token)
    while worker_mock.Next():
      pass

    # No notifications are expected, because path doesn't match the regex
    self.assertEqual(len(MockChangeEvent.CHANGED_URNS), 0)

    fd = aff4.FACTORY.Create(rdfvalue.ClientURN(client_name).Add("b"),
                             token=self.token,
                             aff4_type="AFF4Object")
    fd.Close()

    while worker_mock.Next():
      pass

    # Now we get a notification, because the path matches
    self.assertEqual(len(MockChangeEvent.CHANGED_URNS), 1)
    self.assertEqual(MockChangeEvent.CHANGED_URNS[0],
                     rdfvalue.ClientURN(client_name).Add("b"))

    MockChangeEvent.CHANGED_URNS = []

    # Write again to the same file and check that there's notification again
    fd = aff4.FACTORY.Create(rdfvalue.ClientURN(client_name).Add("b"),
                             token=self.token,
                             aff4_type="AFF4Object")
    fd.Close()

    while worker_mock.Next():
      pass

    self.assertEqual(len(MockChangeEvent.CHANGED_URNS), 1)
    self.assertEqual(MockChangeEvent.CHANGED_URNS[0],
                     rdfvalue.ClientURN(client_name).Add("b"))

    MockChangeEvent.CHANGED_URNS = []

    # Change the rule to notify only if file is written for the first time
    rule_fd = aff4.FACTORY.Open("aff4:/config/aff4_rules/new_rule",
                                mode="rw",
                                token=self.token)
    rule_fd.Set(rule_fd.Schema.NOTIFY_ONLY_IF_NEW, rdfvalue.RDFInteger(1))
    rule_fd.Close()

    # Force update of the rules in the factory
    aff4.FACTORY.UpdateNotificationRules()

    # Check that we don't get a notification for overwriting existing file
    fd = aff4.FACTORY.Create(rdfvalue.ClientURN(client_name).Add("b"),
                             token=self.token,
                             aff4_type="AFF4Object")
    fd.Close()

    while worker_mock.Next():
      pass

    self.assertEqual(len(MockChangeEvent.CHANGED_URNS), 0)

    # Check that we do get a notification for writing a new file
    fd = aff4.FACTORY.Create(rdfvalue.ClientURN(client_name).Add("b2"),
                             token=self.token,
                             aff4_type="AFF4Object")
    fd.Close()

    while worker_mock.Next():
      pass

    self.assertEqual(len(MockChangeEvent.CHANGED_URNS), 1)
    self.assertEqual(MockChangeEvent.CHANGED_URNS[0],
                     rdfvalue.ClientURN(client_name).Add("b2"))
