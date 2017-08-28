#!/usr/bin/env python
"""Base module for end to end tests that run flows on clients."""



import re
import time
import traceback
import unittest


from grr import config as grr_config
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib.rdfvalues import client as rdf_client
from grr.server import aff4
from grr.server import client_index
from grr.server import data_store
from grr.server import flow
from grr.server import flow_utils
from grr.server.aff4_objects import aff4_grr
from grr.server.flows.console import debugging
from grr.server.flows.general import discovery


class Error(Exception):
  """Test base error."""


class ErrorEmptyCollection(Error):
  """Raise when we expect values in a collection, but it is empty."""


class TestStateUncleanError(Error):
  """Raised when tests encounter bad state that indicates a cleanup failure."""


def RecursiveListChildren(prefix=None, token=None):
  all_urns = set()
  act_urns = set([prefix])

  while act_urns:
    next_urns = set()
    for _, children in aff4.FACTORY.MultiListChildren(act_urns, token=token):
      for urn in children:
        next_urns.add(urn)
    all_urns |= next_urns
    act_urns = next_urns
  return all_urns


class ClientTestBase(unittest.TestCase):
  """This is the base class for all client tests.

  Tests should only inherit from this class if they are not safe to be run in
  prod with the EndToEndTests cronjob.
  """
  platforms = []
  flow = None
  args = {}
  network_bytes_limit = None
  timeout = flow_utils.DEFAULT_TIMEOUT
  test_output_path = None
  # How long after flow is marked complete we should expect results to be
  # available in the collection. This is essentially how quickly we expect
  # results to be available to users in the UI.
  RESULTS_SLA_SECONDS = 10

  # Only run on clients after this version
  client_min_version = None

  __metaclass__ = registry.MetaclassRegistry

  def __str__(self):
    return self.__class__.__name__

  def __init__(self,
               client_id=None,
               platform=None,
               local_worker=False,
               token=None,
               local_client=True):
    # If we get passed a string, turn it into a urn.
    self.client_id = rdf_client.ClientURN(client_id)
    self.platform = platform
    self.token = token
    self.local_worker = local_worker
    self.local_client = local_client
    self.delete_urns = set()
    super(ClientTestBase, self).__init__(methodName="runTest")

  def _CleanState(self):
    if self.test_output_path:
      self.delete_urns.add(self.client_id.Add(self.test_output_path))

    for urn in self.delete_urns:
      self.DeleteUrn(urn)

    if self.delete_urns:
      self.VerifyEmpty(self.delete_urns)

  def setUp(self):
    self._CleanState()

  def tearDown(self):
    self._CleanState()

  def runTest(self):
    if self.client_min_version:
      target_client = aff4.FACTORY.Open(self.client_id, token=self.token)
      client_info = target_client.Get(target_client.Schema.CLIENT_INFO)
      if client_info.client_version < self.client_min_version:
        message = "Skipping version %s less than client_min_version: %s" % (
            client_info.client_version, self.client_min_version)
        return self.skipTest(message)

    if self.local_worker:
      self.session_id = debugging.StartFlowAndWorker(self.client_id, self.flow,
                                                     **self.args)
    else:
      self.session_id = flow_utils.StartFlowAndWait(
          self.client_id,
          flow_name=self.flow,
          timeout=self.timeout,
          token=self.token,
          **self.args)

    self.CheckFlow()

  def CheckFlow(self):
    pass

  def VerifyEmpty(self, urns):
    """Verify urns have been deleted."""
    try:
      for urn in urns:
        # TODO(user): aff4.FACTORY.Stat() is the right thing to use here.
        # We open each urn to generate InstantiationError on failures, multiopen
        # ignores these errors.  This isn't too slow since it's almost always
        # just one path anyway.
        aff4.FACTORY.Open(urn, aff4_type=aff4.AFF4Volume, token=self.token)
    except aff4.InstantiationError:
      raise TestStateUncleanError(
          "Path wasn't deleted: %s" % traceback.format_exc())

  def DeleteUrn(self, urn):
    """Deletes an object from the db and the index, and flushes the caches."""
    data_store.DB.DeleteSubject(urn, sync=True, token=self.token)
    aff4.FACTORY._DeleteChildFromIndex(urn, token=self.token)
    aff4.FACTORY.Flush()

  def GetGRRBinaryName(self, run_interrogate=True):
    client = aff4.FACTORY.Open(self.client_id, mode="r", token=self.token)
    self.assertIsInstance(client, aff4_grr.VFSGRRClient)
    config = client.Get(aff4_grr.VFSGRRClient.SchemaCls.GRR_CONFIGURATION)

    if config is None:
      # Try running Interrogate once.
      if run_interrogate:
        flow_utils.StartFlowAndWait(
            self.client_id,
            flow_name=discovery.Interrogate.__name__,
            token=self.token)
        return self.GetGRRBinaryName(run_interrogate=False)
      else:
        self.fail("No valid configuration found, interrogate the client before "
                  "running this test.")
    else:
      try:
        self.binary_name = config["Client.binary_name"]
      except KeyError:
        self.binary_name = config["Client.name"]
      return self.binary_name

  def CheckMacMagic(self, fd):
    data = fd.Read(10)
    magic_values = ["cafebabe", "cefaedfe", "cffaedfe"]
    magic_values = [x.decode("hex") for x in magic_values]
    self.assertIn(
        data[:4],
        magic_values,
        msg="Data %s not one of %s" % (data[:4], magic_values))

  def CheckELFMagic(self, fd):
    data = fd.Read(10)
    self.assertEqual(data[1:4], "ELF")

  def CheckPEMagic(self, fd):
    data = fd.Read(10)
    self.assertEqual(data[:2], "MZ")

  def CheckResultCollectionNotEmptyWithRetry(self, flow_urn):
    """Check collection for results, return list if they exist.

    Args:
      flow_urn: URN of the flow
    Returns:
      The collection contents as a list
    Raises:
      ErrorEmptyCollection: if the collection has no results after
      self.RESULTS_SLA_SECONDS
    """
    coll = flow.GRRFlow.ResultCollectionForFID(flow_urn, token=self.token)
    coll_list = list(coll)
    if not coll_list:
      for _ in range(self.RESULTS_SLA_SECONDS):
        time.sleep(1)
        coll_list = list(coll)
        if coll_list:
          return coll_list
      raise ErrorEmptyCollection("No values in %s after SLA: %s seconds" %
                                 (flow_urn, self.RESULTS_SLA_SECONDS))
    return coll_list

  def OpenFDWithRetry(self, file_urn, token):
    """Try to open a aff4 path, retry if it is AFF4Volume."""
    fd = aff4.FACTORY.Open(file_urn, mode="r", token=token)

    # All types are instances of AFF4Volume so we can't use isinstance.
    if fd.__class__ is aff4.AFF4Volume:
      for _ in range(self.RESULTS_SLA_SECONDS):
        time.sleep(1)
        fd = aff4.FACTORY.Open(file_urn, mode="r", token=token)
        if fd.__class__ is not aff4.AFF4Volume:
          return fd
      self.fail(("No results were written to the data store. Maybe the GRR "
                 "client is not running with root privileges?"))
    return fd

  def GetURNFromGlobPathWithRetry(self, path):
    pos = path.find("*")
    if pos > 0:
      base_urn = self.client_id.Add(path[:pos])
      for _ in range(self.RESULTS_SLA_SECONDS):
        for file_urn in RecursiveListChildren(
            prefix=base_urn, token=self.token):
          if re.search(path + "$", str(file_urn)):
            self.delete_urns.add(file_urn)
            return file_urn
        time.sleep(1)
      self.fail(("Output file %s not found. Maybe the GRR client "
                 "is not running with root privileges?" % path))
    else:
      self.delete_urns.add(self.client_id.Add(path))
      return self.client_id.Add(path)


