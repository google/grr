#!/usr/bin/env python
"""A library for tests."""



import codecs
import datetime
import functools
import itertools
import os
import pdb
import re
import shutil
import signal
import socket
import StringIO
import subprocess
import sys
import tempfile
import time
import types
import unittest
import urlparse


from M2Crypto import X509

import mock

from selenium.common import exceptions
from selenium.webdriver.common import action_chains
from selenium.webdriver.common import keys
from selenium.webdriver.support import select

import logging
import unittest

from grr.client import actions
from grr.client import comms
from grr.client import vfs
from grr.client.client_actions import standard

from grr.lib import access_control
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import config_lib

from grr.lib import data_store
from grr.lib import email_alerts
from grr.lib import flags

from grr.lib import flow

from grr.lib import maintenance_utils
from grr.lib import queue_manager
from grr.lib import queues as queue_config
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import rekall_profile_server

# Server components must also be imported even when the client code is tested.
# pylint: disable=unused-import
from grr.lib import server_plugins
# pylint: enable=unused-import
from grr.lib import startup
from grr.lib import stats
from grr.lib import utils
from grr.lib import worker
from grr.lib import worker_mocks
from grr.proto import tests_pb2

from grr.test_data import client_fixture

flags.DEFINE_list("tests", None,
                  help=("Test module to run. If not specified we run"
                        "All modules in the test suite."))
flags.DEFINE_list("labels", ["small"],
                  "A list of test labels to run. (e.g. benchmarks,small).")


class Error(Exception):
  """Test base error."""


class TimeoutError(Error):
  """Used when command line invocations time out."""


class ClientActionRunnerArgs(rdfvalue.RDFProtoStruct):
  protobuf = tests_pb2.ClientActionRunnerArgs


class ClientActionRunner(flow.GRRFlow):
  """Just call the specified client action directly.
  """
  args_type = ClientActionRunnerArgs
  action_args = {}

  @flow.StateHandler(next_state="End")
  def Start(self):
    self.CallClient(self.args.action, next_state="End", **self.action_args)


class FlowWithOneClientRequest(flow.GRRFlow):
  """Test flow that does one client request in Start() state."""

  @flow.StateHandler(next_state="End")
  def Start(self, unused_message=None):
    self.CallClient("Test", data="test", next_state="End")


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


class SendingFlowArgs(rdfvalue.RDFProtoStruct):
  protobuf = tests_pb2.SendingFlowArgs


class SendingFlow(flow.GRRFlow):
  """Tests sending messages to clients."""
  args_type = SendingFlowArgs

  @flow.StateHandler(next_state="Process")
  def Start(self, unused_response=None):
    """Just send a few messages."""
    for unused_i in range(0, self.args.message_count):
      self.CallClient("ReadBuffer", offset=0, length=100, next_state="Process")


class RaiseOnStart(flow.GRRFlow):
  """A broken flow that raises in the Start method."""

  @flow.StateHandler(next_state="End")
  def Start(self, unused_message=None):
    raise Exception("Broken Start")


class BrokenFlow(flow.GRRFlow):
  """A flow which does things wrongly."""

  @flow.StateHandler(next_state="Process")
  def Start(self, unused_response=None):
    """Send a message to an incorrect state."""
    self.CallClient("ReadBuffer", next_state="WrongProcess")


class DummyLogFlow(flow.GRRFlow):
  """Just emit logs."""

  @flow.StateHandler(next_state="Done")
  def Start(self, unused_response=None):
    """Log."""
    self.Log("First")
    self.CallFlow("DummyLogFlowChild", next_state="Done")
    self.Log("Second")

  @flow.StateHandler()
  def Done(self, unused_response=None):
    self.Log("Third")
    self.Log("Fourth")


class DummyLogFlowChild(flow.GRRFlow):
  """Just emit logs."""

  @flow.StateHandler(next_state="Done")
  def Start(self, unused_response=None):
    """Log."""
    self.Log("Uno")
    self.CallState(next_state="Done")
    self.Log("Dos")

  @flow.StateHandler()
  def Done(self, unused_response=None):
    self.Log("Tres")
    self.Log("Cuatro")


class WellKnownSessionTest(flow.WellKnownFlow):
  """Tests the well known flow implementation."""
  well_known_session_id = rdfvalue.SessionID(queue=rdfvalue.RDFURN("test"),
                                             flow_name="TestSessionId")

  messages = []

  def __init__(self, *args, **kwargs):
    flow.WellKnownFlow.__init__(self, *args, **kwargs)

  def ProcessMessage(self, message):
    """Record the message id for testing."""
    self.messages.append(int(message.args))


class MockSecurityManager(access_control.BasicAccessControlManager):
  """A simple in memory ACL manager which enforces the Admin label.

  It also guarantees that the correct access token has been passed to the
  security manager. It can also optionally limit datastore access for
  certain access types.

  Note: No user management, we assume a single test user.
  """

  def __init__(self, forbidden_datastore_access=""):
    """Constructor.

    Args:
      forbidden_datastore_access: String designating datastore
          permissions. Permissions specified in this argument
          will not be granted when checking for datastore access.

          Known permissions are:
            "r" - for reading,
            "w" - for writing,
            "q" - for querying.
          forbidden_datastore_access should be a combination of the above. By
          default all types of access are permitted.
    """
    super(MockSecurityManager, self).__init__()

    self.forbidden_datastore_access = forbidden_datastore_access

  def CheckFlowAccess(self, token, flow_name, client_id=None):
    _ = flow_name, client_id
    if token is None:
      raise RuntimeError("Security Token is not set correctly.")
    return True

  def CheckHuntAccess(self, token, hunt_urn):
    _ = hunt_urn
    if token is None:
      raise RuntimeError("Security Token is not set correctly.")
    return True

  def CheckCronJobAccess(self, token, cron_job_urn):
    _ = cron_job_urn
    if token is None:
      raise RuntimeError("Security Token is not set correctly.")
    return True

  def CheckDataStoreAccess(self, token, subjects, requested_access="r"):
    _ = subjects, requested_access
    if token is None:
      raise RuntimeError("Security Token is not set correctly.")

    for access in requested_access:
      if access in self.forbidden_datastore_access:
        raise access_control.UnauthorizedAccess("%s access is is not allowed" %
                                                access)

    return True


