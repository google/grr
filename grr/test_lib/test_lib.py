#!/usr/bin/env python
"""A library for tests."""


import codecs
import cProfile
import datetime
import email
import functools
import logging
import os
import pdb
import platform
import shutil
import socket
import sys
import tempfile
import threading
import time
import unittest


import mock
import pkg_resources

import unittest

from grr import config

from grr.client import client_utils_linux
from grr.client import comms
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import utils

from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto as rdf_crypto

from grr.server import access_control
from grr.server import aff4
from grr.server import artifact
from grr.server import client_index
from grr.server import data_store
from grr.server import email_alerts
from grr.server import flow
from grr.server.aff4_objects import aff4_grr
from grr.server.aff4_objects import filestore
from grr.server.aff4_objects import users

from grr.server.flows.general import discovery
from grr.server.hunts import results as hunts_results

from grr.test_lib import testing_startup

flags.DEFINE_list(
    "tests",
    None,
    help=("Test module to run. If not specified we run"
          "All modules in the test suite."))

flags.DEFINE_list("labels", ["small"],
                  "A list of test labels to run. (e.g. benchmarks,small).")

flags.DEFINE_string(
    "profile", "", "If set, the test is run using cProfile, storing the "
    "resulting profile data in the given filename. Running multiple tests"
    "will overwrite this file so --tests should be used to limit this to a"
    "single test.")

FIXED_TIME = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("8d")


class Error(Exception):
  """Test base error."""


