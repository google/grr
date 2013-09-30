#!/usr/bin/env python
"""Find certain types of files, compute hashes, and fetch unknown ones."""



import stat

from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.proto import flows_pb2


class FetchAllFilesArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.FetchAllFilesArgs


class FetchAllFiles(flow.GRRFlow):
  """This flow finds files, computes their hashes, and fetches 'new' files.

  The result from this flow is a population of aff4 objects under
  aff4:/filestore/hash/(generic|pecoff)/<hashname>/<hashvalue>.
  There may also be a symlink from the original file to the retrieved
  content.
  """

  category = "/Filesystem/"
  args_type = FetchAllFilesArgs

  _MAX_FETCHABLE_SIZE = 100 * 1024 * 1024

  @flow.StateHandler(next_state="IterateFind")
  def Start(self):
    """Issue the find request."""
    self.state.Register("files_found", 0)

    self.args.findspec.iterator.number = self.args.iteration_count
    self.CallClient("Find", self.args.findspec, next_state="IterateFind")

  @flow.StateHandler(next_state=["IterateFind", "End"])
  def IterateFind(self, responses):
    """Iterate through find responses, and hash each hit."""
    if not responses.success:
      # We just stop the find iteration, the flow goes on.
      self.Log("Failed Find: %s", responses.status)
      return

    files_to_fetch = []
    for response in responses:
      # Only process regular files.
      if stat.S_ISREG(response.hit.st_mode):
        self.state.files_found += 1

        # If the binary is too large we just ignore it.
        file_size = response.hit.st_size
        if file_size > self._MAX_FETCHABLE_SIZE:
          self.Log("%s too large to fetch. Size=%d",
                   response.pathspec.CollapsePath(), file_size)

        response.hit.aff4path = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
            response.hit.pathspec, self.client_id)
        self.SendReply(response.hit)

        files_to_fetch.append(response.hit)

    # Hold onto the iterator in the state - we might need to re-iterate this
    # later.
    self.args.findspec.iterator = responses.iterator

    if files_to_fetch:
      self.CallFlow("MultiGetFile", files_stat_entries=files_to_fetch,
                    use_external_stores=self.args.use_external_stores,
                    next_state="End")
    else:
      if responses.iterator.state != rdfvalue.Iterator.State.FINISHED:
        self.CallClient("Find", self.args.findspec, next_state="IterateFind")

  @flow.StateHandler(next_state=["IterateFind"])
  def End(self):
   # Only find more files if we have few files in flight.
    if (self.args.findspec.iterator.state != rdfvalue.Iterator.State.FINISHED
        and len(self.state.store) < self.MAX_FILES_IN_FLIGHT):
      self.CallClient("Find", self.args.findspec, next_state="IterateFind")
    else:
      # Done!
      self.Log("Found %d files.", self.state.files_found)


class FetchAllFilesGlobArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.FetchAllFilesGlobArgs


class FetchAllFilesGlob(flow.GRRFlow):
  """This flow globs for files, computes their hashes, and fetches 'new' files.

  The result from this flow is a population of aff4 objects under
  aff4:/filestore/hash/(generic|pecoff)/<hashname>/<hashvalue>.
  There may also be a symlink from the original file to the retrieved
  content.
  """

  category = "/Filesystem/"
  args_type = FetchAllFilesGlobArgs

  _MAX_FETCHABLE_SIZE = 100 * 1024 * 1024

  @flow.StateHandler(next_state="ProcessGlob")
  def Start(self):
    """Issue the find request."""
    self.state.Register("files_found", 0)

    self.CallFlow("Glob", next_state="ProcessGlob", paths=self.args.paths,
                  pathtype=self.args.pathtype)

  @flow.StateHandler(next_state=["ProcessGlob", "End"])
  def ProcessGlob(self, responses):
    """Iterate through glob responses, and hash each hit."""
    if not responses.success:
      # We just stop the find iteration, the flow goes on.
      self.Log("Failed Glob: %s", responses.status)
      return

    files_to_fetch = []
    for response in responses:
      # Only process regular files.
      if stat.S_ISREG(response.st_mode):
        self.state.files_found += 1

        # If the binary is too large we just ignore it.
        file_size = response.st_size
        if file_size > self._MAX_FETCHABLE_SIZE:
          self.Log("%s too large to fetch. Size=%d",
                   response.pathspec.CollapsePath(), file_size)

        response.aff4path = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
            response.pathspec, self.client_id)
        self.SendReply(response)

        files_to_fetch.append(response)

    if files_to_fetch:
      self.CallFlow("MultiGetFile", files_stat_entries=files_to_fetch,
                    use_external_stores=self.args.use_external_stores,
                    next_state="End")

  @flow.StateHandler()
  def End(self):
    self.Log("Found %d files.", self.state.files_found)