class GRRBaseTest(unittest.TestCase):
  """This is the base class for all GRR tests."""

  install_mock_acl = True

  __metaclass__ = registry.MetaclassRegistry
  include_plugins_as_attributes = True

  # The type of this test.
  type = "normal"

  def __init__(self, methodName=None):  # pylint: disable=g-bad-name
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

    tmpdir = os.environ.get("TEST_TMPDIR") or config_lib.CONFIG["Test.tmpdir"]

    # Make a temporary directory for test files.
    self.temp_dir = tempfile.mkdtemp(dir=tmpdir)

    # Reinitialize the config system each time.
    startup.TestInit()

    config_lib.CONFIG.SetWriteBack(
        os.path.join(self.temp_dir, "writeback.yaml"))

    self.base_path = config_lib.CONFIG["Test.data_dir"]
    self.token = access_control.ACLToken(username="test",
                                         reason="Running tests")

    if self.install_mock_acl:
      # Enforce checking that security tokens are propagated to the data store
      # but no actual ACLs.
      data_store.DB.security_manager = MockSecurityManager()

    logging.info("Starting test: %s.%s",
                 self.__class__.__name__, self._testMethodName)

    # "test" must not be a system user or notifications will not be delivered.
    if "test" in aff4.GRRUser.SYSTEM_USERS:
      aff4.GRRUser.SYSTEM_USERS.remove("test")

    # We don't want to send actual email in our tests
    self.smtp_patcher = mock.patch("smtplib.SMTP")
    self.mock_smtp = self.smtp_patcher.start()

  def tearDown(self):
    self.smtp_patcher.stop()
    logging.info("Completed test: %s.%s",
                 self.__class__.__name__, self._testMethodName)

    # This may fail on filesystems which do not support unicode filenames.
    try:
      shutil.rmtree(self.temp_dir, True)
    except UnicodeError:
      pass

  def shortDescription(self):  # pylint: disable=g-bad-name
    doc = self._testMethodDoc or ""
    doc = doc.split("\n")[0].strip()
    # Write the suite and test name so it can be easily copied into the --tests
    # parameter.
    return "\n%s.%s - %s\n" % (
        self.__class__.__name__, self._testMethodName, doc)

  def _EnumerateProto(self, protobuf):
    """Return a sorted list of tuples for the protobuf."""
    result = []
    for desc, value in protobuf.ListFields():
      if isinstance(value, float):
        value = round(value, 2)

      try:
        value = self._EnumerateProto(value)
      except AttributeError:
        pass

      result.append((desc.name, value))

    result.sort()
    return result

  def assertProtoEqual(self, x, y):
    """Check that an RDFStruct is equal to a protobuf."""
    self.assertEqual(self._EnumerateProto(x), self._EnumerateProto(y))

  def run(self, result=None):  # pylint: disable=g-bad-name
    """Run the test case.

    This code is basically the same as the standard library, except that when
    there is an exception, the --debug flag allows us to drop into the raising
    function for interactive inspection of the test failure.

    Args:
      result: The testResult object that we will use.
    """
    if result is None: result = self.defaultTestResult()
    result.startTest(self)
    testMethod = getattr(  # pylint: disable=g-bad-name
        self, self._testMethodName)
    try:
      try:
        self.setUp()
      except unittest.SkipTest:
        result.addSkip(self, sys.exc_info())
        result.stopTest(self)
        return
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
      except unittest.SkipTest:
        result.addSkip(self, sys.exc_info())
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

  def CreateUser(self, username):
    """Creates a user."""
    user = aff4.FACTORY.Create("aff4:/users/%s" % username, "GRRUser",
                               token=self.token.SetUID())
    user.Flush()
    return user

  def CreateAdminUser(self, username):
    """Creates a user and makes it an admin."""
    with self.CreateUser(username) as user:
      user.SetLabels("admin", owner="GRR")

  def GrantClientApproval(self, client_id, token=None):
    token = token or self.token

    # Create the approval and approve it.
    flow.GRRFlow.StartFlow(client_id=client_id,
                           flow_name="RequestClientApprovalFlow",
                           reason=token.reason,
                           subject_urn=rdfvalue.ClientURN(client_id),
                           approver="approver",
                           token=token)

    self.CreateAdminUser("approver")

    approver_token = access_control.ACLToken(username="approver")
    flow.GRRFlow.StartFlow(client_id=client_id,
                           flow_name="GrantClientApprovalFlow",
                           reason=token.reason,
                           delegate=token.username,
                           subject_urn=rdfvalue.ClientURN(client_id),
                           token=approver_token)

  def GrantHuntApproval(self, hunt_urn, token=None):
    token = token or self.token

    # Create the approval and approve it.
    flow.GRRFlow.StartFlow(flow_name="RequestHuntApprovalFlow",
                           subject_urn=rdfvalue.RDFURN(hunt_urn),
                           reason=token.reason,
                           approver="approver",
                           token=token)

    self.CreateAdminUser("approver")

    approver_token = access_control.ACLToken(username="approver")
    flow.GRRFlow.StartFlow(flow_name="GrantHuntApprovalFlow",
                           subject_urn=rdfvalue.RDFURN(hunt_urn),
                           reason=token.reason,
                           delegate=token.username,
                           token=approver_token)

  def GrantCronJobApproval(self, cron_job_urn, token=None):
    token = token or self.token

    # Create cron job approval and approve it.
    flow.GRRFlow.StartFlow(flow_name="RequestCronJobApprovalFlow",
                           subject_urn=rdfvalue.RDFURN(cron_job_urn),
                           reason=self.token.reason,
                           approver="approver",
                           token=token)

    self.CreateAdminUser("approver")

    approver_token = access_control.ACLToken(username="approver")
    flow.GRRFlow.StartFlow(flow_name="GrantCronJobApprovalFlow",
                           subject_urn=rdfvalue.RDFURN(cron_job_urn),
                           reason=token.reason,
                           delegate=token.username,
                           token=approver_token)

  def SetupClients(self, nr_clients):
    client_ids = []
    for i in range(nr_clients):
      client_id = rdfvalue.ClientURN("C.1%015d" % i)
      client_ids.append(client_id)

      with aff4.FACTORY.Create(client_id, "VFSGRRClient",
                               token=self.token) as fd:
        cert = rdfvalue.RDFX509Cert(
            self.ClientCertFromPrivateKey(
                config_lib.CONFIG["Client.private_key"]).as_pem())
        fd.Set(fd.Schema.CERT, cert)

        info = fd.Schema.CLIENT_INFO()
        info.client_name = "GRR Monitor"
        fd.Set(fd.Schema.CLIENT_INFO, info)
        fd.Set(fd.Schema.PING, rdfvalue.RDFDatetime().Now())
        fd.Set(fd.Schema.HOSTNAME("Host-%s" % i))
        fd.Set(fd.Schema.FQDN("Host-%s.example.com" % i))
        fd.Set(fd.Schema.MAC_ADDRESS("aabbccddee%02x" % i))
        fd.Set(fd.Schema.HOST_IPS("192.168.0.%d" % i))

    return client_ids

  def DeleteClients(self, nr_clients):
    for i in range(nr_clients):
      client_id = rdfvalue.ClientURN("C.1%015d" % i)
      data_store.DB.DeleteSubject(client_id, token=self.token)

  def RunForTimeWithNoExceptions(self, cmd, argv, timeout=10, should_exit=False,
                                 check_exit_code=False):
    """Run a command line argument and check for python exceptions raised.

    Args:
      cmd: The command to run as a string.
      argv: The args.
      timeout: How long to let the command run before terminating.
      should_exit: If True we will raise if the command hasn't exited after
          the specified timeout.
      check_exit_code: If True and should_exit is True, we'll check that the
          exit code was 0 and raise if it isn't.

    Raises:
      RuntimeError: On any errors.
    """
    def HandleTimeout(unused_signum, unused_frame):
      raise TimeoutError()

    exited = False
    proc = None
    try:
      logging.info("Running : %s", [cmd] + argv)
      proc = subprocess.Popen([cmd] + argv, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, bufsize=1)
      signal.signal(signal.SIGALRM, HandleTimeout)
      signal.alarm(timeout)

      stdout = StringIO.StringIO()

      while True:
        proc.poll()
        # Iterate through the output so that we get the output data even if we
        # kill the process.
        for line in proc.stdout.readline():
          stdout.write(line)
        if proc.returncode is not None:
          exited = True
          break

    except TimeoutError:
      pass   # We expect timeouts.

    finally:
      signal.alarm(0)
      try:
        if proc:
          proc.kill()
      except OSError:
        pass   # Could already be dead.

    proc.stdout.flush()
    stdout.write(proc.stdout.read())    # Collect any remaining output.

    if "Traceback (" in stdout.getvalue():
      raise RuntimeError("Exception found in stderr of binary Stderr:\n###\n%s"
                         "###\nCmd: %s" % (stdout.getvalue(), cmd))

    if should_exit and not exited:
      raise RuntimeError("Bin: %s got timeout when when executing, expected "
                         "exit. \n%s\n" % (stdout.getvalue(), cmd))

    if not should_exit and exited:
      raise RuntimeError("Bin: %s exited, but should have stayed running.\n%s\n"
                         % (stdout.getvalue(), cmd))

    if should_exit and check_exit_code:
      if proc.returncode != 0:
        raise RuntimeError("Bin: %s should have returned exit code 0 but got "
                           "%s" % (cmd, proc.returncode))

  def ClientCertFromPrivateKey(self, private_key):
    communicator = comms.ClientCommunicator(private_key=private_key)
    csr = communicator.GetCSR()
    request = X509.load_request_string(csr)
    flow_obj = aff4.FACTORY.Create(None, "CAEnroler", token=self.token)
    subject = request.get_subject()
    cn = rdfvalue.ClientURN(subject.as_text().split("=")[-1])
    return flow_obj.MakeCert(cn, request)

  def CreateSignedDriver(self):
    client_context = ["Platform:Windows", "Arch:amd64"]
    # Make sure there is a signed driver for our client.
    driver_path = maintenance_utils.UploadSignedDriverBlob(
        "MZ Driveeerrrrrr", client_context=client_context,
        token=self.token)
    logging.info("Wrote signed driver to %s", driver_path)


