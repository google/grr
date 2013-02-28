#!/usr/bin/env python
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
from grr.lib import config_lib

from grr.lib import data_store
from grr.lib import email_alerts

from grr.lib import flow
from grr.lib import flow_context

from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import scheduler

# Server components must also be imported even when the client code is tested.
from grr.lib import server_plugins  # pylint: disable=W0611
from grr.lib import utils
from grr.test_data import client_fixture

# Default for running in the current directory
config_lib.DEFINE_string("Test.srcdir",
                         os.path.normpath(os.path.dirname(__file__) + "/../.."),
                         "The directory where tests are built.")

config_lib.DEFINE_string("Test.tmpdir", "/tmp/",
                         help="Somewhere to write temporary files.")

config_lib.DEFINE_string("Test.datadir",
                         default="%(Test.srcdir)/grr/test_data",
                         help="The directory where test data exist.")

config_lib.DEFINE_string("Test.config",
                         default="%(Test.datadir)/grr_test.conf",
                         help="The path where the configuration file exists.")

config_lib.DEFINE_string("Test.data_store", "FakeDataStore",
                         "The data store to run the tests against.")

config_lib.DEFINE_integer("Test.remote_pdb_port", 2525,
                          "Remote debugger port.")



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
  well_known_session_id = "aff4:/flows/test:TestSessionId"
  messages = []

  def __init__(self, *args, **kwargs):
    flow.WellKnownFlow.__init__(self, *args, **kwargs)

  def ProcessMessage(self, message):
    """Record the message id for testing."""
    self.messages.append(int(message.args))


class MockUserManager(access_control.BaseUserManager):

  def __init__(self):
    super(MockUserManager, self).__init__()
    self.labels = []

  # pylint: disable=unused-argument
  def SetUserLabels(self, username, labels):
    self.labels = list(labels)

  def GetUserLabels(self, username):
    return self.labels

  # pylint: enable=unused-argument


class MockSecurityManager(access_control.BaseAccessControlManager):
  """A simple in memory ACL manager which only enforces the Admin label.

  This also guarantees that the correct access token has been passed to the
  security manager.

  Note: No user management, we assume a single test user.
  """

  user_manager_cls = MockUserManager

  def CheckAccess(self, token, subjects, requested_access="r"):
    _ = subjects, requested_access
    if token is None:
      raise RuntimeError("Security Token is not set correctly.")
    return True


class GRRBaseTest(unittest.TestCase):
  """This is the base class for all GRR tests."""

  install_mock_acl = True

  __metaclass__ = registry.MetaclassRegistry
  include_plugins_as_attributes = True

  def __init__(self, methodName=None):
    """Hack around unittest's stupid constructor.

    We sometimes need to instantiate the test suite without running any tests -
    e.g. to start initialization or setUp() functions. The unittest constructor
    requires to provide a valid method name.

    Args:
      methodName: The test method to run.
    """
    super(GRRBaseTest, self).__init__(methodName=methodName or "__init__")

  def setUp(self):
    super(GRRBaseTest, self).setUp()

    # Make a temporary directory for test files.
    self.temp_dir = tempfile.mkdtemp(dir=config_lib.CONFIG["Test.tmpdir"])

    self.config_file = os.path.join(self.temp_dir, "test.conf")
    config_path = config_lib.CONFIG["Test.config"]

    shutil.copyfile(config_path, self.config_file)

    # Recreate a new data store each time.
    registry.TestInit()

    # Parse the config as our copy.
    config_lib.CONFIG.Initialize(filename=self.config_file, reset=True,
                                 validate=False)
    config_lib.CONFIG.ExecuteSection("Test")

    self.base_path = config_lib.CONFIG["Test.datadir"]
    self.token = access_control.ACLToken("test", "Running tests")

    if self.install_mock_acl:
      # Enforce checking that security tokens are propagated to the data store
      # but no actual ACLs.
      data_store.DB.security_manager = MockSecurityManager()

  def tearDown(self):
    shutil.rmtree(self.temp_dir, True)

  def shortDescription(self):
    doc = self._testMethodDoc or ""
    doc = doc.split("\n")[0].strip()
    return "%s - %s\n" % (self, doc)

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
      except:
        # Break into interactive debugger on test failure.
        if flags.FLAGS.debug:
          pdb.post_mortem()

        result.addError(self, sys.exc_info())
        # If the setup step failed we stop the entire test suite
        # immediately. This helps catch errors in the setUp() function.
        raise

      ok = False
      try:
        testMethod()
        ok = True
      except self.failureException:
        # Break into interactive debugger on test failure.
        if flags.FLAGS.debug:
          pdb.post_mortem()

        result.addFailure(self, sys.exc_info())
      except KeyboardInterrupt:
        raise
      except Exception:
        # Break into interactive debugger on test failure.
        if flags.FLAGS.debug:
          pdb.post_mortem()

        result.addError(self, sys.exc_info())

      try:
        self.tearDown()
      except KeyboardInterrupt:
        raise
      except Exception:
        # Break into interactive debugger on test failure.
        if flags.FLAGS.debug:
          pdb.post_mortem()

        result.addError(self, sys.exc_info())
        ok = False

      if ok:
        result.addSuccess(self)
    finally:
      result.stopTest(self)

  def MakeUserAdmin(self, username):
    """Makes the test user an admin."""
    data_store.DB.security_manager.user_manager.MakeUserAdmin(username)


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
      arg = rdfvalue.GRRMessage()

    message = rdfvalue.GRRMessage(name=action_name,
                                  payload=arg)
    action_cls = actions.ActionPlugin.classes[message.name]
    results = []

    # Monkey patch a mock SendReply() method
    def MockSendReply(self, reply=None, **kwargs):
      if reply is None:
        reply = self.out_rdfvalue(**kwargs)

      results.append(reply)

    old_sendreply = action_cls.SendReply
    try:
      action_cls.SendReply = MockSendReply

      action = action_cls(message=message)
      action.Run(arg)
    finally:
      action_cls.SendReply = old_sendreply

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
      fd.Set(fd.Schema.CERT, rdfvalue.RDFX509Cert(
          config_lib.CONFIG["Client.certificate"]))

      info = fd.Schema.CLIENT_INFO()
      info.client_name = "GRR Monitor"
      fd.Set(fd.Schema.CLIENT_INFO, info)
      fd.Close()
    return client_ids

  def DeleteClients(self, nr_clients):
    for i in range(nr_clients):
      client_id = "C.1%015d" % i
      data_store.DB.DeleteSubject(client_id, token=self.token)

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
    rdf_flow = flow.FACTORY.FetchFlow(session_id, token=self.token)

    return rdf_flow