class AutomatedTest(ClientTestBase):
  """All tests that are safe to run in prod should inherit from this class."""
  __metaclass__ = registry.MetaclassRegistry

  # Prevents this from automatically registering.
  __abstract = True  # pylint: disable=g-bad-name


class TestVFSPathExists(AutomatedTest):
  """Test that checks expected VFS files were created."""
  result_type = aff4_grr.VFSFile

  def CheckFlow(self):
    """Verify VFS paths were created."""
    urn = self.GetURNFromGlobPathWithRetry(self.test_output_path)
    fd = self.OpenFDWithRetry(urn, token=self.token)
    self.assertEqual(type(fd), self.result_type)


class VFSPathContentExists(AutomatedTest):
  test_output_path = None

  def CheckFlow(self):
    urn = self.GetURNFromGlobPathWithRetry(self.test_output_path)
    fd = self.OpenFDWithRetry(urn, token=self.token)
    return self.CheckFile(fd)

  def CheckFile(self, fd):
    data = fd.Read(10)
    # Some value was read from the sysctl.
    self.assertTrue(data)


class VFSPathContentIsELF(VFSPathContentExists):

  def CheckFile(self, fd):
    self.CheckELFMagic(fd)


class VFSPathContentIsMachO(VFSPathContentExists):

  def CheckFile(self, fd):
    self.CheckMacMagic(fd)


