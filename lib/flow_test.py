#!/usr/bin/env python

# Copyright 2010 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the flow."""


import pickle
import unittest


from grr.client import conf
from grr.client import vfs
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import test_lib
# These import populate the AFF4 registry
from grr.lib.flows import general
from grr.lib.flows import tests
from grr.proto import jobs_pb2
from grr.proto import sysinfo_pb2



class FlowResponseSerialization(flow.GRRFlow):
  """Demonstrate saving responses in the flow."""

  @flow.StateHandler(next_state="Response1")
  def Start(self, unused_message=None):
    self.CallClient("Test",
                    jobs_pb2.PrintStr(data="test"),
                    next_state="Response1")

  @flow.StateHandler(jobs_pb2.DataBlob, next_state="Response2")
  def Response1(self, messages):
    """Record the message id for testing."""
    self.messages = messages
    self.CallClient("Test",
                    jobs_pb2.PrintStr(data="test"),
                    next_state="Response2")

  @flow.StateHandler(jobs_pb2.DataBlob)
  def Response2(self, messages):
    # We need to receive one response and it must be the same as that stored in
    # the previous state.
    if (len(list(messages)) != 1 or
        messages.status.status != jobs_pb2.GrrStatus.OK or
        list(messages) != list(self.messages)):
      raise RuntimeError("Messages not serialized")


class FlowFactoryTest(test_lib.FlowTestsBaseclass):
  """Test the flow factory."""

  def testInitialization(self):
    """Test that WellKnownFlows are created."""
    aff4.AFF4Init()
    # Check that the well known flow is initialized
    flow_subject = (flow.FlowManager.FLOW_TASK_TEMPLATE %
                    test_lib.WellKnownSessionTest.well_known_session_id)

    # This should not raise
    data_store.DB.subjects[flow_subject]

  def testInvalidClientId(self):
    """Should raise if the client_id is invalid."""
    self.assertRaises(IOError, flow.FACTORY.StartFlow,
                      "hello", "FlowOrderTest")

  def testFetchReturn(self):
    """Check that we can Fetch and Return a flow."""
    session_id = flow.FACTORY.StartFlow(self.client_id, "FlowOrderTest")

    flow_pb = flow.FACTORY.FetchFlow(session_id, sync=False)

    # We should not be able to fetch the flow again since its leased
    # now:
    self.assertRaises(flow.LockError, flow.FACTORY.FetchFlow,
                      session_id, sync=False)

    # Ok now its returned
    flow.FACTORY.ReturnFlow(flow_pb)
    flow_pb = flow.FACTORY.FetchFlow(session_id)

    self.assert_(flow_pb)

  def testFlowSerialization(self):
    """Check that we can unpickle flows."""
    session_id = flow.FACTORY.StartFlow(self.client_id, "FlowOrderTest")

    flow_pb = flow.FACTORY.FetchFlow(session_id)

    flow_obj = flow.FACTORY.LoadFlow(flow_pb)

    self.assertEqual(flow_obj.flow_pb.__class__, jobs_pb2.FlowPB)
    self.assertEqual(flow_obj.__class__, test_lib.FlowOrderTest)

    serialized = flow_obj.Dump()

    # Now try to unpickle it
    result = pickle.loads(serialized.pickle)

    self.assertEqual(result.flow_pb, None)

  def testFlowSerialization2(self):
    """Check that we can unpickle flows."""

    class TestClientMock(object):

      def Test(self, args):
        return [jobs_pb2.DataBlob(integer=100)]

    # Run the flow in the simulated way
    for _ in test_lib.TestFlowHelper("FlowResponseSerialization",
                                     TestClientMock(),
                                     client_id=self.client_id):
      pass


