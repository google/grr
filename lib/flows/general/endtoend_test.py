#!/usr/bin/env python
"""Tests for grr.lib.flows.general.endtoend."""

from grr.endtoend_tests import base
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils


class MockEndToEndTest(base.AutomatedTest):
  platforms = ["Linux", "Darwin"]
  flow = "ListDirectory"
  args = {"pathspec": rdfvalue.PathSpec(
      path="/bin",
      pathtype=rdfvalue.PathSpec.PathType.OS)}

  output_path = "/fs/os/bin"
  file_to_find = "ls"

  def setUp(self):
    pass

  def CheckFlow(self):
    pass

  def tearDown(self):
    pass


class MockEndToEndTestBadFlow(MockEndToEndTest):
  flow = "RaiseOnStart"
  args = {}


class TestBadSetUp(MockEndToEndTest):

  def setUp(self):
    raise RuntimeError


class TestBadTearDown(MockEndToEndTest):

  def tearDown(self):
    raise RuntimeError


class TestFailure(MockEndToEndTest):

  def CheckFlow(self):
    raise RuntimeError("This should be logged")


class TestEndToEndTestFlow(test_lib.FlowTestsBaseclass):

  def setUp(self):
    super(TestEndToEndTestFlow, self).setUp()
    summary = rdfvalue.ClientSummary(system_info=rdfvalue.Uname(
        system="Linux",
        node="hostname",
        release="debian",
        version="14.04",
        machine="x86_64",
        kernel="3.15-rc2",
        fqdn="hostname.example.com"))
    self.client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    self.client.Set(self.client.SchemaCls.SUMMARY(summary))
    self.client.Flush()
    self.client_mock = action_mocks.ActionMock("ListDirectory", "StatFile")

  def testRunSuccess(self):
    args = rdfvalue.EndToEndTestFlowArgs(
        test_names=["TestListDirectoryOSLinuxDarwin",
                    "MockEndToEndTest",
                    "TestListDirectoryOSLinuxDarwin"])

    with test_lib.Instrument(flow.GRRFlow, "SendReply") as send_reply:
      for _ in test_lib.TestFlowHelper(
          "EndToEndTestFlow", self.client_mock, client_id=self.client_id,
          token=self.token, args=args):
        pass

      results = []
      for _, reply in send_reply.args:
        if isinstance(reply, rdfvalue.EndToEndTestResult):
          results.append(reply)
          self.assertTrue(reply.success)
          self.assertTrue(reply.test_class_name in [
              "TestListDirectoryOSLinuxDarwin", "MockEndToEndTest"])
          self.assertFalse(reply.log)

      # We only expect 2 results because we dedup test names
      self.assertEqual(len(results), 2)

  def testNoApplicableTests(self):
    """Try to run linux tests on windows."""
    summary = rdfvalue.ClientSummary(system_info=rdfvalue.Uname(
        system="Windows",
        node="hostname",
        release="7",
        version="6.1.7601SP1",
        machine="AMD64",
        kernel="6.1.7601",
        fqdn="hostname.example.com"))
    self.client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    self.client.Set(self.client.SchemaCls.SUMMARY(summary))
    self.client.Flush()

    args = rdfvalue.EndToEndTestFlowArgs(
        test_names=["TestListDirectoryOSLinuxDarwin",
                    "MockEndToEndTest",
                    "TestListDirectoryOSLinuxDarwin"])

    self.assertRaises(flow.FlowError, list, test_lib.TestFlowHelper(
        "EndToEndTestFlow", self.client_mock, client_id=self.client_id,
        token=self.token, args=args))

  def testRunSuccessAndFail(self):
    args = rdfvalue.EndToEndTestFlowArgs()

    with utils.Stubber(base.AutomatedTest, "classes",
                       {"MockEndToEndTest": MockEndToEndTest,
                        "TestFailure": TestFailure}):
      with test_lib.Instrument(flow.GRRFlow, "SendReply") as send_reply:
        for _ in test_lib.TestFlowHelper(
            "EndToEndTestFlow", self.client_mock, client_id=self.client_id,
            token=self.token, args=args):
          pass

        results = []
        for _, reply in send_reply.args:
          if isinstance(reply, rdfvalue.EndToEndTestResult):
            results.append(reply)
            if reply.test_class_name == "MockEndToEndTest":
              self.assertTrue(reply.success)
              self.assertFalse(reply.log)
            elif reply.test_class_name == "TestFailure":
              self.assertFalse(reply.success)
              self.assertTrue("This should be logged" in reply.log)

        self.assertItemsEqual([x.test_class_name for x in results],
                              ["MockEndToEndTest", "TestFailure"])
        self.assertEqual(len(results), 2)

  def testRunBadSetUp(self):
    args = rdfvalue.EndToEndTestFlowArgs(
        test_names=["TestBadSetUp"])

    self.assertRaises(RuntimeError, list, test_lib.TestFlowHelper(
        "EndToEndTestFlow", self.client_mock, client_id=self.client_id,
        token=self.token, args=args))

  def testRunBadTearDown(self):
    args = rdfvalue.EndToEndTestFlowArgs(
        test_names=["TestBadTearDown"])

    self.assertRaises(RuntimeError, list, test_lib.TestFlowHelper(
        "EndToEndTestFlow", self.client_mock, client_id=self.client_id,
        token=self.token, args=args))

  def testRunBadFlow(self):
    """Test behaviour when test flow raises in Start.

    A flow that raises in its Start method will kill the EndToEndTest run.
    Protecting and reporting on this significantly complicates this code, and a
    flow raising in Start is really broken, so we allow this behaviour.
    """
    args = rdfvalue.EndToEndTestFlowArgs(
        test_names=["MockEndToEndTestBadFlow", "MockEndToEndTest"])

    self.assertRaises(RuntimeError, list, test_lib.TestFlowHelper(
        "EndToEndTestFlow", self.client_mock, client_id=self.client_id,
        token=self.token, args=args))

  def testEndToEndTestFailure(self):
    args = rdfvalue.EndToEndTestFlowArgs(
        test_names=["TestFailure"])

    with test_lib.Instrument(flow.GRRFlow, "SendReply") as send_reply:

      for _ in test_lib.TestFlowHelper(
          "EndToEndTestFlow", self.client_mock, client_id=self.client_id,
          token=self.token, args=args):
        pass

      results = []
      for _, reply in send_reply.args:
        if isinstance(reply, rdfvalue.EndToEndTestResult):
          results.append(reply)
          self.assertFalse(reply.success)
          self.assertEqual(reply.test_class_name,
                           "TestFailure")
          self.assertTrue("This should be logged" in reply.log)

      self.assertEqual(len(results), 1)