class EmptyActionTest(GRRBaseTest):
  """Test the client Actions."""

  __metaclass__ = registry.MetaclassRegistry

  def RunAction(self, action_name, arg=None, grr_worker=None):
    if arg is None:
      arg = rdfvalue.GrrMessage()

    self.results = []
    action = self._GetActionInstantace(action_name, arg=arg,
                                       grr_worker=grr_worker)

    action.status = rdfvalue.GrrStatus(
        status=rdfvalue.GrrStatus.ReturnedStatus.OK)
    action.Run(arg)

    return self.results

  def ExecuteAction(self, action_name, arg=None, grr_worker=None):
    message = rdfvalue.GrrMessage(name=action_name, payload=arg,
                                  auth_state="AUTHENTICATED")

    self.results = []
    action = self._GetActionInstantace(action_name, arg=arg,
                                       grr_worker=grr_worker)

    action.Execute(message)

    return self.results

  def _GetActionInstantace(self, action_name, arg=None, grr_worker=None):
    """Run an action and generate responses.

    This basically emulates GRRClientWorker.HandleMessage().

    Args:
       action_name: The action to run.
       arg: A protobuf to pass the action.
       grr_worker: The GRRClientWorker instance to use. If not provided we make
         a new one.
    Returns:
      A list of response protobufs.
    """
    # A mock SendReply() method to collect replies.
    def MockSendReply(mock_self, reply=None, **kwargs):
      if reply is None:
        reply = mock_self.out_rdfvalue(**kwargs)

      self.results.append(reply)

    if grr_worker is None:
      grr_worker = worker_mocks.FakeClientWorker()

    try:
      suspended_action_id = arg.iterator.suspended_action
      action = grr_worker.suspended_actions[suspended_action_id]

    except (AttributeError, KeyError):
      action_cls = actions.ActionPlugin.classes[action_name]
      action = action_cls(grr_worker=grr_worker)

    action.SendReply = types.MethodType(MockSendReply, action)

    return action


class FlowTestsBaseclass(GRRBaseTest):
  """The base class for all flow tests."""

  __metaclass__ = registry.MetaclassRegistry

  def setUp(self):
    GRRBaseTest.setUp(self)
    client_ids = self.SetupClients(1)
    self.client_id = client_ids[0]

  def tearDown(self):
    super(FlowTestsBaseclass, self).tearDown()
    data_store.DB.Clear()

  def FlowSetup(self, name):
    session_id = flow.GRRFlow.StartFlow(client_id=self.client_id,
                                        flow_name=name, token=self.token)

    return aff4.FACTORY.Open(session_id, mode="rw", token=self.token)


def SeleniumAction(f):
  """Decorator to do multiple attempts in case of WebDriverException."""
  @functools.wraps(f)
  def Decorator(*args, **kwargs):
    delay = 0.2
    num_attempts = 15
    cur_attempt = 0
    while True:
      try:
        return f(*args, **kwargs)
      except exceptions.WebDriverException as e:
        logging.warn("Selenium raised %s", utils.SmartUnicode(e))

        cur_attempt += 1
        if cur_attempt == num_attempts:
          raise

        time.sleep(delay)

  return Decorator


class ACLChecksDisabledContextManager(object):

  def __enter__(self):
    self.old_security_manager = data_store.DB.security_manager
    data_store.DB.security_manager = access_control.NullAccessControlManager()
    return None

  def __exit__(self, unused_type, unused_value, unused_traceback):
    data_store.DB.security_manager = self.old_security_manager


class FakeTime(object):
  """A context manager for faking time."""

  def __init__(self, fake_time, increment=0):
    self.time = fake_time
    self.increment = increment

  def __enter__(self):
    self.old_time = time.time

    def Time():
      self.time += self.increment
      return self.time

    time.time = Time

  def __exit__(self, unused_type, unused_value, unused_traceback):
    time.time = self.old_time


class FakeDateTimeUTC(object):
  """A context manager for faking time when using datetime.utcnow."""

  def __init__(self, fake_time, increment=0):
    self.time = fake_time
    self.increment = increment

  def __enter__(self):
    self.old_datetime = datetime.datetime

    class FakeDateTime(object):

      def __init__(self, time_val, increment, orig_datetime):
        self.time = time_val
        self.increment = increment
        self.orig_datetime = orig_datetime

      def __getattribute__(self, name):
        try:
          return object.__getattribute__(self, name)
        except AttributeError:
          return getattr(self.orig_datetime, name)

      def utcnow(self):  # pylint: disable=invalid-name
        self.time += self.increment
        return self.orig_datetime.utcfromtimestamp(self.time)

    datetime.datetime = FakeDateTime(self.time, self.increment,
                                     self.old_datetime)

  def __exit__(self, unused_type, unused_value, unused_traceback):
    datetime.datetime = self.old_datetime


class Instrument(object):
  """A helper to instrument a function call.

  Stores a copy of all function call args locally for later inspection.
  """

  def __init__(self, module, target_name):
    self.old_target = getattr(module, target_name)

    def Wrapper(*args, **kwargs):
      self.args.append(args)
      self.kwargs.append(kwargs)
      self.call_count += 1
      return self.old_target(*args, **kwargs)

    self.stubber = utils.Stubber(module, target_name, Wrapper)
    self.args = []
    self.kwargs = []
    self.call_count = 0

  def __enter__(self):
    self.stubber.__enter__()
    return self

  def __exit__(self, t, value, traceback):
    return self.stubber.__exit__(t, value, traceback)


