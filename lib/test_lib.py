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

"""A library for tests."""


import os
import pdb
import socket
import sys
import time
import unittest


from google.protobuf import text_format
from grr.client import conf as flags
import logging
import selenium

from grr.client import actions
from grr.client import conf
from grr.lib import aff4
from grr.lib import data_store
# Load the fake data store implementation
from grr.lib import fake_data_store
from grr.lib import flow
from grr.lib import registry
from grr.lib import utils
from grr.proto import jobs_pb2
from grr.test_data import client_fixture

# Default for running in the current directory
flags.DEFINE_string("test_srcdir",
                    default=os.getcwd(),
                    help="The directory where tests are built.")
flags.DEFINE_string("test_tmpdir", "/tmp/",
                    help="Somewhere to write temporary files.")
flags.DEFINE_integer("selenium_port", 4444,
                    help="Port for local selenium server.")


flags.DEFINE_string("test_datadir",
                    default="grr/test_data",
                    help="The directory relative to the srcdir "
                    "where test data exist.")

flags.DEFINE_string("test_keydir",
                    default="grr/keys/test",
                    help="The directory relative to the srcdir "
                    "where test keys exist.")

flags.DEFINE_string("test_data_store", "FakeDataStore",
                    "The data store to run the tests against.")

flags.DEFINE_bool("nomock", False,
                  "Run client tests on real system not a mock.")


FLAGS = flags.FLAGS


#  Since GRRFlow is an abstract class we have some concrete
#  implementations here for testing.


class FlowOrderTest(flow.GRRFlow):
  """Tests ordering of inbound messages."""

  def __init__(self, *args, **kwargs):
    self.messages = []
    flow.GRRFlow.__init__(self, *args, **kwargs)

  @flow.StateHandler(next_state="Incoming")
  def Start(self, unused_message=None):
    self.CallClient("Test", data="test",
                    next_state="Incoming")

  @flow.StateHandler(auth_required=True)
  def Incoming(self, responses):
    """Record the message id for testing."""
    self.messages = []

    for _ in responses:
      self.messages.append(responses.message.response_id)


class SendingFlow(flow.GRRFlow):
  """Tests sending messages to clients."""

  def __init__(self, message_count, *args, **kwargs):
    self.message_count = message_count
    flow.GRRFlow.__init__(self, *args, **kwargs)

  @flow.StateHandler(next_state="Process")
  def Start(self, unused_response=None):
    """Just send a few messages."""
    for unused_i in range(0, self.message_count):
      self.CallClient("ReadBuffer", next_state="Process")


class BrokenFlow(flow.GRRFlow):
  """A flow which does things wrongly."""

  @flow.StateHandler(next_state="Process")
  def Start(self, unused_response=None):
    """Send a message to an incorrect state."""
    self.CallClient("ReadBuffer", next_state="WrongProcess")


class WellKnownSessionTest(flow.WellKnownFlow):
  """Tests the well known flow implementation."""
  well_known_session_id = "test:TestSessionId"

  def __init__(self, *args, **kwargs):
    self.messages = []
    flow.WellKnownFlow.__init__(self, *args, **kwargs)

  def ProcessMessage(self, message):
    """Record the message id for testing."""
    self.messages.append(int(message.args))


class GRRBaseTest(unittest.TestCase):
  """This is the base class for all GRR tests."""

  def setUp(self):
    # We want to use the fake usually
    FLAGS.storage = FLAGS.test_data_store
    aff4.AFF4Init(flush=True)

    conf.PARSER.parse_args()
    self.base_path = os.path.join(FLAGS.test_srcdir, FLAGS.test_datadir)
    self.key_path = os.path.join(FLAGS.test_srcdir, FLAGS.test_keydir)

  def shortDescription(self):
    doc = self._testMethodDoc or ""
    doc = doc.split("\n")[0].strip()
    return "%s - %s\n" % (self, doc)


class EmptyActionTest(GRRBaseTest):
  """Test the client Actions."""

  def RunAction(self, action_name, arg=None):
    """Run an action and generate responses.

    Args:
       action_name: The action to run.
       arg: A protobuf to pass the action.

    Returns:
      A list of response protobufs.
    """
    if arg is None: arg = jobs_pb2.GrrMessage()

    message = jobs_pb2.GrrMessage(name=action_name,
                                  args=arg.SerializeToString())
    action_cls = actions.ActionPlugin.classes[message.name]
    results = []

    # Monkey patch a mock SendReply() method
    def MockSendReply(self, reply=None, **kwargs):
      if reply is None:
        reply = self.out_protobuf(**kwargs)
      results.append(reply)

    action_cls.SendReply = MockSendReply

    action = action_cls(message=message)
    action.Run(arg)

    return results


