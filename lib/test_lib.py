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


import codecs
import os
import pdb
import re
import shutil
import socket
import sys
import tempfile
import time
import unittest


from google.protobuf import text_format
from grr.client import conf as flags
import logging
import unittest

from grr.client import actions
from grr.client import conf
from grr.client import vfs
from grr.lib import access_control
from grr.lib import aff4
from grr.lib import aff4_objects
from grr.lib import data_store
# Load the fake data store implementation
from grr.lib import fake_data_store
from grr.lib import flow
from grr.lib import flow_context
from grr.lib import registry
from grr.lib import scheduler
from grr.lib import threadpool
from grr.lib import utils
from grr.proto import jobs_pb2
from grr.test_data import client_fixture

# Default for running in the current directory
flags.DEFINE_string("test_srcdir",
                    default=os.getcwd(),
                    help="The directory where tests are built.")
flags.DEFINE_string("test_tmpdir", "/tmp/",
                    help="Somewhere to write temporary files.")

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

flags.DEFINE_integer("remote_pdb_port", 2525,
                     "Remote debugger port.")


FLAGS = flags.FLAGS

logging.disable(logging.ERROR)

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

  def __init__(self, message_count=0, *args, **kwargs):
    self.message_count = message_count
    flow.GRRFlow.__init__(self, *args, **kwargs)

  @flow.StateHandler(next_state="Process")
  def Start(self, unused_response=None):
    """Just send a few messages."""
    for unused_i in range(0, self.message_count):
      self.CallClient("ReadBuffer", offset=0, length=100, next_state="Process")


class BrokenFlow(flow.GRRFlow):
  """A flow which does things wrongly."""

  @flow.StateHandler(next_state="Process")
  def Start(self, unused_response=None):
    """Send a message to an incorrect state."""
    self.CallClient("ReadBuffer", next_state="WrongProcess")


class WellKnownSessionTest(flow.WellKnownFlow):
  """Tests the well known flow implementation."""
  well_known_session_id = "test:TestSessionId"
  messages = []

  def __init__(self, *args, **kwargs):
    flow.WellKnownFlow.__init__(self, *args, **kwargs)

  def ProcessMessage(self, message):
    """Record the message id for testing."""
    self.messages.append(int(message.args))


class MockSecurityManager(data_store.BaseAccessControlManager):
  """A special security manager which ensures that the token is valid.

  This guarantees that the correct access token has been passed to the security
  manager.
  """

  def CheckAccess(self, token, subjects, requested_access="r"):
    _ = subjects, requested_access
    if token is None:
      raise RuntimeError("Security Token is not set correctly.")
    return True


class GRRBaseTest(unittest.TestCase):
  """This is the base class for all GRR tests."""

  install_mock_acl = True

  __metaclass__ = registry.MetaclassRegistry

  def setUp(self):
    # We want to use the fake usually
    FLAGS.storage = FLAGS.test_data_store

    # Recreate a new data store each time.
    registry.TestInit()
    vfs.VFSInit()

    self.base_path = os.path.join(FLAGS.test_srcdir, FLAGS.test_datadir)
    self.key_path = os.path.join(FLAGS.test_srcdir, FLAGS.test_keydir)
    self.token = data_store.ACLToken("test", "Running tests")

    if self.install_mock_acl:
      # Enforce checking that security tokens are propagated to the data store
      # but no actual ACLs.
      data_store.DB.security_manager = MockSecurityManager()

  def shortDescription(self):
    doc = self._testMethodDoc or ""
    doc = doc.split("\n")[0].strip()
    return "%s - %s\n" % (self, doc)

  def assertItemsEqual(self, x, y):
    """This method is present in python 2.7 but is here for compatibility."""
    self.assertEqual(sorted(x), sorted(y))

  def assertIsInstance(self, got_object, expected_class, msg=""):
    """Checks that got_object is an instance of expected_class or sub-class."""
    if not isinstance(got_object, expected_class):
      self.fail("%r is not an instance of %r. %s" % (got_object,
                                                     expected_class, msg))

  def assertProto2Equal(self, x, y):
   self.assertEqual(x, y)

  def run(self, result=None):
    """Run the test case.

    This code is basically the same as the standard library, except that when
    there is an exception, the --debug flag allows us to drop into the raising
    function for interactive inspection of the test failure.

    Args:
      result: The testResult object that we will use.
    """
    if result is None: result = self.defaultTestResult()
    result.startTest(self)
    testMethod = getattr(self, self._testMethodName)
    try:
      try:
        self.setUp()
      except KeyboardInterrupt:
        raise
      except:
        result.addError(self, sys.exc_info())
        return

      ok = False
      try:
        testMethod()
        ok = True
      except self.failureException:
        # Break into interactive debugger on test failure.
        if FLAGS.debug:
          pdb.post_mortem()

        result.addFailure(self, sys.exc_info())
      except KeyboardInterrupt:
        raise
      except Exception:
        # Break into interactive debugger on test failure.
        if FLAGS.debug:
          pdb.post_mortem()

        result.addError(self, sys.exc_info())

      try:
        self.tearDown()
      except KeyboardInterrupt:
        raise
      except Exception:
        # Break into interactive debugger on test failure.
        if FLAGS.debug:
          pdb.post_mortem()

        result.addError(self, sys.exc_info())
        ok = False

      if ok:
        result.addSuccess(self)
    finally:
      result.stopTest(self)


