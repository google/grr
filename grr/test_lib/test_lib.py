#!/usr/bin/env python
"""A library for tests."""

import datetime

import doctest
import email
import functools
import itertools
import logging
import os
import shutil
import threading
import time
import unittest
from unittest import mock

from absl.testing import absltest
import pkg_resources

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.util import cache
from grr_response_core.lib.util import precondition
from grr_response_core.lib.util import temp
from grr_response_core.stats import stats_collector_instance
from grr_response_server import access_control
from grr_response_server import client_index
from grr_response_server import data_store
from grr_response_server import email_alerts
from grr_response_server import prometheus_stats_collector
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import testing_startup

FIXED_TIME = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration.From(
    8, rdfvalue.DAYS)
TEST_CLIENT_ID = "C.1000000000000000"


class GRRBaseTest(absltest.TestCase):
  """This is the base class for all GRR tests."""

  def __init__(self, methodName=None):  # pylint: disable=g-bad-name
    """Hack around unittest's stupid constructor.

    We sometimes need to instantiate the test suite without running any tests -
    e.g. to start initialization or setUp() functions. The unittest constructor
    requires to provide a valid method name.

    Args:
      methodName: The test method to run.
    """
    super().__init__(methodName=methodName or "__init__")
    self.base_path = config.CONFIG["Test.data_dir"]

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    logging.disable(logging.CRITICAL)

  @classmethod
  def tearDownClass(cls):
    logging.disable(logging.NOTSET)
    super().tearDownClass()

  def setUp(self):
    super().setUp()

    self.test_username = "test"

    system_users_patcher = mock.patch.object(
        access_control, "SYSTEM_USERS",
        frozenset(
            itertools.chain(access_control.SYSTEM_USERS, [self.test_username])))
    system_users_patcher.start()
    self.addCleanup(system_users_patcher.stop)

    self.temp_dir = temp.TempDirPath()
    config.CONFIG.SetWriteBack(os.path.join(self.temp_dir, "writeback.yaml"))
    self.addCleanup(lambda: shutil.rmtree(self.temp_dir, ignore_errors=True))

    # Each datastore is wrapped with DatabaseValidationWrapper, so we have
    # to access the delegate directly (assuming it's an InMemoryDB
    # implementation).
    data_store.REL_DB.delegate.ClearTestDB()

    email_alerts.InitializeEmailAlerterOnce()

    # Stub out the email function
    self.emails_sent = []

    def SendEmailStub(to_addresses, from_address, subject, message,
                      **unused_kwargs):
      self.emails_sent.append((to_addresses, from_address, subject, message))

    self.mail_stubber = utils.MultiStubber(
        (email_alerts.EMAIL_ALERTER, "SendEmail", SendEmailStub),
        (email.utils, "make_msgid", lambda: "<message id stub>"))
    self.mail_stubber.Start()
    self.addCleanup(self.mail_stubber.Stop)

    # We don't want to send actual email in our tests
    self.smtp_patcher = mock.patch("smtplib.SMTP")
    self.mock_smtp = self.smtp_patcher.start()
    self.addCleanup(self.smtp_patcher.stop)

    def DisabledSet(*unused_args, **unused_kw):
      raise NotImplementedError(
          "Usage of Set() is disabled, please use a configoverrider in tests.")

    self.config_set_disable = utils.Stubber(config.CONFIG, "Set", DisabledSet)
    self.config_set_disable.Start()
    self.addCleanup(self.config_set_disable.Stop)

    self._SetupFakeStatsContext()

    # Turn off WithLimitedCallFrequency-based caching in tests. Tests that need
    # to test caching behavior explicitly, should turn it on explicitly.
    with_limited_call_frequency_stubber = utils.Stubber(
        cache, "WITH_LIMITED_CALL_FREQUENCY_PASS_THROUGH", True)
    with_limited_call_frequency_stubber.Start()
    self.addCleanup(with_limited_call_frequency_stubber.Stop)

  def _SetupFakeStatsContext(self):
    """Creates a stats context for running tests based on defined metrics."""
    # Reset stats_collector_instance to None, then reinitialize it.
    patcher = mock.patch.object(stats_collector_instance, "_stats_singleton",
                                None)
    patcher.start()
    self.addCleanup(patcher.stop)
    stats_collector_instance.Set(
        prometheus_stats_collector.PrometheusStatsCollector())

  def SetupClient(self,
                  client_nr,
                  arch="x86_64",
                  fqdn=None,
                  labels=None,
                  last_boot_time=None,
                  install_time=None,
                  kernel="4.0.0",
                  os_version="buster/sid",
                  ping=None,
                  system="Linux",
                  users=None,
                  memory_size=None,
                  add_cert=True,
                  fleetspeak_enabled=False):
    """Prepares a test client mock to be used.

    Args:
      client_nr: int The GRR ID to be used. 0xABCD maps to C.100000000000abcd in
        canonical representation.
      arch: string
      fqdn: string
      labels: list of labels (strings)
      last_boot_time: RDFDatetime
      install_time: RDFDatetime
      kernel: string
      os_version: string
      ping: RDFDatetime
      system: string
      users: list of rdf_client.User objects.
      memory_size: bytes
      add_cert: boolean
      fleetspeak_enabled: boolean

    Returns:
      the client_id: string
    """
    client = self._SetupTestClientObject(
        client_nr,
        add_cert=add_cert,
        arch=arch,
        fqdn=fqdn,
        install_time=install_time,
        labels=labels,
        last_boot_time=last_boot_time,
        kernel=kernel,
        memory_size=memory_size,
        os_version=os_version,
        ping=ping or rdfvalue.RDFDatetime.Now(),
        system=system,
        users=users,
        fleetspeak_enabled=fleetspeak_enabled)
    return client.client_id

  def SetupClients(self, nr_clients, *args, **kwargs):
    """Prepares nr_clients test client mocks to be used."""
    return self.SetupClientsWithIndices(range(nr_clients), *args, **kwargs)

  def SetupClientsWithIndices(self, indices, *args, **kwargs):
    """Sets up mock clients, one for each numerical index in 'indices'."""
    return [self.SetupClient(i, *args, **kwargs) for i in indices]

  def _TestClientInfo(self, labels=None):
    res = rdf_client.ClientInformation(
        client_name="GRR Monitor",
        client_version=config.CONFIG["Source.version_numeric"],
        build_time="1980-01-01")
    if labels is None:
      res.labels = ["label1", "label2"]
    else:
      res.labels = labels
    return res

  def _TestInterfaces(self, client_nr):
    ip1 = rdf_client_network.NetworkAddress()
    ip1.human_readable_address = "192.168.0.%d" % client_nr

    ip2 = rdf_client_network.NetworkAddress()
    ip2.human_readable_address = "2001:abcd::%x" % client_nr

    mac1 = rdf_client_network.MacAddress.FromHumanReadableAddress(
        "abcbccddee%02x" % client_nr)
    mac1 = rdf_client_network.MacAddress.FromHumanReadableAddress(
        "aabbccddee%02x" % client_nr)
    mac2 = rdf_client_network.MacAddress.FromHumanReadableAddress(
        "bbccddeeff%02x" % client_nr)

    return [
        rdf_client_network.Interface(ifname="if0", addresses=[ip1, ip2]),
        rdf_client_network.Interface(ifname="if1", mac_address=mac1),
        rdf_client_network.Interface(ifname="if2", mac_address=mac2),
    ]

  def _SetupTestClientObject(self,
                             client_nr,
                             add_cert=True,
                             arch="x86_64",
                             fqdn=None,
                             install_time=None,
                             last_boot_time=None,
                             kernel="4.0.0",
                             memory_size=None,
                             os_version="buster/sid",
                             ping=None,
                             system="Linux",
                             users=None,
                             labels=None,
                             fleetspeak_enabled=False):
    """Prepares a test client object."""
    client_id = u"C.1%015x" % client_nr

    client = rdf_objects.ClientSnapshot(client_id=client_id)
    client.startup_info.client_info = self._TestClientInfo(labels=labels)
    if last_boot_time is not None:
      client.startup_info.boot_time = last_boot_time

    client.knowledge_base.fqdn = fqdn or "Host-%x.example.com" % client_nr
    client.knowledge_base.os = system
    client.knowledge_base.users = users or [
        rdf_client.User(username=u"user1"),
        rdf_client.User(username=u"user2"),
    ]

    client.os_version = os_version
    client.arch = arch
    client.kernel = kernel

    client.interfaces = self._TestInterfaces(client_nr)
    client.install_time = install_time

    client.hardware_info = rdf_client.HardwareInfo(
        system_manufacturer="System-Manufacturer-%x" % client_nr,
        bios_version="Bios-Version-%x" % client_nr)

    if memory_size is not None:
      client.memory_size = memory_size

    ping = ping or rdfvalue.RDFDatetime.Now()
    if add_cert:
      cert = self.ClientCertFromPrivateKey(config.CONFIG["Client.private_key"])
    else:
      cert = None

    data_store.REL_DB.WriteClientMetadata(
        client_id,
        last_ping=ping,
        certificate=cert,
        fleetspeak_enabled=fleetspeak_enabled)
    data_store.REL_DB.WriteClientSnapshot(client)

    client_index.ClientIndex().AddClient(client)
    if labels is not None:
      data_store.REL_DB.AddClientLabels(client_id, u"GRR", labels)
      client_index.ClientIndex().AddClientLabels(client_id, labels)

    return client

  def AddClientLabel(self, client_id, owner, name):
    data_store.REL_DB.AddClientLabels(client_id, owner, [name])
    client_index.ClientIndex().AddClientLabels(client_id, [name])

  def ClientCertFromPrivateKey(self, private_key):
    common_name = rdf_client.ClientURN.FromPrivateKey(private_key)
    csr = rdf_crypto.CertificateSigningRequest(
        common_name=common_name, private_key=private_key)
    return rdf_crypto.RDFX509Cert.ClientCertFromCSR(csr)


