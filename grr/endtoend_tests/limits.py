#!/usr/bin/env python
"""End to end tests for client resource limits."""


from grr.client.client_actions import admin
from grr.client.client_actions import standard
from grr.endtoend_tests import base
from grr.lib.rdfvalues import paths as rdf_paths
from grr.server import aff4
from grr.server import flow
from grr.server.flows.general import transfer


class NetworkLimitTestFlow(flow.GRRFlow):
  """This flow is used to test the network limit for fastgetfile.

  There isn't any simple way to delete the blobs and blob cache held by the
  stubbyserver between runs.  So we create a unique file each time using
  /dev/urandom.
  """

  @flow.StateHandler()
  def Start(self):
    urandom = rdf_paths.PathSpec(
        path="/dev/urandom",
        file_size_override=2 * 1024 * 1024,
        pathtype=rdf_paths.PathSpec.PathType.OS)
    self.CallClient(
        standard.CopyPathToFile,
        offset=0,
        length=2 * 1024 * 1024,  # 4 default sized blobs
        src_path=urandom,
        dest_dir="",
        gzip_output=False,
        lifetime=600,
        next_state=transfer.MultiGetFile.__name__)

  @flow.StateHandler()
  def MultiGetFile(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)
    self.state.dest_path = responses.First().dest_path
    self.CallFlow(
        transfer.MultiGetFile.__name__,
        pathspecs=[self.state.dest_path],
        next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)


class CPULimitTestFlow(flow.GRRFlow):
  """This flow is used to test the cpu limit."""

  @flow.StateHandler()
  def Start(self):
    self.CallClient(admin.BusyHang, integer=5, next_state="State1")

  @flow.StateHandler()
  def State1(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)
    self.CallClient(admin.BusyHang, integer=5, next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    pass


class TestCPULimit(base.AutomatedTest):
  platforms = ["Linux", "Windows", "Darwin"]
  flow = CPULimitTestFlow.__name__
  args = {"cpu_limit": 3}

  def CheckFlow(self):
    # Reopen the object to check the state.  We use OpenWithLock to avoid
    # reading old state.
    with aff4.FACTORY.OpenWithLock(
        self.session_id, token=self.token) as flow_obj:
      backtrace = flow_obj.context.backtrace

    if backtrace:
      if "BusyHang not available" in backtrace:
        print "Client does not support this test."
      else:
        self.assertTrue("CPU limit exceeded." in backtrace)
    else:
      self.fail("Flow did not raise the proper error.")


class TestNetworkFlowLimit(base.AutomatedTest):
  """Test limit on bytes transferred for a flow."""
  platforms = ["Linux", "Darwin"]
  flow = transfer.GetFile.__name__
  args = {
      "pathspec":
          rdf_paths.PathSpec(
              path="/bin/bash", pathtype=rdf_paths.PathSpec.PathType.OS),
      "network_bytes_limit":
          500 * 1024
  }

  test_output_path = "/fs/os/bin/bash"

  def CheckFlow(self):
    # Reopen the object to check the state.  We use OpenWithLock to avoid
    # reading old state.
    with aff4.FACTORY.OpenWithLock(
        self.session_id, token=self.token) as flow_obj:
      # Make sure we transferred approximately the right amount of data.
      self.assertAlmostEqual(
          flow_obj.context.network_bytes_sent, 500 * 1024, delta=30000)
      backtrace = flow_obj.context.backtrace
      self.assertIsNotNone(backtrace)
      self.assertTrue("Network bytes limit exceeded." in backtrace)


class TestMultiGetFileNetworkLimitExceeded(base.AutomatedTest):
  platforms = ["Linux", "Darwin"]
  flow = NetworkLimitTestFlow.__name__
  args = {"network_bytes_limit": 3 * 512 * 1024}

  def CheckFlow(self):
    # Reopen the object to check the state.  We use OpenWithLock to avoid
    # reading old state.
    with aff4.FACTORY.OpenWithLock(
        self.session_id, token=self.token) as flow_obj:
      backtrace = flow_obj.context.backtrace
      self.assertTrue("Network bytes limit exceeded." in backtrace)

      self.urn = self.client_id.Add(flow_obj.state.dest_path.path)

    fd = aff4.FACTORY.Open(self.urn, mode="r", token=self.token)
    self.assertEqual(type(fd), aff4.AFF4Volume)