class GRRSeleniumTest(GRRBaseTest):
  """Baseclass for selenium UI tests."""

  # Default duration for WaitUntil.
  duration = 10

  # This is the global selenium handle.
  selenium = None

  # Whether InstallACLChecks() was called during the test
  acl_checks_installed = False

  def InstallACLChecks(self):
    """Installs AccessControlManager and stubs out SendEmail."""
    if self.acl_checks_installed:
      return

    self.old_security_manager = data_store.DB.security_manager
    data_store.DB.security_manager = access_control.FullAccessControlManager()

    # Stub out the email function
    self.old_send_email = email_alerts.SendEmail
    self.emails_sent = []

    def SendEmailStub(from_user, to_user, subject, message, **unused_kwargs):
      self.emails_sent.append((from_user, to_user, subject, message))

    email_alerts.SendEmail = SendEmailStub
    self.acl_checks_installed = True

  def UninstallACLChecks(self):
    """Deinstall previously installed ACL checks."""
    if not self.acl_checks_installed:
      return

    data_store.DB.security_manager = self.old_security_manager
    email_alerts.SendEmail = self.old_send_email
    self.acl_checks_installed = False

  def WaitUntil(self, condition_cb, *args):
    for _ in range(self.duration):
      try:
        if condition_cb(*args): return True

      # The element might not exist yet and selenium could raise here. (Also
      # Selenium raises Exception not StandardError).
      except Exception as e:  # pylint: disable=W0703
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
      except Exception as e:  # pylint: disable=W0703
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
      except Exception as e:  # pylint: disable=W0703
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
      message.auth_state = rdfvalue.GRRMessage.Enum("AUTHENTICATED")

      flow_name = scheduler.SCHEDULER.QueueNameFromURN(message.session_id)
      context = flow_context.FlowContext(flow_name=flow_name, token=self.token)
      flow.GRRFlow.classes[flow_name](context=context).ProcessMessage(message)
      return

    # Assume the client is authorized
    message.auth_state = rdfvalue.GRRMessage.Enum("AUTHENTICATED")

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
                                                    token=self.token)

    for task in request_tasks:
      message = task.payload
      response_id = 1
      # Collect all responses for this message from the client mock
      try:
        if hasattr(self.client_mock, "HandleMessage"):
          responses = self.client_mock.HandleMessage(message)
        else:
          responses = getattr(self.client_mock, message.name)(message.args)

        if not responses:
          responses = []

        logging.info("Called client action %s generating %s responses",
                     message.name, len(responses) + 1)

        status = rdfvalue.GrrStatus()
      except Exception as e:  # pylint: disable=W0703
        logging.exception("Error %s occurred in client", e)

        # Error occurred.
        responses = []
        status = rdfvalue.GrrStatus(
            status=rdfvalue.GrrStatus.Enum("GENERIC_ERROR"))

      # Now insert those on the flow state queue
      for response in responses:
        if isinstance(response, rdfvalue.GrrStatus):
          msg_type = rdfvalue.GRRMessage.Enum("STATUS")
          response = rdfvalue.GRRMessage(
              session_id=message.session_id, name=message.name,
              response_id=response_id, request_id=message.request_id,
              payload=response,
              type=msg_type)

        elif not isinstance(response, rdfvalue.GRRMessage):
          msg_type = rdfvalue.GRRMessage.Enum("MESSAGE")
          response = rdfvalue.GRRMessage(
              session_id=message.session_id, name=message.name,
              response_id=response_id, request_id=message.request_id,
              payload=response,
              type=msg_type)

        # Next expected response
        response_id = response.response_id + 1
        self.PushToStateQueue(response)

      # Add a Status message to the end
      self.PushToStateQueue(message, response_id=response_id,
                            payload=status,
                            type=rdfvalue.GRRMessage.Enum("STATUS"))

      # Additionally schedule a task for the worker
      queue_name = scheduler.SCHEDULER.QueueNameFromURN(message.session_id)
      scheduler.SCHEDULER.NotifyQueue(queue_name, message.session_id,
                                      priority=message.priority,
                                      token=self.token)

    return len(request_tasks)