class GRRSeleniumTest(GRRBaseTest):
  """Baseclass for selenium UI tests."""

  # Default duration (in seconds) for WaitUntil.
  duration = 5

  # Time to wait between polls for WaitUntil.
  sleep_time = 0.2

  # This is the global selenium handle.
  driver = None

  # Base url of the Admin UI
  base_url = None

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

  def ACLChecksDisabled(self):
    return ACLChecksDisabledContextManager()

  def WaitUntil(self, condition_cb, *args):
    for _ in range(int(self.duration / self.sleep_time)):
      try:
        res = condition_cb(*args)
        if res:
          return res

      # The element might not exist yet and selenium could raise here. (Also
      # Selenium raises Exception not StandardError).
      except Exception as e:  # pylint: disable=broad-except
        logging.warn("Selenium raised %s", utils.SmartUnicode(e))

      time.sleep(self.sleep_time)

    raise RuntimeError("condition not met, body is: %s" %
                       self.driver.find_element_by_tag_name("body").text)

  def ClickUntil(self, target, condition_cb, *args):
    for _ in range(int(self.duration / self.sleep_time)):
      try:
        res = condition_cb(*args)
        if res:
          return res

      # The element might not exist yet and selenium could raise here. (Also
      # Selenium raises Exception not StandardError).
      except Exception as e:  # pylint: disable=broad-except
        logging.warn("Selenium raised %s", utils.SmartUnicode(e))

      element = self.GetElement(target)
      if element:
        try:
          element.click()
        except exceptions.WebDriverException:
          pass

      time.sleep(self.sleep_time)

    raise RuntimeError("condition not met, body is: %s" %
                       self.driver.find_element_by_tag_name("body").text)

  def _FindElement(self, selector):
    try:
      selector_type, effective_selector = selector.split("=", 1)
    except ValueError:
      effective_selector = selector
      selector_type = None

    if selector_type == "css":
      elems = self.driver.execute_script(
          "return $(\"" + effective_selector.replace("\"", "\\\"") + "\");")
      if not elems:
        raise exceptions.NoSuchElementException()
      else:
        return elems[0]

    elif selector_type == "link":
      links = self.driver.find_elements_by_partial_link_text(effective_selector)
      for l in links:
        if l.text.strip() == effective_selector:
          return l
      raise exceptions.NoSuchElementException()

    elif selector_type == "xpath":
      return self.driver.find_element_by_xpath(effective_selector)

    elif selector_type == "id":
      return self.driver.find_element_by_id(effective_selector)

    elif selector_type == "name":
      return self.driver.find_element_by_name(effective_selector)

    elif selector_type is None:
      if effective_selector.startswith("//"):
        return self.driver.find_element_by_xpath(effective_selector)
      else:
        return self.driver.find_element_by_id(effective_selector)
    else:
      raise RuntimeError("unknown selector type %s" % selector_type)

  @SeleniumAction
  def Open(self, url):
    self.driver.get(self.base_url + url)

    # Sometimes page doesn't get refreshed if url's path and query haven't
    # changed, even if fragments part (part after '#' symbol) of the url has
    # changed. We have to explicitly call Refresh() in such cases.
    prev_parsed_url = urlparse.urlparse(self.driver.current_url)
    new_parsed_url = urlparse.urlparse(url)
    if (prev_parsed_url.path == new_parsed_url.path and
        prev_parsed_url.query == new_parsed_url.query):
      self.Refresh()

  @SeleniumAction
  def Refresh(self):
    self.driver.refresh()

  def WaitUntilNot(self, condition_cb, *args):
    self.WaitUntil(lambda: not condition_cb(*args))

  def IsElementPresent(self, target):
    try:
      self._FindElement(target)
      return True
    except exceptions.NoSuchElementException:
      return False

  def GetElement(self, target):
    try:
      return self._FindElement(target)
    except exceptions.NoSuchElementException:
      return None

  def GetVisibleElement(self, target):
    try:
      element = self._FindElement(target)
      if element.is_displayed():
        return element
    except exceptions.NoSuchElementException:
      pass

    return None

  def IsTextPresent(self, text):
    return self.AllTextsPresent([text])

  def AllTextsPresent(self, texts):
    body = self.driver.find_element_by_tag_name("body").text
    for text in texts:
      if utils.SmartUnicode(text) not in body:
        return False
    return True

  def IsVisible(self, target):
    element = self.GetElement(target)
    return element and element.is_displayed()

  def FileWasDownloaded(self):
    new_count = stats.STATS.GetMetricValue(
        "ui_renderer_latency", fields=["DownloadView"]).count

    result = (new_count - self.prev_download_count) > 0
    self.prev_download_count = new_count
    return result

  def GetText(self, target):
    element = self.WaitUntil(self.GetVisibleElement, target)
    return element.text.strip()

  def GetValue(self, target):
    return self.GetAttribute(target, "value")

  def GetAttribute(self, target, attribute):
    element = self.WaitUntil(self.GetVisibleElement, target)
    return element.get_attribute(attribute)

  def WaitForAjaxCompleted(self):
    self.WaitUntilEqual("", self.GetAttribute,
                        "css=[id=ajax_spinner]", "innerHTML")

  @SeleniumAction
  def Type(self, target, text, end_with_enter=False):
    element = self.WaitUntil(self.GetVisibleElement, target)
    element.clear()
    element.send_keys(text)
    if end_with_enter:
      element.send_keys(keys.Keys.ENTER)

    # We experienced that Selenium sometimes swallows the last character of the
    # text sent. Raising an exception here will just retry in that case.
    if not end_with_enter:
      if text != self.GetValue(target):
        raise exceptions.WebDriverException("Send_keys did not work correctly.")

  @SeleniumAction
  def Click(self, target):
    # Selenium clicks elements by obtaining their position and then issuing a
    # click action in the middle of this area. This may lead to misclicks when
    # elements are moving. Make sure that they are stationary before issuing
    # the click action (specifically, using the bootstrap "fade" class that
    # slides dialogs in is highly discouraged in combination with .Click()).
    self.WaitForAjaxCompleted()
    element = self.WaitUntil(self.GetVisibleElement, target)
    element.click()

  @SeleniumAction
  def DoubleClick(self, target):
    # Selenium clicks elements by obtaining their position and then issuing a
    # click action in the middle of this area. This may lead to misclicks when
    # elements are moving. Make sure that they are stationary before issuing
    # the click action (specifically, using the bootstrap "fade" class that
    # slides dialogs in is highly discouraged in combination with
    # .DoubleClick()).
    self.WaitForAjaxCompleted()
    element = self.WaitUntil(self.GetVisibleElement, target)
    action_chains.ActionChains(self.driver).double_click(element).perform()

  def ClickUntilNotVisible(self, target):
    self.WaitUntil(self.GetVisibleElement, target)
    self.ClickUntil(target, lambda x: not self.IsVisible(x), target)

  @SeleniumAction
  def Select(self, target, label):
    element = self.WaitUntil(self.GetVisibleElement, target)
    select.Select(element).select_by_visible_text(label)

  def GetSelectedLabel(self, target):
    element = self.WaitUntil(self.GetVisibleElement, target)
    return select.Select(element).first_selected_option.text.strip()

  def IsChecked(self, target):
    return self.WaitUntil(self.GetVisibleElement, target).is_selected()

  def GetCssCount(self, target):
    if not target.startswith("css="):
      raise ValueError("invalid target for GetCssCount: " + target)

    return len(self.driver.find_elements_by_css_selector(target[4:]))

  def WaitUntilEqual(self, target, condition_cb, *args):
    for _ in range(int(self.duration / self.sleep_time)):
      try:
        if condition_cb(*args) == target:
          return True

      # The element might not exist yet and selenium could raise here. (Also
      # Selenium raises Exception not StandardError).
      except Exception as e:  # pylint: disable=broad-except
        logging.warn("Selenium raised %s", utils.SmartUnicode(e))

      time.sleep(self.sleep_time)

    raise RuntimeError("condition not met, body is: %s" %
                       self.driver.find_element_by_tag_name("body").text)

  def WaitUntilContains(self, target, condition_cb, *args):
    data = ""
    target = utils.SmartUnicode(target)

    for _ in range(int(self.duration / self.sleep_time)):
      try:
        data = condition_cb(*args)
        if target in data:
          return True

      # The element might not exist yet and selenium could raise here.
      except Exception as e:  # pylint: disable=broad-except
        logging.warn("Selenium raised %s", utils.SmartUnicode(e))

      time.sleep(self.sleep_time)

    raise RuntimeError("condition not met. Got %r" % data)

  def setUp(self):
    super(GRRSeleniumTest, self).setUp()

    self.prev_download_count = stats.STATS.GetMetricValue(
        "ui_renderer_latency", fields=["DownloadView"]).count

    # Make the user use the advanced gui so we can test it.
    with aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("users/test"), aff4_type="GRRUser", mode="w",
        token=self.token) as user_fd:
      user_fd.Set(user_fd.Schema.GUI_SETTINGS(mode="ADVANCED"))

    self.InstallACLChecks()

  def tearDown(self):
    self.UninstallACLChecks()
    super(GRRSeleniumTest, self).tearDown()