class GRRBaseTest(unittest.TestCase):
  """This is the base class for all GRR tests."""

  __metaclass__ = registry.MetaclassRegistry

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
    self.base_path = config.CONFIG["Test.data_dir"]
    test_user = "test"
    users.GRRUser.SYSTEM_USERS.add(test_user)
    self.token = access_control.ACLToken(
        username=test_user, reason="Running tests")

  _set_up_lock = threading.RLock()
  _set_up_done = False

  @classmethod
  def setUpClass(cls):
    super(GRRBaseTest, cls).setUpClass()
    with GRRBaseTest._set_up_lock:
      if not GRRBaseTest._set_up_done:
        testing_startup.TestInit()
        GRRBaseTest._set_up_done = True

  def setUp(self):
    super(GRRBaseTest, self).setUp()

    tmpdir = os.environ.get("TEST_TMPDIR") or config.CONFIG["Test.tmpdir"]

    if platform.system() != "Windows":
      # Make a temporary directory for test files.
      self.temp_dir = tempfile.mkdtemp(dir=tmpdir)
    else:
      self.temp_dir = tempfile.mkdtemp()

    config.CONFIG.SetWriteBack(os.path.join(self.temp_dir, "writeback.yaml"))

    logging.info("Starting test: %s.%s", self.__class__.__name__,
                 self._testMethodName)
    self.last_start_time = time.time()

    data_store.DB.ClearTestDB()

    aff4.FACTORY.Flush()

    # Create a Foreman and Filestores, they are used in many tests.
    aff4_grr.GRRAFF4Init().Run()
    filestore.FileStoreInit().Run()
    hunts_results.ResultQueueInitHook().Run()
    email_alerts.EmailAlerterInit().RunOnce()

    # Stub out the email function
    self.emails_sent = []

    def SendEmailStub(to_user, from_user, subject, message, **unused_kwargs):
      self.emails_sent.append((to_user, from_user, subject, message))

    self.mail_stubber = utils.MultiStubber(
        (email_alerts.EMAIL_ALERTER, "SendEmail", SendEmailStub),
        (email.utils, "make_msgid", lambda: "<message id stub>"))
    self.mail_stubber.Start()

    self.nanny_stubber = utils.Stubber(
        client_utils_linux.NannyController,
        "StartNanny",
        lambda unresponsive_kill_period=None, nanny_logfile=None: True)
    self.nanny_stubber.Start()

    # We don't want to send actual email in our tests
    self.smtp_patcher = mock.patch("smtplib.SMTP")
    self.mock_smtp = self.smtp_patcher.start()

    def DisabledSet(*unused_args, **unused_kw):
      raise NotImplementedError(
          "Usage of Set() is disabled, please use a configoverrider in tests.")

    self.config_set_disable = utils.Stubber(config.CONFIG, "Set", DisabledSet)
    self.config_set_disable.Start()

  def tearDown(self):
    super(GRRBaseTest, self).setUp()

    self.config_set_disable.Stop()
    self.smtp_patcher.stop()
    self.nanny_stubber.Stop()
    self.mail_stubber.Stop()

    logging.info("Completed test: %s.%s (%.4fs)", self.__class__.__name__,
                 self._testMethodName, time.time() - self.last_start_time)

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
    return "\n%s.%s - %s\n" % (self.__class__.__name__, self._testMethodName,
                               doc)

  def _AssertRDFValuesEqual(self, x, y):
    x_has_lsf = hasattr(x, "ListSetFields")
    y_has_lsf = hasattr(y, "ListSetFields")

    if x_has_lsf != y_has_lsf:
      raise AssertionError("%s != %s" % (x, y))

    if not x_has_lsf:
      if isinstance(x, float):
        self.assertAlmostEqual(x, y)
      else:
        self.assertEqual(x, y)
      return

    processed = set()
    for desc, value in x.ListSetFields():
      processed.add(desc.name)
      self._AssertRDFValuesEqual(value, y.Get(desc.name))

    for desc, value in y.ListSetFields():
      if desc.name not in processed:
        self._AssertRDFValuesEqual(value, x.Get(desc.name))

  def assertRDFValuesEqual(self, x, y):
    """Check that two RDFStructs are equal."""
    self._AssertRDFValuesEqual(x, y)

  def DoAfterTestCheck(self):
    """May be overridden by subclasses to perform checks after every test."""
    pass

  def run(self, result=None):  # pylint: disable=g-bad-name
    """Run the test case.

    This code is basically the same as the standard library, except that when
    there is an exception, the --debug (NOTYPO) flag allows us to drop into the
    raising function for interactive inspection of the test failure.

    Args:
      result: The testResult object that we will use.
    """
    if result is None:
      result = self.defaultTestResult()
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
        profile_filename = flags.FLAGS.profile
        if profile_filename:
          cProfile.runctx("testMethod()", globals(), locals(), profile_filename)
        else:
          testMethod()
          # After-test checks are performed only if the test succeeds.
          self.DoAfterTestCheck()

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
      except Exception:  # pylint: disable=broad-except
        # Break into interactive debugger on test failure.
        if flags.FLAGS.debug:
          pdb.post_mortem()

        result.addError(self, sys.exc_info())

      try:
        self.tearDown()
      except KeyboardInterrupt:
        raise
      except Exception:  # pylint: disable=broad-except
        # Break into interactive debugger on test failure.
        if flags.FLAGS.debug:
          pdb.post_mortem()

        result.addError(self, sys.exc_info())
        ok = False

      if ok:
        result.addSuccess(self)
    finally:
      result.stopTest(self)

  def _SetupClientImpl(self,
                       client_nr,
                       index=None,
                       system=None,
                       os_version=None,
                       arch=None):
    client_id_urn = rdf_client.ClientURN("C.1%015x" % client_nr)

    with aff4.FACTORY.Create(
        client_id_urn, aff4_grr.VFSGRRClient, mode="rw",
        token=self.token) as fd:
      cert = self.ClientCertFromPrivateKey(config.CONFIG["Client.private_key"])
      fd.Set(fd.Schema.CERT, cert)

      info = fd.Schema.CLIENT_INFO()
      info.client_name = "GRR Monitor"
      fd.Set(fd.Schema.CLIENT_INFO, info)
      fd.Set(fd.Schema.PING, rdfvalue.RDFDatetime.Now())
      fd.Set(fd.Schema.HOSTNAME("Host-%x" % client_nr))
      fd.Set(fd.Schema.FQDN("Host-%x.example.com" % client_nr))
      fd.Set(
          fd.Schema.MAC_ADDRESS("aabbccddee%02x\nbbccddeeff%02x" % (client_nr,
                                                                    client_nr)))
      fd.Set(
          fd.Schema.HOST_IPS("192.168.0.%d\n2001:abcd::%x" % (client_nr,
                                                              client_nr)))

      if system:
        fd.Set(fd.Schema.SYSTEM(system))
      if os_version:
        fd.Set(fd.Schema.OS_VERSION(os_version))
      if arch:
        fd.Set(fd.Schema.ARCH(arch))

      kb = rdf_client.KnowledgeBase()
      artifact.SetCoreGRRKnowledgeBaseValues(kb, fd)
      fd.Set(fd.Schema.KNOWLEDGE_BASE, kb)

      hardware_info = fd.Schema.HARDWARE_INFO()
      hardware_info.system_manufacturer = ("System-Manufacturer-%x" % client_nr)
      hardware_info.bios_version = ("Bios-Version-%x" % client_nr)
      fd.Set(fd.Schema.HARDWARE_INFO, hardware_info)

      fd.Flush()

      index.AddClient(fd)

    return client_id_urn

  def SetupClient(self,
                  client_nr,
                  index=None,
                  system=None,
                  os_version=None,
                  arch=None):
    """Prepares a test client mock to be used.

    Args:
      client_nr: int The GRR ID to be used. 0xABCD maps to C.100000000000abcd
                     in canonical representation.
      index: client_index.ClientIndex
      system: string
      os_version: string
      arch: string

    Returns:
      rdf_client.ClientURN
    """
    if index is not None:
      # `with:' is expected to be used in the calling function.
      client_id_urn = self._SetupClientImpl(client_nr, index, system,
                                            os_version, arch)
    else:
      with client_index.CreateClientIndex(token=self.token) as index:
        client_id_urn = self._SetupClientImpl(client_nr, index, system,
                                              os_version, arch)

    return client_id_urn

  def SetupClients(self, nr_clients, system=None, os_version=None, arch=None):
    """Prepares nr_clients test client mocks to be used."""
    with client_index.CreateClientIndex(token=self.token) as index:
      client_ids = [
          self.SetupClient(client_nr, index, system, os_version, arch)
          for client_nr in xrange(nr_clients)
      ]

    return client_ids

  def DeleteClient(self, client_nr):
    """Cleans up a test client mock."""
    client_id = rdf_client.ClientURN("C.1%015x" % client_nr)
    data_store.DB.DeleteSubject(client_id, token=self.token)

  def DeleteClients(self, nr_clients):
    """Cleans up test client mocks. Analogous to .SetupClients(nr_clients) ."""
    for client_nr in xrange(nr_clients):
      self.DeleteClient(client_nr)

  def ClientCertFromPrivateKey(self, private_key):
    communicator = comms.ClientCommunicator(private_key=private_key)
    csr = communicator.GetCSR()
    return rdf_crypto.RDFX509Cert.ClientCertFromCSR(csr)

  def _SendNotification(self,
                        notification_type,
                        subject,
                        message,
                        client_id="aff4:/C.0000000000000001"):
    """Sends a notification to the current user."""
    session_id = flow.GRRFlow.StartFlow(
        client_id=client_id,
        flow_name=discovery.Interrogate.__name__,
        token=self.token)

    with aff4.FACTORY.Open(session_id, mode="rw", token=self.token) as flow_obj:
      flow_obj.Notify(notification_type, subject, message)

  def GenerateToken(self, username, reason):
    return access_control.ACLToken(username=username, reason=reason)


