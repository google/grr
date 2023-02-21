#!/usr/bin/env python
"""Find files on the client."""

from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server import server_stubs
from grr_response_server.rdfvalues import objects as rdf_objects


class FindFilesArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FindFilesArgs
  rdf_deps = [
      rdf_client_fs.FindSpec,
  ]

  def Validate(self):
    """Ensure that the request is sane."""
    self.findspec.Validate()


class FindFiles(flow_base.FlowBase):
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

  Returns to parent flow:
    rdf_client_fs.StatEntry objects for each found file.
  """

  category = "/Filesystem/"
  args_type = FindFilesArgs
  friendly_name = "Find Files"

  MAX_FILES_TO_CHECK = 10000000

  def Start(self):
    """Issue the find request to the client."""

    # In newer clients, this action is not an iterator anymore so this field is
    # unused. We set it anyways for legacy clients.
    # TODO(amoser): Remove this no later than April, 2022.
    self.args.findspec.iterator.number = self.MAX_FILES_TO_CHECK

    # Convert the filename glob to a regular expression.
    if self.args.findspec.path_glob:
      self.args.findspec.path_regex = self.args.findspec.path_glob.AsRegEx()

    # Call the client with it
    self.CallClient(
        server_stubs.Find,
        self.args.findspec,
        next_state=self.StoreResults.__name__)

  def StoreResults(self, responses):
    """Stores the results returned from the client."""
    if not responses.success:
      raise IOError(responses.status)

    for response in responses:

      # TODO(amoser): FindSpec is only returned by legacy clients. Remove this
      # no later than April, 2022.
      if isinstance(response, rdf_client_fs.FindSpec):
        response = response.hit

      path_info = rdf_objects.PathInfo.FromStatEntry(response)
      data_store.REL_DB.WritePathInfos(self.client_id, [path_info])

      # Send the stat to the parent flow.
      self.SendReply(response)