class AFF4ObjectTest(GRRBaseTest):
  """The base class of all aff4 object tests."""
  __metaclass__ = registry.MetaclassRegistry

  client_id = rdfvalue.ClientURN("C." + "B" * 16)


class MicroBenchmarks(GRRBaseTest):
  """This base class created the GRR benchmarks."""
  __metaclass__ = registry.MetaclassRegistry

  units = "us"

  def setUp(self, extra_fields=None, extra_format=None):
    super(MicroBenchmarks, self).setUp()

    if extra_fields is None:
      extra_fields = []
    if extra_format is None:
      extra_format = []

    base_scratchpad_fields = ["Benchmark", "Time (%s)", "Iterations"]
    scratchpad_fields = base_scratchpad_fields + extra_fields
    # Create format string for displaying benchmark results.
    initial_fmt = ["45", "<20", "<20"] + extra_format
    self.scratchpad_fmt = " ".join([("{%d:%s}" % (ind, x))
                                    for ind, x in enumerate(initial_fmt)])
    # We use this to store temporary benchmark results.
    self.scratchpad = [scratchpad_fields,
                       ["-" * len(x) for x in scratchpad_fields]]

  def tearDown(self):
    super(MicroBenchmarks, self).tearDown()
    f = 1
    if self.units == "us":
      f = 1e6
    elif self.units == "ms":
      f = 1e3
    if len(self.scratchpad) > 2:
      print "\nRunning benchmark %s: %s" % (self._testMethodName,
                                            self._testMethodDoc or "")

      for row in self.scratchpad:
        if isinstance(row[1], (int, float)):
          row[1] = "%10.4f" % (row[1] * f)
        elif "%" in row[1]:
          row[1] %= self.units

        print self.scratchpad_fmt.format(*row)
      print

  def AddResult(self, name, time_taken, repetitions, *extra_values):
    logging.info("%s: %s (%s)", name, time_taken, repetitions)
    self.scratchpad.append([name, time_taken, repetitions] +
                           list(extra_values))


class AverageMicroBenchmarks(MicroBenchmarks):
  """A MicroBenchmark subclass for tests that need to compute averages."""

  # Increase this for more accurate timing information.
  REPEATS = 1000
  units = "s"

  def setUp(self):
    super(AverageMicroBenchmarks, self).setUp(["Value"])

  def TimeIt(self, callback, name=None, repetitions=None, pre=None, **kwargs):
    """Runs the callback repetitively and returns the average time."""
    if repetitions is None:
      repetitions = self.REPEATS

    if name is None:
      name = callback.__name__

    if pre is not None:
      pre()

    start = time.time()
    for _ in xrange(repetitions):
      return_value = callback(**kwargs)

    time_taken = (time.time() - start) / repetitions
    self.AddResult(name, time_taken, repetitions, return_value)


class GRRTestLoader(unittest.TestLoader):
  """A test suite loader which searches for tests in all the plugins."""

  # This should be overridden by derived classes. We load all tests extending
  # this class.
  base_class = None

  def __init__(self, labels=None):
    super(GRRTestLoader, self).__init__()
    if labels is None:
      labels = set(flags.FLAGS.labels)

    self.labels = set(labels)

  def getTestCaseNames(self, testCaseClass):
    """Filter the test methods according to the labels they have."""
    result = []
    for test_name in super(GRRTestLoader, self).getTestCaseNames(testCaseClass):
      test_method = getattr(testCaseClass, test_name)
      # If the method is not tagged, it will be labeled "small".
      test_labels = getattr(test_method, "labels", set(["small"]))
      if self.labels and not self.labels.intersection(test_labels):
        continue

      result.append(test_name)

    return result

  def loadTestsFromModule(self, _):
    """Just return all the tests as if they were in the same module."""
    test_cases = [
        self.loadTestsFromTestCase(x) for x in self.base_class.classes.values()
        if issubclass(x, self.base_class)]

    return self.suiteClass(test_cases)

  def loadTestsFromName(self, name, module=None):
    """Load the tests named."""
    parts = name.split(".")
    try:
      test_cases = self.loadTestsFromTestCase(self.base_class.classes[parts[0]])
    except KeyError:
      raise RuntimeError("Unable to find test %r - is it registered?" % name)

    # Specifies the whole test suite.
    if len(parts) == 1:
      return self.suiteClass(test_cases)
    elif len(parts) == 2:
      cls = self.base_class.classes[parts[0]]
      return unittest.TestSuite([cls(parts[1])])


