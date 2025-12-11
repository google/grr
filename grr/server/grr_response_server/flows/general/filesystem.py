#!/usr/bin/env python
"""These are filesystem related flows."""

from collections.abc import Iterable
import os
import stat
from typing import Optional

from google.protobuf import any_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import mig_client_fs
from grr_response_core.lib.rdfvalues import mig_paths
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import notification
from grr_response_server import rrg_fs
from grr_response_server import rrg_path
from grr_response_server import rrg_stubs
from grr_response_server import server_stubs
from grr_response_server.rdfvalues import mig_objects
from grr_response_server.rdfvalues import objects as rdf_objects
from grr_response_proto.rrg import fs_pb2 as rrg_fs_pb2
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2
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


def WritePartialFileResults(
    client_id: str,
    stat_entry: rdf_client_fs.StatEntry,
    hash_entry: Optional[rdf_crypto.Hash] = None,
) -> None:
  """Persists information about partial file results (without content).

  Args:
    client_id: An id of a client the stat entries come from.
    stat_entry: A `StatEntry` instance.
    hash_entry: An optional `Hash` instance.
  """
  if stat_entry.pathspec.last.stream_name:
    # This is an ADS. In this case we always need to create a file or
    # we won't be able to access the data. New clients send the correct mode
    # already but to make sure, we set this to a regular file anyways.
    # Clear all file type bits:
    stat_entry.st_mode &= ~stat_type_mask
    stat_entry.st_mode |= stat.S_IFREG

  path_info = rdf_objects.PathInfo.FromStatEntry(stat_entry)
  if hash_entry:
    path_info.hash_entry = hash_entry

  data_store.REL_DB.WritePathInfos(
      client_id, [mig_objects.ToProtoPathInfo(path_info)]
  )


class ListDirectoryArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.ListDirectoryArgs
  rdf_deps = [
      rdf_paths.PathSpec,
  ]


