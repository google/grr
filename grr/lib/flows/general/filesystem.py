#!/usr/bin/env python
"""These are filesystem related flows."""

import fnmatch
import re
import stat

from grr.lib import aff4
from grr.lib import artifact_utils
from grr.lib import flow
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import standard
# pylint: disable=unused-import
from grr.lib.flows.general import transfer
# pylint: enable=unused-import
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import flows_pb2

# This is all bits that define the type of the file in the stat mode. Equal to
# 0b1111000000000000.
stat_type_mask = (stat.S_IFREG | stat.S_IFDIR | stat.S_IFLNK | stat.S_IFBLK
                  | stat.S_IFCHR | stat.S_IFIFO | stat.S_IFSOCK)


def CreateAFF4Object(stat_response, client_id, token, sync=False):
  """This creates a File or a Directory from a stat response."""

  stat_response.aff4path = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
      stat_response.pathspec, client_id)

  if stat_response.pathspec.last.stream_name:
    # This is an ads. In that case we always need to create a file or
    # we won't be able to access the data. New clients send the correct mode
    # already but to make sure, we set this to a regular file anyways.
    # Clear all file type bits:
    stat_response.st_mode &= ~stat_type_mask
    stat_response.st_mode |= stat.S_IFREG

  if stat.S_ISDIR(stat_response.st_mode):
    ftype = standard.VFSDirectory
  else:
    ftype = aff4_grr.VFSFile

  fd = aff4.FACTORY.Create(stat_response.aff4path, ftype, mode="w", token=token)
  fd.Set(fd.Schema.STAT(stat_response))
  fd.Set(fd.Schema.PATHSPEC(stat_response.pathspec))
  fd.Close(sync=sync)


class ListDirectoryArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.ListDirectoryArgs


class ListDirectory(flow.GRRFlow):
  """List files in a directory."""

  category = "/Filesystem/"
  args_type = ListDirectoryArgs
  behaviours = flow.GRRFlow.behaviours + "ADVANCED"

  @flow.StateHandler(next_state=["List", "Stat"])
  def Start(self):
    """Issue a request to list the directory."""
    self.CallClient("StatFile",
                    pathspec=self.state.args.pathspec,
                    next_state="Stat")

    # We use data to pass the path to the callback:
    self.CallClient("ListDirectory",
                    pathspec=self.state.args.pathspec,
                    next_state="List")

  @flow.StateHandler()
  def Stat(self, responses):
    """Save stat information on the directory."""
    # Did it work?
    if not responses.success:
      self.Error("Could not stat directory: %s" % responses.status)

    else:
      # Keep the stat response for later.
      self.state.Register("stat", rdf_client.StatEntry(responses.First()))
      self.state.Register("directory_pathspec", self.state.stat.pathspec)

      # The full path of the object is the combination of the client_id and the
      # path.
      self.state.Register("urn", aff4.AFF4Object.VFSGRRClient.PathspecToURN(
          self.state.directory_pathspec, self.client_id))

  @flow.StateHandler()
  def List(self, responses):
    """Collect the directory listing and store in the datastore."""
    if not responses.success:
      raise flow.FlowError(str(responses.status))

    self.Status("Listed %s", self.state.urn)

    # The AFF4 object is opened for writing with an asyncronous close for speed.
    fd = aff4.FACTORY.Create(self.state.urn,
                             standard.VFSDirectory,
                             mode="w",
                             token=self.token)

    fd.Set(fd.Schema.PATHSPEC(self.state.directory_pathspec))
    fd.Set(fd.Schema.STAT(self.state.stat))

    fd.Close(sync=False)

    for st in responses:
      st = rdf_client.StatEntry(st)
      CreateAFF4Object(st, self.client_id, self.token, sync=False)
      self.SendReply(st)  # Send Stats to parent flows.

    aff4.FACTORY.Flush()

  @flow.StateHandler()
  def End(self):
    if self.state.urn:
      self.Notify("ViewObject", self.state.urn,
                  u"Listed {0}".format(self.state.args.pathspec))


