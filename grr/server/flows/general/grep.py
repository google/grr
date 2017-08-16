#!/usr/bin/env python
"""A simple grep flow."""


import stat

from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import flows_pb2
from grr.server import flow
from grr.server import server_stubs
from grr.server.flows.general import filesystem
from grr.server.flows.general import transfer


class SearchFileContentArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.SearchFileContentArgs
  rdf_deps = [
      rdf_client.BareGrepSpec,
      paths.GlobExpression,
      paths.PathSpec,
  ]


class SearchFileContent(flow.GRRFlow):
  """A flow that runs a glob first and then issues a grep on the results.

  DEPRECATED.
  This flow is now deprecated in favor of FileFinder. To use FileFinder instead
  of SearchFileContent:
  Specify list of glob expressions corresponding to the files you want to
  search in. Add conditions that will be applied to found files. You can
  use "literal match" and "regex match" conditions. Set "action" to
  "Stat" if you're just interested in matches, or "Download" if you want to
  also download the matching files.
  ------------------------------------------------------------------------------

  This flow can be used to search for files by specifying a filename glob.
  e.g. this glob will search recursively under the environment directory for
  files called notepad with any extension:

  %%KnowledgeBase.environ_windir%%/**notepad.*

  The default ** recursion depth is 3 levels, and can be modified using a number
  after the ** like this:

  %%KnowledgeBase.environ_windir%%/**10notepad.*

  Optionally you can also specify File Content Search parameters to search file
  contents.
  """
  category = "/Filesystem/"
  friendly_name = "Search In Files"
  args_type = SearchFileContentArgs
  behaviours = flow.GRRFlow.behaviours + "ADVANCED"

  @classmethod
  def GetDefaultArgs(cls, token=None):
    _ = token
    return cls.args_type(paths=[r"%%Users.homedir%%/.bash_history"])

  @flow.StateHandler()
  def Start(self):
    """Run the glob first."""
    self.CallFlow(
        filesystem.Glob.__name__,
        next_state="Grep",
        root_path=self.args.root_path,
        paths=self.args.paths,
        pathtype=self.args.pathtype)

  @flow.StateHandler()
  def Grep(self, responses):
    if responses.success:
      # Grep not specified - just list all hits.
      if not self.args.grep:
        msgs = [
            rdf_client.BufferReference(pathspec=r.pathspec) for r in responses
        ]
        self.CallStateInline(messages=msgs, next_state="WriteHits")
      else:
        # Grep specification given, ask the client to grep the files.
        for response in responses:
          # Only fetch regular files here.
          if not stat.S_ISDIR(response.st_mode):

            # Cast the BareGrepSpec to a GrepSpec type.
            request = rdf_client.GrepSpec(
                target=response.pathspec, **self.args.grep.AsDict())
            self.CallClient(
                server_stubs.Grep,
                request=request,
                next_state="WriteHits",
                request_data=dict(pathspec=response.pathspec))

  @flow.StateHandler()
  def WriteHits(self, responses):
    """Sends replies about the hits."""
    hits = list(responses)

    for hit in hits:
      # Old clients do not send pathspecs in the Grep response so we add them.
      if not hit.pathspec:
        hit.pathspec = responses.request_data.GetItem("pathspec")
      self.SendReply(hit)

    if self.args.also_download:
      self.CallFlow(
          transfer.MultiGetFile.__name__,
          pathspecs=[x.pathspec for x in hits],
          next_state="End")