class EmptyActionTest(GRRBaseTest):
  """Test the client Actions."""

  __metaclass__ = registry.MetaclassRegistry

  def RunAction(self, action_name, arg=None):
    """Run an action and generate responses.

    Args:
       action_name: The action to run.
       arg: A protobuf to pass the action.

    Returns:
      A list of response protobufs.
    """
    if arg is None:
      arg = jobs_pb2.GrrMessage()

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

  __metaclass__ = registry.MetaclassRegistry

  def SetupClients(self, nr_clients):
    client_ids = []
    for i in range(nr_clients):
      client_id = "C.1%015d" % i
      client_ids.append(client_id)
      fd = aff4.FACTORY.Create(client_id, "VFSGRRClient", token=self.token)
      fd.Set(fd.Schema.CERT, aff4.FACTORY.RDFValue("RDFX509Cert")(
          open(os.path.join(self.key_path, "cert.pem")).read()))
      info = fd.Schema.CLIENT_INFO()
      info.data.client_name = "GRR Monitor"
      fd.Set(fd.Schema.CLIENT_INFO, info)
      fd.Close()
    return client_ids

  def DeleteClients(self, nr_clients):
    for i in range(nr_clients):
      client_id = "C.1%015d" % i
      data_store.DB.DeleteSubject(client_id)

  def setUp(self):
    GRRBaseTest.setUp(self)
    flow.FACTORY.outstanding_flows.clear()

    client_ids = self.SetupClients(1)
    self.client_id = client_ids[0]

  def tearDown(self):
    self.assert_(not flow.FACTORY.outstanding_flows)
    data_store.DB.Clear()

  def FlowSetup(self, name):
    session_id = flow.FACTORY.StartFlow(self.client_id, name, token=self.token)
    flow_pb = flow.FACTORY.FetchFlow(session_id, token=self.token)

    return flow_pb


class GRRSeleniumTest(GRRBaseTest):
  """Baseclass for selenium UI tests."""

  __metaclass__ = registry.MetaclassRegistry
  include_plugins_as_attributes = True

  # Default duration for WaitUntil.
  duration = 10

  # This is the global selenium handle.
  selenium = None

  def WaitUntil(self, condition_cb, *args):
    for _ in range(self.duration):
      try:
        if condition_cb(*args): return True

      # The element might not exist yet and selenium could raise here. (Also
      # Selenium raises Exception not StandardError).
      except Exception as e:
        logging.warn("Selenium raised %s", e)

      time.sleep(0.5)

    raise RuntimeError("condition not met.")

  def WaitUntilEqual(self, target, condition_cb, *args):
    for _ in range(self.duration):
      try:
        if condition_cb(*args) == target:
          return True

      # The element might not exist yet and selenium could raise here. (Also
      # Selenium raises Exception not StandardError).
      except Exception as e:
        logging.warn("Selenium raised %s", e)

      time.sleep(0.5)

    raise RuntimeError("condition not met.")

  def WaitUntilContains(self, target, condition_cb, *args):
    data = ""
    for _ in range(self.duration):
      try:
        data = condition_cb(*args)
        if target in data:
          return True

      # The element might not exist yet and selenium could raise here.
      except Exception as e:
        logging.warn("Selenium raised %s", e)

      time.sleep(0.5)

    raise RuntimeError("condition not met. Got %r" % data)