class ConfigOverrider(object):
  """A context to temporarily change config options."""

  def __init__(self, overrides):
    self._overrides = overrides
    self._saved_values = {}

  def __enter__(self):
    self.Start()

  def Start(self):
    for k, v in self._overrides.iteritems():
      self._saved_values[k] = config.CONFIG.GetRaw(k)
      try:
        config.CONFIG.SetRaw.old_target(k, v)
      except AttributeError:
        config.CONFIG.SetRaw(k, v)

  def __exit__(self, unused_type, unused_value, unused_traceback):
    self.Stop()

  def Stop(self):
    for k, v in self._saved_values.iteritems():
      try:
        config.CONFIG.SetRaw.old_target(k, v)
      except AttributeError:
        config.CONFIG.SetRaw(k, v)


class PreserveConfig(object):

  def __enter__(self):
    self.Start()

  def Start(self):
    self.old_config = config.CONFIG
    config.CONFIG = self.old_config.MakeNewConfig()
    config.CONFIG.initialized = self.old_config.initialized
    config.CONFIG.SetWriteBack(self.old_config.writeback.filename)
    config.CONFIG.raw_data = self.old_config.raw_data.copy()
    config.CONFIG.writeback_data = self.old_config.writeback_data.copy()

  def __exit__(self, unused_type, unused_value, unused_traceback):
    self.Stop()

  def Stop(self):
    config.CONFIG = self.old_config