class MockThreadPool(object):
  """A mock thread pool which runs all jobs serially."""

  def __init__(self, *_):
    pass

  def AddTask(self, target, args, name="Unnamed task"):
    _ = name
    try:
      target(*args)
      # The real threadpool can not raise from a task. We emulate this here.
    except Exception:  # pylint: disable=broad-except
      pass

  def Join(self):
    pass


class MockWorker(flow.GRRWorker):
  """Mock the worker."""

  def __init__(self, queue_name="W", check_flow_errors=True, token=None):
    self.queue_name = queue_name
    self.check_flow_errors = check_flow_errors
    self.token = token

    self.pool = MockThreadPool("MockWorker_pool", 25)

    # Collect all the well known flows.
    self.well_known_flows = {}
    for name, cls in flow.GRRFlow.classes.items():
      if aff4.issubclass(cls, flow.WellKnownFlow) and cls.well_known_session_id:
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
    sessions_available = scheduler.SCHEDULER.GetSessionsFromQueue(
        self.queue_name, self.token)

    # Run all the flows until they are finished
    run_sessions = []

    # Only sample one session at the time to force serialization of flows after
    # each state run - this helps to catch unpickleable objects.
    for session_id in sessions_available[:1]:
      scheduler.SCHEDULER.DeleteNotification(self.queue_name, session_id,
                                             token=self.token)
      run_sessions.append(session_id)

      # Handle well known flows here.
      if session_id in self.well_known_flows:
        self.well_known_flows[session_id].ProcessCompletedRequests(
            self.pool)
        continue

      # Unpack the flow
      rdf_flow = flow.FACTORY.FetchFlow(session_id, lock=True, sync=False,
                                        token=self.token)
      try:
        flow_obj = flow.FACTORY.LoadFlow(rdf_flow)

        # Run it
        flow_obj.ProcessCompletedRequests(self.pool)
        # Pack it back up
        rdf_flow = flow_obj.Dump()
        flow_obj.FlushMessages()

        logging.info("Flow pickle is %s bytes",
                     len(rdf_flow.SerializeToString()))
        if (self.check_flow_errors and
            rdf_flow.state == rdfvalue.Flow.Enum("ERROR")):
          logging.exception("Flow terminated in state %s with an error: %s",
                            flow_obj.context.current_state, rdf_flow.backtrace)
          raise RuntimeError(rdf_flow.backtrace)

      finally:
        flow.FACTORY.ReturnFlow(rdf_flow, token=self.token)

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
    self.action_counts = dict((x, 0) for x in action_names)

  def HandleMessage(self, message):
    message.auth_state = rdfvalue.GRRMessage.Enum("AUTHENTICATED")
    client_worker = self.FakeClientWorker()
    if hasattr(self, message.name):
      return getattr(self, message.name)(message.args)

    action_cls = self.action_classes[message.name]
    action = action_cls(message=message, grr_worker=client_worker)
    action.Execute()
    self.action_counts[message.name] += 1
    return client_worker.responses

  class FakeClientWorker(object):
    """A Fake GRR client worker which just collects SendReplys."""

    def __init__(self):
      self.responses = []

    def SendReply(self, rdf_value,
                  message_type=rdfvalue.GRRMessage.Enum("MESSAGE"), **kw):
      message = rdfvalue.GRRMessage(
          type=message_type, payload=rdf_value, **kw)

      self.responses.append(message)