class FlowTest(test_lib.FlowTestsBaseclass):
  """Tests the Flow."""

  def testBrokenFlow(self):
    """Check that flows which call to incorrect states raise."""
    self.assertRaises(flow.FlowError, flow.FACTORY.StartFlow,
                      self.client_id, "BrokenFlow")

  def SendMessages(self, response_ids, session_id, authenticated=True):
    """Send messages to the flow."""
    for response_id in response_ids:
      message = jobs_pb2.GrrMessage()
      message.request_id = 1
      message.response_id = response_id
      message.session_id = session_id

      if authenticated:
        message.auth_state = jobs_pb2.GrrMessage.AUTHENTICATED

      self.SendMessage(message)

  def SendMessage(self, message):
    # Now messages are set in the data store
    response_attribute = flow.FlowManager.FLOW_RESPONSE_TEMPLATE % (
        message.request_id,
        message.response_id)

    data_store.DB.Set(
        flow.FlowManager.FLOW_STATE_TEMPLATE % message.session_id,
        response_attribute,
        message)

  def SendOKStatus(self, response_id, session_id):
    """Send a message to the flow."""
    message = jobs_pb2.GrrMessage()
    message.request_id = 1
    message.response_id = response_id
    message.session_id = session_id
    message.type = jobs_pb2.GrrMessage.STATUS
    message.auth_state = jobs_pb2.GrrMessage.AUTHENTICATED

    status = jobs_pb2.GrrStatus(status=jobs_pb2.GrrStatus.OK)
    message.args = status.SerializeToString()

    self.SendMessage(message)

    # Now also set the state on the RequestState
    request_state, _ = data_store.DB.Resolve(
        flow.FlowManager.FLOW_STATE_TEMPLATE % message.session_id,
        flow.FlowManager.FLOW_REQUEST_TEMPLATE % message.request_id,
        decoder=jobs_pb2.RequestState)

    request_state.status.CopyFrom(status)

    data_store.DB.Set(
        flow.FlowManager.FLOW_STATE_TEMPLATE % message.session_id,
        flow.FlowManager.FLOW_REQUEST_TEMPLATE % message.request_id,
        request_state)

    return message

  def testReordering(self):
    """Check that out of order client messages are reordered."""
    flow_pb = self.FlowSetup("FlowOrderTest")

    # Retrieve the flow object
    flow_obj = flow.FACTORY.LoadFlow(flow_pb)

    # Simultate processing messages arriving in random order
    message_ids = [2, 1, 4, 3, 5]
    self.SendMessages(message_ids, flow_pb.session_id)

    # Send the status message
    message = self.SendOKStatus(6, flow_pb.session_id)

    flow_obj.ProcessCompletedRequests([message])

    # Check that the messages were processed in order
    self.assertEqual(flow_obj.messages, [1, 2, 3, 4, 5])

  def testCallClient(self):
    """Flows can send client messages using CallClient()."""
    flow_pb = self.FlowSetup("FlowOrderTest")

    # Check that a message went out to the client
    tasks = flow.SCHEDULER.Query(self.client_id, limit=100,
                                 decoder=jobs_pb2.GrrMessage)

    self.assertEqual(len(tasks), 1)

    message = tasks[0].value

    self.assertEqual(message.session_id, flow_pb.session_id)
    self.assertEqual(message.request_id, 1)
    self.assertEqual(message.name, "Test")

  def testAuthentication1(self):
    """Test that flows refuse to processes unauthenticated messages."""
    flow_pb = self.FlowSetup("FlowOrderTest")

    # Retrieve the flow object
    flow_obj = flow.FACTORY.LoadFlow(flow_pb)

    # Simultate processing messages arriving in random order
    message_ids = [2, 1, 4, 3, 5]
    self.SendMessages(message_ids, flow_pb.session_id,
                      authenticated=False)

    # Send the status message
    message = self.SendOKStatus(6, flow_pb.session_id)

    flow_obj.ProcessCompletedRequests([message])

    # Now messages should actually be processed
    self.assertEqual(flow_obj.messages, [])

  def testAuthentication2(self):
    """Test that flows refuse to processes unauthenticated messages.

    Here we try to simulate an attacker injecting unauthenticated
    messages midstream.

    The current implementation actually fails to process the entire
    flow since the injected messages displace the real ones if they
    arrive earlier. This can be an effective DoS against legitimate
    clients but would require attackers to guess session ids.
    """
    flow_pb = self.FlowSetup("FlowOrderTest")

    # Retrieve the flow object
    flow_obj = flow.FACTORY.LoadFlow(flow_pb)

    # Simultate processing messages arriving in random order
    message_ids = [1, 2]
    self.SendMessages(message_ids, flow_pb.session_id,
                      authenticated=True)

    # Now suppose some of the messages are spoofed
    message_ids = [3, 4, 5]
    self.SendMessages(message_ids, flow_pb.session_id,
                      authenticated=False)

    # And now our real messages arrive
    message_ids = [5, 6]
    self.SendMessages(message_ids, flow_pb.session_id,
                      authenticated=True)

    # Send the status message
    message = self.SendOKStatus(7, flow_pb.session_id)

    flow_obj.ProcessCompletedRequests([message])

    # Some messages should actually be processed
    self.assertEqual(flow_obj.messages, [1, 2, 5, 6])

  def testWellKnownFlows(self):
    """Test the well known flows."""
    flow_pb = self.FlowSetup("WellKnownSessionTest")

    # Retrieve the flow object
    test_flow = flow.FACTORY.LoadFlow(flow_pb)

    # Make sure the session ID is well known
    self.assertEqual(test_flow.session_id,
                     test_lib.WellKnownSessionTest.well_known_session_id)

    # Messages to Well Known flows can be unauthenticated
    messages = [jobs_pb2.GrrMessage(args=str(i)) for i in range(10)]

    test_flow.ProcessCompletedRequests(messages)

    # Make sure that messages were processed even without a status
    # message to complete the transaction (Well known flows do not
    # have transactions or states - all messages always get to the
    # ProcessMessage method):
    self.assertEqual(test_flow.messages, range(10))


