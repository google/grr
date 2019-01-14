#!/usr/bin/env python
"""A library for tests."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime
import email
import functools
import logging
import os
import shutil
import threading
import time
import unittest


from absl.testing import absltest
from builtins import range  # pylint: disable=redefined-builtin
from future.utils import iteritems
from future.utils import itervalues
import mock
import pkg_resources

from grr_response_client import comms
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.stats import default_stats_collector
from grr_response_core.stats import stats_collector_instance
from grr_response_core.stats import stats_test_utils
from grr_response_server import access_control
from grr_response_server import aff4
from grr_response_server import artifact
from grr_response_server import client_index
from grr_response_server import data_store
from grr_response_server import email_alerts
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.aff4_objects import filestore
from grr_response_server.aff4_objects import users as aff4_users
from grr_response_server.flows.general import audit
from grr_response_server.hunts import results as hunts_results
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import temp
from grr.test_lib import testing_startup

FIXED_TIME = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("8d")
TEST_CLIENT_ID = rdf_client.ClientURN("C.1000000000000000")


class GRRBaseTest(absltest.TestCase):
  """This is the base class for all GRR tests."""

  use_relational_reads = False

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
    test_user = u"test"
    aff4_users.GRRUser.SYSTEM_USERS.add(test_user)
    self.token = access_control.ACLToken(
        username=test_user, reason="Running tests")

  def setUp(self):
    super(GRRBaseTest, self).setUp()

    self.temp_dir = temp.TempDirPath()
    config.CONFIG.SetWriteBack(os.path.join(self.temp_dir, "writeback.yaml"))

    logging.info("Starting test: %s.%s", self.__class__.__name__,
                 self._testMethodName)
    self.last_start_time = time.time()

    data_store.DB.ClearTestDB()
    # Each datastore is wrapped with DatabaseValidationWrapper, so we have
    # to access the delegate directly (assuming it's an InMemoryDB
    # implementation).
    data_store.REL_DB.delegate.ClearTestDB()

    aff4.FACTORY.Flush()

    # Create a Foreman and Filestores, they are used in many tests.
    aff4_grr.GRRAFF4Init().Run()
    filestore.FileStoreInit().Run()
    hunts_results.ResultQueueInitHook().Run()
    email_alerts.EmailAlerterInit().RunOnce()
    audit.AuditEventListener._created_logs.clear()

    # Stub out the email function
    self.emails_sent = []

    def SendEmailStub(to_user, from_user, subject, message, **unused_kwargs):
      self.emails_sent.append((to_user, from_user, subject, message))

    self.mail_stubber = utils.MultiStubber(
        (email_alerts.EMAIL_ALERTER, "SendEmail", SendEmailStub),
        (email.utils, "make_msgid", lambda: "<message id stub>"))
    self.mail_stubber.Start()

    # We don't want to send actual email in our tests
    self.smtp_patcher = mock.patch("smtplib.SMTP")
    self.mock_smtp = self.smtp_patcher.start()

    def DisabledSet(*unused_args, **unused_kw):
      raise NotImplementedError(
          "Usage of Set() is disabled, please use a configoverrider in tests.")

    self.config_set_disable = utils.Stubber(config.CONFIG, "Set", DisabledSet)
    self.config_set_disable.Start()

    if self.use_relational_reads:
      self.relational_read_stubber = utils.Stubber(
          data_store, "RelationalDBReadEnabled", lambda: True)
      self.relational_read_stubber.Start()

    self._SetupFakeStatsContext()

  def _SetupFakeStatsContext(self):
    """Creates a stats context for running tests based on defined metrics."""
    metrics_metadata = list(
        itervalues(stats_collector_instance.Get().GetAllMetricsMetadata()))
    fake_stats_collector = default_stats_collector.DefaultStatsCollector(
        metrics_metadata)
    fake_stats_context = stats_test_utils.FakeStatsContext(fake_stats_collector)
    fake_stats_context.start()
    self.addCleanup(fake_stats_context.stop)

  def tearDown(self):
    super(GRRBaseTest, self).tearDown()

    self.config_set_disable.Stop()
    self.smtp_patcher.stop()
    self.mail_stubber.Stop()
    if self.use_relational_reads:
      self.relational_read_stubber.Stop()

    logging.info("Completed test: %s.%s (%.4fs)", self.__class__.__name__,
                 self._testMethodName,
                 time.time() - self.last_start_time)

    # This may fail on filesystems which do not support unicode filenames.
    try:
      shutil.rmtree(self.temp_dir, True)
    except UnicodeError:
      pass

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

  def _SetupClientImpl(self,
                       client_nr,
                       index=None,
                       arch="x86_64",
                       fqdn=None,
                       install_time=None,
                       last_boot_time=None,
                       kernel="4.0.0",
                       os_version="buster/sid",
                       ping=None,
                       system="Linux",
                       users=None,
                       memory_size=None,
                       add_cert=True,
                       fleetspeak_enabled=False):
    client_id_urn = rdf_client.ClientURN("C.1%015x" % client_nr)

    with aff4.FACTORY.Create(
        client_id_urn, aff4_grr.VFSGRRClient, mode="rw",
        token=self.token) as fd:
      if add_cert:
        cert = self.ClientCertFromPrivateKey(
            config.CONFIG["Client.private_key"])
        fd.Set(fd.Schema.CERT, cert)

      fd.Set(fd.Schema.CLIENT_INFO, self._TestClientInfo())
      fd.Set(fd.Schema.PING, ping or rdfvalue.RDFDatetime.Now())
      if fqdn is not None:
        fd.Set(fd.Schema.HOSTNAME(fqdn.split(".", 1)[0]))
        fd.Set(fd.Schema.FQDN(fqdn))
      else:
        fd.Set(fd.Schema.HOSTNAME("Host-%x" % client_nr))
        fd.Set(fd.Schema.FQDN("Host-%x.example.com" % client_nr))
      fd.Set(
          fd.Schema.MAC_ADDRESS(
              "aabbccddee%02x\nbbccddeeff%02x" % (client_nr, client_nr)))
      fd.Set(
          fd.Schema.HOST_IPS(
              "192.168.0.%d\n2001:abcd::%x" % (client_nr, client_nr)))

      if system:
        fd.Set(fd.Schema.SYSTEM(system))
      if os_version:
        fd.Set(fd.Schema.OS_VERSION(os_version))
      if arch:
        fd.Set(fd.Schema.ARCH(arch))
      if kernel:
        fd.Set(fd.Schema.KERNEL(kernel))
      if memory_size:
        fd.Set(fd.Schema.MEMORY_SIZE(memory_size))

      if last_boot_time:
        fd.Set(fd.Schema.LAST_BOOT_TIME(last_boot_time))
      if install_time:
        fd.Set(fd.Schema.INSTALL_DATE(install_time))
      if fleetspeak_enabled:
        fd.Set(fd.Schema.FLEETSPEAK_ENABLED, rdfvalue.RDFBool(True))

      kb = rdf_client.KnowledgeBase()
      kb.fqdn = fqdn or "Host-%x.example.com" % client_nr
      kb.users = users or [
          rdf_client.User(username="user1"),
          rdf_client.User(username="user2"),
      ]
      artifact.SetCoreGRRKnowledgeBaseValues(kb, fd)
      fd.Set(fd.Schema.KNOWLEDGE_BASE, kb)

      fd.Set(fd.Schema.INTERFACES(self._TestInterfaces(client_nr)))

      hardware_info = fd.Schema.HARDWARE_INFO()
      hardware_info.system_manufacturer = ("System-Manufacturer-%x" % client_nr)
      hardware_info.bios_version = ("Bios-Version-%x" % client_nr)
      fd.Set(fd.Schema.HARDWARE_INFO, hardware_info)

      fd.Flush()

      index.AddClient(fd)

    return client_id_urn

  def SetupClient(self,
                  client_nr,
                  arch="x86_64",
                  fqdn=None,
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
      rdf_client.ClientURN
    """
    res = None
    if data_store.RelationalDBWriteEnabled():
      client = self.SetupTestClientObject(
          client_nr,
          add_cert=add_cert,
          arch=arch,
          fqdn=fqdn,
          install_time=install_time,
          last_boot_time=last_boot_time,
          kernel=kernel,
          memory_size=memory_size,
          os_version=os_version,
          ping=ping or rdfvalue.RDFDatetime.Now(),
          system=system,
          users=users,
          fleetspeak_enabled=fleetspeak_enabled)
      # TODO(amoser): Make this function return unicode client ids only.
      res = rdf_client.ClientURN(client.client_id)

    if data_store.AFF4Enabled():
      with client_index.CreateClientIndex(token=self.token) as index:
        res = self._SetupClientImpl(
            client_nr,
            index=index,
            arch=arch,
            fqdn=fqdn,
            install_time=install_time,
            last_boot_time=last_boot_time,
            kernel=kernel,
            os_version=os_version,
            ping=ping,
            system=system,
            users=users,
            memory_size=memory_size,
            add_cert=add_cert,
            fleetspeak_enabled=fleetspeak_enabled)

    return res

  def SetupClients(self, nr_clients, *args, **kwargs):
    """Prepares nr_clients test client mocks to be used."""
    return self.SetupClientsWithIndices(range(nr_clients), *args, **kwargs)

  def SetupClientsWithIndices(self, indices, *args, **kwargs):
    """Sets up mock clients, one for each numerical index in 'indices'."""
    return [self.SetupClient(i, *args, **kwargs) for i in indices]

  def _TestClientInfo(self):
    return rdf_client.ClientInformation(
        client_name="GRR Monitor",
        client_version=config.CONFIG["Source.version_numeric"],
        build_time="1980-01-01",
        labels=["label1", "label2"])

  def _TestInterfaces(self, client_nr):
    ip1 = rdf_client_network.NetworkAddress()
    ip1.human_readable_address = "192.168.0.%d" % client_nr

    ip2 = rdf_client_network.NetworkAddress()
    ip2.human_readable_address = "2001:abcd::%x" % client_nr

    mac1 = rdf_client_network.MacAddress()
    mac1.human_readable_address = "aabbccddee%02x" % client_nr

    mac2 = rdf_client_network.MacAddress()
    mac2.human_readable_address = "bbccddeeff%02x" % client_nr

    return [
        rdf_client_network.Interface(addresses=[ip1, ip2]),
        rdf_client_network.Interface(mac_address=mac1),
        rdf_client_network.Interface(mac_address=mac2),
    ]

  def SetupTestClientObjects(self,
                             client_count,
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
    res = {}
    for client_nr in range(client_count):
      client = self.SetupTestClientObject(
          client_nr,
          add_cert=add_cert,
          arch=arch,
          fqdn=fqdn,
          install_time=install_time,
          last_boot_time=last_boot_time,
          kernel=kernel,
          memory_size=memory_size,
          os_version=os_version,
          ping=ping,
          system=system,
          users=users,
          labels=labels,
          fleetspeak_enabled=fleetspeak_enabled)
      res[client.client_id] = client
    return res

  def SetupTestClientObject(self,
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
    client.startup_info.client_info = self._TestClientInfo()
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

    if labels:
      data_store.REL_DB.AddClientLabels(client_id, u"GRR", labels)
      client_index.ClientIndex().AddClientLabels(
          client_id, data_store.REL_DB.ReadClientLabels(client_id))

    return client

  def AddClientLabel(self, client_id, owner, name):
    if data_store.RelationalDBReadEnabled():
      if hasattr(client_id, "Basename"):
        client_id = client_id.Basename()

      data_store.REL_DB.AddClientLabels(client_id, owner, [name])
      client_index.ClientIndex().AddClientLabels(client_id, [name])
    else:
      with aff4.FACTORY.Open(
          client_id, mode="rw", token=self.token) as client_obj:
        client_obj.AddLabel(name, owner=owner)

        with client_index.CreateClientIndex(token=self.token) as index:
          index.AddClient(client_obj)

  def ClientCertFromPrivateKey(self, private_key):
    communicator = comms.ClientCommunicator(private_key=private_key)
    csr = communicator.GetCSR()
    return rdf_crypto.RDFX509Cert.ClientCertFromCSR(csr)

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
    for k, v in iteritems(self._overrides):
      self._saved_values[k] = config.CONFIG.GetRaw(k)
      try:
        config.CONFIG.SetRaw.old_target(k, v)
      except AttributeError:
        config.CONFIG.SetRaw(k, v)

  def __exit__(self, unused_type, unused_value, unused_traceback):
    self.Stop()

  def Stop(self):
    for k, v in iteritems(self._saved_values):
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
      self.time = fake_time.AsMicrosecondsSinceEpoch() / 1e6
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

  class _WorkerThreadExit(BaseException):
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
    if not isinstance(duration, rdfvalue.Duration):
      raise TypeError("`duration` is not an instance of `rdfvalue.Duration")

    if self._worker_thread is None:
      raise AssertionError("Worker thread hasn't been started (method was "
                           "probably called without context initialization)")

    if self._worker_thread_done:
      return

    self._budget += duration.seconds

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
        raise unittest.SkipTest(
            "Skipping, package %s not installed" % package_name)
      return test_function(*args, **kwargs)

    return Wrapper

  return Decorator


class SuppressLogs(object):
  """A context manager for suppressing logging."""

  def __enter__(self):
    self.old_error = logging.error
    self.old_warn = logging.warn
    self.old_info = logging.info
    self.old_debug = logging.debug
    logging.error = lambda *args, **kw: None
    logging.warn = lambda *args, **kw: None
    logging.info = lambda *args, **kw: None
    logging.debug = lambda *args, **kw: None

    return self

  def __exit__(self, unused_type, unused_value, unused_traceback):
    logging.error = self.old_error
    logging.warn = self.old_warn
    logging.info = self.old_info
    logging.debug = self.old_debug


def main(argv=None):
  del argv  # Unused.
  testing_startup.TestInit()
  absltest.main()