class FakeTime(object):
  """A context manager for faking time."""

  def __init__(self, fake_time, increment=0):
    if isinstance(fake_time, rdfvalue.RDFDatetime):
      self.time = fake_time.AsSecondsFromEpoch()
    else:
      self.time = fake_time
    self.increment = increment

  def __enter__(self):
    self.old_time = time.time

    def Time():
      self.time += self.increment
      return self.time

    time.time = Time

    self.old_strftime = time.strftime

    def Strftime(form, t=time.localtime(Time())):
      return self.old_strftime(form, t)

    time.strftime = Strftime

    return self

  def __exit__(self, unused_type, unused_value, unused_traceback):
    time.time = self.old_time
    time.strftime = self.old_strftime


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

      def __call__(self, *args, **kw):
        return self.orig_datetime(*args, **kw)

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

  def __exit__(self, t, value, tb):
    return self.stubber.__exit__(t, value, tb)


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
        if issubclass(x, self.base_class)
    ]

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


def RequiresPackage(package_name):
  """Skip this test if required package isn't present.

  Note this will only work in opensource testing where we actually have
  packages.

  Args:
    package_name: string
  Returns:
    Decorator function
  """

  def Decorator(test_function):

    @functools.wraps(test_function)
    def Wrapper(*args, **kwargs):
      try:
        pkg_resources.get_distribution(package_name)
      except pkg_resources.DistributionNotFound:
        raise unittest.SkipTest(
            "Skipping, package %s not installed" % package_name)
      return test_function(*args, **kwargs)

    return Wrapper

  return Decorator


def SetLabel(*labels):
  """Sets a label on a function so we can run tests with different types."""

  def Decorator(f):
    # If the method is not already tagged, we replace its label (the default
    # label is "small").
    function_labels = getattr(f, "labels", set())
    f.labels = function_labels.union(set(labels))

    return f

  return Decorator


class GrrTestProgram(unittest.TestProgram):
  """A Unit test program which is compatible with conf based args parsing.

  This program ignores the testLoader passed to it and implements its
  own test loading behavior in case the --tests argument was specified
  when the program is ran. It magically reads from the --tests argument.

  In case no --tests argument was specified, the program uses the test
  loader to load the tests.
  """

  def __init__(self, labels=None, **kw):
    self.labels = labels
    super(GrrTestProgram, self).__init__(**kw)

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

    pdb.Pdb.__init__(
        self, stdin=self.handle, stdout=codecs.getwriter("utf8")(self.handle))

  def ListenForConnection(self):
    """Listens and accepts a single connection."""
    logging.warn("Remote debugger waiting for connection on %s",
                 config.CONFIG["Test.remote_pdb_port"])

    RemotePDB.old_stdout = sys.stdout
    RemotePDB.old_stdin = sys.stdin
    RemotePDB.skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    RemotePDB.skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    RemotePDB.skt.bind(("127.0.0.1", config.CONFIG["Test.remote_pdb_port"]))
    RemotePDB.skt.listen(1)

    (clientsocket, address) = RemotePDB.skt.accept()
    RemotePDB.handle = clientsocket.makefile("rw", 1)
    logging.warn("Received a connection from %s", address)


def main(argv=None):
  del argv  # Unused.
  unittest.main()
