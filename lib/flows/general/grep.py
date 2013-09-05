#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""A simple grep flow."""



import time

from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils
from grr.proto import flows_pb2


class GrepArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.GrepArgs

  def Validate(self):
    self.request.Validate()


class Grep(flow.GRRFlow):
  """Greps a file on the client for a pattern or a regex.

  This flow operates on files only, see GlobAndGrep if you want to grep a
  directory.

  Returns to parent flow:
      RDFValueArray of BufferReference objects.
  """

  category = "/Filesystem/"

  XOR_IN_KEY = 37
  XOR_OUT_KEY = 57

  args_type = GrepArgs

  @flow.StateHandler(next_state=["StoreResults"])
  def Start(self):
    """Start Grep flow."""
    self.state.args.request.xor_in_key = self.XOR_IN_KEY
    self.state.args.request.xor_out_key = self.XOR_OUT_KEY

    # For literal matches we xor the search term. In the event we search the
    # memory this stops us matching the GRR client itself.
    if self.state.args.request.literal:
      self.state.args.request.literal = utils.Xor(
          self.state.args.request.literal, self.XOR_IN_KEY)

    self.state.Register("output_collection", None)
    self.CallClient("Grep", self.state.args.request, next_state="StoreResults")

  @flow.StateHandler()
  def StoreResults(self, responses):
    if responses.success:
      output = self.state.args.output.format(t=time.time(),
                                             u=self.state.context.user)
      out_urn = self.client_id.Add(output)

      fd = aff4.FACTORY.Create(out_urn, "GrepResultsCollection",
                               mode="w", token=self.token)

      self.state.output_collection = fd

      fd.Set(fd.Schema.DESCRIPTION("Grep by %s: %s" % (
          self.state.context.user, str(self.state.args.request))))

      for response in responses:
        response.data = utils.Xor(response.data,
                                  self.XOR_OUT_KEY)
        response.length = len(response.data)
        fd.Add(response)
        self.SendReply(response)

    else:
      self.Notify("FlowStatus", self.session_id,
                  "Error grepping file: %s." % responses.status)

  @flow.StateHandler()
  def End(self):
    if self.state.output_collection is not None:
      self.state.output_collection.Flush()
      self.Notify("ViewObject", self.state.output_collection.urn,
                  u"Grep completed. %d hits" %
                  len(self.state.output_collection))


class GrepAndDownload(flow.GRRFlow):
  """Downloads file if a signature is found.

  This flow greps a file on the client for a literal or regex and, if the
  pattern is found, downloads the file.
  """

  category = "/Filesystem/"

  args_type = GrepArgs

  @flow.StateHandler(next_state=["DownloadFile"])
  def Start(self):
    self.state.request.mode = rdfvalue.GrepSpec.Mode.FIRST_HIT
    self.CallFlow("Grep", request=self.state.request, next_state="DownloadFile")

  @flow.StateHandler(next_state=["StoreDownload", "End"])
  def DownloadFile(self, responses):
    if responses:
      self.Log("Grep completed with %s hits, downloading file.", len(responses))
      self.CallFlow("FastGetFile", pathspec=responses.First().pathspec,
                    next_state="StoreDownload")
    else:
      self.Log("Grep did not yield any results.")

  @flow.StateHandler()
  def StoreDownload(self, responses):
    if not responses.success:
      raise flow.FlowError("Error while downloading file: %s" %
                           responses.status.error_message)
    else:
      stat = responses.First()
      self.Notify("ViewObject", stat.aff4path,
                  "File downloaded successfully")
