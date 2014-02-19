#!/usr/bin/env python
"""Flows to take a screenshot."""


import time

from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue


# TODO(user): This needs a test...
class TakeScreenshot(flow.GRRFlow):
  """Take a screenshot from a running system."""

  category = "/Misc/"
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  @flow.StateHandler(next_state=["RetrieveFile"])
  def Start(self):
    """Start processing."""
    fd = aff4.FACTORY.Open(self.client_id, token=self.token)
    system = fd.Get(fd.Schema.SYSTEM)
    if system != "Darwin":
      raise flow.FlowError("Only OSX is supported for screen capture.")

    self.state.Register("hostname", fd.Get(fd.Schema.HOSTNAME))
    self.state.Register("sspath", "/tmp/ss.dat")
    self.state.Register("filename", "")
    self.state.Register("new_urn", "")
    # TODO(user): Add support for non-constrained parameters so file can be
    # random/hidden.
    cmd = rdfvalue.ExecuteRequest(cmd="/usr/sbin/screencapture",
                                  args=["-x", "-t", "jpg", self.state.sspath],
                                  time_limit=15)
    self.CallClient("ExecuteCommand", cmd, next_state="RetrieveFile")

  @flow.StateHandler(next_state=["ProcessFile"])
  def RetrieveFile(self, responses):
    """Retrieve the file if we successfully captured."""

    if not responses.success or responses.First().exit_status != 0:
      raise flow.FlowError("Capture failed to run." % responses.status)

    pathspec = rdfvalue.PathSpec(pathtype=rdfvalue.PathSpec.PathType.OS,
                                 path=self.state.sspath)
    self.CallFlow("GetFile", next_state="ProcessFile",
                  pathspec=pathspec)

  @flow.StateHandler(next_state=["FinishedRemove"])
  def ProcessFile(self, responses):
    """Process the file we retrieved."""
    if not responses.success:
      raise flow.FlowError("Failed to retrieve captured file. This may be due"
                           "to the screen being off.")

    ss_file = responses.First()
    ss_urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(ss_file.pathspec,
                                                        self.client_id)
    ss_fd = aff4.FACTORY.Open(ss_urn, aff4_type="HashImage")
    content = ss_fd.Read(10000000)

    curr_time = time.asctime(time.gmtime())
    self.state.filename = "%s.screencap.%s" % (self.state.hostname, curr_time)
    self.state.new_urn = self.client_id.Add("analysis").Add(
        "screencaps").Add(self.state.filename)
    fd = aff4.FACTORY.Create(self.state.new_urn, "VFSFile", token=self.token)
    fd.Write(content)
    fd.Close()

    cmd = rdfvalue.ExecuteRequest(cmd="/bin/rm",
                                  args=["-f", self.state.sspath],
                                  time_limit=15)
    self.CallClient("ExecuteCommand", cmd, next_state="FinishedRemove")

  @flow.StateHandler()
  def FinishedRemove(self, responses):
    """Check the status of the rm."""
    if not responses.success:
      self.Log("Failed to remove captured file")

  @flow.StateHandler()
  def End(self):
    self.Notify("ViewObject", self.state.new_urn,
                "Got screencap %s" % self.state.filename)
