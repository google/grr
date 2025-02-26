#!/usr/bin/env python
"""These are filesystem related flows."""

import os
import stat
from typing import Iterable

from google.protobuf import any_pb2
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_proto import objects_pb2
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import notification
from grr_response_server import server_stubs
from grr_response_server.rdfvalues import mig_objects
from grr_response_server.rdfvalues import objects as rdf_objects
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg import fs_pb2 as rrg_fs_pb2
from grr_response_proto.rrg.action import get_file_metadata_pb2 as rrg_get_file_metadata_pb2


# This is all bits that define the type of the file in the stat mode. Equal to
# 0b1111000000000000.
stat_type_mask = (
    stat.S_IFREG
    | stat.S_IFDIR
    | stat.S_IFLNK
    | stat.S_IFBLK
    | stat.S_IFCHR
    | stat.S_IFIFO
    | stat.S_IFSOCK
)


def _FilterOutPathInfoDuplicates(path_infos):
  """Filters out duplicates from passed PathInfo objects.

  Args:
    path_infos: An iterable with PathInfo objects.

  Returns:
    A list of PathInfo objects with duplicates removed. Duplicates are
    removed following this logic: they're sorted by (ctime, mtime, atime,
    inode number) in the descending order and then the first one is taken
    and the others are dropped.
  """
  pi_dict = {}

  for pi in path_infos:
    path_key = (pi.path_type, pi.GetPathID())
    pi_dict.setdefault(path_key, []).append(pi)

  def _SortKey(pi):
    return (
        pi.stat_entry.st_ctime,
        pi.stat_entry.st_mtime,
        pi.stat_entry.st_atime,
        pi.stat_entry.st_ino,
    )

  for pi_values in pi_dict.values():
    if len(pi_values) > 1:
      pi_values.sort(key=_SortKey, reverse=True)

  return [v[0] for v in pi_dict.values()]


def WriteStatEntries(stat_entries, client_id):
  """Persists information about stat entries.

  Args:
    stat_entries: A list of `StatEntry` instances.
    client_id: An id of a client the stat entries come from.
  """

  for stat_response in stat_entries:
    if stat_response.pathspec.last.stream_name:
      # This is an ads. In that case we always need to create a file or
      # we won't be able to access the data. New clients send the correct mode
      # already but to make sure, we set this to a regular file anyways.
      # Clear all file type bits:
      stat_response.st_mode &= ~stat_type_mask
      stat_response.st_mode |= stat.S_IFREG

  path_infos = _FilterOutPathInfoDuplicates(
      [rdf_objects.PathInfo.FromStatEntry(s) for s in stat_entries]
  )
  proto_path_infos = [mig_objects.ToProtoPathInfo(pi) for pi in path_infos]
  # NOTE: TSK may return duplicate entries. This is may be either due to
  # a bug in TSK implementation, or due to the fact that TSK is capable
  # of returning deleted files information. Our VFS data model only supports
  # storing multiple versions of the files when we collect the versions
  # ourselves. At the moment we can't store multiple versions of the files
  # "as returned by TSK".
  #
  # Current behaviour is to simply drop excessive version before the
  # WritePathInfo call. This way files returned by TSK will still make it
  # into the flow's results, but not into the VFS data.
  data_store.REL_DB.WritePathInfos(client_id, proto_path_infos)


def WriteFileFinderResults(
    file_finder_results: Iterable[rdf_file_finder.FileFinderResult],
    client_id: str,
) -> None:
  """Persists information about file finder results.

  Args:
    file_finder_results: A list of `FileFinderResult` instances.
    client_id: An id of a client the stat entries come from.
  """

  path_infos = []
  for r in file_finder_results:
    if r.stat_entry.pathspec.last.stream_name:
      # This is an ADS. In this case we always need to create a file or
      # we won't be able to access the data. New clients send the correct mode
      # already but to make sure, we set this to a regular file anyways.
      # Clear all file type bits:
      r.stat_entry.st_mode &= ~stat_type_mask
      r.stat_entry.st_mode |= stat.S_IFREG

    path_info = rdf_objects.PathInfo.FromStatEntry(r.stat_entry)
    if r.HasField("hash_entry"):
      path_info.hash_entry = r.hash_entry
    path_infos.append(path_info)

  path_infos = _FilterOutPathInfoDuplicates(path_infos)
  proto_path_infos = [mig_objects.ToProtoPathInfo(pi) for pi in path_infos]
  # NOTE: TSK may return duplicate entries. This is may be either due to
  # a bug in TSK implementation, or due to the fact that TSK is capable
  # of returning deleted files information. Our VFS data model only supports
  # storing multiple versions of the files when we collect the versions
  # ourselves. At the moment we can't store multiple versions of the files
  # "as returned by TSK".
  #
  # Current behaviour is to simply drop excessive version before the
  # WritePathInfo call. This way files returned by TSK will still make it
  # into the flow's results, but not into the VFS data.
  data_store.REL_DB.WritePathInfos(client_id, proto_path_infos)


class ListDirectoryArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.ListDirectoryArgs
  rdf_deps = [
      rdf_paths.PathSpec,
  ]


class ListDirectory(flow_base.FlowBase):
  """List files in a directory."""

  category = "/Filesystem/"
  args_type = ListDirectoryArgs
  behaviours = flow_base.BEHAVIOUR_ADVANCED
  return_types = (rdf_client_fs.StatEntry,)

  def Start(self):
    """Issue a request to list the directory."""
    self.state.urn = None

    if (
        self.rrg_support
        and self.args.pathspec.pathtype == rdf_paths.PathSpec.PathType.OS
    ):
      args = rrg_get_file_metadata_pb2.Args()
      args.path.raw_bytes = self.args.pathspec.path.encode("utf-8")

      self.CallRRG(
          action=rrg_pb2.Action.GET_FILE_METADATA,
          args=args,
          next_state=self.HandleRRGGetFileMetadata.__name__,
      )
    else:
      request = rdf_client_action.GetFileStatRequest(
          pathspec=self.args.pathspec,
          follow_symlink=True,
      )
      self.CallClient(
          server_stubs.GetFileStat,
          request,
          next_state=self.Stat.__name__,
      )

    # We use data to pass the path to the callback:
    self.CallClient(
        server_stubs.ListDirectory,
        request=rdf_client_action.ListDirRequest(pathspec=self.args.pathspec),
        next_state=self.List.__name__,
    )

  @flow_base.UseProto2AnyResponses
  def HandleRRGGetFileMetadata(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      message = f"File metadata collection failure: {responses.status}"
      raise flow_base.FlowError(message)

    if len(responses) != 1:
      message = f"Unexpected number of responses: {len(responses)}"
      raise flow_base.FlowError(message)

    result = rrg_get_file_metadata_pb2.Result()
    result.ParseFromString(list(responses)[0].value)

    if result.metadata.type == rrg_fs_pb2.FileMetadata.DIR:
      mode = stat.S_IFDIR
    elif result.metadata.type == rrg_fs_pb2.FileMetadata.SYMLINK:
      mode = stat.S_IFLNK
    else:
      message = f"Unexpected file type: {result.metadata.type}"
      raise flow_base.FlowError(message)

    stat_entry = rdf_client_fs.StatEntry()
    stat_entry.pathspec.pathtype = rdf_paths.PathSpec.PathType.OS
    stat_entry.pathspec.path = (
        # Paths coming from RRG use WTF-8 encoding, so they are almost UTF-8 but
        # with some caveats. For now, we just replace non-UTF-8 bytes, but in
        # the future we should have a utility for working with WTF-8 paths.
        result.path.raw_bytes.decode("utf-8", "backslashreplace")
    )
    stat_entry.symlink = (
        # See the comment above on why we do `backslashreplace`.
        result.path.raw_bytes.decode("utf-8", "backslashreplace")
    )
    stat_entry.st_mode = mode
    stat_entry.st_size = result.metadata.size
    stat_entry.st_atime = result.metadata.access_time.seconds
    stat_entry.st_mtime = result.metadata.modification_time.seconds
    stat_entry.st_btime = result.metadata.creation_time.seconds

    self.state.stat = stat_entry
    self.state.urn = stat_entry.pathspec.AFF4Path(self.client_urn)

  def Stat(self, responses):
    """Save stat information on the directory."""
    # Did it work?
    if not responses.success:
      raise flow_base.FlowError(
          "Could not stat directory: %s" % responses.status
      )

    # Keep the stat response for later.
    stat_entry = rdf_client_fs.StatEntry(responses.First())
    self.state.stat = stat_entry

    # The full path of the object is the combination of the client_id and the
    # path.
    self.state.urn = stat_entry.pathspec.AFF4Path(self.client_urn)

  def List(self, responses):
    """Collect the directory listing and store in the datastore."""
    if not responses.success:
      raise flow_base.FlowError(str(responses.status))

    self.Log("Listed %s", self.state.urn)

    path_info = rdf_objects.PathInfo.FromStatEntry(self.state.stat)
    data_store.REL_DB.WritePathInfos(
        self.client_id, [mig_objects.ToProtoPathInfo(path_info)]
    )

    stat_entries = list(map(rdf_client_fs.StatEntry, responses))
    WriteStatEntries(stat_entries, client_id=self.client_id)

    for stat_entry in stat_entries:
      self.SendReply(stat_entry)  # Send Stats to parent flows.

  def NotifyAboutEnd(self):
    """Sends a notification that this flow is done."""
    if not self.state.urn:
      super().NotifyAboutEnd()
      return

    st = self.state.stat

    ps_path_type = st.pathspec.last.pathtype
    path_type = rdf_objects.PathInfo.PathTypeFromPathspecPathType(ps_path_type)

    full_path = st.pathspec.CollapsePath()
    path_components = full_path.strip("/").split("/")

    file_ref = objects_pb2.VfsFileReference(
        client_id=self.client_id,
        path_type=path_type,
        path_components=path_components,
    )

    notification.Notify(
        self.creator,
        objects_pb2.UserNotification.Type.TYPE_VFS_LIST_DIRECTORY_COMPLETED,
        f"Listed {full_path}",
        objects_pb2.ObjectReference(
            reference_type=objects_pb2.ObjectReference.Type.VFS_FILE,
            vfs_file=file_ref,
        ),
    )


class RecursiveListDirectoryArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.RecursiveListDirectoryArgs
  rdf_deps = [
      rdf_paths.PathSpec,
  ]


class RecursiveListDirectory(flow_base.FlowBase):
  """Recursively list directory on the client."""

  category = "/Filesystem/"

  args_type = RecursiveListDirectoryArgs
  return_types = (rdf_client_fs.StatEntry,)

  def Start(self):
    """List the initial directory."""
    # The first directory we listed.
    self.state.first_directory = None

    self.state.dir_count = 0
    self.state.file_count = 0

    self.CallClient(
        server_stubs.ListDirectory,
        request=rdf_client_action.ListDirRequest(pathspec=self.args.pathspec),
        next_state=self.ProcessDirectory.__name__,
    )

  def ProcessDirectory(self, responses):
    """Recursively list the directory, and add to the timeline."""
    if responses.success:
      response = responses.First()

      if response is None:
        return

      directory_pathspec = response.pathspec.Dirname()

      urn = directory_pathspec.AFF4Path(self.client_urn)

      self.StoreDirectory(responses)

      if self.state.first_directory is None:
        self.state.first_directory = urn

      # If the urn is too deep we quit to prevent recursion errors.
      relative_name = urn.RelativeName(self.state.first_directory) or ""
      if _Depth(relative_name) >= self.args.max_depth - 1:
        self.Log(
            "Exceeded maximum path depth at %s.",
            urn.RelativeName(self.state.first_directory),
        )
        return

      for stat_response in responses:
        # Queue a list directory for each directory here, but do not follow
        # symlinks.
        is_dir = stat.S_ISDIR(int(stat_response.st_mode))
        if not stat_response.symlink and is_dir:
          self.CallClient(
              server_stubs.ListDirectory,
              request=rdf_client_action.ListDirRequest(
                  pathspec=stat_response.pathspec,
              ),
              next_state=self.ProcessDirectory.__name__,
          )
          self.state.dir_count += 1
          if self.state.dir_count % 100 == 0:  # Log every 100 directories
            self.Log(
                "Reading %s. (%d nodes, %d directories done)",
                urn.RelativeName(self.state.first_directory),
                self.state.file_count,
                self.state.dir_count,
            )

      self.state.file_count += len(responses)

  def StoreDirectory(self, responses):
    """Stores all stat responses."""
    stat_entries = list(map(rdf_client_fs.StatEntry, responses))
    WriteStatEntries(stat_entries, client_id=self.client_id)

    for stat_entry in stat_entries:
      self.SendReply(stat_entry)  # Send Stats to parent flows.

  def NotifyAboutEnd(self):
    status_text = "Recursive Directory Listing complete %d nodes, %d dirs"

    urn = self.state.first_directory
    if not urn:
      try:
        urn = self.args.pathspec.AFF4Path(self.client_urn)
      except ValueError:
        pass

    object_ref = None
    if urn:
      components = urn.Split()
      if len(components) > 3:
        file_ref = objects_pb2.VfsFileReference(
            client_id=components[0],
            path_type=components[2].upper(),
            path_components=components[3:],
        )
      object_ref = objects_pb2.ObjectReference(
          reference_type=objects_pb2.ObjectReference.Type.VFS_FILE,
          vfs_file=file_ref,
      )
    notification.Notify(
        self.creator,
        objects_pb2.UserNotification.Type.TYPE_VFS_RECURSIVE_LIST_DIRECTORY_COMPLETED,
        status_text % (self.state.file_count, self.state.dir_count),
        object_ref,
    )

  def End(self) -> None:
    status_text = "Recursive Directory Listing complete %d nodes, %d dirs"
    self.Log(status_text, self.state.file_count, self.state.dir_count)


def _Depth(relative_path):
  """Calculates the depth of a given path."""
  if not relative_path:
    return 0
  return len(os.path.normpath(relative_path).split("/"))
