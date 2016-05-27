#!/usr/bin/env python
"""These are processes memory dump related flows."""


from grr.lib import flow

from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import flows_pb2


class DumpProcessMemoryArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.DumpProcessMemoryArgs


class DumpProcessMemory(flow.GRRFlow):
  """Flow to dump memory from processes using C++ client.

  Note that this flow currently requires the experimental C++ client, which
  currently only works on Linux. The intention is to implement similar
  functionality in the regular python client and make it work across OS X and
  Windows as well.
  """

  category = "/Memory/"
  behaviours = flow.GRRFlow.behaviours + "ADVANCED"
  args_type = DumpProcessMemoryArgs

  @flow.StateHandler(next_state=["DownloadImage"])
  def Start(self):
    """Start processing."""
    for pid in self.args.pids:
      self.CallClient("DumpProcessMemory",
                      rdf_client.DumpProcessMemoryRequest(
                          pid=pid, pause=self.args.pause),
                      next_state="DownloadImage")

  @flow.StateHandler(next_state=["DeleteFile"])
  def DownloadImage(self, responses):
    if not responses.success:
      self.Error("Could not dump memory image: %s" % responses.status)
    self.CallFlow("MultiGetFile",
                  pathspecs=[responses.First()],
                  next_state="DeleteFile")

  @flow.StateHandler(next_state=["End"])
  def DeleteFile(self, responses):
    self.CallClient("DeleteGRRTempFiles",
                    responses.First().pathspec,
                    next_state="End")
