#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""A simple grep flow."""


import stat

from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.proto import flows_pb2


class SearchFileContentArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.SearchFileContentArgs


class SearchFileContent(flow.GRRFlow):
  """A flow that runs a glob first and then issues a grep on the results.

  This flow can be used to search for files by filename. Simply specify a glob
  expression for the filename:

  %%KnowledgeBase.environ_windir%%/notepad.exe

  By also specifying a grep specification, the file contents can also be
  searched.
  """
  category = "/Filesystem/"
  friendly_name = "Search In Files"
  args_type = rdfvalue.SearchFileContentArgs
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  @classmethod
  def GetDefaultArgs(cls, token=None):
    _ = token
    return cls.args_type(paths=[r"%%Users.homedir%%/.bash_history"])

  @flow.StateHandler(next_state=["Grep"])
  def Start(self):
    """Run the glob first."""
    if self.runner.output:
      self.runner.output = aff4.FACTORY.Create(
          self.runner.output.urn, "GrepResultsCollection", mode="rw",
          token=self.token)

      self.runner.output.Set(self.runner.output.Schema.DESCRIPTION(
          "SearchFiles {0}".format(self.__class__.__name__)))

    self.CallFlow("Glob", next_state="Grep",
                  paths=self.args.paths, pathtype=self.args.pathtype)

  @flow.StateHandler(next_state=["WriteHits"])
  def Grep(self, responses):
    if responses.success:
      for response in responses:
        # Only fetch regular files here.
        if not stat.S_ISDIR(response.st_mode):

          # Cast the BareGrepSpec to a GrepSpec type.
          request = rdfvalue.GrepSpec(target=response.pathspec,
                                      **self.args.grep.AsDict())

          # Grep not specified - just list all hits.
          if not self.args.grep:
            for response in responses:
              hit = rdfvalue.BufferReference(pathspec=response.pathspec)
              self.SendReply(hit)

          else:
            # Grep specification given, ask the client to grep the files.
            self.CallClient("Grep", request=request, next_state="WriteHits",
                            request_data=dict(stat=response))

  @flow.StateHandler(next_state="End")
  def WriteHits(self, responses):
    for hit in responses:
      self.SendReply(hit)

    if self.args.also_download:
      self.CallClient("MultiGetFile", pathspecs=[x.pathspec for x in responses],
                      next_state="End")
