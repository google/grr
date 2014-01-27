#!/usr/bin/env python
"""Find certain types of files, compute hashes, and fetch unknown ones."""



import stat

from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.proto import flows_pb2


class FetchFilesArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.FetchFilesArgs


class FetchFiles(flow.GRRFlow):
  """This flow globs for files, computes their hashes, and fetches 'new' files.

  The result from this flow is a population of aff4 objects under
  aff4:/filestore/hash/(generic|pecoff)/<hashname>/<hashvalue>.
  There may also be a symlink from the original file to the retrieved
  content.
  """
  friendly_name = "Fetch Files"
  category = "/Filesystem/"
  args_type = FetchFilesArgs
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  @classmethod
  def GetDefaultArgs(cls, token=None):
    _ = token
    return cls.args_type(paths=[r"c:\windows\system32\notepad.*"])

  @flow.StateHandler(next_state=["ProcessGlob", "ProcessFind"])
  def Start(self):
    """Issue the find request."""
    self.state.Register("files_to_fetch", [])
    self.state.Register("files_found", 0)

    if self.args.findspec:
      self.CallFlow("FindFiles", next_state="ProcessFind",
                    findspec=self.args.findspec)

    if self.args.paths:
      self.CallFlow("Glob", next_state="ProcessGlob", paths=self.args.paths,
                    root_path=self.args.root_path,
                    pathtype=self.args.pathtype)

  @flow.StateHandler(next_state=["ProcessGlob", "Done"])
  def ProcessFind(self, responses):
    """Iterate through glob responses, and hash each hit."""
    if not responses.success:
      # Find failing is fatal here.
      return self.Error("Failed Find: %s", responses.status)

    self.ProcessResponses(responses)

  @flow.StateHandler(next_state=["ProcessGlob", "Done"])
  def ProcessGlob(self, responses):
    """Iterate through glob responses, and hash each hit."""
    if not responses.success:
      # Glob failing is fatal here.
      return self.Error("Failed Glob: %s", responses.status)

    self.ProcessResponses(responses)

  def ProcessResponses(self, responses):
    """Process stat responses and call fetch the files."""
    files_to_fetch = []

    for response in responses:
      # Only process regular files.
      if stat.S_ISREG(response.st_mode):
        self.state.files_found += 1

        # If the binary is too large we just ignore it.
        file_size = response.st_size
        if file_size > self.args.max_size:
          self.Log("%s too large to fetch. Size=%d",
                   response.pathspec.CollapsePath(), file_size)

        response.aff4path = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
            response.pathspec, self.client_id)
        self.SendReply(response)

        files_to_fetch.append(response.pathspec)

    if files_to_fetch:
      self.CallFlow("MultiGetFile", pathspecs=files_to_fetch,
                    use_external_stores=self.args.use_external_stores,
                    next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    if not responses.success:
      return self.Error("Failed to retrieve files: %s", responses.status)

    self.Log("Found %d files.", self.state.files_found)