class IteratedListDirectory(ListDirectory):
  """A Flow to retrieve a directory listing using an iterator.

  This flow is an example for how to use the iterated client actions. Normally
  you do not need to call this flow - a ListDirectory flow is enough.
  """

  category = None

  @flow.StateHandler(next_state="List")
  def Start(self):
    """Issue a request to list the directory."""
    self.state.Register("responses", [])
    self.state.Register("urn", None)

    # We use data to pass the path to the callback:
    self.state.Register("request",
                        rdf_client.ListDirRequest(
                            pathspec=self.state.args.pathspec))

    # For this example we will use a really small number to force many round
    # trips with the client. This is a performance killer.
    self.state.request.iterator.number = 50

    self.CallClient("IteratedListDirectory",
                    self.state.request,
                    next_state="List")

  @flow.StateHandler(next_state="List")
  def List(self, responses):
    """Collect the directory listing and store in the data store."""
    if not responses.success:
      raise flow.FlowError(str(responses.status))

    if responses:
      for response in responses:
        self.state.responses.append(response)

      self.state.request.iterator = responses.iterator
      self.CallClient("IteratedListDirectory",
                      self.state.request,
                      next_state="List")
    else:
      self.StoreDirectory()

  def StoreDirectory(self):
    """Store the content of the directory listing in the AFF4 object."""
    # The full path of the object is the combination of the client_id and the
    # path.
    if not self.state.responses:
      return

    directory_pathspec = self.state.responses[0].pathspec.Dirname()

    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(directory_pathspec,
                                                     self.client_id)

    # First dir we get back is the main urn.
    if not self.state.urn:
      self.state.urn = urn

    fd = aff4.FACTORY.Create(urn, standard.VFSDirectory, token=self.token)
    fd.Close(sync=False)

    for st in self.state.responses:
      st = rdf_client.StatEntry(st)
      CreateAFF4Object(st, self.client_id, self.token)
      self.SendReply(st)  # Send Stats to parent flows.

  @flow.StateHandler()
  def End(self):
    self.Notify("ViewObject", self.state.urn,
                "List of {0} completed.".format(self.state.args.pathspec))


class RecursiveListDirectoryArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.RecursiveListDirectoryArgs


class RecursiveListDirectory(flow.GRRFlow):
  """Recursively list directory on the client."""

  category = "/Filesystem/"

  args_type = RecursiveListDirectoryArgs

  @flow.StateHandler(next_state="ProcessDirectory")
  def Start(self):
    """List the initial directory."""
    # The first directory we listed.
    self.state.Register("first_directory", None)

    self.state.Register("dir_count", 0)
    self.state.Register("file_count", 0)

    self.CallClient("ListDirectory",
                    pathspec=self.state.args.pathspec,
                    next_state="ProcessDirectory")

  @flow.StateHandler(next_state="ProcessDirectory")
  def ProcessDirectory(self, responses):
    """Recursively list the directory, and add to the timeline."""
    if responses.success:
      response = responses.First()

      if response is None:
        return

      directory_pathspec = response.pathspec.Dirname()

      urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(directory_pathspec,
                                                       self.client_id)

      self.StoreDirectory(responses)

      # If the urn is too deep we quit to prevent recursion errors.
      if self.state.first_directory is None:
        self.state.first_directory = urn

      else:
        relative_name = urn.RelativeName(self.state.first_directory) or ""
        if len(relative_name.split("/")) >= self.state.args.max_depth:
          self.Log("Exceeded maximum path depth at %s.",
                   urn.RelativeName(self.state.first_directory))
          return

      for stat_response in responses:
        # Queue a list directory for each directory here, but do not follow
        # symlinks.
        if not stat_response.symlink and stat.S_ISDIR(stat_response.st_mode):
          self.CallClient("ListDirectory",
                          pathspec=stat_response.pathspec,
                          next_state="ProcessDirectory")
          self.state.dir_count += 1
          if self.state.dir_count % 100 == 0:  # Log every 100 directories
            self.Status("Reading %s. (%d nodes, %d directories done)",
                        urn.RelativeName(self.state.first_directory),
                        self.state.file_count, self.state.dir_count)

      self.state.file_count += len(responses)

  def StoreDirectory(self, responses):
    """Stores all stat responses."""
    for st in responses:
      st = rdf_client.StatEntry(st)
      CreateAFF4Object(st, self.client_id, self.token)
      self.SendReply(st)  # Send Stats to parent flows.

  @flow.StateHandler()
  def End(self):
    status_text = "Recursive Directory Listing complete %d nodes, %d dirs"
    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(self.state.args.pathspec,
                                                     self.client_id)
    self.Notify("ViewObject", self.state.first_directory or urn,
                status_text % (self.state.file_count, self.state.dir_count))
    self.Status(status_text, self.state.file_count, self.state.dir_count)


class UpdateSparseImageChunksArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.UpdateSparseImageChunksArgs


class UpdateSparseImageChunks(flow.GRRFlow):
  """Updates a list of chunks of a sparse image from the client."""

  category = "/Filesystem/"
  args_type = UpdateSparseImageChunksArgs

  def GetBufferForChunk(self, chunk):
    chunk_offset = chunk * self.state.chunksize
    request = rdf_client.BufferReference(pathspec=self.state.pathspec,
                                         length=self.state.chunksize,
                                         offset=chunk_offset)
    return request

  @flow.StateHandler(next_state="UpdateChunk")
  def Start(self):

    fd = aff4.FACTORY.Open(self.state.args.file_urn,
                           token=self.token,
                           aff4_type=standard.AFF4SparseImage,
                           mode="rw")
    pathspec = fd.Get(fd.Schema.PATHSPEC)
    self.state.Register("pathspec", pathspec)
    self.state.Register("fd", fd)
    self.state.Register("chunksize", fd.chunksize)
    self.state.Register("missing_chunks", self.state.args.chunks_to_fetch)

    if self.state.missing_chunks:
      # TODO(user): At the moment we aren't using deduplication, since
      # we're transferring every chunk from the client, regardless of whether
      # it's a known blob. We should do something similar to MultiGetFile here
      # instead.
      chunk = self.state.missing_chunks.Pop(0)
      request = self.GetBufferForChunk(chunk)
      self.CallClient("TransferBuffer", request, next_state="UpdateChunk")

  @flow.StateHandler(next_state="UpdateChunk")
  def UpdateChunk(self, responses):
    if not responses.success:
      raise IOError("Error running TransferBuffer: %s" % responses.status)
    response = responses.First()

    chunk_number = response.offset / self.state.chunksize
    self.state.fd.AddBlob(blob_hash=response.data,
                          length=response.length,
                          chunk_number=chunk_number)
    self.state.fd.Flush()

    if len(self.state.missing_chunks) >= 1:
      next_chunk = self.state.missing_chunks.Pop(0)
      request = self.GetBufferForChunk(next_chunk)
      self.CallClient("TransferBuffer", request, next_state="UpdateChunk")


class FetchBufferForSparseImageArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FetchBufferForSparseImageArgs


