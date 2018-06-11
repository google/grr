#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.
"""Find files on the client."""
import stat

from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import objects as rdf_objects
from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server import flow
from grr.server.grr_response_server import server_stubs
from grr.server.grr_response_server.aff4_objects import aff4_grr
from grr.server.grr_response_server.aff4_objects import standard


class FindFilesArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FindFilesArgs
  rdf_deps = [
      rdf_client.FindSpec,
  ]

  def Validate(self):
    """Ensure that the request is sane."""
    self.findspec.Validate()


class FindFiles(flow.GRRFlow):
  r"""Find files on the client.

    The logic is:
    - Find files under "Path"
    - Filter for files with os.path.basename matching "Path Regular Expression"
    - Filter for files with sizes between min and max limits
    - Filter for files that contain "Data Regular Expression" in the first 1MB
        of file data
    - Return a StatEntry rdfvalue for each of the results

    Path and data regexes, and file size limits are optional. Don"t encode path
    information in the regex.  See correct usage below.

    Example:

    Path="/usr/local"
    Path Regular Expression="admin"

    Match: "/usr/local/bin/admin"      (file)
    Match: "/usr/local/admin"          (directory)
    No Match: "/usr/admin/local/blah"

    The result from this flow is a list of StatEntry objects, one for
    each file matching the criteria. Matching files will not be
    downloaded by this flow, only the metadata of the file is fetched.

    Note: This flow is inefficient for collecting a large number of files.

  Returns to parent flow:
    rdf_client.StatEntry objects for each found file.
  """

  category = "/Filesystem/"
  args_type = FindFilesArgs
  friendly_name = "Find Files"

  @flow.StateHandler()
  def Start(self, unused_response):
    """Issue the find request to the client."""
    self.state.received_count = 0

    # Build up the request protobuf.
    self.args.findspec.iterator.number = self.args.iteration_count

    # Convert the filename glob to a regular expression.
    if self.args.findspec.path_glob:
      self.args.findspec.path_regex = self.args.findspec.path_glob.AsRegEx()

    # Call the client with it
    self.CallClient(
        server_stubs.Find, self.args.findspec, next_state="IterateFind")

  @flow.StateHandler()
  def IterateFind(self, responses):
    """Iterate in this state until no more results are available."""
    if not responses.success:
      raise IOError(responses.status)

    with data_store.DB.GetMutationPool() as pool:
      for response in responses:
        # Create the file in the VFS
        vfs_urn = response.hit.pathspec.AFF4Path(self.client_id)

        if stat.S_ISDIR(response.hit.st_mode):
          fd = aff4.FACTORY.Create(
              vfs_urn,
              standard.VFSDirectory,
              mutation_pool=pool,
              token=self.token)
        else:
          fd = aff4.FACTORY.Create(
              vfs_urn, aff4_grr.VFSFile, mutation_pool=pool, token=self.token)

        with fd:
          stat_response = fd.Schema.STAT(response.hit)
          fd.Set(stat_response)
          fd.Set(fd.Schema.PATHSPEC(response.hit.pathspec))

        if data_store.RelationalDBWriteEnabled():
          client_id = self.client_id.Basename()
          path_info = rdf_objects.PathInfo.FromStatEntry(response.hit)
          data_store.REL_DB.WritePathInfos(client_id, [path_info])

        # Send the stat to the parent flow.
        self.SendReply(stat_response)

    self.state.received_count += len(responses)

    # Exit if we hit the max result count we wanted or we're finished. Note that
    # we may exceed the max_results if the iteration yielded too many results,
    # we simply will not return to the client for another iteration.
    if (self.state.received_count < self.args.max_results and
        responses.iterator.state != responses.iterator.State.FINISHED):

      self.args.findspec.iterator = responses.iterator

      # If we are close to max_results reduce the iterator.
      self.args.findspec.iterator.number = min(
          self.args.findspec.iterator.number,
          self.args.max_results - self.state.received_count)

      self.CallClient(
          server_stubs.Find, self.args.findspec, next_state="IterateFind")
      self.Log("%d files processed.", self.state.received_count)