class ListDirectory(
    flow_base.FlowBase[
        flows_pb2.ListDirectoryArgs,
        flows_pb2.ListDirectoryStore,
        flows_pb2.DefaultFlowProgress,
    ]
):
  """List files in a directory."""

  category = "/Filesystem/"
  args_type = ListDirectoryArgs
  behaviours = flow_base.BEHAVIOUR_ADVANCED
  result_types = (rdf_client_fs.StatEntry,)

  proto_args_type = flows_pb2.ListDirectoryArgs
  proto_result_types = (jobs_pb2.StatEntry,)
  proto_store_type = flows_pb2.ListDirectoryStore
  only_protos_allowed = True

  def Start(self):
    """Issue a request to list the directory."""
    if (
        self.rrg_support
        and self.proto_args.pathspec.pathtype == rdf_paths.PathSpec.PathType.OS
    ):
      path_raw_bytes = self.proto_args.pathspec.path.encode("utf-8")  # pytype: disable=attribute-error

      # TODO: Sometimes GRR "fixes" Windows paths and inserts a
      # leading '/' in front (e.g. to have `/C:/Windows`). RRG does not treat it
      # as a valid absolute path and so we need to "unfix" it here.
      #
      # We should fix GRR not to do this path fixing.
      if self.rrg_os_type == rrg_os_pb2.WINDOWS:
        path_raw_bytes = path_raw_bytes.removeprefix(b"/")

      action = rrg_stubs.GetFileMetadata()
      action.args.paths.add().raw_bytes = path_raw_bytes
      action.args.max_depth = 1
      action.Call(self.HandleRRGGetFileMetadata)
    else:
      request = jobs_pb2.GetFileStatRequest(
          pathspec=self.proto_args.pathspec,
          follow_symlink=True,
      )
      self.CallClientProto(
          server_stubs.GetFileStat,
          request,
          next_state=self.Stat.__name__,
      )

      # We use data to pass the path to the callback:
      self.CallClientProto(
          server_stubs.ListDirectory,
          jobs_pb2.ListDirRequest(pathspec=self.proto_args.pathspec),
          next_state=self.List.__name__,
      )

  @flow_base.UseProto2AnyResponses
  def HandleRRGGetFileMetadata(
      self,
      responses_any: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses_any.success or not responses_any:
      message = f"File metadata collection failure: {responses_any.status}"
      raise flow_base.FlowError(message)

    responses: list[rrg_get_file_metadata_pb2.Result] = []

    for response_any in responses_any:
      response = rrg_get_file_metadata_pb2.Result()
      response.ParseFromString(response_any.value)

      responses.append(response)

    responses.sort(key=lambda _: _.path.raw_bytes)
    response_dir, *responses = responses

    dir_path = rrg_path.PurePath.For(self.rrg_os_type, response_dir.path)
    dir_symlink = rrg_path.PurePath.For(self.rrg_os_type, response_dir.symlink)

    path_info_dir = rrg_fs.PathInfo(response_dir.metadata)
    path_info_dir.path_type = objects_pb2.PathInfo.PathType.OS
    path_info_dir.components.extend(dir_path.components)
    path_info_dir.stat_entry.pathspec.pathtype = jobs_pb2.PathSpec.PathType.OS
    path_info_dir.stat_entry.pathspec.path = str(dir_path)

    if response_dir.symlink.raw_bytes:
      if responses:
        raise flow_base.FlowError(
            f"Unexpected responses for symlink: {responses}",
        )

      path_info_dir.stat_entry.symlink = str(dir_symlink)

      # We are dealing with a symlink, so we it means we need to list contents
      # of the folder it points to. Note that it may point to another symlink
      # (or even form a cycle), so we put a limit on a depth of such recursion.
      self.store.symlink_depth += 1
      if self.store.symlink_depth > _SYMLINK_DEPTH_LIMIT:
        raise flow_base.FlowError(
            f"Symlink depth reached: {_SYMLINK_DEPTH_LIMIT}",
        )

      self.Log("Found symlink, listing '%s'", dir_symlink)

      get_file_metadata = rrg_stubs.GetFileMetadata()
      get_file_metadata.args.paths.add().raw_bytes = bytes(
          (dir_path.parent / dir_symlink).normal
      )
      get_file_metadata.args.max_depth = 1
      get_file_metadata.Call(self.HandleRRGGetFileMetadata)

    if response_dir.metadata.type not in [
        rrg_fs_pb2.FileMetadata.Type.DIR,
        rrg_fs_pb2.FileMetadata.Type.SYMLINK,
    ]:
      raise flow_base.FlowError(f"Unexpected file type in: {response_dir}")

    self.store.stat_entry.CopyFrom(path_info_dir.stat_entry)
    self.store.urn = str(
        mig_client_fs.ToRDFStatEntry(path_info_dir.stat_entry).AFF4Path(
            self.client_urn
        )
    )

    path_infos = [path_info_dir]

    for response in responses:
      path = rrg_path.PurePath.For(self.rrg_os_type, response.path)
      symlink = rrg_path.PurePath.For(self.rrg_os_type, response.symlink)

      path_info = rrg_fs.PathInfo(response.metadata)
      path_info.path_type = objects_pb2.PathInfo.PathType.OS
      path_info.components.extend(path.components)
      path_info.stat_entry.pathspec.pathtype = jobs_pb2.PathSpec.PathType.OS
      path_info.stat_entry.pathspec.path = str(path)
      # TODO: Fix path separator in stat entries.
      if self.rrg_os_type == rrg_os_pb2.WINDOWS:
        path_info.stat_entry.pathspec.path = str(path).replace("\\", "/")

      if response.symlink.raw_bytes:
        path_info.stat_entry.symlink = str(symlink)

      self.SendReplyProto(path_info.stat_entry)
      path_infos.append(path_info)

    data_store.REL_DB.WritePathInfos(self.client_id, path_infos)

  @flow_base.UseProto2AnyResponses
  def Stat(self, responses: flow_responses.Responses[any_pb2.Any]) -> None:
    """Save stat information on the directory."""
    # Did it work?
    if not responses.success or len(list(responses)) < 1:
      raise flow_base.FlowError(
          "Could not stat directory: %s" % responses.status
      )
    # Keep the stat response for later.
    stat_entry = jobs_pb2.StatEntry()
    stat_entry.ParseFromString(list(responses)[0].value)
    self.store.stat_entry.CopyFrom(stat_entry)

    # The full path of the object is the combination of the client_id and the
    # path.
    self.store.urn = str(
        mig_client_fs.ToRDFStatEntry(stat_entry).AFF4Path(self.client_urn)
    )

  @flow_base.UseProto2AnyResponses
  def List(self, responses: flow_responses.Responses[any_pb2.Any]) -> None:
    """Collect the directory listing and store in the datastore."""
    if not responses.success:
      raise flow_base.FlowError(str(responses.status))

    self.Log("Listed %s", self.store.urn)

    # TODO: Get proto path info from proto stat entry.
    path_info = rdf_objects.PathInfo.FromStatEntry(
        mig_client_fs.ToRDFStatEntry(self.store.stat_entry)
    )
    data_store.REL_DB.WritePathInfos(
        self.client_id, [mig_objects.ToProtoPathInfo(path_info)]
    )

    rdf_stat_entries = []
    for response_any in responses:
      stat_entry = jobs_pb2.StatEntry()
      stat_entry.ParseFromString(response_any.value)
      self.SendReplyProto(stat_entry)
      rdf_stat_entries.append(mig_client_fs.ToRDFStatEntry(stat_entry))
    WriteStatEntries(rdf_stat_entries, client_id=self.client_id)

  def NotifyAboutEnd(self):
    """Sends a notification that this flow is done."""
    if not self.store.urn:
      super().NotifyAboutEnd()
      return

    st = mig_client_fs.ToRDFStatEntry(self.store.stat_entry)

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


class RecursiveListDirectory(
    flow_base.FlowBase[
        flows_pb2.RecursiveListDirectoryArgs,
        flows_pb2.RecursiveListDirectoryStore,
        flows_pb2.RecursiveListDirectoryProgress,
    ]
):
  """Recursively list directory on the client."""

  category = "/Filesystem/"

  args_type = RecursiveListDirectoryArgs
  result_types = (rdf_client_fs.StatEntry,)
  proto_args_type = flows_pb2.RecursiveListDirectoryArgs
  proto_result_types = (jobs_pb2.StatEntry,)
  proto_store_type = flows_pb2.RecursiveListDirectoryStore
  proto_progress_type = flows_pb2.RecursiveListDirectoryProgress
  only_protos_allowed = True

  def Start(self):
    """List the initial directory."""
    # The first directory we listed.
    self.store.first_directory = ""

    self.progress.dir_count = 0
    self.progress.file_count = 0

    self.CallClientProto(
        server_stubs.ListDirectory,
        jobs_pb2.ListDirRequest(pathspec=self.proto_args.pathspec),
        next_state=self.ProcessDirectory.__name__,
    )

  @flow_base.UseProto2AnyResponses
  def ProcessDirectory(
      self, responses: flow_responses.Responses[any_pb2.Any]
  ) -> None:
    """Recursively list the directory, and add to the timeline."""
    if not responses.success or len(list(responses)) < 1:
      return

    first_proto = jobs_pb2.StatEntry()
    first_proto.ParseFromString(list(responses)[0].value)
    first_rdf = mig_client_fs.ToRDFStatEntry(first_proto)
    directory_pathspec = first_rdf.pathspec.Dirname()
    urn = directory_pathspec.AFF4Path(self.client_urn)

    # Store directory.
    rdf_stat_entries = []
    proto_stat_entries = []
    for response_any in responses:
      stat_entry = jobs_pb2.StatEntry()
      stat_entry.ParseFromString(response_any.value)
      self.SendReplyProto(stat_entry)
      proto_stat_entries.append(stat_entry)
      rdf_stat_entries.append(mig_client_fs.ToRDFStatEntry(stat_entry))
    WriteStatEntries(rdf_stat_entries, client_id=self.client_id)

    if not self.store.first_directory:
      self.store.first_directory = str(urn)

    # If the urn is too deep we quit to prevent recursion errors.
    relative_name = urn.RelativeName(self.store.first_directory) or ""
    if _Depth(relative_name) >= self.proto_args.max_depth - 1:
      self.Log(
          "Exceeded maximum path depth at %s.",
          urn.RelativeName(self.store.first_directory),
      )
      return

    for stat_response in proto_stat_entries:
      # Queue a list directory for each directory here, but do not follow
      # symlinks.
      is_dir = stat.S_ISDIR(int(stat_response.st_mode))
      if not stat_response.symlink and is_dir:
        self.CallClientProto(
            server_stubs.ListDirectory,
            jobs_pb2.ListDirRequest(
                pathspec=stat_response.pathspec,
            ),
            next_state=self.ProcessDirectory.__name__,
        )
        self.progress.dir_count += 1
        if self.progress.dir_count % 100 == 0:  # Log every 100 directories
          self.Log(
              "Reading %s. (%d nodes, %d directories done)",
              urn.RelativeName(self.store.first_directory),
              self.progress.file_count,
              self.progress.dir_count,
          )

    self.progress.file_count += len(responses)

  def NotifyAboutEnd(self):
    status_text = "Recursive Directory Listing complete %d nodes, %d dirs"

    urn = rdfvalue.RDFURN(self.store.first_directory)
    if not self.store.first_directory:
      try:
        urn = mig_paths.ToRDFPathSpec(self.proto_args.pathspec).AFF4Path(
            self.client_urn
        )
      except ValueError:
        pass

    object_ref = None
    if urn:
      components = urn.Split()
      object_ref = objects_pb2.ObjectReference(
          reference_type=objects_pb2.ObjectReference.Type.VFS_FILE,
      )
      if len(components) > 3:
        file_ref = objects_pb2.VfsFileReference(
            client_id=components[0],
            path_type=components[2].upper(),
            path_components=components[3:],
        )
        object_ref.vfs_file.CopyFrom(file_ref)

    notification.Notify(
        self.creator,
        objects_pb2.UserNotification.Type.TYPE_VFS_RECURSIVE_LIST_DIRECTORY_COMPLETED,
        status_text % (self.progress.file_count, self.progress.dir_count),
        object_ref,
    )

  def End(self) -> None:
    status_text = "Recursive Directory Listing complete %d nodes, %d dirs"
    self.Log(status_text, self.progress.file_count, self.progress.dir_count)

  def GetProgressProto(self) -> flows_pb2.RecursiveListDirectoryProgress:
    return self.progress


def _Depth(relative_path: str) -> int:
  """Calculates the depth of a given path."""
  if not relative_path:
    return 0
  return len(os.path.normpath(relative_path).split("/"))


_SYMLINK_DEPTH_LIMIT = 3
