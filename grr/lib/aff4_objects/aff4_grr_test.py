#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""Test the grr aff4 objects."""

import time

from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths


class MockChangeEvent(flow.EventListener):
  EVENTS = ["MockChangeEvent"]

  well_known_session_id = rdfvalue.SessionID(
      flow_name="MockChangeEventHandler")

  CHANGED_URNS = []

  @flow.EventHandler(allow_client_access=True)
  def ProcessMessage(self, message=None, event=None):
    _ = event
    if (message.auth_state !=
        rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED):
      return

    urn = rdfvalue.RDFURN(message.payload)
    MockChangeEvent.CHANGED_URNS.append(urn)


class AFF4GRRTest(test_lib.AFF4ObjectTest):
  """Test the client aff4 implementation."""

  def setUp(self):
    super(AFF4GRRTest, self).setUp()
    MockChangeEvent.CHANGED_URNS = []

  def testPathspecToURN(self):
    """Test the pathspec to URN conversion function."""
    pathspec = rdf_paths.PathSpec(
        path="\\\\.\\Volume{1234}\\", pathtype=rdf_paths.PathSpec.PathType.OS,
        mount_point="/c:/").Append(
            path="/windows",
            pathtype=rdf_paths.PathSpec.PathType.TSK)

    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
        pathspec, "C.1234567812345678")
    self.assertEqual(
        urn, rdfvalue.RDFURN(
            r"aff4:/C.1234567812345678/fs/tsk/\\.\Volume{1234}\/windows"))

    # Test an ADS
    pathspec = rdf_paths.PathSpec(
        path="\\\\.\\Volume{1234}\\", pathtype=rdf_paths.PathSpec.PathType.OS,
        mount_point="/c:/").Append(
            pathtype=rdf_paths.PathSpec.PathType.TSK,
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

    kb = fd.Schema.KNOWLEDGE_BASE()
    for i in range(5):
      kb.users.Append(rdf_client.User(username="user%s" % i))
    fd.Set(kb)
    fd.Close()

    for i, user in enumerate(
        fd.GetValuesForAttribute("KnowledgeBase.users").next()):
      self.assertEqual(user.username, "user%s" % i)

  def testVFSFileContentLastNotUpdated(self):
    """Make sure CONTENT_LAST does not update when only STAT is written.."""
    path = "/C.12345/contentlastchecker"

    timestamp = 1
    with utils.Stubber(time, "time", lambda: timestamp):
      fd = aff4.FACTORY.Create(path, "VFSFile", mode="w", token=self.token)

      timestamp += 1
      fd.SetChunksize(10)

      # Make lots of small writes - The length of this string and the chunk size
      # are relative primes for worst case.
      for i in range(100):
        fd.Write("%s%08X\n" % ("Test", i))

        # Flush after every write.
        fd.Flush()

        # And advance the time.
        timestamp += 1

      fd.Set(fd.Schema.STAT, rdf_client.StatEntry())

      fd.Close()

    fd = aff4.FACTORY.Open(path, mode="rw", token=self.token)
    # Make sure the attribute was written when the write occured.
    self.assertEqual(int(fd.GetContentAge()), 101000000)

    # Write the stat (to be the same as before, but this still counts
    # as a write).
    fd.Set(fd.Schema.STAT, fd.Get(fd.Schema.STAT))
    fd.Flush()

    fd = aff4.FACTORY.Open(path, token=self.token)

    # The age of the content should still be the same.
    self.assertEqual(int(fd.GetContentAge()), 101000000)

  def testGetClientSummary(self):
    hostname = "test"
    system = "Linux"
    os_release = "12.02"
    kernel = "3.15-rc2"
    fqdn = "test.test.com"
    arch = "amd64"
    install_time = rdfvalue.RDFDatetime().Now()
    user = "testuser"
    userobj = rdf_client.User(username=user)
    interface = rdf_client.Interface(ifname="eth0")

    timestamp = 1
    with utils.Stubber(time, "time", lambda: timestamp):
      with aff4.FACTORY.Create("C.0000000000000000", "VFSGRRClient", mode="rw",
                               token=self.token) as fd:
        kb = rdf_client.KnowledgeBase()
        kb.users.Append(userobj)
        empty_summary = fd.GetSummary()
        self.assertEqual(empty_summary.client_id, "C.0000000000000000")
        self.assertFalse(empty_summary.system_info.version)
        self.assertEqual(empty_summary.timestamp.AsSecondsFromEpoch(), 1)

        # This will cause TYPE to be written with current time = 101 when the
        # object is closed
        timestamp += 100
        fd.Set(fd.Schema.HOSTNAME(hostname))
        fd.Set(fd.Schema.SYSTEM(system))
        fd.Set(fd.Schema.OS_RELEASE(os_release))
        fd.Set(fd.Schema.KERNEL(kernel))
        fd.Set(fd.Schema.FQDN(fqdn))
        fd.Set(fd.Schema.ARCH(arch))
        fd.Set(fd.Schema.INSTALL_DATE(install_time))
        fd.Set(fd.Schema.KNOWLEDGE_BASE(kb))
        fd.Set(fd.Schema.USERNAMES([user]))
        fd.Set(fd.Schema.LAST_INTERFACES([interface]))

      with aff4.FACTORY.Open("C.0000000000000000", "VFSGRRClient", mode="rw",
                             token=self.token) as fd:
        summary = fd.GetSummary()
        self.assertEqual(summary.system_info.node, hostname)
        self.assertEqual(summary.system_info.system, system)
        self.assertEqual(summary.system_info.release, os_release)
        self.assertEqual(summary.system_info.kernel, kernel)
        self.assertEqual(summary.system_info.fqdn, fqdn)
        self.assertEqual(summary.system_info.machine, arch)
        self.assertEqual(summary.system_info.install_date, install_time)
        self.assertItemsEqual(summary.users, [userobj])
        self.assertItemsEqual(summary.interfaces, [interface])
        self.assertFalse(summary.client_info)

        self.assertEqual(summary.timestamp.AsSecondsFromEpoch(), 101)
