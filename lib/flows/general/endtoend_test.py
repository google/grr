#!/usr/bin/env python
"""Tests for grr.lib.flows.general.endtoend."""

# pylint: disable=unused-import, g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import, g-bad-import-order

from grr.endtoend_tests import base
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
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
    install_time = rdfvalue.RDFDatetime().Now()
    user = "testuser"
    userobj = rdfvalue.User(username=user)
    interface = rdfvalue.Interface(ifname="eth0")
    self.client = aff4.FACTORY.Create(self.client_id, "VFSGRRClient", mode="rw",
                                      token=self.token, age=aff4.ALL_TIMES)
    self.client.Set(self.client.Schema.HOSTNAME("hostname"))
    self.client.Set(self.client.Schema.SYSTEM("Linux"))
    self.client.Set(self.client.Schema.OS_RELEASE("debian"))
    self.client.Set(self.client.Schema.OS_VERSION("14.04"))
    self.client.Set(self.client.Schema.KERNEL("3.15-rc2"))
    self.client.Set(self.client.Schema.FQDN("hostname.example.com"))
    self.client.Set(self.client.Schema.ARCH("x86_64"))
    self.client.Set(self.client.Schema.INSTALL_DATE(install_time))
    self.client.Set(self.client.Schema.USER([userobj]))
    self.client.Set(self.client.Schema.USERNAMES([user]))
    self.client.Set(self.client.Schema.LAST_INTERFACES([interface]))
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
    install_time = rdfvalue.RDFDatetime().Now()
    user = "testuser"
    userobj = rdfvalue.User(username=user)
    interface = rdfvalue.Interface(ifname="eth0")
    self.client = aff4.FACTORY.Create(self.client_id, "VFSGRRClient", mode="rw",
                                      token=self.token, age=aff4.ALL_TIMES)

    self.client.Set(self.client.Schema.HOSTNAME("hostname"))
    self.client.Set(self.client.Schema.SYSTEM("Windows"))
    self.client.Set(self.client.Schema.OS_RELEASE("7"))
    self.client.Set(self.client.Schema.OS_VERSION("6.1.7601SP1"))
    self.client.Set(self.client.Schema.KERNEL("6.1.7601"))
    self.client.Set(self.client.Schema.FQDN("hostname.example.com"))
    self.client.Set(self.client.Schema.ARCH("AMD64"))
    self.client.Set(self.client.Schema.INSTALL_DATE(install_time))
    self.client.Set(self.client.Schema.USER([userobj]))
    self.client.Set(self.client.Schema.USERNAMES([user]))
    self.client.Set(self.client.Schema.LAST_INTERFACES([interface]))
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


class FlowTestLoader(test_lib.GRRTestLoader):
  base_class = TestEndToEndTestFlow


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv, testLoader=FlowTestLoader())

if __name__ == "__main__":
  flags.StartMain(main)