class AFF4ObjectTest(GRRBaseTest):
  """The base class of all aff4 object tests."""
  __metaclass__ = registry.MetaclassRegistry

  client_id = "C." + "B" * 16


class GRRTestLoader(unittest.TestLoader):
  """A test suite loader which searches for tests in all the plugins."""

  # This should be overridden by derived classes. We load all tests extending
  # this class.
  base_class = None

  def loadTestsFromModule(self, _):
    """Just return all the tests as if they were in the same module."""
    test_cases = [
        self.loadTestsFromTestCase(x) for x in self.base_class.classes.values()]
    return self.suiteClass(test_cases)

  def loadTestsFromName(self, name, module=None):
    """Load the tests named."""
    parts = name.split(".")
    test_cases = self.loadTestsFromTestCase(self.base_class.classes[parts[0]])

    # Specifies the whole test suite.
    if len(parts) == 1:
      return self.suiteClass(test_cases)
    elif len(parts) == 2:
      cls = self.base_class.classes[parts[0]]
      return unittest.TestSuite([cls(parts[1])])


class MockClient(object):
  def __init__(self, client_id, client_mock, token=None):
    self.client_id = client_id
    self.client_mock = client_mock
    self.token = token

  def PushToStateQueue(self, message, **kw):
    # Handle well known flows
    if message.request_id == 0:
      # Assume the message is authenticated and comes from this client.
      message.source = self.client_id
      message.auth_state = jobs_pb2.GrrMessage.AUTHENTICATED

      flow_name = message.session_id.split(":")[1]
      context = flow_context.FlowContext(flow_name=flow_name, token=self.token)
      flow.GRRFlow.classes[flow_name](context=context).ProcessMessage(message)
      return

    # Assume the client is authorized
    message.auth_state = jobs_pb2.GrrMessage.AUTHENTICATED

    # Update kw args
    for k, v in kw.items():
      setattr(message, k, v)

    queue_name = (flow_context.FlowManager.FLOW_STATE_TEMPLATE %
                  message.session_id)

    attribute_name = flow_context.FlowManager.FLOW_RESPONSE_TEMPLATE % (
        message.request_id, message.response_id)

    data_store.DB.Set(queue_name, attribute_name, message.SerializeToString(),
                      token=self.token)

  def Next(self):
    # Grab tasks for us from the queue.
    request_tasks = scheduler.SCHEDULER.QueryAndOwn(self.client_id, limit=1,
                                                    token=self.token,
                                                    decoder=jobs_pb2.GrrMessage)

    for task in request_tasks:
      message = task.value
      response_id = 1
      # Collect all responses for this message from the client mock
      try:
        if hasattr(self.client_mock, "HandleMessage"):
          responses = self.client_mock.HandleMessage(message)
        else:
          responses = getattr(self.client_mock, message.name)(message.args)

        logging.info("Called client action %s generating %s responses",
                     message.name, len(responses) + 1)

        status = jobs_pb2.GrrStatus()
      except Exception as e:
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

        # Next expected response
        response_id = response.response_id + 1
        self.PushToStateQueue(response)

      # Add a Status message to the end
      self.PushToStateQueue(message, response_id=response_id,
                            args=status.SerializeToString(),
                            type=jobs_pb2.GrrMessage.STATUS)

      # Additionally schedule a task for the worker
      queue_name = message.session_id.split(":")[0]
      scheduler.SCHEDULER.NotifyQueue(queue_name, message.session_id,
                                      token=self.token)

    return len(request_tasks)