class GeneralFlowsTest(test_lib.FlowTestsBaseclass):
  """Tests some flows."""

  def testChainedFlow(self):
    """Test the ability to chain flows."""
    # Run the flow in the simulated way
    for _ in test_lib.TestFlowHelper("ParentFlow", ClientMock(),
                                     client_id=self.client_id):
      pass

  def testBrokenChainedFlow(self):
    """Test that exceptions are properly handled in chain flows."""

    # Run the flow in the simulated way
    for _ in test_lib.TestFlowHelper(
        "BrokenParentFlow", ClientMock(), client_id=self.client_id,
        check_flow_errors=False):
      pass

  def testIteratedDirectoryListing(self):
    """Test that the client iterator works."""
    path = "/mock/foobar"
    # Run the flow in the simulated way
    client_mock = test_lib.ActionMock("IteratedListDirectory")
    for _ in test_lib.TestFlowHelper(
        "IteratedListDirectory", client_mock, client_id=self.client_id,
        path=path):
      pass

    # The flow should have stored it in the AFF4 DIRECTORY attribute.
    fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add(self.client_id).Add(path))
    directory = fd.Get(fd.Schema.DIRECTORY)
    pb = jobs_pb2.Path(path=path, pathtype=jobs_pb2.Path.OS)
    directory2 = vfs.VFSHandlerFactory(pb).ListFiles()

    # Make sure that the resulting directory is what it should be
    for x, y in zip(directory, directory2):
      self.assertEqual(x, y)


# This registers the mock as a handler for paths which begin with /mock/
class MockVFSHandler(vfs.AbstractDirectoryHandler):
  """A mock VFS handler with fake files."""
  children = [jobs_pb2.StatResponse(path="Foo%s" % x) for x in range(10)]
  supported_pathtype = jobs_pb2.Path.OS

  def __init__(self, pathspec):
    path = pathspec.mountpoint + pathspec.path
    if not path.startswith("/mock/"):
      raise IOError("not mocking")

  def ListFiles(self):
    return self.children


class ClientMock(object):
  """Mock of client actions."""

  def Test(self, _):
    return [jobs_pb2.DataBlob(string="Hello World")]


class ChildFlow(flow.GRRFlow):
  """This flow will be called by our parent."""

  @flow.StateHandler(next_state="ReceiveHello")
  def Start(self):
    self.CallClient("Test", next_state="ReceiveHello")

  @flow.StateHandler()
  def ReceiveHello(self, responses):
    # Relay the client's message to our parent
    for response in responses:
      self.SendReply(jobs_pb2.DataBlob(string="Child received"))
      self.SendReply(response)


class BrokenChildFlow(ChildFlow):
  """A broken flow which raises."""

  @flow.StateHandler()
  def ReceiveHello(self, responses):
    raise IOError("Boo")


class ParentFlow(flow.GRRFlow):
  """This flow will launch a child flow."""

  @flow.StateHandler(next_state="ParentReceiveHello")
  def Start(self):
    # Call the child flow.
    self.CallFlow("ChildFlow",
                  next_state="ParentReceiveHello")

  @flow.StateHandler(jobs_pb2.DataBlob)
  def ParentReceiveHello(self, responses):
    responses = list(responses)
    if (len(responses) != 2 or "Child" not in responses[0].string or
        "Hello" not in responses[1].string):
      raise RuntimeError("Messages not passed to parent")


class BrokenParentFlow(flow.GRRFlow):
  """This flow will launch a broken child flow."""

  @flow.StateHandler(next_state="ReceiveHello")
  def Start(self):
    # Call the child flow.
    self.CallFlow("BrokenChildFlow",
                  next_state="ReceiveHello")

  @flow.StateHandler(jobs_pb2.DataBlob)
  def ReceiveHello(self, responses):
    if (responses or
        responses.status.status == jobs_pb2.GrrStatus.OK):
      raise RuntimeError("Error not propagated to parent")


class FlowTestLoader(unittest.TestLoader):
  """A test suite loader which searches for tests in all the plugins."""

  def loadTestsFromModule(self, _):
    """Just return all the tests as if they were in the same module."""
    test_cases = [self.loadTestsFromTestCase(x)
                  for x in test_lib.FlowTestsBaseclass.classes.values()]
    return self.suiteClass(test_cases)

  def loadTestsFromName(self, name, module=None):
    """Load the tests named."""
    parts = name.split(".")
    test_cases = self.loadTestsFromTestCase(
        test_lib.FlowTestsBaseclass.classes[parts[0]])

    # Specifies the whole test suite.
    if len(parts) == 1:
      return self.suiteClass(test_cases)
    elif len(parts) == 2:
      cls = test_lib.FlowTestsBaseclass.classes[parts[0]]
      return unittest.TestSuite([cls(parts[1])])


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv, testLoader=FlowTestLoader())

if __name__ == "__main__":
  conf.StartMain(main)