class FlowTestsBaseclass(GRRBaseTest):
  """Tests the Flow Factory."""
  client_id = "C." + "A" * 16

  __metaclass__ = registry.MetaclassRegistry

  def setUp(self):
    GRRBaseTest.setUp(self)

    # Create a client for testing
    fd = aff4.FACTORY.Create(self.client_id, "VFSGRRClient")
    fd.Set(fd.Schema.CERT, aff4.FACTORY.RDFValue("RDFX509Cert")(
        open(os.path.join(self.key_path, "cert.pem")).read()))
    fd.Close()

  def tearDown(self):
    data_store.DB.Flush()

  def FlowSetup(self, name):
    session_id = flow.FACTORY.StartFlow(self.client_id, name)
    flow_pb = flow.FACTORY.FetchFlow(session_id)

    return flow_pb


class GRRSeleniumTest(GRRBaseTest):
  """Baseclass for selenium UI tests."""

  __metaclass__ = registry.MetaclassRegistry

  # Default duration for WaitUntil.
  duration = 60

  def setUp(self):
    self.selenium = selenium.selenium("localhost", FLAGS.selenium_port,
                                      "*chrome", "http://localhost:%s/" % FLAGS.port)
    self.selenium.start()

  def tearDown(self):
    self.selenium.stop()

  def WaitUntil(self, condition_cb, *args):
    for _ in range(self.duration):
      if condition_cb(*args): return True

    raise RuntimeError("condition not met.")

  def WaitUntilEqual(self, target, condition_cb, *args):
    for _ in range(self.duration):
      try:
        if condition_cb(*args) == target:
          return True

      # The element might not exist yet and selenium could raise here.
      except Exception: pass
      time.sleep(0.5)


class MockClient(object):
  def __init__(self, client_id, client_mock):
    self.client_id = client_id
    self.client_mock = client_mock

  def PushToStateQueue(self, message, **kw):
    # Assume the client is authorized
    message.auth_state = jobs_pb2.GrrMessage.AUTHENTICATED

    # Update kw args
    for k, v in kw.items():
      setattr(message, k, v)

    queue_name = flow.FlowManager.FLOW_STATE_TEMPLATE % message.session_id

    attribute_name = flow.FlowManager.FLOW_RESPONSE_TEMPLATE % (
        message.request_id, message.response_id)

    data_store.DB.Set(queue_name, attribute_name, message.SerializeToString())

  def Next(self):
    # Grab tasks for us from the queue
    request_tasks = flow.SCHEDULER.QueryAndOwn(self.client_id,
                                               decoder=jobs_pb2.GrrMessage)
    # Remove these from the client queue
    flow.SCHEDULER.Delete(self.client_id, request_tasks)

    for task in request_tasks:
      message = task.value
      response_id = 1
      # Collect all responses for this message from the client mock
      try:
        try:
          logging.debug("Calling %s", message)
          responses = self.client_mock.HandleMessage(message)
        except AttributeError:
          responses = getattr(self.client_mock, message.name)(message.args)

        status = jobs_pb2.GrrStatus()
      except StandardError, e:
        logging.exception("Error %s occurred in client", e)
        # Error occurred.
        responses = []
        status = jobs_pb2.GrrStatus(status=jobs_pb2.GrrStatus.GENERIC_ERROR)

      # Now insert those on the flow state queue
      for response in responses:
        if not isinstance(response, jobs_pb2.GrrMessage):
          response = jobs_pb2.GrrMessage(
              session_id=message.session_id, name=message.name,
              response_id=response_id, request_id=message.request_id,
              args=response.SerializeToString())
        self.PushToStateQueue(response)

        response_id += 1

      # Add a Status message to the end
      self.PushToStateQueue(message, response_id=response_id,
                            args=status.SerializeToString(),
                            type=jobs_pb2.GrrMessage.STATUS)

      # Additionally schedule a task for the worker
      queue_name = message.session_id.split(":")[0]
      task = flow.SCHEDULER.Task(queue=queue_name, value=message)
      flow.SCHEDULER.Schedule([task])

    return len(request_tasks)


class MockWorker(object):
  """Mock the worker."""

  def __init__(self, queue_name="W", check_flow_errors=True):
    self.queue_name = queue_name
    self.check_flow_errors = check_flow_errors

  def Next(self):
    """Very simple emulator of the worker.

    We wake each flow in turn and run it.

    Returns:
      total number of flows still alive.

    Raises:
      RuntimeError: if the flow terminates with an error.
    """
    # Grab tasks for us from the queue
    request_tasks = flow.SCHEDULER.QueryAndOwn(self.queue_name,
                                               decoder=jobs_pb2.GrrMessage)
    # Remove these from the client queue
    flow.SCHEDULER.Delete(self.queue_name, request_tasks)

    # Run all the flows until they are finished
    run_sessions = []

    for task in request_tasks:
      message = task.value

      # Unpack the flow
      flow_pb = flow.FACTORY.FetchFlow(message.session_id)
      flow_obj = flow.FACTORY.LoadFlow(flow_pb)

      # Make note that we ran this flow
      run_sessions.append(message.session_id)

      # Run it
      flow_obj.ProcessCompletedRequests([message])

      # Pack it back up
      flow_pb = flow_obj.Dump()
      if self.check_flow_errors and flow_pb.state == jobs_pb2.FlowPB.ERROR:
        logging.exception("Flow terminated in state %s with an error: %s",
                          flow_obj.current_state, flow_pb.backtrace)
        raise RuntimeError()

      flow.FACTORY.ReturnFlow(flow_pb)

    return run_sessions


