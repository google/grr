#!/usr/bin/env python
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

  @flow.StateHandler(next_state=["WriteHits", "End"])
  def Grep(self, responses):
    if responses.success:
      # Grep not specified - just list all hits.
      if not self.args.grep:
        msgs = [rdfvalue.BufferReference(pathspec=r.pathspec)
                for r in responses]
        self.CallStateInline(messages=msgs, next_state="WriteHits")
      else:
        # Grep specification given, ask the client to grep the files.
        for response in responses:
          # Only fetch regular files here.
          if not stat.S_ISDIR(response.st_mode):

            # Cast the BareGrepSpec to a GrepSpec type.
            request = rdfvalue.GrepSpec(target=response.pathspec,
                                        **self.args.grep.AsDict())
            self.CallClient("Grep", request=request, next_state="WriteHits",
                            request_data=dict(pathspec=response.pathspec))

  @flow.StateHandler(next_state="End")
  def WriteHits(self, responses):
    """Sends replies about the hits."""
    hits = list(responses)

    for hit in hits:
      # Old clients do not send pathspecs in the Grep response so we add them.
      if not hit.pathspec:
        hit.pathspec = responses.request_data.GetItem("pathspec")
      self.SendReply(hit)

    if self.args.also_download:
      self.CallFlow("MultiGetFile", pathspecs=[x.pathspec for x in hits],
                    next_state="End")