class MockClient(object):
  """Simple emulation of the client.

  This implementation operates directly on the server's queue of client
  messages, bypassing the need to actually send the messages through the comms
  library.
  """

  def __init__(self, client_id, client_mock, token=None):
    if not isinstance(client_id, rdfvalue.ClientURN):
      raise RuntimeError("Client id must be an instance of ClientURN")

    if client_mock is None:
      client_mock = action_mocks.InvalidActionMock()

    self.status_message_enforced = getattr(
        client_mock, "STATUS_MESSAGE_ENFORCED", True)
    self.client_id = client_id
    self.client_mock = client_mock
    self.token = token

    # Well known flows are run on the front end.
    self.well_known_flows = flow.WellKnownFlow.GetAllWellKnownFlows(token=token)

  def PushToStateQueue(self, manager, message, **kw):
    # Assume the client is authorized
    message.auth_state = rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED

    # Update kw args
    for k, v in kw.items():
      setattr(message, k, v)

    # Handle well known flows
    if message.request_id == 0:

      # Well known flows only accept messages of type MESSAGE.
      if message.type == rdfvalue.GrrMessage.Type.MESSAGE:
        # Assume the message is authenticated and comes from this client.
        message.SetWireFormat(
            "source", utils.SmartStr(self.client_id.Basename()))

        message.auth_state = "AUTHENTICATED"

        session_id = message.session_id

        logging.info("Running well known flow: %s", session_id)
        self.well_known_flows[session_id.FlowName()].ProcessMessage(message)

      return

    manager.QueueResponse(message.session_id, message)

  def Next(self):
    # Grab tasks for us from the server's queue.
    with queue_manager.QueueManager(token=self.token) as manager:
      request_tasks = manager.QueryAndOwn(self.client_id.Queue(),
                                          limit=1,
                                          lease_seconds=10000)
      for message in request_tasks:
        status = None
        response_id = 1

        # Collect all responses for this message from the client mock
        try:
          if hasattr(self.client_mock, "HandleMessage"):
            responses = self.client_mock.HandleMessage(message)
          else:
            self.client_mock.message = message
            responses = getattr(self.client_mock, message.name)(message.payload)

          if not responses:
            responses = []

          logging.info("Called client action %s generating %s responses",
                       message.name, len(responses) + 1)

          if self.status_message_enforced:
            status = rdfvalue.GrrStatus()
        except Exception as e:  # pylint: disable=broad-except
          logging.exception("Error %s occurred in client", e)

          # Error occurred.
          responses = []
          if self.status_message_enforced:
            status = rdfvalue.GrrStatus(
                status=rdfvalue.GrrStatus.ReturnedStatus.GENERIC_ERROR)

        # Now insert those on the flow state queue
        for response in responses:
          if isinstance(response, rdfvalue.GrrStatus):
            msg_type = rdfvalue.GrrMessage.Type.STATUS
            response = rdfvalue.GrrMessage(
                session_id=message.session_id, name=message.name,
                response_id=response_id, request_id=message.request_id,
                payload=response, type=msg_type)
          elif isinstance(response, rdfvalue.Iterator):
            msg_type = rdfvalue.GrrMessage.Type.ITERATOR
            response = rdfvalue.GrrMessage(
                session_id=message.session_id, name=message.name,
                response_id=response_id, request_id=message.request_id,
                payload=response, type=msg_type)
          elif not isinstance(response, rdfvalue.GrrMessage):
            msg_type = rdfvalue.GrrMessage.Type.MESSAGE
            response = rdfvalue.GrrMessage(
                session_id=message.session_id, name=message.name,
                response_id=response_id, request_id=message.request_id,
                payload=response, type=msg_type)

          # Next expected response
          response_id = response.response_id + 1
          self.PushToStateQueue(manager, response)

        # Status may only be None if the client reported itself as crashed.
        if status is not None:
          self.PushToStateQueue(manager, message, response_id=response_id,
                                payload=status,
                                type=rdfvalue.GrrMessage.Type.STATUS)
        else:
          # Status may be None only if status_message_enforced is False.
          if self.status_message_enforced:
            raise RuntimeError("status message can only be None when "
                               "status_message_enforced is False")

        # Additionally schedule a task for the worker
        manager.QueueNotification(session_id=message.session_id,
                                  priority=message.priority)

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
    except Exception as e:  # pylint: disable=broad-except
      logging.exception("Thread worker raised %s", e)

  def Join(self):
    pass


class MockWorker(worker.GRRWorker):
  """Mock the worker."""

  # Resource accounting off by default, set these arrays to emulate CPU and
  # network usage.
  USER_CPU = [0]
  SYSTEM_CPU = [0]
  NETWORK_BYTES = [0]

  def __init__(self, queues=queue_config.WORKER_LIST,
               check_flow_errors=True, token=None):
    self.queues = queues
    self.check_flow_errors = check_flow_errors
    self.token = token

    self.pool = MockThreadPool("MockWorker_pool", 25)

    # Collect all the well known flows.
    self.well_known_flows = flow.WellKnownFlow.GetAllWellKnownFlows(token=token)

    # Simple generators to emulate CPU and network usage
    self.cpu_user = itertools.cycle(self.USER_CPU)
    self.cpu_system = itertools.cycle(self.SYSTEM_CPU)
    self.network_bytes = itertools.cycle(self.NETWORK_BYTES)

  def Simulate(self):
    while self.Next():
      pass

    self.pool.Join()

  def Next(self):
    """Very simple emulator of the worker.

    We wake each flow in turn and run it.

    Returns:
      total number of flows still alive.

    Raises:
      RuntimeError: if the flow terminates with an error.
    """
    with queue_manager.QueueManager(token=self.token) as manager:
      run_sessions = []
      for queue in self.queues:
        notifications_available = manager.GetNotificationsForAllShards(queue)
        # Run all the flows until they are finished

        # Only sample one session at the time to force serialization of flows
        # after each state run - this helps to catch unpickleable objects.
        for notification in notifications_available[:1]:
          session_id = notification.session_id
          manager.DeleteNotification(session_id, end=notification.timestamp)
          run_sessions.append(session_id)

          # Handle well known flows here.
          flow_name = session_id.FlowName()
          if flow_name in self.well_known_flows:
            well_known_flow = self.well_known_flows[flow_name]
            with well_known_flow:
              responses = well_known_flow.FetchAndRemoveRequestsAndResponses(
                  well_known_flow.well_known_session_id)
            well_known_flow.ProcessResponses(responses, self.pool)
            continue

          with aff4.FACTORY.OpenWithLock(
              session_id, token=self.token, blocking=False) as flow_obj:

            # Run it
            runner = flow_obj.GetRunner()
            cpu_used = runner.context.client_resources.cpu_usage
            user_cpu = self.cpu_user.next()
            system_cpu = self.cpu_system.next()
            network_bytes = self.network_bytes.next()
            cpu_used.user_cpu_time += user_cpu
            cpu_used.system_cpu_time += system_cpu
            runner.context.network_bytes_sent += network_bytes
            runner.ProcessCompletedRequests(notification, self.pool)

            if (self.check_flow_errors and
                runner.context.state == rdfvalue.Flow.State.ERROR):
              logging.exception("Flow terminated in state %s with an error: %s",
                                runner.context.current_state,
                                runner.context.backtrace)
              raise RuntimeError(runner.context.backtrace)

    return run_sessions


class Test(actions.ActionPlugin):
  """A test action which can be used in mocks."""
  in_rdfvalue = rdfvalue.DataBlob
  out_rdfvalue = rdfvalue.DataBlob


def CheckFlowErrors(total_flows, token=None):
  # Check that all the flows are complete.
  for session_id in total_flows:
    try:
      flow_obj = aff4.FACTORY.Open(session_id, aff4_type="GRRFlow", mode="r",
                                   token=token)
    except IOError:
      continue

    if flow_obj.state.context.state != rdfvalue.Flow.State.TERMINATED:
      if flags.FLAGS.debug:
        pdb.set_trace()
      raise RuntimeError("Flow %s completed in state %s" % (
          flow_obj.state.context.args.flow_name,
          flow_obj.state.context.state))


def TestFlowHelper(flow_urn_or_cls_name, client_mock=None, client_id=None,
                   check_flow_errors=True, token=None, notification_event=None,
                   sync=True, **kwargs):
  """Build a full test harness: client - worker + start flow.

  Args:
    flow_urn_or_cls_name: RDFURN pointing to existing flow (in this case the
                          given flow will be run) or flow class name (in this
                          case flow of the given class will be created and run).
    client_mock: Client mock object.
    client_id: Client id of an emulated client.
    check_flow_errors: If True, TestFlowHelper will raise on errors during flow
                       execution.
    token: Security token.
    notification_event: A well known flow session_id of an event listener. Event
                        will be published once the flow finishes.
    sync: Whether StartFlow call should be synchronous or not.
    **kwargs: Arbitrary args that will be passed to flow.GRRFlow.StartFlow().
  Yields:
    The caller should iterate over the generator to get all the flows
    and subflows executed.
  """
  if client_id or client_mock:
    client_mock = MockClient(client_id, client_mock, token=token)

  worker_mock = MockWorker(check_flow_errors=check_flow_errors, token=token)

  if isinstance(flow_urn_or_cls_name, rdfvalue.RDFURN):
    session_id = flow_urn_or_cls_name
  else:
    # Instantiate the flow:
    session_id = flow.GRRFlow.StartFlow(
        client_id=client_id, flow_name=flow_urn_or_cls_name,
        notification_event=notification_event, sync=sync,
        token=token, **kwargs)

  total_flows = set()
  total_flows.add(session_id)

  # Run the client and worker until nothing changes any more.
  while True:
    if client_mock:
      client_processed = client_mock.Next()
    else:
      client_processed = 0

    flows_run = []
    for flow_run in worker_mock.Next():
      total_flows.add(flow_run)
      flows_run.append(flow_run)

    if client_processed == 0 and not flows_run:
      break

    yield session_id

  # We should check for flow errors:
  if check_flow_errors:
    CheckFlowErrors(total_flows, token=token)


