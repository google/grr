#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""A simple grep flow."""



import time

from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils


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

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.GrepspecType(
          description="The file which will be grepped.",
          name="request"),

      type_info.String(
          description="The output collection.",
          name="output",
          default="analysis/grep/{u}-{t}"),
      )

  @flow.StateHandler(next_state=["StoreResults"])
  def Start(self):
    """Start Grep flow."""
    self.state.request.xor_in_key = self.XOR_IN_KEY
    self.state.request.xor_out_key = self.XOR_OUT_KEY

    # For literal matches we xor the search term. In the event we search the
    # memory this stops us matching the GRR client itself.
    if self.state.request.literal:
      self.state.request.literal = utils.Xor(self.state.request.literal,
                                             self.XOR_IN_KEY)

    self.state.Register("output_collection", None)
    self.CallClient("Grep", self.state.request, next_state="StoreResults")

  @flow.StateHandler()
  def StoreResults(self, responses):
    if responses.success:
      output = self.state.output.format(t=time.time(),
                                        u=self.state.context.user)
      out_urn = self.client_id.Add(output)

      fd = aff4.FACTORY.Create(out_urn, "GrepResultsCollection",
                               mode="w", token=self.token)

      self.state.output_collection = fd

      if self.state.request.HasField("literal"):
        self.state.request.literal = utils.Xor(self.state.request.literal,
                                               self.XOR_IN_KEY)
      fd.Set(fd.Schema.DESCRIPTION("Grep by %s: %s" % (
          self.state.context.user, str(self.state.request))))

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

  flow_typeinfo = (Grep.flow_typeinfo)

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