class MockWorker(object):
  """Mock the worker."""

  def __init__(self, queue_name="W", check_flow_errors=True, token=None):
    self.queue_name = queue_name
    self.check_flow_errors = check_flow_errors
    self.token = token

    self.pool = threadpool.ThreadPool.Factory("MockWorker_pool", 25)
    self.pool.Start()

    # Collect all the well known flows.
    self.well_known_flows = {}
    for name, cls in flow.GRRFlow.classes.items():
      if issubclass(cls, flow.WellKnownFlow) and cls.well_known_session_id:
        context = flow_context.FlowContext(flow_name=name, token=self.token)
        self.well_known_flows[
            cls.well_known_session_id] = cls(context)

  def Next(self):
    """Very simple emulator of the worker.

    We wake each flow in turn and run it.

    Returns:
      total number of flows still alive.

    Raises:
      RuntimeError: if the flow terminates with an error.
    """

    # Check which sessions have new data. Very small limit forces serialization
    # of flows after each state run to catch unpickleable objects.
    active_sessions = []
    for predicate, _, _ in data_store.DB.ResolveRegex(
        self.queue_name, flow_context.FlowManager.FLOW_TASK_REGEX,
        timestamp=data_store.DB.NEWEST_TIMESTAMP,
        token=self.token, limit=1):
      session_id = predicate.split(":", 1)[1]
      active_sessions.append(session_id)

    # Run all the flows until they are finished
    run_sessions = []

    for session_id in active_sessions:
      # Handle well known flows here.
      if session_id in self.well_known_flows:
        self.well_known_flows[session_id].ProcessCompletedRequests(
            self.pool)
        continue

      # Unpack the flow
      flow_pb = flow.FACTORY.FetchFlow(session_id, lock=True, sync=False,
                                       token=self.token)
      try:
        flow_obj = flow.FACTORY.LoadFlow(flow_pb)

        scheduler.SCHEDULER.DeleteNotification(self.queue_name, session_id,
                                               token=self.token)

        # Make note that we ran this flow
        run_sessions.append(session_id)

        # Run it
        flow_obj.ProcessCompletedRequests(self.pool)
        # Pack it back up
        flow_pb = flow_obj.Dump()
        flow_obj.FlushMessages()

        logging.info("Flow pickle is %s bytes",
                     len(flow_pb.SerializeToString()))
        if self.check_flow_errors and flow_pb.state == jobs_pb2.FlowPB.ERROR:
          logging.exception("Flow terminated in state %s with an error: %s",
                            flow_obj.context.current_state, flow_pb.backtrace)
          raise RuntimeError(flow_pb.backtrace)

      finally:
        flow.FACTORY.ReturnFlow(flow_pb, token=self.token)

    return run_sessions


class ActionMock(object):
  """A client mock which runs a real action.

  This can be used as input for TestFlowHelper.

  It is possible to mix mocked actions with real actions. Simple extend this
  class and add methods for the mocked actions, while instantiating with the
  list of read actions to run:

  class MixedActionMock(ActionMock):
    def __init__(self):
      super(MixedActionMock, self).__init__("RealAction")

    def MockedAction(self, args):
      return []

  Will run the real action "RealAction" at the same time as a mocked action
  MockedAction.
  """

  def __init__(self, *action_names):
    self.action_names = action_names
    self.action_classes = dict(
        [(k, v) for (k, v) in actions.ActionPlugin.classes.items()
         if k in action_names])

  def HandleMessage(self, message):
    message.auth_state = jobs_pb2.GrrMessage.AUTHENTICATED
    client_worker = self.FakeClientWorker()
    if hasattr(self, message.name):
      return getattr(self, message.name)(message.args)

    action_cls = self.action_classes[message.name]
    action = action_cls(message=message, grr_worker=client_worker)
    action.Execute(message)
    return client_worker.responses

  class FakeClientWorker(object):
    """A Fake GRR client worker which just collects SendReplys."""

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


def CheckFlowErrors(total_flows, token=None):
  # Check that all the flows are complete.
  for session_id in total_flows:
    flow_pb = flow.FACTORY.FetchFlow(session_id, token=token)
    if flow_pb.state != jobs_pb2.FlowPB.TERMINATED:
      if FLAGS.debug:
        pdb.set_trace()

      raise RuntimeError("Flow %s completed in state %s" % (
          flow_pb.name, flow_pb.state))
    flow.FACTORY.ReturnFlow(flow_pb, token=token)


def TestFlowHelper(flow_class_name, client_mock, client_id=None,
                   check_flow_errors=True, token=None, **kwargs):
  """Build a full test harness: client - worker + start flow."""

  client_mock = MockClient(client_id, client_mock, token=token)
  worker_mock = MockWorker(check_flow_errors=check_flow_errors, token=token)

  # Instantiate the flow:
  session_id = flow.FACTORY.StartFlow(client_id, flow_class_name,
                                      token=token, **kwargs)

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
    CheckFlowErrors(total_flows, token=token)