class ConfigOverrider(object):
  """A context to temporarily change config options."""

  def __init__(self, overrides):
    self._overrides = overrides
    self._old_cache = None
    self._old_global_override = None

  def __enter__(self):
    self.Start()

  def Start(self):
    self._old_cache = config.CONFIG.cache
    config.CONFIG.cache = dict()

    self._old_global_override = config.CONFIG.global_override
    config.CONFIG.global_override = self._old_global_override.copy()
    config.CONFIG.global_override.update(self._overrides)

  def __exit__(self, unused_type, unused_value, unused_traceback):
    self.Stop()

  def Stop(self):
    config.CONFIG.cache = self._old_cache
    config.CONFIG.global_override = self._old_global_override


class PreserveConfig(object):

  def __enter__(self):
    self.Start()

  def Start(self):
    self.old_config = config.CONFIG
    config.CONFIG = self.old_config.MakeNewConfig()
    config.CONFIG.initialized = self.old_config.initialized
    config.CONFIG.SetWriteBack(self.old_config.writeback.config_path)
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
      self.time = fake_time.AsMicrosecondsSinceEpoch() / 1e6
    elif isinstance(fake_time, str):
      self.time = rdfvalue.RDFDatetime.FromHumanReadable(
          fake_time).AsMicrosecondsSinceEpoch() / 1e6
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