class FetchBufferForSparseImage(flow.GRRFlow):
  """Reads data from a client-side file, specified by a length and offset.

  This data is written to an AFF4SparseImage object. Note that
  more data than is requested may be read since we align reads to chunks.
  """

  category = "/Filesystem/"
  args_type = FetchBufferForSparseImageArgs

  @flow.StateHandler(next_state="TransferBuffer")
  def Start(self):

    urn = self.state.args.file_urn

    fd = aff4.FACTORY.Open(urn,
                           token=self.token,
                           aff4_type=standard.AFF4SparseImage,
                           mode="rw")
    self.state.Register("fd", fd)

    pathspec = fd.Get(fd.Schema.PATHSPEC)

    # Use the object's chunk size, in case it's different to the class-wide
    # chunk size.
    chunksize = fd.chunksize
    self.state.Register("pathspec", pathspec)
    self.state.Register("chunksize", chunksize)

    # Make sure we always read a whole number of chunks.
    new_length, new_offset = self.AlignToChunks(self.state.args.length,
                                                self.state.args.offset,
                                                chunksize)

    # Remember where we're up to in reading the file, and how much we have left
    # to read.
    self.state.Register("bytes_left_to_read", new_length)
    self.state.Register("current_offset", new_offset)

    # Always read one chunk at a time.
    request = rdf_client.BufferReference(pathspec=self.state.pathspec,
                                         length=self.state.chunksize,
                                         offset=self.state.current_offset)
    # Remember where we're up to, and that we're about to read one chunk.
    self.state.bytes_left_to_read -= chunksize
    self.state.current_offset += chunksize

    self.CallClient("TransferBuffer", request, next_state="TransferBuffer")

  @flow.StateHandler(next_state="TransferBuffer")
  def TransferBuffer(self, responses):
    # Did it work?
    if not responses.success:
      raise IOError("Error running TransferBuffer: %s" % responses.status)

    response = responses.First()

    # Write the data we got from the client to the file.
    sparse_image = self.state.fd
    chunk_number = response.offset / sparse_image.chunksize
    sparse_image.AddBlob(blob_hash=response.data,
                         length=response.length,
                         chunk_number=chunk_number)
    sparse_image.Flush()

    length_to_read = min(self.state.chunksize, self.state.bytes_left_to_read)

    if length_to_read:
      request = rdf_client.BufferReference(pathspec=self.state.pathspec,
                                           length=length_to_read,
                                           offset=self.state.current_offset)
      # TODO(user): Again, this is going to be too slow, since we're
      # waiting for a client response every time we request a buffer. We need to
      # queue up multiple reads.
      self.CallClient("TransferBuffer", request, next_state="TransferBuffer")

      # Move our offset along the file by how much we read.
      self.state.current_offset += length_to_read
      # Remember how much more we need to read.
      self.state.bytes_left_to_read = max(
          0, self.state.bytes_left_to_read - length_to_read)

  @staticmethod
  def AlignToChunks(length, offset, chunksize):
    """Make sure that if we are reading part of a chunk, we read all of it.

    Args:
      length: How much data to read.
      offset: Where in the file to read it from.
      chunksize: How big the chunks in the file are.

    Returns:
      A (length, offset) tuple, containing the length and offset
      required to read all affected chunks.
    """
    start_chunk = offset / chunksize
    end_chunk = (offset + length) / chunksize
    # If we happened to round down to the beginning of the end chunk, make sure
    # to read to the end of it (which is the beginning of the next chunk).
    if (offset + length) % chunksize != 0:
      end_chunk += 1

    # New offset starts from the beginning of the start chunk.
    new_offset = start_chunk * chunksize
    new_length = (end_chunk * chunksize) - new_offset

    return new_length, new_offset


class MakeNewAFF4SparseImageArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.MakeNewAFF4SparseImageArgs


class MakeNewAFF4SparseImage(flow.GRRFlow):
  """Gets a new file from the client, possibly as an AFF4SparseImage.

  If the filesize is >= the size threshold, then we get the file as an empty
  AFF4SparseImage, otherwise we just call GetFile, which gets the complete file.

  We do the check to see if the file is big enough to get as an AFF4SparseImage
  in this flow so we don't need to do another round trip to the client.

  Args:
    pathspec: Pathspec of the file to look at.
    size_threshold: If the file is bigger than this size, we'll get it as an
    empty AFF4SparseImage, otherwise we'll just download the whole file as
    usual with GetFile.
  """

  category = "/Filesystem/"
  args_type = MakeNewAFF4SparseImageArgs

  @flow.StateHandler(next_state="ProcessStat")
  def Start(self):
    self.CallClient("StatFile",
                    pathspec=self.state.args.pathspec,
                    next_state="ProcessStat")

  @flow.StateHandler(next_state="End")
  def ProcessStat(self, responses):
    # Did it work?
    if not responses.success:
      # It's better to raise rather than merely logging since it will
      # make it to the flow's protobuf and users can
      # inspect the reason this flow failed.
      raise IOError("Could not stat file: %s" % responses.status)

    client_stat = responses.First()

    # Update the pathspec to the one we got from the client.
    self.state.Register("pathspec", client_stat.pathspec)

    # If the file was big enough, we'll store it as an AFF4SparseImage
    if client_stat.st_size > self.state.args.size_threshold:
      urn = aff4_grr.VFSGRRClient.PathspecToURN(self.state.pathspec,
                                                self.client_id)

      # TODO(user) When we can check the last update time of the
      # contents of a file, raise if the contents have been updated before here.

      fd = aff4.FACTORY.Create(urn,
                               aff4_type=standard.AFF4SparseImage,
                               token=self.token,
                               mode="rw")
      fd.Set(fd.Schema.PATHSPEC, self.state.pathspec)
      fd.Set(fd.Schema.STAT, client_stat)
      fd.Flush()
    else:
      # Otherwise, just get the whole file.
      self.CallFlow("MultiGetFile",
                    pathspecs=[self.state.pathspec],
                    next_state="End")

  @flow.StateHandler()
  def End(self, responses):
    # Check that the GetFile flow worked.
    if not responses.success:
      raise IOError("Could not get file: %s" % responses.status)


class GlobArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.GlobArgs

  def Validate(self):
    """Ensure that the glob paths are valid."""
    self.paths.Validate()


class GlobMixin(object):
  """A MixIn to implement the glob functionality."""

  def GlobForPaths(self,
                   paths,
                   pathtype="OS",
                   root_path=None,
                   no_file_type_check=False):
    """Starts the Glob.

    This is the main entry point for this flow mixin.

    First we convert the pattern into regex components, and then we
    interpolate each component. Finally, we generate a cartesian product of all
    combinations.

    Args:
      paths: A list of GlobExpression instances.
      pathtype: The pathtype to use for creating pathspecs.
      root_path: A pathspec where to start searching from.
      no_file_type_check: Work with all kinds of files - not only with regular
                          ones.
    """
    patterns = []

    if not paths:
      # Nothing to do.
      return

    client = aff4.FACTORY.Open(self.client_id, token=self.token)

    self.state.Register("pathtype", pathtype)
    self.state.Register("root_path", root_path)
    self.state.Register("no_file_type_check", no_file_type_check)

    # Transform the patterns by substitution of client attributes. When the
    # client has multiple values for an attribute, this generates multiple
    # copies of the pattern, one for each variation. e.g.:
    # /home/%%Usernames%%/* -> [ /home/user1/*, /home/user2/* ]
    for path in paths:
      patterns.extend(path.Interpolate(client=client))

    # Expand each glob pattern into a list of components. A component is either
    # a wildcard or a literal component.
    # e.g. /usr/lib/*.exe -> ['/usr/lib', '.*.exe']

    # We build a tree for each component such that duplicated components are
    # merged. We do not need to reissue the same client requests for the same
    # components. For example, the patterns:
    # '/home/%%Usernames%%*' -> {'/home/': {
    #      'syslog.*\\Z(?ms)': {}, 'test.*\\Z(?ms)': {}}}
    # Note: The component tree contains serialized pathspecs in dicts.
    for pattern in patterns:
      # The root node.
      node = self.state.component_tree

      for component in self.ConvertGlobIntoPathComponents(pattern):
        node = node.setdefault(component.SerializeToString(), {})

    root_path = self.state.component_tree.keys()[0]
    self.CallStateInline(messages=[None],
                         next_state="ProcessEntry",
                         request_data=dict(component_path=[root_path]))

  def GlobReportMatch(self, stat_response):
    """Called when we've found a matching a StatEntry."""
    # By default write the stat_response to the AFF4 VFS.
    CreateAFF4Object(stat_response, self.client_id, self.token)

  # A regex indicating if there are shell globs in this path.
  GLOB_MAGIC_CHECK = re.compile("[*?[]")

  # Maximum number of files to inspect in a single directory
  FILE_MAX_PER_DIR = 100000

  def ConvertGlobIntoPathComponents(self, pattern):
    """Converts a glob pattern into a list of pathspec components.

    Wildcards are also converted to regular expressions. The pathspec components
    do not span directories, and are marked as a regex or a literal component.

    We also support recursion into directories using the ** notation.  For
    example, /home/**2/foo.txt will find all files named foo.txt recursed 2
    directories deep. If the directory depth is omitted, it defaults to 3.

    Example:
     /home/test/* -> ['home', 'test', '.*\\Z(?ms)']

    Args:
      pattern: A glob expression with wildcards.

    Returns:
      A list of PathSpec instances for each component.

    Raises:
      ValueError: If the glob is invalid.
    """

    components = []
    for path_component in pattern.split("/"):
      # A ** in the path component means recurse into directories that match the
      # pattern.
      m = rdf_paths.GlobExpression.RECURSION_REGEX.search(path_component)
      if m:
        path_component = path_component.replace(m.group(0), "*")

        component = rdf_paths.PathSpec(
            path=fnmatch.translate(path_component),
            pathtype=self.state.pathtype,
            path_options=rdf_paths.PathSpec.Options.RECURSIVE)

        # Allow the user to override the recursion depth.
        if m.group(1):
          component.recursion_depth = int(m.group(1))

      elif self.GLOB_MAGIC_CHECK.search(path_component):
        component = rdf_paths.PathSpec(
            path=fnmatch.translate(path_component),
            pathtype=self.state.pathtype,
            path_options=rdf_paths.PathSpec.Options.REGEX)
      else:
        pathtype = self.state.pathtype
        # TODO(user): This is a backwards compatibility hack. Remove when
        # all clients reach 3.0.0.2.
        if (pathtype == rdf_paths.PathSpec.PathType.TSK and
            re.match("^.:$", path_component)):
          path_component = "%s\\" % path_component
        component = rdf_paths.PathSpec(
            path=path_component,
            pathtype=pathtype,
            path_options=rdf_paths.PathSpec.Options.CASE_INSENSITIVE)

      components.append(component)

    return components

  @flow.StateHandler()
  def Start(self, **_):
    super(GlobMixin, self).Start()
    self.state.Register("component_tree", {})

  def FindNode(self, component_path):
    """Find the node in the component_tree from component_path.

    Args:
      component_path: A list of components which reference a node in the
        component tree. This allows us to resume processing in the tree.

    Returns:
      A node in the component_tree.
    """
    # Find the node that the component path is referring to.
    node = self.state.component_tree
    for component in component_path:
      node = node[component]

    return node

  def _MatchPath(self, pathspec, response):
    """Check if the responses matches the pathspec (considering options)."""
    to_match = response.pathspec.Basename()
    if pathspec.path_options == rdf_paths.PathSpec.Options.CASE_INSENSITIVE:
      return to_match.lower() == pathspec.path.lower()
    elif pathspec.path_options == rdf_paths.PathSpec.Options.CASE_LITERAL:
      return to_match == pathspec.path
    elif pathspec.path_options == rdf_paths.PathSpec.Options.REGEX:
      return bool(re.match(pathspec.path, to_match, flags=re.IGNORECASE))
    elif pathspec.path_options == rdf_paths.PathSpec.Options.RECURSIVE:
      return True
    raise ValueError("Unknown Pathspec type.")

  @flow.StateHandler(next_state="ProcessEntry")
  def ProcessEntry(self, responses):
    """Process the responses from the client."""
    if not responses.success:
      return

    # If we get a response with an unfinished iterator then we missed some
    # files. Call Find on the client until we're done.
    if (responses.iterator and
        responses.iterator.state != responses.iterator.State.FINISHED):
      findspec = rdf_client.FindSpec(responses.request.request.payload)
      findspec.iterator = responses.iterator
      self.CallClient("Find",
                      findspec,
                      next_state="ProcessEntry",
                      request_data=responses.request_data)

    # The Find client action does not return a StatEntry but a
    # FindSpec. Normalize to a StatEntry.
    stat_responses = [r.hit if isinstance(r, rdf_client.FindSpec) else r
                      for r in responses]

    # If this was a pure path matching call without any regex / recursion, we
    # know exactly which node in the component tree we have to process next and
    # get it from the component_path. If this was a regex match though, we
    # sent the client a combined regex that matches all nodes in order to save
    # round trips and client processing time. In that case we only get the
    # base node and have to check for all subnodes if the response actually
    # matches that subnode before we continue processing.
    component_path = responses.request_data.get("component_path")
    if component_path is not None:

      for response in stat_responses:
        self._ProcessResponse(response, [component_path])

    else:
      # This is a combined match.
      base_path = responses.request_data["base_path"]
      base_node = self.FindNode(base_path)
      for response in stat_responses:
        matching_components = []
        for next_node in base_node.keys():
          pathspec = rdf_paths.PathSpec(next_node)

          if self._MatchPath(pathspec, response):
            matching_path = base_path + [next_node]
            matching_components.append(matching_path)

        if matching_components:
          self._ProcessResponse(response,
                                matching_components,
                                base_wildcard=True)

  def _GetBasePathspec(self, response):
    if response:
      return response.pathspec.Copy()
    else:
      root_path = self.state.root_path
      if root_path:
        return root_path.Copy()
    return None

  def _ProcessResponse(self, response, component_paths, base_wildcard=False):
    for component_path in component_paths:
      regexes_to_get = []
      recursions_to_get = {}

      node = self.FindNode(component_path)

      if not node:
        # Node is empty representing a leaf node - we found a hit - report it.
        self.GlobReportMatch(response)
        return

      # There are further components in the tree - iterate over them.
      for component_str, next_node in node.items():
        component = rdf_paths.PathSpec(component_str)
        next_component = component_path + [component_str]

        # If we reach this point, we are instructed to go deeper into the
        # directory structure. We only want to actually do this if
        # - the last response was a proper directory,
        # - or it was a file (an image) that was explicitly given meaning
        #   no wildcards or groupings,
        # - or no_file_type_check was set.
        #
        # This reduces the number of TSK opens on the client that may
        # sometimes lead to instabilities due to bugs in the library.

        if response and (
            not (stat.S_ISDIR(response.st_mode) or not base_wildcard or
                 self.state.no_file_type_check)):
          continue

        if component.path_options == component.Options.RECURSIVE:
          recursions_to_get.setdefault(component.recursion_depth,
                                       []).append(component)
        elif component.path_options == component.Options.REGEX:
          regexes_to_get.append(component)

        elif component.path_options == component.Options.CASE_INSENSITIVE:
          # Here we need to create the next pathspec by appending the current
          # component to what we already have. If we don't have anything yet, we
          # fall back to the root path. If there is no root path either, the
          # current component becomes the new base.
          base_pathspec = self._GetBasePathspec(response)
          if base_pathspec:
            pathspec = base_pathspec.Append(component)
          else:
            pathspec = component

          if not next_node:
            # Check for the existence of the last node.
            request = rdf_client.ListDirRequest(pathspec=pathspec)

            if (response is None or (response and
                                     (response.st_mode == 0 or
                                      not stat.S_ISREG(response.st_mode)))):
              # If next node is empty, this node is a leaf node, we therefore
              # must stat it to check that it is there. There is a special case
              # here where this pathspec points to a file/directory in the root
              # directory. In this case, response will be None but we still need
              # to stat it.
              self.CallClient("StatFile",
                              request,
                              next_state="ProcessEntry",
                              request_data=dict(component_path=next_component))
          else:
            # There is no need to go back to the client for intermediate
            # paths in the prefix tree, just emulate this by recursively
            # calling this state inline.
            self.CallStateInline(
                [rdf_client.StatEntry(pathspec=pathspec)],
                next_state="ProcessEntry",
                request_data=dict(component_path=next_component))

      if recursions_to_get or regexes_to_get:
        # Recursions or regexes need a base pathspec to operate on. If we
        # have neither a response or a root path, we send a default pathspec
        # that opens the root with pathtype "OS".
        base_pathspec = self._GetBasePathspec(response)
        if not base_pathspec:
          base_pathspec = rdf_paths.PathSpec(path="/", pathtype="OS")

        for depth, recursions in recursions_to_get.iteritems():
          path_regex = "(?i)^" + "$|^".join(set([c.path for c in recursions
                                                ])) + "$"

          findspec = rdf_client.FindSpec(pathspec=base_pathspec,
                                         cross_devs=True,
                                         max_depth=depth,
                                         path_regex=path_regex)

          findspec.iterator.number = self.FILE_MAX_PER_DIR
          self.CallClient("Find",
                          findspec,
                          next_state="ProcessEntry",
                          request_data=dict(base_path=component_path))

        if regexes_to_get:
          path_regex = "(?i)^" + "$|^".join(set([c.path for c in regexes_to_get
                                                ])) + "$"
          findspec = rdf_client.FindSpec(pathspec=base_pathspec,
                                         max_depth=1,
                                         path_regex=path_regex)

          findspec.iterator.number = self.FILE_MAX_PER_DIR
          self.CallClient("Find",
                          findspec,
                          next_state="ProcessEntry",
                          request_data=dict(base_path=component_path))


