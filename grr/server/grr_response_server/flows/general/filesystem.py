#!/usr/bin/env python
"""These are filesystem related flows."""
import fnmatch
import re
import stat

from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import objects as rdf_objects
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import artifact_utils
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server import flow
from grr.server.grr_response_server import notification
from grr.server.grr_response_server import server_stubs
from grr.server.grr_response_server.aff4_objects import aff4_grr
from grr.server.grr_response_server.aff4_objects import standard
from grr.server.grr_response_server.flows.general import transfer

# This is all bits that define the type of the file in the stat mode. Equal to
# 0b1111000000000000.
stat_type_mask = (
    stat.S_IFREG | stat.S_IFDIR | stat.S_IFLNK | stat.S_IFBLK
    | stat.S_IFCHR | stat.S_IFIFO | stat.S_IFSOCK)


# TODO(hanuszczak): Name of this function is pretty bad. Consider changing it.
def CreateAFF4Object(stat_response, client_id, mutation_pool, token=None):
  """This creates a File or a Directory from a stat response."""

  urn = stat_response.pathspec.AFF4Path(client_id)

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

  with aff4.FACTORY.Create(
      urn, ftype, mode="w", mutation_pool=mutation_pool, token=token) as fd:
    fd.Set(fd.Schema.STAT(stat_response))
    fd.Set(fd.Schema.PATHSPEC(stat_response.pathspec))


def WriteStatEntries(stat_entries, client_id, mutation_pool, token=None):
  """Persists information about stat entries.

  Args:
    stat_entries: A list of `StatEntry` instances.
    client_id: An id of a client the stat entries come from.
    mutation_pool: A mutation pool used for writing into the AFF4 data store.
    token: A token used for writing into the AFF4 data store.
  """
  for stat_entry in stat_entries:
    CreateAFF4Object(
        stat_entry,
        client_id=client_id,
        mutation_pool=mutation_pool,
        token=token)

  if data_store.RelationalDBWriteEnabled():
    path_infos = map(rdf_objects.PathInfo.FromStatEntry, stat_entries)
    data_store.REL_DB.WritePathInfos(client_id.Basename(), path_infos)


class ListDirectoryArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.ListDirectoryArgs
  rdf_deps = [
      rdf_paths.PathSpec,
  ]


class ListDirectory(flow.GRRFlow):
  """List files in a directory."""

  category = "/Filesystem/"
  args_type = ListDirectoryArgs
  behaviours = flow.GRRFlow.behaviours + "ADVANCED"

  @flow.StateHandler()
  def Start(self):
    """Issue a request to list the directory."""
    self.state.urn = None

    # TODO(hanuszczak): Support for old clients ends on 2021-01-01.
    # This conditional should be removed after that date.
    if self.client_version >= 3221:
      stub = server_stubs.GetFileStat
      request = rdf_client.GetFileStatRequest(pathspec=self.args.pathspec)
    else:
      stub = server_stubs.StatFile
      request = rdf_client.ListDirRequest(pathspec=self.args.pathspec)

    self.CallClient(stub, request, next_state="Stat")

    # We use data to pass the path to the callback:
    self.CallClient(
        server_stubs.ListDirectory,
        pathspec=self.args.pathspec,
        next_state="List")

  @flow.StateHandler()
  def Stat(self, responses):
    """Save stat information on the directory."""
    # Did it work?
    if not responses.success:
      self.Error("Could not stat directory: %s" % responses.status)

    else:
      # Keep the stat response for later.
      stat_entry = rdf_client.StatEntry(responses.First())
      self.state.stat = stat_entry

      # The full path of the object is the combination of the client_id and the
      # path.
      self.state.urn = stat_entry.pathspec.AFF4Path(self.client_id)

  @flow.StateHandler()
  def List(self, responses):
    """Collect the directory listing and store in the datastore."""
    if not responses.success:
      raise flow.FlowError(str(responses.status))

    self.Status("Listed %s", self.state.urn)

    with data_store.DB.GetMutationPool() as pool:
      with aff4.FACTORY.Create(
          self.state.urn,
          standard.VFSDirectory,
          mode="w",
          mutation_pool=pool,
          token=self.token) as fd:
        fd.Set(fd.Schema.PATHSPEC(self.state.stat.pathspec))
        fd.Set(fd.Schema.STAT(self.state.stat))

      if data_store.RelationalDBWriteEnabled():
        path_info = rdf_objects.PathInfo.FromStatEntry(self.state.stat)
        data_store.REL_DB.WritePathInfos(self.client_id.Basename(), [path_info])

      stat_entries = map(rdf_client.StatEntry, responses)
      WriteStatEntries(
          stat_entries,
          client_id=self.client_id,
          mutation_pool=pool,
          token=self.token)

      for stat_entry in stat_entries:
        self.SendReply(stat_entry)  # Send Stats to parent flows.

  def NotifyAboutEnd(self):
    if not self.runner.ShouldSendNotifications():
      return

    if not self.state.urn:
      super(ListDirectory, self).NotifyAboutEnd()
      return

    components = self.state.urn.Split()
    file_ref = None
    if len(components) > 3:
      file_ref = rdf_objects.VfsFileReference(
          client_id=components[0],
          path_type=components[2].upper(),
          path_components=components[3:])
    notification.Notify(
        self.token.username,
        notification.UserNotification.Type.TYPE_VFS_LIST_DIRECTORY_COMPLETED,
        "Listed {0}".format(utils.SmartStr(self.args.pathspec)),
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.VFS_FILE,
            vfs_file=file_ref))