class VFSPathContentIsPE(VFSPathContentExists):

  def CheckFile(self, fd):
    self.CheckPEMagic(fd)


class LocalWorkerTest(ClientTestBase):

  SKIP_MESSAGE = ("This test uses a flow that is debug only. Use a "
                  "local worker to run this test.")

  def runTest(self):
    if not self.local_worker:
      print self.SKIP_MESSAGE
      return self.skipTest(self.SKIP_MESSAGE)
    super(LocalWorkerTest, self).runTest()


class LocalClientTest(ClientTestBase):

  SKIP_MESSAGE = ("This test needs to run with a local client and be invoked"
                  " with local_client=True.")

  def runTest(self):
    if not self.local_client:
      print self.SKIP_MESSAGE
      return self.skipTest(self.SKIP_MESSAGE)
    super(LocalClientTest, self).runTest()


def GetClientTestTargets(client_ids=None,
                         hostnames=None,
                         token=None,
                         checkin_duration_threshold="20m"):
  """Get client urns for end-to-end tests.

  Args:
    client_ids: list of client id URN strings or rdf_client.ClientURNs
    hostnames: list of hostnames to search for
    token: access token
    checkin_duration_threshold: clients that haven't checked in for this long
                                will be excluded
  Returns:
    client_id_set: set of rdf_client.ClientURNs available for end-to-end tests.
  """

  if client_ids:
    client_ids = set(client_ids)
  else:
    client_ids = set(grr_config.CONFIG.Get("Test.end_to_end_client_ids"))

  if hostnames:
    hosts = set(hostnames)
  else:
    hosts = set(grr_config.CONFIG.Get("Test.end_to_end_client_hostnames"))

  if hosts:
    client_id_dict = client_index.GetClientURNsForHostnames(hosts, token=token)
    for client_list in client_id_dict.values():
      client_ids.update(client_list)

  client_id_set = set([rdf_client.ClientURN(x) for x in client_ids])
  duration_threshold = rdfvalue.Duration(checkin_duration_threshold)
  for client in aff4.FACTORY.MultiOpen(client_id_set, token=token):
    # Only test against client IDs that have checked in recently.  Test machines
    # tend to have lots of old client IDs hanging around that will cause lots of
    # waiting for timeouts in the tests.
    if (rdfvalue.RDFDatetime.Now() - client.Get(client.Schema.LAST) >
        duration_threshold):
      client_id_set.remove(client.urn)

  return client_id_set