class CrashClientMock(object):

  STATUS_MESSAGE_ENFORCED = False

  def __init__(self, client_id, token):
    self.client_id = client_id
    self.token = token

  def HandleMessage(self, message):
    status = rdfvalue.GrrStatus(
        status=rdfvalue.GrrStatus.ReturnedStatus.CLIENT_KILLED,
        error_message="Client killed during transaction")

    msg = rdfvalue.GrrMessage(
        request_id=message.request_id, response_id=1,
        session_id=message.session_id,
        type=rdfvalue.GrrMessage.Type.STATUS,
        payload=status,
        auth_state=rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED)
    msg.SetWireFormat("source", utils.SmartStr(self.client_id.Basename()))

    self.flow_id = message.session_id

    # This is normally done by the FrontEnd when a CLIENT_KILLED message is
    # received.
    flow.Events.PublishEvent("ClientCrash", msg, token=self.token)


class SampleHuntMock(object):

  def __init__(self, failrate=2, data="Hello World!"):
    self.responses = 0
    self.data = data
    self.failrate = failrate
    self.count = 0

  def StatFile(self, args):
    return self._StatFile(args)

  def _StatFile(self, args):
    req = rdfvalue.ListDirRequest(args)

    response = rdfvalue.StatEntry(
        pathspec=req.pathspec,
        st_mode=33184,
        st_ino=1063090,
        st_dev=64512L,
        st_nlink=1,
        st_uid=139592,
        st_gid=5000,
        st_size=len(self.data),
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892)

    self.responses += 1
    self.count += 1

    # Create status message to report sample resource usage
    status = rdfvalue.GrrStatus(status=rdfvalue.GrrStatus.ReturnedStatus.OK)
    status.cpu_time_used.user_cpu_time = self.responses
    status.cpu_time_used.system_cpu_time = self.responses * 2
    status.network_bytes_sent = self.responses * 3

    # Every "failrate" client does not have this file.
    if self.count == self.failrate:
      self.count = 0
      return [status]

    return [response, status]

  def TransferBuffer(self, args):
    response = rdfvalue.BufferReference(args)

    offset = min(args.offset, len(self.data))
    response.data = self.data[offset:]
    response.length = len(self.data[offset:])
    return [response]


def TestHuntHelperWithMultipleMocks(client_mocks, check_flow_errors=False,
                                    token=None):
  total_flows = set()

  client_mocks = [MockClient(client_id, client_mock, token=token)
                  for client_id, client_mock in client_mocks.iteritems()]
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


def TestHuntHelper(client_mock, client_ids, check_flow_errors=False,
                   token=None):
  return TestHuntHelperWithMultipleMocks(
      dict([(client_id, client_mock) for client_id in client_ids]),
      check_flow_errors=check_flow_errors, token=token)


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


def SetLabel(*labels):
  """Sets a label on a function so we can run tests with different types."""
  def Decorator(f):
    # If the method is not already tagged, we replace its label (the default
    # label is "small").
    function_labels = getattr(f, "labels", set())
    f.labels = function_labels.union(set(labels))

    return f

  return Decorator


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
    self.client_id = rdfvalue.ClientURN(client_id)
    self.args["client_id"] = self.client_id.Basename()
    self.args["age"] = self.age
    self.CreateClientObject(fixture or client_fixture.VFS)

  def CreateClientObject(self, vfs_fixture):
    """Make a new client object."""

    # First remove the old fixture just in case its still there.
    aff4.FACTORY.Delete(self.client_id, token=self.token)

    # Create the fixture at a fixed time.
    with FakeTime(self.age):
      for path, (aff4_type, attributes) in vfs_fixture:
        path %= self.args

        aff4_object = aff4.FACTORY.Create(self.client_id.Add(path),
                                          aff4_type, mode="rw",
                                          token=self.token)
        for attribute_name, value in attributes.items():
          attribute = aff4.Attribute.PREDICATES[attribute_name]
          if isinstance(value, (str, unicode)):
            # Interpolate the value
            value %= self.args

          # Is this supposed to be an RDFValue array?
          if aff4.issubclass(attribute.attribute_type, rdfvalue.RDFValueArray):
            rdfvalue_object = attribute()
            for item in value:
              new_object = rdfvalue_object.rdf_type.FromTextFormat(
                  utils.SmartStr(item))
              rdfvalue_object.Append(new_object)

          # It is a text serialized protobuf.
          elif aff4.issubclass(attribute.attribute_type,
                               rdfvalue.RDFProtoStruct):
            # Use the alternate constructor - we always write protobufs in
            # textual form:
            rdfvalue_object = attribute.attribute_type.FromTextFormat(
                utils.SmartStr(value))

          else:
            rdfvalue_object = attribute(value)

          # If we don't already have a pathspec, try and get one from the stat.
          if aff4_object.Get(aff4_object.Schema.PATHSPEC) is None:
            # If the attribute was a stat, it has a pathspec nested in it.
            # We should add that pathspec as an attribute.
            if attribute.attribute_type == rdfvalue.StatEntry:
              stat_object = attribute.attribute_type.FromTextFormat(
                  utils.SmartStr(value))
              if stat_object.pathspec:
                pathspec_attribute = aff4.Attribute(
                    "aff4:pathspec", rdfvalue.PathSpec,
                    "The pathspec used to retrieve "
                    "this object from the client.",
                    "pathspec")
                aff4_object.AddAttribute(pathspec_attribute,
                                         stat_object.pathspec)

          if attribute in ["aff4:content", "aff4:content"]:
            # For AFF4MemoryStreams we need to call Write() instead of
            # directly setting the contents..
            aff4_object.Write(rdfvalue_object)
          else:
            aff4_object.AddAttribute(attribute, rdfvalue_object)

        # Make sure we do not actually close the object here - we only want to
        # sync back its attributes, not run any finalization code.
        aff4_object.Flush()