class Glob(GlobMixin, flow.GRRFlow):
  """Glob the filesystem for patterns.

  Returns:
    StatEntry messages, one for each matching file.
  """

  category = "/Filesystem/"
  behaviours = flow.GRRFlow.behaviours + "ADVANCED"
  args_type = GlobArgs

  @flow.StateHandler(next_state="ProcessEntry")
  def Start(self):
    """Starts the Glob.

    First we convert the pattern into regex components, and then we
    interpolate each component. Finally, we generate a cartesian product of all
    combinations.
    """
    super(Glob, self).Start()
    self.GlobForPaths(self.args.paths,
                      pathtype=self.args.pathtype,
                      root_path=self.args.root_path,
                      no_file_type_check=self.args.no_file_type_check)

  def GlobReportMatch(self, stat_response):
    """Called when we've found a matching a StatEntry."""
    super(Glob, self).GlobReportMatch(stat_response)
    self.SendReply(stat_response)


class DiskVolumeInfoArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.DiskVolumeInfoArgs


def PathHasDriveLetter(path):
  """Check path for windows drive letter.

  Use 1:2 to avoid raising on single character paths.

  Args:
    path: path string
  Returns:
    True if this path has a drive letter.
  """
  return path[1:2] == ":"


class DiskVolumeInfo(flow.GRRFlow):
  """Get disk volume info for a given path.

  On linux and OS X we call StatFS on each path and return the results. For
  windows we collect all the volume information and filter it using the drive
  letters in the supplied path list.
  """
  args_type = DiskVolumeInfoArgs
  category = "/Filesystem/"
  behaviours = flow.GRRFlow.behaviours + "ADVANCED"

  @flow.StateHandler(next_state=["CollectVolumeInfo", "StoreSystemRoot"])
  def Start(self):
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.state.Register("system", client.Get(client.Schema.SYSTEM))
    self.state.Register("drive_letters", set())
    self.state.Register("system_root_required", False)

    if self.state.system == "Windows":
      # Handle the case where a path is specified without the drive letter by
      # collecting systemroot and making sure we report the disk usage for it.
      for path in self.args.path_list:
        if PathHasDriveLetter(path):
          self.state.drive_letters.add(path[0:2])
        else:
          self.state.system_root_required = True
      if self.state.system_root_required:
        self.CallFlow("ArtifactCollectorFlow",
                      artifact_list=["SystemRoot"],
                      next_state="StoreSystemRoot")
        return

    self.CallStateInline(next_state="CollectVolumeInfo")

  @flow.StateHandler(next_state=["CollectVolumeInfo"])
  def StoreSystemRoot(self, responses):
    if not responses.success or not responses.First():
      if self.state.drive_letters:
        # We have at least one path that already has a drive letter so we'll log
        # rather than raise.
        self.Log("Error collecting SystemRoot artifact: %s", responses.status)
      else:
        raise flow.FlowError("Error collecting SystemRoot artifact: %s" %
                             responses.status)

    drive = str(responses.First())[0:2]
    if drive:
      self.state.drive_letters.add(drive)
    else:
      self.Log("Bad result for systemdrive: %s", responses.First())

    self.CallStateInline(next_state="CollectVolumeInfo")

  @flow.StateHandler(next_state=["ProcessVolumes", "ProcessWindowsVolumes"])
  def CollectVolumeInfo(self, unused_responses):
    if self.state.system == "Windows":
      # No dependencies for WMI
      deps = artifact_utils.ArtifactCollectorFlowArgs.Dependency.IGNORE_DEPS
      self.CallFlow("ArtifactCollectorFlow",
                    artifact_list=["WMILogicalDisks"],
                    next_state="ProcessWindowsVolumes",
                    dependencies=deps,
                    store_results_in_aff4=True)
    else:
      self.CallClient("StatFS",
                      rdf_client.StatFSRequest(path_list=self.args.path_list,
                                               pathtype=self.args.pathtype),
                      next_state="ProcessVolumes")

  @flow.StateHandler()
  def ProcessWindowsVolumes(self, responses):
    if not responses.success:
      self.Log("Error running WMILogicalDisks artifact: %s", responses.status)

    for response in responses:
      if response.windowsvolume.drive_letter in self.state.drive_letters:
        self.SendReply(response)

  @flow.StateHandler()
  def ProcessVolumes(self, responses):
    if not responses.success:
      self.Log("Error running StatFS: %s", responses.status)

    for response in responses:
      self.SendReply(response)