# TODO(hanuszczak): `FakeTime` and `FakeTimeline` serve a similar purpose,
# although `FakeTimeline` (arguably) allows to write more sophisticated tests.
# Therefore, it should be possible to rewrite existing test code to use
# `FakeTimeline` instead of `FakeTime`. Once done, `FakeTime` should be removed.
# TODO(hanuszczak): Write proper documentation.
class FakeTimeline(object):
  """A context manager for testing time-aware code.

  This utility class overrides `time.sleep` and `time.time` methods so that the
  code that uses them can be tested. It is assumed that the code that needs to
  be tested runs on some thread. Using `Run` method one can simulate running
  this thread for certain amount of time but without spending that time waiting
  for anything.

  While internally the simulation actually executes the code on a separate
  thread, it can be thought as if the code was executed synchronously on the
  current thread. However, the time flow is "immediate" and `time.sleep` calls
  do not really block.

  For example, it is possible to instantly simulate running a thread for half an
  hour (assuming that most of that time the thread would be spent sleeping).

  In order to reliably test flow of time-aware code, it is assumed that only the
  `time.sleep` function causes the time flow. In other words, every non-`sleep`
  line of code is assumed to be executed instantly. In particular, if there is
  an infinite loop without any `time.sleep` calls the running the simulation
  for any number of seconds will block indefinitely. This is not a big issue
  since this class is intended to be used only for testing purposes.
  """

  class _WorkerThreadExit(Exception):  # pylint: disable=g-bad-exception-name
    pass

  def __init__(self, thread, now=None):
    """Initializes the timeline.

    Args:
      thread: A thread to perform controlled execution on.
      now: An `RDFDatetime` object representing starting point of the timeline.
        If no value is provided, current time is used.

    Raises:
      TypeError: If `thread` is not an instance of `Thread` or if `now` is not
                 an instance of `RDFDatetime`.
    """
    if not isinstance(thread, threading.Thread):
      raise TypeError("`thread` is not an instance of `threading.Thread`")
    if now is not None and not isinstance(now, rdfvalue.RDFDatetime):
      raise TypeError("`now` is not an instance of `rdfvalue.RDFDatetime`")

    self._thread = thread

    self._owner_thread_turn = threading.Event()
    self._worker_thread_turn = threading.Event()

    # Fake, "current" number of seconds since epoch.
    self._time = (now or rdfvalue.RDFDatetime.Now()).AsSecondsSinceEpoch()
    # Number of seconds that the worker thread can sleep.
    self._budget = 0

    self._worker_thread = None
    self._worker_thread_done = False
    self._worker_thread_exception = None

  def Run(self, duration):
    """Simulated running the underlying thread for the specified duration.

    Args:
      duration: A `Duration` object describing for how long simulate the thread.

    Raises:
      TypeError: If `duration` is not an instance of `rdfvalue.Duration`.
      AssertionError: If this method is called without automatic context.
    """
    precondition.AssertType(duration, rdfvalue.Duration)

    if self._worker_thread is None:
      raise AssertionError("Worker thread hasn't been started (method was "
                           "probably called without context initialization)")

    if self._worker_thread_done:
      return

    self._budget += duration.ToInt(rdfvalue.SECONDS)

    self._original_time = time.time
    self._original_sleep = time.sleep

    with utils.Stubber(time, "time", self._Time),\
         utils.Stubber(time, "sleep", self._Sleep):
      self._owner_thread_turn.clear()
      self._worker_thread_turn.set()
      self._owner_thread_turn.wait()

    if self._worker_thread_exception is not None:
      # TODO(hanuszczak): Investigate why this linter warning is triggered.
      raise self._worker_thread_exception  # pylint: disable=raising-bad-type

  def __enter__(self):
    if self._worker_thread is not None:
      raise AssertionError("Worker thread has been already started, context "
                           "cannot be reused.")

    def Worker():
      self._worker_thread_turn.wait()

      try:
        if self._worker_thread_done:
          raise FakeTimeline._WorkerThreadExit

        self._thread.run()
      except FakeTimeline._WorkerThreadExit:
        pass
      except Exception as exception:  # pylint: disable=broad-except
        self._worker_thread_exception = exception

      self._worker_thread_done = True
      self._owner_thread_turn.set()

    self._worker_thread = threading.Thread(
        target=Worker, name="FakeTimelineThread")
    self._worker_thread.start()

    return self

  def __exit__(self, exc_type, exc_value, exc_traceback):
    del exc_type, exc_value, exc_traceback  # Unused.

    self._worker_thread_done = True
    self._worker_thread_turn.set()
    self._worker_thread.join(5.0)
    if self._worker_thread.is_alive():
      raise RuntimeError("FakeTimelineThread did not complete.")

  def _Sleep(self, seconds):
    if threading.current_thread() is not self._worker_thread:
      return self._original_sleep(seconds)

    self._time += seconds
    self._budget -= seconds

    while self._budget < 0:
      self._worker_thread_turn.clear()
      self._owner_thread_turn.set()
      self._worker_thread_turn.wait()

      if self._worker_thread_done:
        raise FakeTimeline._WorkerThreadExit()

  def _Time(self):
    if threading.current_thread() is not self._worker_thread:
      return self._original_time()

    return self._time


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

    @functools.wraps(self.old_target)
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
        raise unittest.SkipTest("Skipping, package %s not installed" %
                                package_name)
      return test_function(*args, **kwargs)

    return Wrapper

  return Decorator