def TestHuntHelper(client_mock, client_ids, check_flow_errors=False,
                   token=None):
  total_flows = set()

  client_mocks = [MockClient(client_id, client_mock, token=token)
                  for client_id in client_ids]
  worker_mock = MockWorker(check_flow_errors=check_flow_errors, token=token)

  # Run the clients and worker until nothing changes any more.
  while True:
    client_processed = 0
    for client_mock in client_mocks:
      client_processed += client_mock.Next()
    flows_run = []
    for flow_run in worker_mock.Next():
      total_flows.add(flow_run)
      flows_run.append(flow_run)

    if client_processed == 0 and not flows_run:
      break

  if check_flow_errors:
    CheckFlowErrors(total_flows, token=token)


# Default fixture age is (Mon Mar 26 14:07:13 2012).
FIXTURE_TIME = 1332788833


def FilterFixture(fixture=None, regex="."):
  """Returns a sub fixture by only returning objects which match the regex."""
  result = []
  regex = re.compile(regex)

  if fixture is None:
    fixture = client_fixture.VFS

  for path, attributes in fixture:
    if regex.match(path):
      result.append((path, attributes))

  return result


class ClientFixture(object):
  """A tool to create a client fixture.

  This will populate the AFF4 object tree in the data store with a mock client
  filesystem, including various objects. This allows us to test various
  end-to-end aspects (e.g. GUI).
  """

  def __init__(self, client_id, token=None, fixture=None, age=None,
               **kwargs):
    """Constructor.

    Args:
      client_id: The unique id for the new client.
      token: An instance of data_store.ACLToken security token.
      fixture: An optional fixture to install. If not provided we use
        client_fixture.VFS.
      age: Create the fixture at this timestamp. If None we use FIXTURE_TIME.

      **kwargs: Any other parameters which need to be interpolated by the
        fixture.
    """
    self.args = kwargs
    self.token = token
    self.age = age or FIXTURE_TIME
    self.args["client_id"] = client_id
    self.args["age"] = self.age
    self.CreateClientObject(fixture or client_fixture.VFS)

  def CreateClientObject(self, vfs_fixture):
    """Make a new client object."""
    old_time = time.time

    try:
      # Create the fixture at a fixed time.
      time.time = lambda: self.age
      for path, (aff4_type, attributes) in vfs_fixture:
        path %= self.args

        aff4_object = aff4.FACTORY.Create(self.args["client_id"] + path,
                                          aff4_type, mode="rw",
                                          token=self.token)
        for attribute_name, value in attributes.items():
          attribute = aff4.Attribute.PREDICATES[attribute_name]

          if isinstance(value, str) or isinstance(value, unicode):
            # Interpolate the value
            value %= self.args

            # For readability we store protobufs in text encoding.
            if issubclass(attribute.attribute_type, aff4.RDFProto):
              tmp_proto = attribute.attribute_type._proto()

              text_format.Merge(utils.SmartStr(value), tmp_proto)
              value = tmp_proto

          if issubclass(attribute.attribute_type, aff4.RDFProtoArray):
            act = aff4_object.Get(attribute) or attribute()
            act.Append(value)
            aff4_object.Set(attribute, act)
          else:
            aff4_object.AddAttribute(attribute, attribute(value))

        # Make sure we do not actually close the object here - we only want to
        # sync back its attributes, not run any finalization code.
        aff4_object.Flush()

    finally:
      # Restore the time function.
      time.time = old_time