class ActionMock(object):
  """A client mock which runs a real action.

  This can be used as input for TestFlowHelper.
  """

  def __init__(self, *action_names):
    self.action_names = action_names
    self.action_classes = dict(
        [(k, v) for (k, v) in actions.ActionPlugin.classes.items()
         if k in action_names])

  def HandleMessage(self, message):
    message.auth_state = jobs_pb2.GrrMessage.AUTHENTICATED
    context = self.FakeContext()
    action_cls = self.action_classes[message.name]
    action = action_cls(message=message, grr_context=context)
    action.Execute(message)
    return context.responses

  class FakeContext(object):
    """A Fake GRR context which just collects SendReplys."""

    def __init__(self):
      self.responses = []

    def SendReply(self, protobuf, message_type=jobs_pb2.GrrMessage.MESSAGE,
                  **kw):
      message = jobs_pb2.GrrMessage(
          type=message_type, args=protobuf.SerializeToString(), **kw)

      self.responses.append(message)


class Test(actions.ActionPlugin):
  """A test action which can be used in mocks."""
  in_protobuf = jobs_pb2.DataBlob
  out_protobuf = jobs_pb2.DataBlob


def TestFlowHelper(flow_class_name, client_mock, client_id=None,
                   check_flow_errors=True, **kwargs):
  """Build a full test harness: client - worker + start flow."""
  client_mock = MockClient(client_id, client_mock)
  worker_mock = MockWorker(check_flow_errors=check_flow_errors)

  # Instantiate the flow:
  session_id = flow.FACTORY.StartFlow(client_id, flow_class_name, **kwargs)

  total_flows = set()
  total_flows.add(session_id)

  # Run the client and worker until nothing changes any more.
  while True:
    client_processed = client_mock.Next()
    flows_run = []
    for flow_run in worker_mock.Next():
      total_flows.add(flow_run)
      flows_run.append(flow_run)

    if client_processed == 0 and not flows_run:
      break

    yield client_processed

  # We should check for flow errors:
  if check_flow_errors:
    # Check that all the flows are complete
    for session_id in total_flows:
      flow_pb = flow.FACTORY.FetchFlow(session_id)
      if flow_pb.state != jobs_pb2.FlowPB.TERMINATED:
        if FLAGS.debug:
          pdb.set_trace()

        raise RuntimeError("Flow %s completed in state %s" % (
            flow_pb.name, flow_pb.state))


class ClientFixture(object):
  """A tool to create a client fixture.

  This will populate the AFF4 object tree in the data store with a mock client
  filesystem, including various objects. This allows us to test various
  end-to-end aspects (e.g. GUI).
  """

  def __init__(self, client_id, **kwargs):
    """Constructor.

    Args:
      client_id: The unique id for the new client.
      kwargs: Any other parameters which need to be interpolated by the fixture.
    """
    self.args = kwargs
    self.args["client_id"] = client_id
    self.CreateClientObject(client_fixture.VFS)

  def CreateClientObject(self, vfs_fixture):
    """Make a new client object."""
    for path, (aff4_type, attributes) in vfs_fixture:
      path %= self.args

      aff4_object = aff4.FACTORY.Create(self.args["client_id"] + path,
                                        aff4_type)
      for attribute_name, value in attributes.items():
        # Interpolate the value
        value %= self.args

        attribute = aff4.Attribute.PREDICATES[attribute_name]
        # For readability we store protobufs in text encoding
        if issubclass(attribute.attribute_type, aff4.RDFProto):
          tmp_proto = attribute.attribute_type._proto()

          text_format.Merge(utils.SmartStr(value), tmp_proto)
          value = tmp_proto

        aff4_object.AddAttribute(attribute, attribute(value))

      aff4_object.Close()


class GrrTestProgram(unittest.TestProgram):
  """A Unit test program which is compatible with conf based args parsing."""

  def parseArgs(self, argv):
    """Delegate arg parsing to the conf subsystem."""
    if FLAGS.verbose: self.verbosity = 2
    argv = argv[1:]

    # Give the same behaviour as regular unittest
    if not argv:
      self.test = self.testLoader.loadTestsFromModule(self.module)
      return

    self.testNames = argv
    self.createTests()


def main(argv=None):
  if argv is None:
    argv = sys.argv

  conf.PARSER.parse_args()
  print "Running test %s" % argv[0]
  GrrTestProgram(argv=argv)
