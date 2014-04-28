#!/usr/bin/env python
"""Base module for end to end tests that run flows on clients."""



import unittest


import logging
from grr.lib import access_control
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow_utils
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import test_lib
from grr.lib.flows.console import debugging


def TestFlows(client_id, platform, testname=None, local_worker=False):
  """Test a bunch of flows."""

  if platform not in ["windows", "linux", "darwin"]:
    raise RuntimeError("Requested operating system not supported.")

  # This token is not really used since there is no approval for the
  # tested client - these tests are designed for raw access - but we send it
  # anyways to have an access reason.
  token = access_control.ACLToken(username="test", reason="client testing")

  client_id = rdfvalue.RDFURN(client_id)
  RunTests(client_id, platform=platform, testname=testname,
           token=token, local_worker=local_worker)


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


class ClientTestBase(test_lib.GRRBaseTest):
  """This is the base class for all client tests."""
  platforms = []
  flow = None
  args = {}
  cpu_limit = None
  network_bytes_limit = None

  __metaclass__ = registry.MetaclassRegistry

  def __init__(self, client_id=None, platform=None, local_worker=False,
               token=None, timeout=None, local_client=True):
    # If we get passed a string, turn it into a urn.
    self.client_id = rdfvalue.RDFURN(client_id)
    self.platform = platform
    self.token = token
    self.local_worker = local_worker
    self.local_client = local_client
    self.timeout = timeout or flow_utils.DEFAULT_TIMEOUT
    super(ClientTestBase, self).__init__(methodName="runTest")

  def setUp(self):
    # Disable setUp since the cleanup between unit tests does not make sense
    # here.
    pass

  def tearDown(self):
    # Disable tearDown since the cleanup between unit tests does not make sense
    # here.
    pass

  def runTest(self):
    if self.local_worker:
      self.session_id = debugging.StartFlowAndWorker(
          self.client_id, self.flow, cpu_limit=self.cpu_limit,
          network_bytes_limit=self.network_bytes_limit, **self.args)
    else:
      self.session_id = flow_utils.StartFlowAndWait(
          self.client_id, flow_name=self.flow,
          cpu_limit=self.cpu_limit, timeout=self.timeout,
          network_bytes_limit=self.network_bytes_limit, token=self.token,
          **self.args)

    self.CheckFlow()

  def CheckFlow(self):
    pass

  def DeleteUrn(self, urn):
    """Deletes an object from the db and the index, and flushes the caches."""
    data_store.DB.DeleteSubject(urn, token=self.token)
    aff4.FACTORY._DeleteChildFromIndex(urn, token=self.token)
    aff4.FACTORY.Flush()

  def GetGRRBinaryName(self, run_interrogate=True):
    client = aff4.FACTORY.Open(self.client_id, mode="r", token=self.token)
    self.assertIsInstance(client, aff4.VFSGRRClient)
    config = client.Get(aff4.VFSGRRClient.SchemaCls.GRR_CONFIGURATION)

    if config is None:
      # Try running Interrogate once.
      if run_interrogate:
        flow_utils.StartFlowAndWait(self.client_id,
                                    flow_name="Interrogate", token=self.token)
        return self.GetGRRBinaryName(run_interrogate=False)
      else:
        self.fail("No valid configuration found, interrogate the client before "
                  "running this test.")
    else:
      self.binary_name = config["Client.binary_name"]
      return self.binary_name


class LocalClientTest(ClientTestBase):

  def runTest(self):
    if not self.local_worker:
      print ("This test uses a flow that is debug only. Use a local worker"
             " to run this test.")
      return
    super(LocalClientTest, self).runTest()


def RunTests(client_id=None, platform=None, testname=None,
             token=None, local_worker=False):
  runner = unittest.TextTestRunner()

  for cls in ClientTestBase.classes.values():
    if testname is not None and testname != cls.__name__:
      continue

    if not aff4.issubclass(cls, ClientTestBase):
      continue

    if platform in cls.platforms:
      print "Running %s." % cls.__name__
      try:
        runner.run(cls(client_id=client_id, platform=platform,
                       token=token, local_worker=local_worker))
      except Exception:  # pylint: disable=broad-except
        logging.exception("Failed to run test %s", cls)