class ClientVFSHandlerFixture(vfs.VFSHandler):
  """A client side VFS handler for the OS type - returns the fixture."""
  # A class wide cache for fixtures. Key is the prefix, and value is the
  # compiled fixture.
  cache = {}

  paths = None
  supported_pathtype = jobs_pb2.Path.OS

  # Do not auto-register.
  auto_register = False

  # Everything below this prefix is emulated
  prefix = "/fs/os"

  def __init__(self, base_fd, prefix=None, pathspec=None):
    super(ClientVFSHandlerFixture, self).__init__(base_fd, pathspec=pathspec)

    self.prefix = self.prefix or prefix
    self.pathspec.Append(pathspec)
    self.path = self.pathspec.CollapsePath()
    self.paths = self.cache.get(self.prefix)

    self.PopulateCache()

  def PopulateCache(self):
    """Parse the paths from the fixture."""
    if self.paths: return

    # The cache is attached to the class so it can be shared by all instance.
    self.paths = self.__class__.cache[self.prefix] = {}
    for path, (_, attributes) in client_fixture.VFS:
      if not path.startswith(self.prefix): continue

      path = utils.NormalizePath(path[len(self.prefix):])
      if path == "/":
        continue

      stat = jobs_pb2.StatResponse()
      try:
        content = attributes["aff4:stat"]
        text_format.Merge(utils.SmartStr(content), stat)
      except KeyError:
        pass
      stat.pathspec.pathtype = self.supported_pathtype
      stat.pathspec.path = path
      # TODO(user): Once we add tests around not crossing device boundaries,
      # we need to be smarter here, especially for the root entry.
      stat.st_dev = 1
      self.paths[path] = stat

    self.BuildIntermediateDirectories()

  def BuildIntermediateDirectories(self):
    """Interpolate intermediate directories based on their children.

    This avoids us having to put in useless intermediate directories to the
    client fixture.
    """
    for dirname, stat in self.paths.items():
      while 1:
        dirname = os.path.dirname(dirname)
        partial_pathspec = utils.Pathspec(stat.pathspec).Dirname()

        if dirname == "/" or dirname in self.paths: break

        new_stat = jobs_pb2.StatResponse()
        new_stat.st_mode = 16877
        new_stat.st_size = 1
        new_stat.st_dev = 1
        new_stat.pathspec.MergeFrom(partial_pathspec.ToProto())

        self.paths[dirname] = new_stat

  def ListFiles(self):
    # First return exact matches
    for k, stat in self.paths.items():
      dirname = os.path.dirname(k)

      if dirname == self.path:
        yield stat

  def Read(self, length):
    result = self.paths.get(self.path)
    if not result:
      raise IOError("File not found")
    data = result.resident[self.offset:self.offset + length]
    self.offset += len(data)
    return data

  def ListNames(self):
    for stat in self.ListFiles():
      yield os.path.basename(stat.pathspec.path)

  def IsDirectory(self):
    return bool(self.ListFiles())

  def Stat(self):
    response = jobs_pb2.StatResponse()

    self.pathspec.ToProto(response.pathspec)

    response.st_mode = 16877
    response.st_size = 12288
    response.st_atime = 1319796280
    response.st_dev = 1

    return response


class GrrTestProgram(unittest.TestProgram):
  """A Unit test program which is compatible with conf based args parsing."""

  def __init__(self, **kw):
    conf.PARSER.parse_args()
    registry.TestInit()
    super(GrrTestProgram, self).__init__(**kw)

  def parseArgs(self, argv):
    """Delegate arg parsing to the conf subsystem."""
    if FLAGS.verbose:
      self.verbosity = 2
      logging.set_verbosity(logging.DEBUG)

    argv = argv[1:]

    # Give the same behaviour as regular unittest
    if not argv:
      self.test = self.testLoader.loadTestsFromModule(self.module)
      return

    self.testNames = argv
    self.createTests()


class TempDirectory(object):
  """A self cleaning temporary directory."""

  def __enter__(self):
    self.name = tempfile.mkdtemp()

    return self.name

  def __exit__(self, exc_type, exc_value, traceback):
    shutil.rmtree(self.name, True)


class RemotePDB(pdb.Pdb):
  """A Remote debugger facility.

  Place breakpoints in the code using:
  test_lib.RemotePDB().set_trace()

  Once the debugger is attached all remote break points will use the same
  connection.
  """
  handle = None
  prompt = "RemotePDB>"

  def __init__(self):
    # Use a global socket for remote debugging.
    if RemotePDB.handle is None:
      self.ListenForConnection()

    pdb.Pdb.__init__(self, stdin=self.handle,
                     stdout=codecs.getwriter("utf8")(self.handle))

  def ListenForConnection(self):
    """Listens and accepts a single connection."""
    logging.warn("Remote debugger waiting for connection on %s",
                 FLAGS.remote_pdb_port)

    RemotePDB.old_stdout = sys.stdout
    RemotePDB.old_stdin = sys.stdin
    RemotePDB.skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    RemotePDB.skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    RemotePDB.skt.bind(("127.0.0.1", FLAGS.remote_pdb_port))
    RemotePDB.skt.listen(1)

    (clientsocket, address) = RemotePDB.skt.accept()
    RemotePDB.handle = clientsocket.makefile("rw", 1)
    logging.warn("Received a connection from %s", address)


def main(argv=None):
  if argv is None:
    argv = sys.argv

  print "Running test %s" % argv[0]
  GrrTestProgram(argv=argv)
