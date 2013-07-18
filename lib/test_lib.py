#!/usr/bin/env python
"""A library for tests."""



import codecs
import functools
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
import unittest


from selenium.common import exceptions
from selenium.webdriver.common import keys
from selenium.webdriver.support import select

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
from grr.lib import flow_runner

from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import scheduler

# Server components must also be imported even when the client code is tested.
from grr.lib import server_plugins  # pylint: disable=W0611
from grr.lib import startup
from grr.lib import type_info
from grr.lib import utils
from grr.lib import worker
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


flags.DEFINE_list("tests", None,
                  help=("Test module to run. If not specified we run"
                        "All modules in the test suite."))


class Error(Exception):
  """Test base error."""


class TimeoutError(Error):
  """Used when command line invocations time out."""


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

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.Integer(
          name="message_count",
          default=0))

  @flow.StateHandler(next_state="Process")
  def Start(self, unused_response=None):
    """Just send a few messages."""
    for unused_i in range(0, self.state.message_count):
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
    startup.TestInit()

    # Parse the config as our copy.
    config_lib.CONFIG.Initialize(filename=self.config_file, reset=True,
                                 validate=False)

    # Set the flag as well in case someone wants to reload the config.
    self.real_config = flags.FLAGS.config
    flags.FLAGS.config = self.config_file

    config_lib.CONFIG.ExecuteSection("Test")
    self.base_path = config_lib.CONFIG["Test.datadir"]
    self.token = access_control.ACLToken("test", "Running tests")

    if self.install_mock_acl:
      # Enforce checking that security tokens are propagated to the data store
      # but no actual ACLs.
      data_store.DB.security_manager = MockSecurityManager()

  def tearDown(self):
    shutil.rmtree(self.temp_dir, True)
    flags.FLAGS.config = self.real_config

  def shortDescription(self):
    doc = self._testMethodDoc or ""
    doc = doc.split("\n")[0].strip()
    return "%s - %s\n" % (self, doc)

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

  def RunForTimeWithNoExceptions(self, cmd, timeout=10, should_exit=False,
                                 check_exit_code=False):
    """Run a command line argument and check for python exceptions raised.

    Args:
      cmd: The command to run as a string.
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
    try:
      logging.info("Running : %s", cmd)
      proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
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
      arg = rdfvalue.GrrMessage()

    message = rdfvalue.GrrMessage(name=action_name,
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
  """The base class for all flow tests."""

  __metaclass__ = registry.MetaclassRegistry

  def SetupClients(self, nr_clients):
    client_ids = []
    for i in range(nr_clients):
      client_id = rdfvalue.ClientURN("C.1%015d" % i)
      client_ids.append(client_id)
      fd = aff4.FACTORY.Create(client_id, "VFSGRRClient", token=self.token)
      fd.Set(fd.Schema.CERT, rdfvalue.RDFX509Cert(
          config_lib.CONFIG["Client.certificate"]))

      info = fd.Schema.CLIENT_INFO()
      info.client_name = "GRR Monitor"
      fd.Set(fd.Schema.CLIENT_INFO, info)
      fd.Set(fd.Schema.PING, rdfvalue.RDFDatetime().Now())
      fd.Set(fd.Schema.HOSTNAME("Host-%s" % i))
      fd.Set(fd.Schema.FQDN("Host-%s.example.com" % i))
      fd.Set(fd.Schema.MAC_ADDRESS("aabbccddee%02x" % i))
      fd.Close()
    return client_ids

  def DeleteClients(self, nr_clients):
    for i in range(nr_clients):
      client_id = rdfvalue.ClientURN("C.1%015d" % i)
      data_store.DB.DeleteSubject(client_id, token=self.token)

  def setUp(self):
    GRRBaseTest.setUp(self)
    client_ids = self.SetupClients(1)
    self.client_id = client_ids[0]

  def tearDown(self):
    data_store.DB.Clear()

  def FlowSetup(self, name):
    session_id = flow.GRRFlow.StartFlow(self.client_id, name, token=self.token)

    return aff4.FACTORY.Open(session_id, mode="rw", token=self.token)


def SeleniumAction(f):
  """Decorator to do multiple attempts in case of WebDriverException."""
  @functools.wraps(f)
  def Decorator(*args, **kwargs):
    delay = 0.5
    num_attempts = 5
    cur_attempt = 0
    while True:
      try:
        return f(*args, **kwargs)
      except exceptions.WebDriverException as e:
        logging.warn("Selenium raised %s", e)

        cur_attempt += 1
        if cur_attempt == num_attempts:
          raise

        time.sleep(delay)

  return Decorator


class GRRSeleniumTest(GRRBaseTest):
  """Baseclass for selenium UI tests."""

  # Default duration (in seconds) for WaitUntil.
  duration = 5

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

  def WaitUntil(self, condition_cb, *args):
    delay = 0.5
    for _ in range(int(self.duration / delay)):
      try:
        if condition_cb(*args): return True

      # The element might not exist yet and selenium could raise here. (Also
      # Selenium raises Exception not StandardError).
      except Exception as e:  # pylint: disable=W0703
        logging.warn("Selenium raised %s", e)

      time.sleep(delay)

    raise RuntimeError("condition not met.")

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
      links = self.driver.find_elements_by_tag_name("a")
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

  def WaitUntilNot(self, condition_cb, *args):
    self.WaitUntil(lambda: not condition_cb(*args))

  def IsElementPresent(self, target):
    try:
      self._FindElement(target)
      return True
    except exceptions.NoSuchElementException:
      return False

  def IsTextPresent(self, text):
    text = utils.SmartUnicode(text)
    return text in self.driver.find_element_by_tag_name("body").text

  def IsVisible(self, target):
    return (self.IsElementPresent(target) and
            self._FindElement(target).is_displayed())

  def GetText(self, target):
    self.WaitUntil(self.IsVisible, target)
    return self._FindElement(target).text.strip()

  def GetValue(self, target):
    self.WaitUntil(self.IsVisible, target)
    return self._FindElement(target).get_attribute("value")

  @SeleniumAction
  def Type(self, target, text, end_with_enter=False):
    self.WaitUntil(self.IsVisible, target)
    elem = self._FindElement(target)
    elem.clear()
    elem.send_keys(text)
    if end_with_enter:
      elem.send_keys(keys.Keys.ENTER)

  @SeleniumAction
  def Click(self, target):
    self.WaitUntil(self.IsVisible, target)
    self._FindElement(target).click()

  @SeleniumAction
  def Select(self, target, label):
    self.WaitUntil(self.IsVisible, target)
    select.Select(self._FindElement(target)).select_by_visible_text(label)

  def GetSelectedLabel(self, target):
    self.WaitUntil(self.IsVisible, target)
    return select.Select(
        self._FindElement(target)).first_selected_option.text.strip()

  def IsChecked(self, target):
    self.WaitUntil(self.IsVisible, target)
    return self._FindElement(target).is_selected()

  def GetCssCount(self, target):
    if not target.startswith("css="):
      raise ValueError("invalid target for GetCssCount: " + target)

    return len(self.driver.find_elements_by_css_selector(target[4:]))

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
    target = utils.SmartUnicode(target)

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

  client_id = rdfvalue.ClientURN("C." + "B" * 16)


class MicroBenchmarks(GRRBaseTest):
  """This base class created the GRR benchmarks."""
  __metaclass__ = registry.MetaclassRegistry

  # Increase this for more accurate timing information.
  REPEATS = 1000

  units = "us"

  def setUp(self):
    super(MicroBenchmarks, self).setUp()

    # We use this to store temporary benchmark results.
    self.benchmark_scratchpad = [
        ["Benchmark", "Time (%s)", "Iterations"],
        ["---------", "---------", "----------"]]

  def tearDown(self):
    f = 1
    if self.units == "us":
      f = 1e6
    elif self.units == "ms":
      f = 1e3
    if len(self.benchmark_scratchpad) > 2:
      print "\nRunning benchmark %s: %s" % (self._testMethodName,
                                            self._testMethodDoc or "")

      for row in self.benchmark_scratchpad:
        if isinstance(row[1], (int, float)):
          row[1] = "%10.4f" % (row[1] * f)
        elif "%" in row[1]:
          row[1] %= self.units

        if len(row) == 4 and isinstance(row[-1], (basestring, int, float)):
          print "{0:45} {1:<20} {2:<20} ({3})".format(*row)
        else:
          print "{0:45} {1:<20} {2:<20}".format(*row)
      print

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
      v = callback(**kwargs)

    time_taken = (time.time() - start)/repetitions
    self.AddResult(name, time_taken, repetitions, v)

  def AddResult(self, name, time_taken, repetitions, v=None):
    self.benchmark_scratchpad.append(
        [name, time_taken, repetitions, v])


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
  def __init__(self, client_id, client_mock, token=None):
    if not isinstance(client_id, rdfvalue.ClientURN):
      raise RuntimeError("Client id must be an instance of ClientURN")

    if client_mock is None:
      client_mock = InvalidActionMock()

    self.client_id = client_id
    self.client_mock = client_mock
    self.token = token

    # Well known flows are run on the front end.
    self.well_known_flows = flow.WellKnownFlow.GetAllWellKnownFlows(token=token)

  def PushToStateQueue(self, message, **kw):
    # Handle well known flows
    if message.request_id == 0:
      # Assume the message is authenticated and comes from this client.
      message.source = self.client_id
      message.auth_state = rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED

      session_id = message.session_id

      logging.info("Running well known flow: %s", session_id)
      self.well_known_flows[str(session_id)].ProcessMessage(message)
      return

    # Assume the client is authorized
    message.auth_state = rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED

    # Update kw args
    for k, v in kw.items():
      setattr(message, k, v)

    queue_name = (flow_runner.FlowManager.FLOW_STATE_TEMPLATE %
                  message.session_id)

    attribute_name = flow_runner.FlowManager.FLOW_RESPONSE_TEMPLATE % (
        message.request_id, message.response_id)

    data_store.DB.Set(queue_name, attribute_name, message.SerializeToString(),
                      token=self.token)

  def Next(self):
    # Grab tasks for us from the queue.
    request_tasks = scheduler.SCHEDULER.QueryAndOwn(self.client_id, limit=1,
                                                    lease_seconds=10000,
                                                    token=self.token)
    for task in request_tasks:
      message = task.payload
      response_id = 1
      # Collect all responses for this message from the client mock
      try:
        if hasattr(self.client_mock, "HandleMessage"):
          responses = self.client_mock.HandleMessage(message)
        else:
          responses = getattr(self.client_mock, message.name)(message.payload)

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
            status=rdfvalue.GrrStatus.ReturnedStatus.GENERIC_ERROR)

      # Now insert those on the flow state queue
      for response in responses:
        if isinstance(response, rdfvalue.GrrStatus):
          msg_type = rdfvalue.GrrMessage.Type.STATUS
          response = rdfvalue.GrrMessage(
              session_id=message.session_id, name=message.name,
              response_id=response_id, request_id=message.request_id,
              payload=response,
              type=msg_type)

        elif not isinstance(response, rdfvalue.GrrMessage):
          msg_type = rdfvalue.GrrMessage.Type.MESSAGE
          response = rdfvalue.GrrMessage(
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
                            type=rdfvalue.GrrMessage.Type.STATUS)

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


class MockWorker(worker.GRRWorker):
  """Mock the worker."""

  def __init__(self, queue_name="W", check_flow_errors=True, token=None):
    self.queue_name = queue_name
    self.check_flow_errors = check_flow_errors
    self.token = token

    self.pool = MockThreadPool("MockWorker_pool", 25)

    # Collect all the well known flows.
    self.well_known_flows = flow.WellKnownFlow.GetAllWellKnownFlows(token=token)

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

      with aff4.FACTORY.OpenWithLock(
          session_id, token=self.token, blocking=False) as flow_obj:
        # Run it
        runner = flow_obj.CreateRunner()
        flow_obj.ProcessCompletedRequests(runner, self.pool)

      runner.FlushMessages()

      if (self.check_flow_errors and
          flow_obj.state.context.state == rdfvalue.Flow.State.ERROR):
        logging.exception("Flow terminated in state %s with an error: %s",
                          flow_obj.state.context.current_state,
                          flow_obj.backtrace)
        raise RuntimeError(flow_obj.backtrace)

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
    message.auth_state = rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED
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

    def ChargeBytesToSession(self, session_id, length):
      pass

    def SendReply(self, rdf_value,
                  message_type=rdfvalue.GrrMessage.Type.MESSAGE, **kw):
      message = rdfvalue.GrrMessage(
          type=message_type, payload=rdf_value, **kw)

      self.responses.append(message)


class InvalidActionMock(object):
  """An action mock which raises for all actions."""

  def HandleMessage(self, unused_message):
    raise RuntimeError("Invalid Action Mock.")


class Test(actions.ActionPlugin):
  """A test action which can be used in mocks."""
  in_rdfvalue = rdfvalue.DataBlob
  out_rdfvalue = rdfvalue.DataBlob


def CheckFlowErrors(total_flows, token=None):
  # Check that all the flows are complete.
  for session_id in total_flows:
    flow_obj = aff4.FACTORY.Open(session_id, mode="r", token=token)
    if flow_obj.state.context.state != rdfvalue.Flow.State.TERMINATED:
      if flags.FLAGS.debug:
        pdb.set_trace()

      raise RuntimeError("Flow %s completed in state %s" % (
          flow_obj.state.context.flow_name,
          flow_obj.state.context.state))


def TestFlowHelper(flow_class_name, client_mock=None, client_id=None,
                   check_flow_errors=True, token=None, notification_event=None,
                   **kwargs):
  """Build a full test harness: client - worker + start flow."""
  if client_id or client_mock:
    client_mock = MockClient(client_id, client_mock, token=token)

  worker_mock = MockWorker(check_flow_errors=check_flow_errors, token=token)

  # Instantiate the flow:
  session_id = flow.GRRFlow.StartFlow(client_id, flow_class_name,
                                      notification_event=notification_event,
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

    yield client_processed

  # We should check for flow errors:
  if check_flow_errors:
    CheckFlowErrors(total_flows, token=token)


class CrashClientMock(object):

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
        args=status.SerializeToString(),
        source=self.client_id,
        auth_state=rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED)

    self.flow_id = message.session_id

    # This is normally done by the FrontEnd when a CLIENT_KILLED message is
    # received.
    flow.PublishEvent("ClientCrash", msg, token=self.token)

    return [status]


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
    old_time = time.time

    try:
      # Create the fixture at a fixed time.
      time.time = lambda: self.age
      for path, (aff4_type, attributes) in vfs_fixture:
        path %= self.args

        aff4_object = aff4.FACTORY.Create(self.client_id.Add(path),
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
  supported_pathtype = rdfvalue.PathSpec.PathType.OS

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
        stat = rdfvalue.StatEntry.FromTextFormat(
            utils.SmartStr(attributes["aff4:stat"]))
      except KeyError:
        pass

      stat.pathspec = rdfvalue.PathSpec(pathtype=self.supported_pathtype,
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
    return rdfvalue.StatEntry(pathspec=self.pathspec,
                              st_mode=16877,
                              st_size=12288,
                              st_atime=1319796280,
                              st_dev=1)


class GrrTestProgram(unittest.TestProgram):
  """A Unit test program which is compatible with conf based args parsing."""

  def __init__(self, **kw):
    # Force the test config to be read in
    flags.FLAGS.config = config_lib.CONFIG["Test.config"]
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


def main(argv=None):
  if argv is None:
    argv = sys.argv

  print "Running test %s" % argv[0]
  GrrTestProgram(argv=argv)
