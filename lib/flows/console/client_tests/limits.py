#!/usr/bin/env python
"""End to end tests for client resource limits."""


from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib.flows.console.client_tests import base


class NetworkLimitTestFlow(flow.GRRFlow):
  """This flow is used to test the network limit for fastgetfile.

  There isn't any simple way to delete the blobs and blob cache held by the
  stubbyserver between runs.  So we create a unique file each time using
  /dev/urandom.
  """

  @flow.StateHandler(next_state="MultiGetFile")
  def Start(self):
    urandom = rdfvalue.PathSpec(path="/dev/urandom",
                                pathtype=rdfvalue.PathSpec.PathType.OS)
    self.CallClient("CopyPathToFile",
                    offset=0,
                    length=2 * 1024 * 1024,  # 4 default sized blobs
                    src_path=urandom,
                    dest_dir="",
                    gzip_output=False,
                    lifetime=10,
                    next_state="MultiGetFile")

  @flow.StateHandler(next_state="Done")
  def MultiGetFile(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)
    self.state.Register("dest_path", responses.First().dest_path)
    self.CallFlow("MultiGetFile", pathspecs=[self.state.dest_path],
                  next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)


class CPULimitTestFlow(flow.GRRFlow):
  """This flow is used to test the cpu limit."""

  @flow.StateHandler(next_state="State1")
  def Start(self):
    self.CallClient("BusyHang", integer=5, next_state="State1")

  @flow.StateHandler(next_state="Done")
  def State1(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)
    self.CallClient("BusyHang", integer=5, next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    pass


class TestCPULimit(base.LocalClientTest):
  platforms = ["linux", "windows", "darwin"]

  flow = "CPULimitTestFlow"

  cpu_limit = 7

  def CheckFlow(self):
    # Reopen the object to update the state.
    flow_obj = aff4.FACTORY.Open(self.session_id, token=self.token)
    backtrace = flow_obj.state.context.get("backtrace", "")
    if backtrace:
      if "BusyHang not available" in backtrace:
        print "Client does not support this test."
      else:
        self.assertTrue("CPU limit exceeded." in backtrace)
    else:
      self.fail("Flow did not raise the proper error.")


class TestNetworkFlowLimit(base.ClientTestBase):
  """Test limit on bytes transferred for a flow."""
  platforms = ["linux", "darwin"]
  flow = "GetFile"
  network_bytes_limit = 500 * 1024
  args = {"pathspec": rdfvalue.PathSpec(path="/bin/bash",
                                        pathtype=rdfvalue.PathSpec.PathType.OS)}

  output_path = "/fs/os/bin/bash"

  def setUp(self):
    self.urn = self.client_id.Add(self.output_path)
    self.DeleteUrn(self.urn)
    fd = aff4.FACTORY.Open(self.urn, mode="r", token=self.token)
    self.assertEqual(type(fd), aff4.AFF4Volume)

  def CheckFlow(self):
    # Reopen the object to update the state.
    flow_obj = aff4.FACTORY.Open(self.session_id, token=self.token)

    # Make sure we transferred approximately the right amount of data.
    self.assertAlmostEqual(flow_obj.state.context.network_bytes_sent,
                           self.network_bytes_limit, delta=30000)
    backtrace = flow_obj.state.context.get("backtrace", "")
    self.assertTrue("Network bytes limit exceeded." in backtrace)


class TestMultiGetFileNetworkLimitExceeded(base.LocalClientTest):
  platforms = ["linux", "darwin"]
  flow = "NetworkLimitTestFlow"
  args = {}
  network_bytes_limit = 3 * 512 * 1024

  def CheckFlow(self):
    # Reopen the object to update the state.
    flow_obj = aff4.FACTORY.Open(self.session_id, token=self.token)
    backtrace = flow_obj.state.context.get("backtrace", "")
    self.assertTrue("Network bytes limit exceeded." in backtrace)

    self.output_path = flow_obj.state.dest_path.path
    self.urn = self.client_id.Add(self.output_path)

    fd = aff4.FACTORY.Open(self.urn, mode="r", token=self.token)
    self.assertEqual(type(fd), aff4.AFF4Volume)

