#!/usr/bin/env python
"""Base module for end to end tests that run flows on clients."""



import traceback
import unittest


from grr.lib import aff4
from grr.lib import client_index
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import flow_utils
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib.aff4_objects import aff4_grr
from grr.lib.flows.console import debugging
from grr.lib.rdfvalues import client as rdf_client


class Error(Exception):
  """Test base error."""


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

  # Only run on clients after this version
  client_min_version = None

  __metaclass__ = registry.MetaclassRegistry

  def __call__(self):
    """Stub out __call__ to avoid django calling it during rendering.

    See
    https://docs.djangoproject.com/en/dev/ref/templates/api/#variables-and-lookups

    Since __call__ is used by the Python testing framework to run tests, the
    effect of __call__ is to run the test inside the adminui, resulting in very
    slow rendering and extra test runs. We put the real __call__ back when tests
    are run from tools/end_to_end_tests.py, but we don't need it here since we
    effectively have our own test runner.
    """
    pass

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
      self.session_id = flow_utils.StartFlowAndWait(self.client_id,
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
        # We open each urn to generate InstantiationError on failures, multiopen
        # ignores these errors.  This isn't too slow since it's almost always
        # just one path anyway.
        aff4.FACTORY.Open(urn, aff4_type=aff4.AFF4Volume, token=self.token)
    except aff4.InstantiationError:
      raise TestStateUncleanError("Path wasn't deleted: %s" %
                                  traceback.format_exc())

  def DeleteUrn(self, urn):
    """Deletes an object from the db and the index, and flushes the caches."""
    data_store.DB.DeleteSubject(urn, token=self.token)
    aff4.FACTORY._DeleteChildFromIndex(urn, token=self.token)
    aff4.FACTORY.Flush()

  def GetGRRBinaryName(self, run_interrogate=True):
    client = aff4.FACTORY.Open(self.client_id, mode="r", token=self.token)
    self.assertIsInstance(client, aff4_grr.VFSGRRClient)
    config = client.Get(aff4_grr.VFSGRRClient.SchemaCls.GRR_CONFIGURATION)

    if config is None:
      # Try running Interrogate once.
      if run_interrogate:
        flow_utils.StartFlowAndWait(self.client_id,
                                    flow_name="Interrogate",
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
    self.assertTrue(data[:4] in magic_values)


class AutomatedTest(ClientTestBase):
  """All tests that are safe to run in prod should inherit from this class."""
  __metaclass__ = registry.MetaclassRegistry

  # Prevents this from automatically registering.
  __abstract = True  # pylint: disable=g-bad-name


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
    client_ids = set(config_lib.CONFIG.Get("Test.end_to_end_client_ids"))

  if hostnames:
    hosts = set(hostnames)
  else:
    hosts = set(config_lib.CONFIG.Get("Test.end_to_end_client_hostnames"))

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
    if (rdfvalue.RDFDatetime().Now() - client.Get(client.Schema.LAST) >
        duration_threshold):
      client_id_set.remove(client.urn)

  return client_id_set