class SuppressLogs(object):
  """A context manager for suppressing logging."""

  def __enter__(self):
    self.old_error = logging.error
    self.old_warning = logging.warning
    self.old_info = logging.info
    self.old_debug = logging.debug
    logging.error = lambda *args, **kw: None
    logging.warning = lambda *args, **kw: None
    logging.info = lambda *args, **kw: None
    logging.debug = lambda *args, **kw: None

    return self

  def __exit__(self, unused_type, unused_value, unused_traceback):
    logging.error = self.old_error
    logging.warning = self.old_warning
    logging.info = self.old_info
    logging.debug = self.old_debug


class DocTest(absltest.TestCase):
  """A TestCase that tests examples in docstrings using doctest.

  Attributes:
    module: A reference to the module to be tested.
  """
  module = None

  def testDocStrings(self):
    """Test all examples in docstrings using doctest."""

    self.assertIsNotNone(self.module, "Set DocTest.module to test docstrings.")
    try:
      num_failed, num_attempted = doctest.testmod(
          self.module, raise_on_error=True)
    except doctest.DocTestFailure as e:
      name = e.test.name
      if "." in name:
        name = name.split(".")[-1]  # Remove long module prefix.

      filename = os.path.basename(e.test.filename)

      self.fail("DocTestFailure in {} ({} on line {}):\n"
                ">>> {}Expected : {}Actual   : {}".format(
                    name, filename, e.test.lineno, e.example.source,
                    e.example.want, e.got))

    # Fail if DocTest is referenced, but no examples in docstrings are present.
    self.assertGreater(num_attempted, 0, "No doctests were found!")

    # num_failed > 0 should not happen because raise_on_error = True.
    self.assertEqual(num_failed, 0, "{} doctests failed.".format(num_failed))


def main(argv=None):
  del argv  # Unused.
  testing_startup.TestInit()
  absltest.main()