class Test(actions.ActionPlugin):
  """A test action which can be used in mocks."""
  in_rdfvalue = rdfvalue.DataBlob
  out_rdfvalue = rdfvalue.DataBlob


def CheckFlowErrors(total_flows, token=None):
  # Check that all the flows are complete.
  for session_id in total_flows:
    rdf_flow = flow.FACTORY.FetchFlow(session_id, token=token)
    if rdf_flow.state != rdfvalue.Flow.Enum("TERMINATED"):
      if flags.FLAGS.debug:
        pdb.set_trace()

      raise RuntimeError("Flow %s completed in state %s" % (
          rdf_flow.name, rdf_flow.state))
    flow.FACTORY.ReturnFlow(rdf_flow, token=token)


def TestFlowHelper(flow_class_name, client_mock, client_id=None,
                   check_flow_errors=True, token=None, notification_event=None,
                   **kwargs):
  """Build a full test harness: client - worker + start flow."""

  client_mock = MockClient(client_id, client_mock, token=token)
  worker_mock = MockWorker(check_flow_errors=check_flow_errors, token=token)

  # Instantiate the flow:
  session_id = flow.FACTORY.StartFlow(client_id, flow_class_name,
                                      notification_event=notification_event,
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
      token: An instance of access_control.ACLToken security token.
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
          if isinstance(value, (str, unicode)):
            # Interpolate the value
            value = utils.SmartUnicode(value) % self.args

          # Is this supposed to be an RDFValue array?
          if aff4.issubclass(attribute.attribute_type, rdfvalue.RDFValueArray):
            rdfvalue_object = attribute()
            for item in value:
              new_object = rdfvalue_object.rdf_type.FromTextProtobuf(
                  utils.SmartStr(item))
              rdfvalue_object.Append(new_object)

          # It is a text serialized protobuf.
          elif aff4.issubclass(attribute.attribute_type, rdfvalue.RDFProto):
            # Use the alternate constructor - we always write protobufs in
            # textual form:
            rdfvalue_object = attribute.attribute_type.FromTextProtobuf(
                utils.SmartStr(value))

          else:
            rdfvalue_object = attribute(value)

          aff4_object.AddAttribute(attribute, rdfvalue_object)

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
  supported_pathtype = rdfvalue.RDFPathSpec.Enum("OS")

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

      stat = rdfvalue.StatEntry()
      try:
        content = attributes["aff4:stat"]
        text_format.Merge(utils.SmartStr(content), stat)
      except KeyError:
        pass
      stat.pathspec = rdfvalue.RDFPathSpec(pathtype=self.supported_pathtype,
                                           path=path)
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
        partial_pathspec = stat.pathspec.Dirname()

        if dirname == "/" or dirname in self.paths: break

        self.paths[dirname] = rdfvalue.StatEntry(st_mode=16877,
                                                 st_size=1,
                                                 st_dev=1,
                                                 pathspec=partial_pathspec)

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
    return rdfvalue.StatEntry(pathspec=self.pathspec,
                              st_mode=16877,
                              st_size=12288,
                              st_atime=1319796280,
                              st_dev=1)


class GrrTestProgram(unittest.TestProgram):
  """A Unit test program which is compatible with conf based args parsing."""

  def __init__(self, **kw):
    conf.PARSER.add_argument("module", nargs="*", help="Test module to run.")
    conf.PARSER.parse_args()

    # Force the test config to be read in
    flags.FLAGS.config = config_lib.CONFIG["Test.config"]

    # Recreate a new data store each time.
    registry.TestInit()
    vfs.VFSInit()

    super(GrrTestProgram, self).__init__(**kw)

  def parseArgs(self, argv):
    """Delegate arg parsing to the conf subsystem."""
    if flags.FLAGS.verbose:
      self.verbosity = 2
      logging.getLogger().setLevel(logging.DEBUG)

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
                 config_lib.CONFIG["Test.remote_pdb_port"])

    RemotePDB.old_stdout = sys.stdout
    RemotePDB.old_stdin = sys.stdin
    RemotePDB.skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    RemotePDB.skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    RemotePDB.skt.bind(("127.0.0.1", config_lib.CONFIG["Test.remote_pdb_port"]))
    RemotePDB.skt.listen(1)

    (clientsocket, address) = RemotePDB.skt.accept()
    RemotePDB.handle = clientsocket.makefile("rw", 1)
    logging.warn("Received a connection from %s", address)


def main(argv=None):
  if argv is None:
    argv = sys.argv

  print "Running test %s" % argv[0]
  GrrTestProgram(argv=argv)