class IteratedListDirectory(ListDirectory):
  """A Flow to retrieve a directory listing using an iterator.

  This flow is an example for how to use the iterated client actions. Normally
  you do not need to call this flow - a ListDirectory flow is enough.
  """

  category = None

  @flow.StateHandler()
  def Start(self):
    """Issue a request to list the directory."""
    self.state.responses = []
    self.state.urn = None

    # We use data to pass the path to the callback:
    self.state.request = rdf_client.ListDirRequest(pathspec=self.args.pathspec)

    # For this example we will use a really small number to force many round
    # trips with the client. This is a performance killer.
    self.state.request.iterator.number = 50

    self.CallClient(
        server_stubs.IteratedListDirectory,
        self.state.request,
        next_state="List")

  @flow.StateHandler()
  def List(self, responses):
    """Collect the directory listing and store in the data store."""
    if not responses.success:
      raise flow.FlowError(str(responses.status))

    if responses:
      for response in responses:
        self.state.responses.append(response)

      self.state.request.iterator = responses.iterator
      self.CallClient(
          server_stubs.IteratedListDirectory,
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

    urn = directory_pathspec.AFF4Path(self.client_id)

    # First dir we get back is the main urn.
    if not self.state.urn:
      self.state.urn = urn

    with data_store.DB.GetMutationPool() as pool:
      with aff4.FACTORY.Create(
          urn, standard.VFSDirectory, mutation_pool=pool, token=self.token):
        pass

      stat_entries = map(rdf_client.StatEntry, self.state.responses)
      WriteStatEntries(
          stat_entries,
          client_id=self.client_id,
          mutation_pool=pool,
          token=self.token)

      for stat_entry in stat_entries:
        self.SendReply(stat_entry)  # Send Stats to parent flows.

  def NotifyAboutEnd(self):
    if not self.runner.ShouldSendNotifications():
      return

    if self.state.urn:
      components = self.state.urn.Split()
      file_ref = None
      if len(components) > 3:
        file_ref = rdf_objects.VfsFileReference(
            client_id=components[0],
            path_type=components[2].upper(),
            path_components=components[3:])
      notification.Notify(
          self.token.username,
          notification.UserNotification.Type.TYPE_VFS_LIST_DIRECTORY_COMPLETED,
          "List of {0} completed.".format(utils.SmartStr(self.args.pathspec)),
          rdf_objects.ObjectReference(
              reference_type=rdf_objects.ObjectReference.Type.VFS_FILE,
              vfs_file=file_ref))
    else:
      super(IteratedListDirectory, self).NotifyAboutEnd()


class RecursiveListDirectoryArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.RecursiveListDirectoryArgs
  rdf_deps = [
      rdf_paths.PathSpec,
  ]


class RecursiveListDirectory(flow.GRRFlow):
  """Recursively list directory on the client."""

  category = "/Filesystem/"

  args_type = RecursiveListDirectoryArgs

  @flow.StateHandler()
  def Start(self):
    """List the initial directory."""
    # The first directory we listed.
    self.state.first_directory = None

    self.state.dir_count = 0
    self.state.file_count = 0

    self.CallClient(
        server_stubs.ListDirectory,
        pathspec=self.args.pathspec,
        next_state="ProcessDirectory")

  @flow.StateHandler()
  def ProcessDirectory(self, responses):
    """Recursively list the directory, and add to the timeline."""
    if responses.success:
      response = responses.First()

      if response is None:
        return

      directory_pathspec = response.pathspec.Dirname()

      urn = directory_pathspec.AFF4Path(self.client_id)

      self.StoreDirectory(responses)

      # If the urn is too deep we quit to prevent recursion errors.
      if self.state.first_directory is None:
        self.state.first_directory = urn

      else:
        relative_name = urn.RelativeName(self.state.first_directory) or ""
        if len(relative_name.split("/")) >= self.args.max_depth:
          self.Log("Exceeded maximum path depth at %s.",
                   urn.RelativeName(self.state.first_directory))
          return

      for stat_response in responses:
        # Queue a list directory for each directory here, but do not follow
        # symlinks.
        if not stat_response.symlink and stat.S_ISDIR(stat_response.st_mode):
          self.CallClient(
              server_stubs.ListDirectory,
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
    with data_store.DB.GetMutationPool() as pool:

      stat_entries = map(rdf_client.StatEntry, responses)
      WriteStatEntries(
          stat_entries,
          client_id=self.client_id,
          mutation_pool=pool,
          token=self.token)

      for stat_entry in stat_entries:
        self.SendReply(stat_entry)  # Send Stats to parent flows.

  def NotifyAboutEnd(self):
    if not self.runner.ShouldSendNotifications():
      return

    status_text = "Recursive Directory Listing complete %d nodes, %d dirs"

    urn = self.state.first_directory
    if not urn:
      try:
        urn = self.args.pathspec.AFF4Path(self.client_id)
      except ValueError:
        pass

    if urn:
      components = urn.Split()
      file_ref = None
      if len(components) > 3:
        file_ref = rdf_objects.VfsFileReference(
            client_id=components[0],
            path_type=components[2].upper(),
            path_components=components[3:])

    notification.Notify(
        self.token.username, rdf_objects.UserNotification.Type.
        TYPE_VFS_RECURSIVE_LIST_DIRECTORY_COMPLETED,
        status_text % (self.state.file_count, self.state.dir_count),
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.VFS_FILE,
            vfs_file=file_ref))

  @flow.StateHandler()
  def End(self):
    status_text = "Recursive Directory Listing complete %d nodes, %d dirs"
    self.Status(status_text, self.state.file_count, self.state.dir_count)


class UpdateSparseImageChunksArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.UpdateSparseImageChunksArgs
  rdf_deps = [
      rdfvalue.RDFURN,
  ]


class UpdateSparseImageChunks(flow.GRRFlow):
  """Updates a list of chunks of a sparse image from the client."""

  category = "/Filesystem/"
  args_type = UpdateSparseImageChunksArgs

  def GetBufferForChunk(self, chunk):
    chunk_offset = chunk * self.state.chunksize
    request = rdf_client.BufferReference(
        pathspec=self.state.pathspec,
        length=self.state.chunksize,
        offset=chunk_offset)
    return request

  @flow.StateHandler()
  def Start(self):

    fd = aff4.FACTORY.Open(
        self.args.file_urn,
        token=self.token,
        aff4_type=standard.AFF4SparseImage,
        mode="rw")
    pathspec = fd.Get(fd.Schema.PATHSPEC)

    self.state.pathspec = pathspec
    self.state.blobs = []
    self.state.chunksize = fd.chunksize
    self.state.missing_chunks = list(self.args.chunks_to_fetch)

    if self.state.missing_chunks:
      # TODO(user): At the moment we aren't using deduplication, since
      # we're transferring every chunk from the client, regardless of whether
      # it's a known blob. We should do something similar to MultiGetFile here
      # instead.
      chunk = self.state.missing_chunks.pop(0)
      request = self.GetBufferForChunk(chunk)
      self.CallClient(
          server_stubs.TransferBuffer, request, next_state="UpdateChunk")

  @flow.StateHandler()
  def UpdateChunk(self, responses):
    if not responses.success:
      raise IOError("Error running TransferBuffer: %s" % responses.status)
    response = responses.First()

    chunk_number = response.offset / self.state.chunksize

    self.state.blobs.append([chunk_number, response])

    if len(self.state.missing_chunks) >= 1:
      next_chunk = self.state.missing_chunks.pop(0)
      request = self.GetBufferForChunk(next_chunk)
      self.CallClient(
          server_stubs.TransferBuffer, request, next_state="UpdateChunk")
    else:
      with aff4.FACTORY.Open(
          self.args.file_urn,
          token=self.token,
          aff4_type=standard.AFF4SparseImage,
          mode="rw") as fd:
        for chunk_number, response in self.state.blobs:
          fd.AddBlob(
              blob_hash=response.data,
              length=response.length,
              chunk_number=chunk_number)

        del self.state.blobs


class FetchBufferForSparseImageArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FetchBufferForSparseImageArgs
  rdf_deps = [
      rdfvalue.RDFURN,
  ]


class FetchBufferForSparseImage(flow.GRRFlow):
  """Reads data from a client-side file, specified by a length and offset.

  This data is written to an AFF4SparseImage object. Note that
  more data than is requested may be read since we align reads to chunks.
  """

  category = "/Filesystem/"
  args_type = FetchBufferForSparseImageArgs

  @flow.StateHandler()
  def Start(self):

    urn = self.args.file_urn

    fd = aff4.FACTORY.Open(
        urn, token=self.token, aff4_type=standard.AFF4SparseImage, mode="rw")
    pathspec = fd.Get(fd.Schema.PATHSPEC)

    # Use the object's chunk size, in case it's different to the class-wide
    # chunk size.
    chunksize = fd.chunksize
    self.state.pathspec = pathspec
    self.state.chunksize = chunksize
    self.state.blobs = []

    # Make sure we always read a whole number of chunks.
    new_length, new_offset = self.AlignToChunks(self.args.length,
                                                self.args.offset, chunksize)

    # Remember where we're up to in reading the file, and how much we have left
    # to read.
    self.state.bytes_left_to_read = new_length
    self.state.current_offset = new_offset

    # Always read one chunk at a time.
    request = rdf_client.BufferReference(
        pathspec=self.state.pathspec,
        length=self.state.chunksize,
        offset=self.state.current_offset)
    # Remember where we're up to, and that we're about to read one chunk.
    self.state.bytes_left_to_read -= chunksize
    self.state.current_offset += chunksize

    self.CallClient(
        server_stubs.TransferBuffer, request, next_state="TransferBuffer")

  @flow.StateHandler()
  def TransferBuffer(self, responses):
    # Did it work?
    if not responses.success:
      raise IOError("Error running TransferBuffer: %s" % responses.status)

    response = responses.First()

    # Write the data we got from the client to the file.
    # sparse_image = self.state.fd
    chunk_number = response.offset / self.state.chunksize
    self.state.blobs.append([chunk_number, response])

    length_to_read = min(self.state.chunksize, self.state.bytes_left_to_read)

    if length_to_read:
      request = rdf_client.BufferReference(
          pathspec=self.state.pathspec,
          length=length_to_read,
          offset=self.state.current_offset)
      # TODO(user): Again, this is going to be too slow, since we're
      # waiting for a client response every time we request a buffer. We need to
      # queue up multiple reads.
      self.CallClient(
          server_stubs.TransferBuffer, request, next_state="TransferBuffer")

      # Move our offset along the file by how much we read.
      self.state.current_offset += length_to_read
      # Remember how much more we need to read.
      self.state.bytes_left_to_read = max(
          0, self.state.bytes_left_to_read - length_to_read)

    else:
      with aff4.FACTORY.Open(
          self.args.file_urn,
          token=self.token,
          aff4_type=standard.AFF4SparseImage,
          mode="rw") as fd:
        for chunk_number, response in self.state.blobs:
          fd.AddBlob(
              blob_hash=response.data,
              length=response.length,
              chunk_number=chunk_number)

        del self.state.blobs

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
  rdf_deps = [
      rdf_paths.PathSpec,
  ]


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

  @flow.StateHandler()
  def Start(self):
    # TODO(hanuszczak): Support for old clients ends on 2021-01-01.
    # This conditional should be removed after that date.
    if self.client_version >= 3221:
      stub = server_stubs.GetFileStat
      request = rdf_client.GetFileStatRequest(pathspec=self.args.pathspec)
    else:
      stub = server_stubs.StatFile
      request = rdf_client.ListDirRequest(pathspec=self.args.pathspec)

    self.CallClient(stub, request, next_state="ProcessStat")

  @flow.StateHandler()
  def ProcessStat(self, responses):
    # Did it work?
    if not responses.success:
      # It's better to raise rather than merely logging since it will
      # make it to the flow's protobuf and users can
      # inspect the reason this flow failed.
      raise IOError("Could not stat file: %s" % responses.status)

    client_stat = responses.First()

    # Update the pathspec to the one we got from the client.
    self.state.pathspec = client_stat.pathspec

    # If the file was big enough, we'll store it as an AFF4SparseImage
    if client_stat.st_size > self.args.size_threshold:
      urn = self.state.pathspec.AFF4Path(self.client_id)

      # TODO(user) When we can check the last update time of the
      # contents of a file, raise if the contents have been updated before here.

      fd = aff4.FACTORY.Create(
          urn, aff4_type=standard.AFF4SparseImage, token=self.token, mode="rw")
      fd.Set(fd.Schema.PATHSPEC, self.state.pathspec)
      fd.Set(fd.Schema.STAT, client_stat)
      fd.Flush()

      if data_store.RelationalDBWriteEnabled():
        path_info = rdf_objects.PathInfo.FromStatEntry(client_stat)
        data_store.REL_DB.WritePathInfos(self.client_id.Basename(), [path_info])
    else:
      # Otherwise, just get the whole file.
      self.CallFlow(
          transfer.MultiGetFile.__name__,
          pathspecs=[self.state.pathspec],
          next_state="End")

  @flow.StateHandler()
  def End(self, responses):
    # Check that the GetFile flow worked.
    if not responses.success:
      raise IOError("Could not get file: %s" % responses.status)


class GlobArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.GlobArgs
  rdf_deps = [
      rdf_paths.GlobExpression,
      rdf_paths.PathSpec,
  ]

  def Validate(self):
    """Ensure that the glob paths are valid."""
    self.paths.Validate()


class GlobMixin(object):
  """A MixIn to implement the glob functionality."""

  def GlobForPaths(self,
                   paths,
                   pathtype="OS",
                   root_path=None,
                   process_non_regular_files=False,
                   collect_ext_attrs=False):
    """Starts the Glob.

    This is the main entry point for this flow mixin.

    First we convert the pattern into regex components, and then we
    interpolate each component. Finally, we generate a cartesian product of all
    combinations.

    Args:
      paths: A list of GlobExpression instances.
      pathtype: The pathtype to use for creating pathspecs.
      root_path: A pathspec where to start searching from.
      process_non_regular_files: Work with all kinds of files - not only with
          regular ones.
      collect_ext_attrs: Whether to gather information about file extended
          attributes.
    """
    patterns = []

    if not paths:
      # Nothing to do.
      return

    client = aff4.FACTORY.Open(self.client_id, token=self.token)

    self.state.pathtype = pathtype
    self.state.root_path = root_path
    self.state.process_non_regular_files = process_non_regular_files
    self.state.collect_ext_attrs = collect_ext_attrs

    # Transform the patterns by substitution of client attributes. When the
    # client has multiple values for an attribute, this generates multiple
    # copies of the pattern, one for each variation. e.g.:
    # /home/%%Usernames%%/* -> [ /home/user1/*, /home/user2/* ]
    for path in paths:
      patterns.extend(path.Interpolate(client=client))

    # Sort the patterns so that if there are files whose paths conflict with
    # directory paths, the files get handled after the conflicting directories
    # have been added to the component tree.
    patterns.sort(key=len, reverse=True)

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
      curr_node = self.state.component_tree

      components = self.ConvertGlobIntoPathComponents(pattern)
      for i, curr_component in enumerate(components):
        is_last_component = i == len(components) - 1
        next_node = curr_node.get(curr_component.SerializeToString(), {})
        if is_last_component and next_node:
          # There is a conflicting directory already existing in the tree.
          # Replace the directory node with a node representing this file.
          curr_node[curr_component.SerializeToString()] = {}
        else:
          curr_node = curr_node.setdefault(curr_component.SerializeToString(),
                                           {})

    root_path = self.state.component_tree.keys()[0]
    self.CallStateInline(
        messages=[None],
        next_state="ProcessEntry",
        request_data=dict(component_path=[root_path]))

  def GlobReportMatch(self, stat_response):
    """Called when we've found a matching a StatEntry."""
    # By default write the stat_response to the AFF4 VFS.
    with data_store.DB.GetMutationPool() as pool:
      WriteStatEntries(
          [stat_response],
          client_id=self.client_id,
          mutation_pool=pool,
          token=self.token)

  # A regex indicating if there are shell globs in this path.
  GLOB_MAGIC_CHECK = re.compile("[*?[]")

  # Maximum number of files to inspect in a single directory
  FILE_MAX_PER_DIR = 100000

  def ConvertGlobIntoPathComponents(self, pattern):
    r"""Converts a glob pattern into a list of pathspec components.

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
        # TODO(amoser): This is a backwards compatibility hack. Remove when
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
    self.state.component_tree = {}

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

  @flow.StateHandler()
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
      self.CallClient(
          server_stubs.Find,
          findspec,
          next_state="ProcessEntry",
          request_data=responses.request_data)

    # The Find client action does not return a StatEntry but a
    # FindSpec. Normalize to a StatEntry.
    stat_responses = [
        r.hit if isinstance(r, rdf_client.FindSpec) else r for r in responses
    ]

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
          pathspec = rdf_paths.PathSpec.FromSerializedString(next_node)

          if self._MatchPath(pathspec, response):
            matching_path = base_path + [next_node]
            matching_components.append(matching_path)

        if matching_components:
          self._ProcessResponse(
              response, matching_components, base_wildcard=True)

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
        component = rdf_paths.PathSpec.FromSerializedString(component_str)
        next_component = component_path + [component_str]

        # If we reach this point, we are instructed to go deeper into the
        # directory structure. We only want to actually do this if
        # - the last response was a proper directory,
        # - or it was a file (an image) that was explicitly given meaning
        #   no wildcards or groupings,
        # - or process_non_regular_files was set.
        #
        # This reduces the number of TSK opens on the client that may
        # sometimes lead to instabilities due to bugs in the library.

        if response and (not (stat.S_ISDIR(response.st_mode) or
                              not base_wildcard or
                              self.state.process_non_regular_files)):
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
            if (response is None or (response and
                                     (response.st_mode == 0 or
                                      not stat.S_ISREG(response.st_mode)))):
              # If next node is empty, this node is a leaf node, we therefore
              # must stat it to check that it is there. There is a special case
              # here where this pathspec points to a file/directory in the root
              # directory. In this case, response will be None but we still need
              # to stat it.

              # TODO(hanuszczak): Support for old clients ends on 2021-01-01.
              # This conditional should be removed after that date.
              if self.client_version >= 3221:
                stub = server_stubs.GetFileStat
                request = rdf_client.GetFileStatRequest(
                    pathspec=pathspec,
                    collect_ext_attrs=self.state.collect_ext_attrs)
              else:
                stub = server_stubs.StatFile
                request = rdf_client.ListDirRequest(pathspec=pathspec)

              self.CallClient(
                  stub,
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

          findspec = rdf_client.FindSpec(
              pathspec=base_pathspec,
              cross_devs=True,
              max_depth=depth,
              path_regex=path_regex)

          findspec.iterator.number = self.FILE_MAX_PER_DIR
          self.CallClient(
              server_stubs.Find,
              findspec,
              next_state="ProcessEntry",
              request_data=dict(base_path=component_path))

        if regexes_to_get:
          path_regex = "(?i)^" + "$|^".join(
              set([c.path for c in regexes_to_get])) + "$"
          findspec = rdf_client.FindSpec(
              pathspec=base_pathspec, max_depth=1, path_regex=path_regex)

          findspec.iterator.number = self.FILE_MAX_PER_DIR
          self.CallClient(
              server_stubs.Find,
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

  @flow.StateHandler()
  def Start(self):
    """Starts the Glob.

    First we convert the pattern into regex components, and then we
    interpolate each component. Finally, we generate a cartesian product of all
    combinations.
    """
    super(Glob, self).Start()
    self.GlobForPaths(
        self.args.paths,
        pathtype=self.args.pathtype,
        root_path=self.args.root_path,
        process_non_regular_files=self.args.process_non_regular_files)

  def GlobReportMatch(self, stat_response):
    """Called when we've found a matching StatEntry."""
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

  @flow.StateHandler()
  def Start(self):
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.state.system = client.Get(client.Schema.SYSTEM)
    self.state.drive_letters = set()
    self.state.system_root_required = False

    if self.state.system == "Windows":
      # Handle the case where a path is specified without the drive letter by
      # collecting systemroot and making sure we report the disk usage for it.
      for path in self.args.path_list:
        if PathHasDriveLetter(path):
          self.state.drive_letters.add(path[0:2])
        else:
          self.state.system_root_required = True
      if self.state.system_root_required:
        self.CallFlow(
            # TODO(user): dependency loop between collectors.py and
            # filesystem.py.
            # collectors.ArtifactCollectorFlow.__name__,
            "ArtifactCollectorFlow",
            artifact_list=["WindowsEnvironmentVariableSystemRoot"],
            next_state="StoreSystemRoot")
        return

    self.CallStateInline(next_state="CollectVolumeInfo")

  @flow.StateHandler()
  def StoreSystemRoot(self, responses):
    if not responses.success or not responses.First():
      if self.state.drive_letters:
        # We have at least one path that already has a drive letter so we'll log
        # rather than raise.
        self.Log("Error collecting SystemRoot artifact: %s", responses.status)
      else:
        raise flow.FlowError(
            "Error collecting SystemRoot artifact: %s" % responses.status)

    drive = str(responses.First())[0:2]
    if drive:
      self.state.drive_letters.add(drive)
    else:
      self.Log("Bad result for systemdrive: %s", responses.First())

    self.CallStateInline(next_state="CollectVolumeInfo")

  @flow.StateHandler()
  def CollectVolumeInfo(self, unused_responses):
    if self.state.system == "Windows":
      # No dependencies for WMI
      deps = artifact_utils.ArtifactCollectorFlowArgs.Dependency.IGNORE_DEPS
      self.CallFlow(
          # TODO(user): dependency loop between collectors.py and
          # filesystem.py.
          # collectors.ArtifactCollectorFlow.__name__,
          "ArtifactCollectorFlow",
          artifact_list=["WMILogicalDisks"],
          next_state="ProcessWindowsVolumes",
          dependencies=deps)
    else:
      self.CallClient(
          server_stubs.StatFS,
          rdf_client.StatFSRequest(
              path_list=self.args.path_list, pathtype=self.args.pathtype),
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