class ClientVFSHandlerFixture(vfs.VFSHandler):
  """A client side VFS handler for the OS type - returns the fixture."""
  # A class wide cache for fixtures. Key is the prefix, and value is the
  # compiled fixture.
  cache = {}

  paths = None
  supported_pathtype = rdfvalue.PathSpec.PathType.OS

  # Do not auto-register.
  auto_register = False

  # Everything below this prefix is emulated
  prefix = "/fs/os"

  def __init__(self, base_fd, prefix=None, pathspec=None,
               progress_callback=None):
    super(ClientVFSHandlerFixture, self).__init__(
        base_fd, pathspec=pathspec, progress_callback=progress_callback)

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
    for path, (vfs_type, attributes) in client_fixture.VFS:
      if not path.startswith(self.prefix): continue

      path = utils.NormalizePath(path[len(self.prefix):])
      if path == "/":
        continue

      stat = rdfvalue.StatEntry()
      args = {"client_id": "C.1234"}
      attrs = attributes.get("aff4:stat")

      if attrs:
        attrs %= args  # Remove any %% and interpolate client_id.
        stat = rdfvalue.StatEntry.FromTextFormat(utils.SmartStr(attrs))

      stat.pathspec = rdfvalue.PathSpec(pathtype=self.supported_pathtype,
                                        path=path)

      # TODO(user): Once we add tests around not crossing device boundaries,
      # we need to be smarter here, especially for the root entry.
      stat.st_dev = 1
      path = self._NormalizeCaseForPath(path, vfs_type)
      self.paths[path] = (vfs_type, stat)

    self.BuildIntermediateDirectories()

  def _NormalizeCaseForPath(self, path, vfs_type):
    """Handle casing differences for different filesystems."""
    # Special handling for case sensitivity of registry keys.
    # This mimicks the behavior of the operating system.
    if self.supported_pathtype == rdfvalue.PathSpec.PathType.REGISTRY:
      self.path = self.path.replace("\\", "/")
      parts = path.split("/")
      if vfs_type == "VFSFile":
        # If its a file, the last component is a value which is case sensitive.
        lower_parts = [x.lower() for x in parts[0:-1]]
        lower_parts.append(parts[-1])
        path = utils.Join(*lower_parts)
      else:
        path = utils.Join(*[x.lower() for x in parts])
    return path

  def BuildIntermediateDirectories(self):
    """Interpolate intermediate directories based on their children.

    This avoids us having to put in useless intermediate directories to the
    client fixture.
    """
    for dirname, (_, stat) in self.paths.items():
      pathspec = stat.pathspec
      while 1:
        dirname = os.path.dirname(dirname)

        new_pathspec = pathspec.Copy()
        new_pathspec.path = os.path.dirname(pathspec.path)
        pathspec = new_pathspec

        if dirname == "/" or dirname in self.paths: break

        self.paths[dirname] = ("VFSDirectory",
                               rdfvalue.StatEntry(st_mode=16877,
                                                  st_size=1,
                                                  st_dev=1,
                                                  pathspec=new_pathspec))

  def ListFiles(self):
    # First return exact matches
    for k, (_, stat) in self.paths.items():
      dirname = os.path.dirname(k)
      if dirname == self._NormalizeCaseForPath(self.path, None):
        yield stat

  def Read(self, length):
    result = self.paths.get(self._NormalizeCaseForPath(self.path, "VFSFile"))
    if not result:
      raise IOError("File not found")

    result = result[1]   # We just want the stat.
    data = ""
    if result.HasField("resident"):
      data = result.resident
    elif result.HasField("registry_type"):
      data = utils.SmartStr(result.registry_data.GetValue())

    data = data[self.offset:self.offset + length]

    self.offset += len(data)
    return data

  def ListNames(self):
    for stat in self.ListFiles():
      yield os.path.basename(stat.pathspec.path)

  def IsDirectory(self):
    return bool(self.ListFiles())

  def Stat(self):
    """Get Stat for self.path."""
    stat_data = self.paths.get(self._NormalizeCaseForPath(self.path, None))
    if (not stat_data and
        self.supported_pathtype == rdfvalue.PathSpec.PathType.REGISTRY):
      # Check in case it is a registry value. Unfortunately our API doesn't let
      # the user specify if they are after a value or a key, so we have to try
      # both.
      stat_data = self.paths.get(self._NormalizeCaseForPath(self.path,
                                                            "VFSFile"))
    if stat_data:
      return stat_data[1]   # Strip the vfs_type.
    else:
      # We return some fake data, this makes writing tests easier for some
      # things but we give an error to the tester as it is often not what you
      # want.
      logging.warn("Fake value for %s under %s", self.path, self.prefix)
      return rdfvalue.StatEntry(pathspec=self.pathspec,
                                st_mode=16877,
                                st_size=12288,
                                st_atime=1319796280,
                                st_dev=1)


class FakeRegistryVFSHandler(ClientVFSHandlerFixture):
  """Special client VFS mock that will emulate the registry."""
  prefix = "/registry"
  supported_pathtype = rdfvalue.PathSpec.PathType.REGISTRY


class FakeFullVFSHandler(ClientVFSHandlerFixture):
  """Full client VFS mock."""
  prefix = "/"
  supported_pathtype = rdfvalue.PathSpec.PathType.OS


class FakeTestDataVFSHandler(ClientVFSHandlerFixture):
  """Client VFS mock that looks for files in the test_data directory."""
  prefix = "/fs/os"
  supported_pathtype = rdfvalue.PathSpec.PathType.OS

  def Read(self, length):
    test_data_path = os.path.join(config_lib.CONFIG["Test.data_dir"],
                                  os.path.basename(self.path))
    if not os.path.exists(test_data_path):
      raise IOError("Could not find %s" % test_data_path)

    data = open(test_data_path, "r").read()[self.offset:self.offset + length]

    self.offset += len(data)
    return data


class GrrTestProgram(unittest.TestProgram):
  """A Unit test program which is compatible with conf based args parsing."""

  def __init__(self, labels=None, **kw):
    self.labels = labels

    # Recreate a new data store each time.
    startup.TestInit()

    self.setUp()
    try:
      super(GrrTestProgram, self).__init__(**kw)
    finally:
      try:
        self.tearDown()
      except Exception as e:  # pylint: disable=broad-except
        logging.exception(e)

  def setUp(self):
    """Any global initialization goes here."""

  def tearDown(self):
    """Global teardown code goes here."""

  def parseArgs(self, argv):
    """Delegate arg parsing to the conf subsystem."""
    # Give the same behaviour as regular unittest
    if not flags.FLAGS.tests:
      self.test = self.testLoader.loadTestsFromModule(self.module)
      return

    self.testNames = flags.FLAGS.tests
    self.createTests()


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


class TestRekallRepositoryProfileServer(rekall_profile_server.ProfileServer):
  """This server gets the profiles locally from the test data dir."""

  def __init__(self, *args, **kw):
    super(TestRekallRepositoryProfileServer, self).__init__(*args, **kw)
    self.profiles_served = 0

  def GetProfileByName(self, profile_name, version="v1.0"):
    try:
      profile_data = open(os.path.join(
          config_lib.CONFIG["Test.data_dir"], "profiles", version,
          profile_name + ".gz"), "rb").read()

      self.profiles_served += 1

      return rdfvalue.RekallProfile(name=profile_name,
                                    version=version,
                                    data=profile_data)
    except IOError:
      return None


class OSSpecificClientTests(EmptyActionTest):
  """OS-specific client action tests.

  We need to temporarily disable the actionplugin class registry to avoid
  registering actions for other OSes.
  """

  def setUp(self):
    super(OSSpecificClientTests, self).setUp()
    self.old_action_reg = actions.ActionPlugin.classes
    self.old_standard_reg = standard.ExecuteBinaryCommand.classes
    actions.ActionPlugin.classes = {}
    standard.ExecuteBinaryCommand.classes = {}

  def tearDown(self):
    super(OSSpecificClientTests, self).tearDown()
    actions.ActionPlugin.classes = self.old_action_reg
    standard.ExecuteBinaryCommand.classes = self.old_standard_reg


def main(argv=None):
  if argv is None:
    argv = sys.argv

  print "Running test %s" % argv[0]
  GrrTestProgram(argv=argv)
