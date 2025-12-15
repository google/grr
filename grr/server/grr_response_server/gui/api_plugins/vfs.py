#!/usr/bin/env python
"""API handlers for dealing with files in a client's virtual file system."""

from collections.abc import Collection, Iterable, Iterator, Sequence
import csv
import io
import itertools
import os
import re
import stat
from typing import Optional
import zipfile

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import text
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_proto.api import vfs_pb2
from grr_response_server import data_store
from grr_response_server import data_store_utils
from grr_response_server import file_store
from grr_response_server import flow
from grr_response_server import notification
from grr_response_server.databases import db
from grr_response_server.flows.general import filesystem
from grr_response_server.flows.general import mig_filesystem
from grr_response_server.flows.general import mig_transfer
from grr_response_server.flows.general import transfer
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.rdfvalues import mig_objects
from grr_response_server.rdfvalues import objects as rdf_objects

# Files can only be accessed if their first path component is from this list.
_ROOT_FILES_ALLOWLIST = ["fs", "registry", "temp"]


def ValidateVfsPath(path: str) -> None:
  """Validates a VFS path."""

  components = (path or "").lstrip("/").split("/")
  if not components:
    raise ValueError("Empty path is not a valid path: %s." % path)

  if components[0] not in _ROOT_FILES_ALLOWLIST:
    raise ValueError(
        "First path component was '%s', but has to be one of %s"
        % (components[0], ", ".join(_ROOT_FILES_ALLOWLIST))
    )


# TODO(hanuszczak): Fix the linter warning properly.
class FileNotFoundError(api_call_handler_base.ResourceNotFoundError):  # pylint: disable=redefined-builtin
  """Raised when a certain file is not found.

  Attributes:
    client_id: An id of the client for which the file was not found.
    path_type: A type of the path for which the file was not found.
    components: Components of the path for which the file was not found.
  """

  def __init__(self, client_id, path_type, components):
    self.client_id = client_id
    self.path_type = path_type
    self.components = components

    path = "/" + "/".join(components)

    message = "{path_type} path '{path}' for client '{client_id}' not found"
    message = message.format(
        client_id=client_id, path_type=path_type, path=path
    )
    super().__init__(message)


class FileContentNotFoundError(api_call_handler_base.ResourceNotFoundError):
  """Raised when the content for a specific file could not be found.

  Attributes:
    client_id: An id of the client for which the file content was not found.
    path_type: A type of the path for which the file content was not found.
    components: Components of the path for which the file content was not found.
    timestamp: A timestamp of the file which content was not found.
  """

  def __init__(self, client_id, path_type, components, timestamp=None):
    self.client_id = client_id
    self.path_type = path_type
    self.components = components
    self.timestamp = timestamp

    path = "/" + "/".join(components)

    if timestamp is None:
      message = "Content for {} file with path '{}' for client '{}' not found"
      message = message.format(path_type, path, client_id)
    else:
      message = (
          "Content for {} file with path '{}' and timestamp '{}' for "
          "client '{}' not found"
      )
      message = message.format(path_type, path, timestamp, client_id)

    super().__init__(message)


class VfsRefreshOperationNotFoundError(
    api_call_handler_base.ResourceNotFoundError
):
  """Raised when a vfs refresh operation could not be found."""


class VfsFileContentUpdateNotFoundError(
    api_call_handler_base.ResourceNotFoundError
):
  """Raised when a file content update operation could not be found."""


class ApiAff4ObjectAttributeValue(rdf_structs.RDFProtoStruct):
  protobuf = vfs_pb2.ApiAff4ObjectAttributeValue
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]

  def GetValueClass(self):
    try:
      return rdfvalue.RDFValue.GetPlugin(self.type)
    except KeyError:
      raise ValueError("No class found for type %s." % self.type)


class ApiAff4ObjectAttribute(rdf_structs.RDFProtoStruct):
  protobuf = vfs_pb2.ApiAff4ObjectAttribute
  rdf_deps = [
      ApiAff4ObjectAttributeValue,
  ]


class ApiAff4ObjectType(rdf_structs.RDFProtoStruct):
  """A representation of parts of an Aff4Object.

  ApiAff4ObjectType represents a subset of all attributes of an Aff4Object
  defined by a certain class of the inheritance hierarchy of the Aff4Object.
  """

  protobuf = vfs_pb2.ApiAff4ObjectType
  rdf_deps = [
      ApiAff4ObjectAttribute,
  ]


class ApiAff4ObjectRepresentation(rdf_structs.RDFProtoStruct):
  """A proto-based representation of an Aff4Object used to render responses.

  ApiAff4ObjectRepresentation contains all attributes of an Aff4Object,
  structured by type. If an attribute is found multiple times, it is only
  added once at the type where it is first encountered.
  """

  protobuf = vfs_pb2.ApiAff4ObjectRepresentation
  rdf_deps = [
      ApiAff4ObjectType,
  ]


class ApiFile(rdf_structs.RDFProtoStruct):
  protobuf = vfs_pb2.ApiFile
  rdf_deps = [
      ApiAff4ObjectRepresentation,
      rdf_crypto.Hash,
      rdfvalue.RDFDatetime,
      rdf_client_fs.StatEntry,
  ]

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    try:
      self.age = kwargs["age"]
    except KeyError:
      self.age = rdfvalue.RDFDatetime.Now()


# TODO: Reassess and migrate to proto-based implementation.
def _GenerateApiFileDetails(
    path_infos: Sequence[rdf_objects.PathInfo],
) -> ApiAff4ObjectRepresentation:
  """Generate file details based on path infos history."""

  type_attrs = []
  hash_attrs = []
  size_attrs = []
  stat_attrs = []
  pathspec_attrs = []

  def _Value(age, value):
    """Generate ApiAff4ObjectAttributeValue from an age and a value."""

    v = ApiAff4ObjectAttributeValue(age=age)
    # With dynamic values we first have to set the type and
    # then the value itself.
    # TODO(user): refactor dynamic values logic so that it's not needed,
    # possibly just removing the "type" attribute completely.
    v.Set("type", value.__class__.__name__)
    v.value = value
    return v

  for pi in path_infos:
    if pi.directory:
      object_type = "VFSDirectory"
    else:
      object_type = "VFSFile"

    type_attrs.append(_Value(pi.timestamp, rdfvalue.RDFString(object_type)))

    if pi.hash_entry:
      hash_attrs.append(_Value(pi.timestamp, pi.hash_entry))
      size_attrs.append(
          _Value(pi.timestamp, rdfvalue.RDFInteger(pi.hash_entry.num_bytes))
      )
    if pi.stat_entry:
      stat_attrs.append(_Value(pi.timestamp, pi.stat_entry))

      if pi.stat_entry.pathspec:
        pathspec_attrs.append(_Value(pi.timestamp, pi.stat_entry.pathspec))

  return ApiAff4ObjectRepresentation(
      types=[
          ApiAff4ObjectType(
              name="AFF4Object",
              attributes=[
                  ApiAff4ObjectAttribute(
                      name="TYPE",
                      values=type_attrs,
                  ),
              ],
          ),
          ApiAff4ObjectType(
              name="AFF4Stream",
              attributes=[
                  ApiAff4ObjectAttribute(
                      name="HASH",
                      values=hash_attrs,
                  ),
                  ApiAff4ObjectAttribute(
                      name="SIZE",
                      values=size_attrs,
                  ),
              ],
          ),
          ApiAff4ObjectType(
              name="VFSFile",
              attributes=[
                  ApiAff4ObjectAttribute(
                      name="PATHSPEC",
                      values=pathspec_attrs,
                  ),
                  ApiAff4ObjectAttribute(
                      name="STAT",
                      values=stat_attrs,
                  ),
              ],
          ),
      ]
  )


class ApiGetFileDetailsHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves the details of a given file."""

  proto_args_type = vfs_pb2.ApiGetFileDetailsArgs
  proto_result_type = vfs_pb2.ApiGetFileDetailsResult

  def Handle(
      self,
      args: vfs_pb2.ApiGetFileDetailsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> vfs_pb2.ApiGetFileDetailsResult:
    ValidateVfsPath(args.file_path)

    # Directories are not really "files" so they cannot be stored in the
    # database but they still can be queried so we need to return something.
    # Sometimes they contain a trailing slash so we need to take care of that.
    #
    # TODO(hanuszczak): Require VFS paths to be normalized so that trailing
    # slash is either forbidden or mandatory.
    if args.file_path.endswith("/"):
      args.file_path = args.file_path[:-1]
    if args.file_path in [
        "fs",
        "registry",
        "temp",
        "fs/os",
        "fs/tsk",
        "fs/ntfs",
    ]:
      api_file = vfs_pb2.ApiFile(
          name=args.file_path,
          path=args.file_path,
          is_directory=True,
          details=ToProtoApiAff4ObjectRepresentation(
              _GenerateApiFileDetails([])
          ),
      )
      return vfs_pb2.ApiGetFileDetailsResult(file=api_file)

    path_type, components = rdf_objects.ParseCategorizedPath(args.file_path)
    args_timestamp = None
    if args.HasField("timestamp"):
      args_timestamp = rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
          args.timestamp
      )
    try:
      path_info = data_store.REL_DB.ReadPathInfo(
          client_id=args.client_id,
          path_type=path_type,
          components=components,
          timestamp=args_timestamp,
      )
    except db.UnknownPathError as ex:
      raise FileNotFoundError(
          client_id=args.client_id, path_type=path_type, components=components
      ) from ex

    client_path = db.ClientPath.FromPathInfo(args.client_id, path_info)
    last_collection_pi = (
        data_store.REL_DB.ReadLatestPathInfosWithHashBlobReferences(
            [client_path],
            max_timestamp=args_timestamp,
        )[client_path]
    )

    history = data_store.REL_DB.ReadPathInfoHistory(
        client_id=args.client_id,
        path_type=path_type,
        components=components,
        cutoff=args_timestamp,
    )
    history.reverse()

    # It might be the case that we do not have any history about the file, but
    # we have some information because it is an implicit path.
    if not history:
      history = [path_info]
    history = [mig_objects.ToRDFPathInfo(pi) for pi in history]
    file_obj = vfs_pb2.ApiFile(
        name=components[-1],
        path=rdf_objects.ToCategorizedPath(path_type, components),
        stat=path_info.stat_entry,
        hash=path_info.hash_entry,
        details=ToProtoApiAff4ObjectRepresentation(
            _GenerateApiFileDetails(history)
        ),
        is_directory=path_info.directory,
        age=path_info.timestamp,
    )

    if last_collection_pi:
      file_obj.last_collected = last_collection_pi.timestamp
      file_obj.last_collected_size = last_collection_pi.hash_entry.num_bytes

    return vfs_pb2.ApiGetFileDetailsResult(file=file_obj)


def _PathInfoToApiFile(path_info: objects_pb2.PathInfo) -> vfs_pb2.ApiFile:
  """Converts a PathInfo to an ApiFile."""
  if path_info.path_type == objects_pb2.PathInfo.PathType.OS:
    prefix = "fs/os/"
  elif path_info.path_type == objects_pb2.PathInfo.PathType.TSK:
    prefix = "fs/tsk/"
  elif path_info.path_type == objects_pb2.PathInfo.PathType.NTFS:
    prefix = "fs/ntfs/"
  elif path_info.path_type == objects_pb2.PathInfo.PathType.REGISTRY:
    prefix = "registry/"
  elif path_info.path_type == objects_pb2.PathInfo.PathType.TEMP:
    prefix = "temp/"
  else:
    raise ValueError(f"Unknown PathType {path_info.path_type}")

  api_file = vfs_pb2.ApiFile(
      name=path_info.components[-1] if path_info.components else "",
      path=prefix + "/".join(path_info.components),
      # TODO(hanuszczak): `PathInfo#directory` tells us whether given path has
      # ever been observed as a directory. Is this what we want here or should
      # we use `st_mode` information instead?
      is_directory=path_info.directory,
      age=path_info.timestamp,
  )

  if path_info.HasField("stat_entry"):
    api_file.stat.CopyFrom(path_info.stat_entry)

  if path_info.HasField("last_hash_entry_timestamp"):
    api_file.last_collected = path_info.last_hash_entry_timestamp
    api_file.last_collected_size = path_info.hash_entry.num_bytes

  return api_file


class ApiListFilesHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves the child files for a given file."""

  proto_args_type = vfs_pb2.ApiListFilesArgs
  proto_result_type = vfs_pb2.ApiListFilesResult

  def _GetRootChildren(
      self,
      args: vfs_pb2.ApiListFilesArgs,
  ) -> vfs_pb2.ApiListFilesResult:

    items = []

    fs_item = vfs_pb2.ApiFile()
    fs_item.name = "fs"
    fs_item.path = "fs"
    fs_item.is_directory = True
    items.append(fs_item)

    temp_item = vfs_pb2.ApiFile()
    temp_item.name = "temp"
    temp_item.path = "temp"
    temp_item.is_directory = True
    items.append(temp_item)

    if data_store_utils.GetClientOs(args.client_id) == "Windows":
      registry_item = vfs_pb2.ApiFile()
      registry_item.name = "registry"
      registry_item.path = "registry"
      registry_item.is_directory = True
      items.append(registry_item)

    if args.count:
      items = items[args.offset : args.offset + args.count]
    else:
      items = items[args.offset :]

    return vfs_pb2.ApiListFilesResult(items=items)

  def _GetFilesystemChildren(
      self, args: vfs_pb2.ApiListFilesArgs
  ) -> vfs_pb2.ApiListFilesResult:
    items = []

    ntfs_item = vfs_pb2.ApiFile()
    ntfs_item.name = "ntfs"
    ntfs_item.path = "fs/ntfs"
    ntfs_item.is_directory = True
    items.append(ntfs_item)

    os_item = vfs_pb2.ApiFile()
    os_item.name = "os"
    os_item.path = "fs/os"
    os_item.is_directory = True
    items.append(os_item)

    tsk_item = vfs_pb2.ApiFile()
    tsk_item.name = "tsk"
    tsk_item.path = "fs/tsk"
    tsk_item.is_directory = True
    items.append(tsk_item)

    if args.count:
      items = items[args.offset : args.offset + args.count]
    else:
      items = items[args.offset :]

    return vfs_pb2.ApiListFilesResult(items=items)

  def Handle(
      self,
      args: vfs_pb2.ApiListFilesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> vfs_pb2.ApiListFilesResult:
    if not args.file_path or args.file_path == "/":
      return self._GetRootChildren(args)

    if args.file_path == "fs":
      return self._GetFilesystemChildren(args)

    path_type, components = rdf_objects.ParseCategorizedPath(args.file_path)
    args_timestamp = None
    if args.HasField("timestamp"):
      args_timestamp = rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
          args.timestamp
      )
    # TODO: This API handler should return a 404 response if the
    # path is not found. Currently, 500 is returned.
    child_path_infos = data_store.REL_DB.ListChildPathInfos(
        client_id=args.client_id,
        path_type=path_type,
        components=components,
        timestamp=args_timestamp,
    )

    items = []

    for child_path_info in child_path_infos:
      if args.directories_only and not child_path_info.directory:
        continue
      items.append(_PathInfoToApiFile(child_path_info))

    # TODO(hanuszczak): Instead of getting the whole list from the database and
    # then filtering the results we should do the filtering directly in the
    # database query.
    if args.filter:
      pattern = re.compile(args.filter, re.IGNORECASE)
      is_matching = lambda item: pattern.search(item.name)
      items = list(filter(is_matching, items))

    items.sort(key=lambda item: item.path)

    if args.count:
      items = items[args.offset : args.offset + args.count]
    else:
      items = items[args.offset :]

    return vfs_pb2.ApiListFilesResult(items=items)


class ApiBrowseFilesystemHandler(api_call_handler_base.ApiCallHandler):
  """List OS, TSK, NTFS files & directories in a given VFS directory."""

  proto_args_type = vfs_pb2.ApiBrowseFilesystemArgs
  proto_result_type = vfs_pb2.ApiBrowseFilesystemResult

  def Handle(
      self,
      args: vfs_pb2.ApiBrowseFilesystemArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> vfs_pb2.ApiBrowseFilesystemResult:
    del context  # Unused.

    timestamp = (
        rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(args.timestamp)
        if args.HasField("timestamp")
        else None
    )

    last_components = rdf_objects.ParsePath(args.path)

    path_types_to_query = {
        objects_pb2.PathInfo.PathType.OS,
        objects_pb2.PathInfo.PathType.TSK,
        objects_pb2.PathInfo.PathType.NTFS,
    }

    result = vfs_pb2.ApiBrowseFilesystemResult()

    if args.include_directory_tree:
      all_components = self._GetDirectoryTree(last_components)
    else:
      all_components = [last_components]

    root = self._GetDirectory(
        args.client_id, path_types_to_query, all_components[0], timestamp
    )
    if root:
      result.root_entry.file.CopyFrom(root)
    parent = result.root_entry
    for depth, cur_components in enumerate(all_components):
      if depth > 0:
        for child in parent.children:
          if child.file.name == cur_components[-1]:
            parent = child
            break
      if parent is None:
        # The listing of the parent directory does not contain the
        # requested path component.
        break
      path_types_to_query, children = self._ListDirectory(
          args.client_id,
          path_types_to_query,
          cur_components,
          timestamp,
      )

      if children is None:
        # When the current directory was not found, stop querying because
        # no transitive children can possibly exist.
        break

      for file in children:
        child = parent.children.add()
        child.file.CopyFrom(file)

    return result

  def _GetDirectoryTree(
      self, components: Collection[str]
  ) -> Iterable[Collection[str]]:
    result = [[]]  # First, include the root folder "/".
    for i in range(len(components)):
      result.append(components[: i + 1])
    return result

  def _MergePathInfos(
      self,
      path_infos: dict[str, objects_pb2.PathInfo],
      cur_path_infos: Collection[objects_pb2.PathInfo],
  ) -> None:
    """Merges PathInfos from different PathTypes (OS, TSK, NTFS)."""

    for pi in cur_path_infos:
      existing = path_infos.get(pi.components[-1] if pi.components else "")
      # If the VFS has the same file in two PathTypes, use the latest collected
      # version.

      if (
          existing is None
          or not existing.HasField("timestamp")
          or (pi.HasField("timestamp") and existing.timestamp < pi.timestamp)
      ):
        path_infos[pi.components[-1] if pi.components else ""] = pi

  def _GetDirectory(
      self,
      client_id: str,
      path_types: Collection["objects_pb2.PathInfo.PathType"],
      components: Collection[str],
      timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> Optional[vfs_pb2.ApiFile]:
    path_infos: dict[str, objects_pb2.PathInfo] = {}

    for path_type in path_types:
      try:
        cur_path_info = data_store.REL_DB.ReadPathInfo(
            client_id=client_id,
            path_type=path_type,
            components=components,
            timestamp=timestamp,
        )
      except (db.UnknownPathError, db.NotDirectoryPathError):
        continue

      self._MergePathInfos(path_infos, [cur_path_info])

    api_files = [_PathInfoToApiFile(pi) for pi in path_infos.values()]
    return api_files[0] if api_files else None

  def _ListDirectory(
      self,
      client_id: str,
      path_types: Collection["objects_pb2.PathInfo.PathType"],
      components: Collection[str],
      timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> tuple[
      set["objects_pb2.PathInfo.PathType"],
      Optional[Collection[vfs_pb2.ApiFile]],
  ]:
    path_infos: dict[str, objects_pb2.PathInfo] = {}
    existing_path_types = set(path_types)

    for path_type in path_types:
      try:
        cur_path_infos = data_store.REL_DB.ListChildPathInfos(
            client_id=client_id,
            path_type=path_type,
            components=components,
            timestamp=timestamp,
        )

      except (db.UnknownPathError, db.NotDirectoryPathError):
        # Whenever a directory cannot be found with a given PathType, we remove
        # this PathType from the list of existing PathTypes to not wastefully
        # try to load children of a folder whose parent is known to not exist.
        existing_path_types.remove(path_type)
        continue

      self._MergePathInfos(path_infos, cur_path_infos)

    if existing_path_types:
      api_files = [_PathInfoToApiFile(pi) for pi in path_infos.values()]
      api_files.sort(key=lambda api_file: api_file.name)
      return existing_path_types, api_files
    else:
      return existing_path_types, None


class ApiGetFileTextHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves the text for a given file."""

  proto_args_type = vfs_pb2.ApiGetFileTextArgs
  proto_result_type = vfs_pb2.ApiGetFileTextResult

  def _Decode(self, codec_name, data):
    """Decode data with the given codec name."""
    try:
      return data.decode(codec_name, "replace")
    except LookupError as e:
      raise RuntimeError("Codec could not be found.") from e
    except AssertionError as e:
      raise RuntimeError("Codec failed to decode") from e

  def Handle(
      self,
      args: vfs_pb2.ApiGetFileTextArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> vfs_pb2.ApiGetFileTextResult:
    ValidateVfsPath(args.file_path)

    path_type, components = rdf_objects.ParseCategorizedPath(args.file_path)
    client_path = db.ClientPath(str(args.client_id), path_type, components)

    timestamp = None
    if args.HasField("timestamp"):
      timestamp = rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
          args.timestamp
      )

    try:
      fd = file_store.OpenFile(client_path, max_timestamp=timestamp)
    except file_store.FileHasNoContentError as e:
      raise FileContentNotFoundError(
          args.client_id, path_type, components, timestamp
      ) from e

    fd.seek(args.offset)
    # No need to protect against args.length == 0 case and large files:
    # file_store logic has all necessary checks in place.
    byte_content = fd.read(args.length or None)

    if args.encoding:
      encoding = args.encoding
    else:
      encoding = vfs_pb2.ApiGetFileTextArgs.Encoding.UTF_8

    encoding_str = vfs_pb2.ApiGetFileTextArgs.Encoding.Name(encoding).lower()
    text_content = self._Decode(encoding_str, byte_content)

    return vfs_pb2.ApiGetFileTextResult(
        total_size=fd.size, content=text_content
    )


class ApiGetFileBlobHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves the byte content for a given file."""

  proto_args_type = vfs_pb2.ApiGetFileBlobArgs

  CHUNK_SIZE = 1024 * 1024 * 4

  def _GenerateFile(self, file_obj, offset, length):
    file_obj.seek(offset)
    for start in range(offset, offset + length, self.CHUNK_SIZE):
      yield file_obj.read(min(self.CHUNK_SIZE, offset + length - start))

  def _WrapContentGenerator(
      self,
      generator: Iterable[bytes],
      args: vfs_pb2.ApiGetFileBlobArgs,
      username: str,
  ) -> Iterator[bytes]:
    try:
      for item in generator:
        yield item
    except Exception as e:
      path_type, components = rdf_objects.ParseCategorizedPath(args.file_path)
      vfs_file_ref = objects_pb2.VfsFileReference(
          client_id=args.client_id,
          path_type=path_type,
          path_components=components,
      )
      object_reference = objects_pb2.ObjectReference(
          reference_type=objects_pb2.ObjectReference.Type.VFS_FILE,
          vfs_file=vfs_file_ref,
      )

      notification.Notify(
          username,
          objects_pb2.UserNotification.Type.TYPE_FILE_BLOB_FETCH_FAILED,
          "File blob fetch failed for path %s on client %s: %s"
          % (args.client_id, args.file_path, e),
          object_reference,
      )
      raise

  def Handle(
      self,
      args: vfs_pb2.ApiGetFileBlobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_call_handler_base.ApiBinaryStream:
    assert context is not None
    ValidateVfsPath(args.file_path)

    path_type, components = rdf_objects.ParseCategorizedPath(args.file_path)
    client_path = db.ClientPath(args.client_id, path_type, components)

    timestamp = None
    if args.HasField("timestamp"):
      timestamp = rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
          args.timestamp
      )

    try:
      file_obj = file_store.OpenFile(client_path, max_timestamp=timestamp)
    except file_store.FileNotFoundError as e:
      raise FileNotFoundError(args.client_id, path_type, components) from e
    except file_store.FileHasNoContentError as e:
      raise FileContentNotFoundError(
          args.client_id, path_type, components, timestamp
      ) from e

    size = max(0, file_obj.size - args.offset)
    if args.length and args.length < size:
      size = args.length

    generator = self._WrapContentGenerator(
        self._GenerateFile(file_obj, args.offset, size), args, context.username
    )
    return api_call_handler_base.ApiBinaryStream(
        filename=components[-1],
        content_generator=generator,
        content_length=size,
    )


class ApiGetFileVersionTimesHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves the list of version times of the given file."""

  proto_args_type = vfs_pb2.ApiGetFileVersionTimesArgs
  proto_result_type = vfs_pb2.ApiGetFileVersionTimesResult

  def Handle(
      self,
      args: vfs_pb2.ApiGetFileVersionTimesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> vfs_pb2.ApiGetFileVersionTimesResult:
    del context  # unused
    ValidateVfsPath(args.file_path)

    try:
      path_type, components = rdf_objects.ParseCategorizedPath(
          args.file_path.rstrip("/")
      )
    except ValueError:
      # If the path does not point to a file (i.e. "fs"), just return an
      # empty response.
      return vfs_pb2.ApiGetFileVersionTimesResult()

    history = data_store.REL_DB.ReadPathInfoHistory(
        str(args.client_id), path_type, components
    )
    times = reversed([pi.timestamp for pi in history])

    return vfs_pb2.ApiGetFileVersionTimesResult(times=times)


class ApiGetFileDownloadCommandHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves the export command for a given file."""

  proto_args_type = vfs_pb2.ApiGetFileDownloadCommandArgs
  proto_result_type = vfs_pb2.ApiGetFileDownloadCommandResult

  def Handle(
      self,
      args: vfs_pb2.ApiGetFileDownloadCommandArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> vfs_pb2.ApiGetFileDownloadCommandResult:
    del context  # unused
    ValidateVfsPath(args.file_path)

    output_fname = os.path.basename(args.file_path)

    code_to_execute = (
        """grrapi.Client("%s").File(r\"\"\"%s\"\"\").GetBlob()."""
        """WriteToFile("./%s")"""
    ) % (args.client_id, args.file_path, output_fname)

    export_command = " ".join([
        config.CONFIG["AdminUI.export_command"],
        "--exec_code",
        utils.ShellQuote(code_to_execute),
    ])

    return vfs_pb2.ApiGetFileDownloadCommandResult(command=export_command)


class ApiCreateVfsRefreshOperationHandler(api_call_handler_base.ApiCallHandler):
  """Creates a new refresh operation for a given VFS path.

  This effectively triggers a refresh of a given VFS path. Refresh status
  can be monitored by polling the returned URL of the operation.
  """

  proto_args_type = vfs_pb2.ApiCreateVfsRefreshOperationArgs
  proto_result_type = vfs_pb2.ApiCreateVfsRefreshOperationResult

  def _FindPathspec(self, args: vfs_pb2.ApiCreateVfsRefreshOperationArgs):
    path_type, components = rdf_objects.ParseCategorizedPath(
        args.file_path.rstrip("/")
    )

    components_copy = components[:]
    all_components = []
    while components_copy:
      all_components.append(components_copy)
      components_copy = components_copy[:-1]

    res = data_store.REL_DB.ReadPathInfos(
        args.client_id, path_type, all_components
    )

    # Find the longest available "path_spec" that has a "stat_entry", if equal
    # to the requested path return. Otherwise append a new "nested_path" with
    # the missing part of the path and return.
    for k in sorted(res, key=len, reverse=True):
      path_info = res[k]
      if path_info is None:
        raise FileNotFoundError(args.client_id, path_type, components)

      if path_info.HasField("stat_entry") and path_info.stat_entry.HasField(
          "pathspec"
      ):
        ps = path_info.stat_entry.pathspec
        if len(k) < len(components):
          new_path = utils.JoinPath(*components[len(k) :])

          pathspec = ps
          last_pathtype = (
              ps.pathtype
              if ps.HasField("pathtype")
              else jobs_pb2.PathSpec.PathType.OS
          )
          while pathspec.HasField("nested_path"):
            pathspec = pathspec.nested_path
            last_pathtype = pathspec.pathtype

          pathspec.nested_path.path = new_path
          pathspec.nested_path.pathtype = last_pathtype

        return ps

    # We don't have any pathspec in the database so we just send the path we
    # have with the correct path type and hope for the best.
    pathspec = jobs_pb2.PathSpec(path="/" + "/".join(components))

    if path_type == objects_pb2.PathInfo.PathType.TSK:
      pathspec.pathtype = jobs_pb2.PathSpec.PathType.TSK
    elif path_type == objects_pb2.PathInfo.PathType.NTFS:
      pathspec.pathtype = jobs_pb2.PathSpec.PathType.NTFS
    elif path_type == objects_pb2.PathInfo.PathType.OS:
      pathspec.pathtype = jobs_pb2.PathSpec.PathType.OS
    elif path_type == objects_pb2.PathInfo.PathType.REGISTRY:
      pathspec.pathtype = jobs_pb2.PathSpec.PathType.REGISTRY
    elif path_type == objects_pb2.PathInfo.PathType.TEMP:
      pathspec.pathtype = jobs_pb2.PathSpec.PathType.TMPFILE
    else:
      raise ValueError("Invalid path_type: %r" % path_type)
    return pathspec

  def Handle(
      self,
      args: vfs_pb2.ApiCreateVfsRefreshOperationArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> vfs_pb2.ApiCreateVfsRefreshOperationResult:
    if args.max_depth == 1:
      flow_args = flows_pb2.ListDirectoryArgs(pathspec=self._FindPathspec(args))
      flow_args = mig_filesystem.ToRDFListDirectoryArgs(flow_args)
      flow_cls = filesystem.ListDirectory
    else:
      flow_args = flows_pb2.RecursiveListDirectoryArgs(
          pathspec=self._FindPathspec(args), max_depth=args.max_depth
      )
      flow_args = mig_filesystem.ToRDFRecursiveListDirectoryArgs(flow_args)
      flow_cls = filesystem.RecursiveListDirectory

    flow_id = flow.StartFlow(
        client_id=str(args.client_id),
        flow_cls=flow_cls,
        flow_args=flow_args,
        creator=context.username if context else None,
    )

    return vfs_pb2.ApiCreateVfsRefreshOperationResult(operation_id=flow_id)


class ApiGetVfsRefreshOperationStateHandler(
    api_call_handler_base.ApiCallHandler
):
  """Retrieves the state of the refresh operation specified."""

  proto_args_type = vfs_pb2.ApiGetVfsRefreshOperationStateArgs
  proto_result_type = vfs_pb2.ApiGetVfsRefreshOperationStateResult

  def Handle(
      self,
      args: vfs_pb2.ApiGetVfsRefreshOperationStateArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> vfs_pb2.ApiGetVfsRefreshOperationStateResult:
    try:
      flow_obj = data_store.REL_DB.ReadFlowObject(
          str(args.client_id), str(args.operation_id)
      )
    except db.UnknownFlowError as ex:
      raise VfsRefreshOperationNotFoundError(
          "Operation with id %s not found" % args.operation_id
      ) from ex

    if flow_obj.flow_class_name not in [
        "RecursiveListDirectory",
        "ListDirectory",
    ]:
      raise VfsRefreshOperationNotFoundError(
          "Operation with id %s not found" % args.operation_id
      )

    complete = flow_obj.flow_state != flows_pb2.Flow.FlowState.RUNNING
    result = vfs_pb2.ApiGetVfsRefreshOperationStateResult()
    if complete:
      result.state = vfs_pb2.ApiGetVfsRefreshOperationStateResult.State.FINISHED
    else:
      result.state = vfs_pb2.ApiGetVfsRefreshOperationStateResult.State.RUNNING

    return result


def _GetTimelineStatEntries(
    client_id: str,
    file_path: str,
    with_history: bool = True,
) -> Iterable[tuple[str, jobs_pb2.StatEntry, jobs_pb2.Hash]]:
  """Gets timeline entries from REL_DB."""
  path_type, components = rdf_objects.ParseCategorizedPath(file_path)

  try:
    root_path_info = data_store.REL_DB.ReadPathInfo(
        client_id, path_type, components
    )
  except db.UnknownPathError:
    return

  path_infos = []
  for path_info in itertools.chain(
      [root_path_info],
      data_store.REL_DB.ListDescendantPathInfos(
          client_id, path_type, components
      ),
  ):
    # TODO(user): this is to keep the compatibility with current
    # AFF4 implementation. Check if this check is needed.
    if path_info.HasField("directory") and path_info.directory:
      continue

    categorized_path = rdf_objects.ToCategorizedPath(
        path_info.path_type, path_info.components
    )
    if with_history:
      path_infos.append(path_info)
    else:
      stat_entry, hash_entry = None, None
      if path_info.HasField("stat_entry"):
        stat_entry = path_info.stat_entry
      if path_info.HasField("hash_entry"):
        hash_entry = path_info.hash_entry
      yield categorized_path, stat_entry, hash_entry

  if with_history:
    hist_path_infos = data_store.REL_DB.ReadPathInfosHistories(
        client_id, path_type, [tuple(pi.components) for pi in path_infos]
    )
    for path_info in itertools.chain.from_iterable(hist_path_infos.values()):
      categorized_path = rdf_objects.ToCategorizedPath(
          path_info.path_type, path_info.components
      )
      stat_entry, hash_entry = None, None
      if path_info.HasField("stat_entry"):
        stat_entry = path_info.stat_entry
      if path_info.HasField("hash_entry"):
        hash_entry = path_info.hash_entry

      yield categorized_path, stat_entry, hash_entry


def _GetTimelineItems(
    client_id: str, file_path: str
) -> Iterable[vfs_pb2.ApiVfsTimelineItem]:
  """Gets timeline items for a given client id and path."""

  items = []

  for file_path, stat_entry, _ in _GetTimelineStatEntries(
      client_id, file_path, with_history=True
  ):

    # It may be that for a given timestamp only hash entry is available, we're
    # skipping those.
    if stat_entry is None:
      continue

    # Add a new event for each MAC time if it exists.
    if stat_entry.HasField("st_mtime"):
      items.append(
          vfs_pb2.ApiVfsTimelineItem(
              timestamp=int(
                  rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                      stat_entry.st_mtime
                  )
              ),
              action=vfs_pb2.ApiVfsTimelineItem.FileActionType.MODIFICATION,
              file_path=file_path,
          )
      )
    if stat_entry.HasField("st_atime"):
      items.append(
          vfs_pb2.ApiVfsTimelineItem(
              timestamp=int(
                  rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                      stat_entry.st_atime
                  )
              ),
              action=vfs_pb2.ApiVfsTimelineItem.FileActionType.ACCESS,
              file_path=file_path,
          )
      )
    if stat_entry.HasField("st_ctime"):
      items.append(
          vfs_pb2.ApiVfsTimelineItem(
              timestamp=int(
                  rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                      stat_entry.st_ctime
                  )
              ),
              action=vfs_pb2.ApiVfsTimelineItem.FileActionType.METADATA_CHANGED,
              file_path=file_path,
          )
      )
  return sorted(items, key=lambda x: x.timestamp, reverse=True)


class ApiGetVfsTimelineHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves the timeline for a given file path."""

  proto_args_type = vfs_pb2.ApiGetVfsTimelineArgs
  proto_result_type = vfs_pb2.ApiGetVfsTimelineResult

  def Handle(
      self,
      args: vfs_pb2.ApiGetVfsTimelineArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> vfs_pb2.ApiGetVfsTimelineResult:
    ValidateVfsPath(args.file_path)

    items = _GetTimelineItems(args.client_id, args.file_path)
    return vfs_pb2.ApiGetVfsTimelineResult(items=items)


class ApiGetVfsTimelineAsCsvHandler(api_call_handler_base.ApiCallHandler):
  """Exports the timeline for a given file path."""

  proto_args_type = vfs_pb2.ApiGetVfsTimelineAsCsvArgs

  CHUNK_SIZE = 1000

  def _GenerateDefaultExport(
      self, items: list[vfs_pb2.ApiVfsTimelineItem]
  ) -> Iterable[bytes]:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")

    # Write header. Since we do not stick to a specific timeline format, we
    # can export a format suited for TimeSketch import.
    writer.writerow(["Timestamp", "Datetime", "Message", "Timestamp_desc"])

    for start in range(0, len(items), self.CHUNK_SIZE):
      for item in items[start : start + self.CHUNK_SIZE]:
        writer.writerow([
            str(item.timestamp),
            str(
                rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(item.timestamp)
            ),
            item.file_path,
            vfs_pb2.ApiVfsTimelineItem.FileActionType.Name(item.action),
        ])

      yield buffer.getvalue().encode("utf-8")

      buffer = io.StringIO()
      writer = csv.writer(buffer)

  def _HandleDefaultFormat(
      self,
      args: vfs_pb2.ApiGetVfsTimelineAsCsvArgs,
  ) -> api_call_handler_base.ApiBinaryStream:
    items = _GetTimelineItems(args.client_id, args.file_path)
    return api_call_handler_base.ApiBinaryStream(
        "%s_%s_timeline" % (args.client_id, os.path.basename(args.file_path)),
        content_generator=self._GenerateDefaultExport(items),
    )

  def _GenerateBodyExport(
      self,
      file_infos: Iterable[tuple[str, jobs_pb2.StatEntry, jobs_pb2.Hash]],
  ) -> Iterable[bytes]:
    for path, st, hash_v in file_infos:
      if st is None:
        continue

      buffer = io.StringIO()
      writer = csv.writer(buffer, delimiter="|", lineterminator="\n")

      if hash_v and hash_v.HasField("md5") and hash_v.md5:
        hash_str = text.Hexify(hash_v.md5)
      else:
        hash_str = ""

      # Details about Body format:
      # https://wiki.sleuthkit.org/index.php?title=Body_file
      # MD5|name|inode|mode_as_string|UID|GID|size|atime|mtime|ctime|crtime
      writer.writerow([
          hash_str,
          path,
          str(st.st_ino),
          str(stat.filemode(st.st_mode)),
          str(st.st_uid),
          str(st.st_gid),
          str(st.st_size),
          str(st.st_atime),
          str(st.st_mtime),
          str(st.st_ctime),
          str(st.st_btime),
      ])
      yield buffer.getvalue().encode("utf-8")

  def _HandleBodyFormat(
      self, args: vfs_pb2.ApiGetVfsTimelineAsCsvArgs
  ) -> api_call_handler_base.ApiBinaryStream:
    file_infos = _GetTimelineStatEntries(
        args.client_id, args.file_path, with_history=False
    )
    return api_call_handler_base.ApiBinaryStream(
        "%s_%s_timeline" % (args.client_id, os.path.basename(args.file_path)),
        content_generator=self._GenerateBodyExport(file_infos),
    )

  def Handle(
      self,
      args: vfs_pb2.ApiGetVfsTimelineAsCsvArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_call_handler_base.ApiBinaryStream:
    ValidateVfsPath(args.file_path)

    if (
        args.format == vfs_pb2.ApiGetVfsTimelineAsCsvArgs.Format.UNSET
        or args.format == vfs_pb2.ApiGetVfsTimelineAsCsvArgs.Format.GRR
    ):
      return self._HandleDefaultFormat(args)
    elif args.format == args.Format.BODY:
      return self._HandleBodyFormat(args)
    else:
      raise ValueError("Unexpected file format: %s" % args.format)


class ApiUpdateVfsFileContentHandler(api_call_handler_base.ApiCallHandler):
  """Creates a file update operation for a given VFS file.

  Triggers a flow to refresh a given VFS file. The refresh status
  can be monitored by polling the operation id.
  """

  proto_args_type = vfs_pb2.ApiUpdateVfsFileContentArgs
  proto_result_type = vfs_pb2.ApiUpdateVfsFileContentResult

  def Handle(
      self,
      args: vfs_pb2.ApiUpdateVfsFileContentArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> vfs_pb2.ApiUpdateVfsFileContentResult:
    assert context is not None

    path_type, components = rdf_objects.ParseCategorizedPath(args.file_path)

    path_info = data_store.REL_DB.ReadPathInfo(
        str(args.client_id), path_type, components
    )

    if (
        not path_info
        or not path_info.HasField("stat_entry")
        or not path_info.stat_entry.HasField("pathspec")
    ):
      raise FileNotFoundError(
          client_id=str(args.client_id),
          path_type=path_type,
          components=components,
      )

    flow_args = flows_pb2.MultiGetFileArgs(
        pathspecs=[path_info.stat_entry.pathspec]
    )
    flow_id = flow.StartFlow(
        client_id=args.client_id,
        flow_cls=transfer.MultiGetFile,
        flow_args=mig_transfer.ToRDFMultiGetFileArgs(flow_args),
        creator=context.username,
    )

    return vfs_pb2.ApiUpdateVfsFileContentResult(operation_id=flow_id)


class ApiGetVfsFileContentUpdateStateHandler(
    api_call_handler_base.ApiCallHandler
):
  """Retrieves the state of the update operation specified."""

  proto_args_type = vfs_pb2.ApiGetVfsFileContentUpdateStateArgs
  proto_result_type = vfs_pb2.ApiGetVfsFileContentUpdateStateResult

  def Handle(
      self,
      args: vfs_pb2.ApiGetVfsFileContentUpdateStateArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> vfs_pb2.ApiGetVfsFileContentUpdateStateResult:
    try:
      flow_obj = data_store.REL_DB.ReadFlowObject(
          str(args.client_id), str(args.operation_id)
      )
    except db.UnknownFlowError as e:
      raise VfsFileContentUpdateNotFoundError(
          "Operation with id %s not found" % args.operation_id
      ) from e

    if flow_obj.flow_class_name != "MultiGetFile":
      raise VfsFileContentUpdateNotFoundError(
          "Operation with id %s not found" % args.operation_id
      )

    result = vfs_pb2.ApiGetVfsFileContentUpdateStateResult()
    if flow_obj.flow_state == flows_pb2.Flow.FlowState.RUNNING:
      result.state = vfs_pb2.ApiGetVfsFileContentUpdateStateResult.State.RUNNING
    else:
      result.state = (
          vfs_pb2.ApiGetVfsFileContentUpdateStateResult.State.FINISHED
      )

    return result


class ApiGetVfsFilesArchiveHandler(api_call_handler_base.ApiCallHandler):
  """Streams archive with files collected in the VFS of a client."""

  proto_args_type = vfs_pb2.ApiGetVfsFilesArchiveArgs

  def _GenerateContent(
      self,
      client_id: str,
      start_paths: list[str],
      path_prefix: str,
      timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> Iterator[utils.StreamingZipGenerator]:
    client_paths = []
    for start_path in start_paths:
      path_type, components = rdf_objects.ParseCategorizedPath(start_path)
      for path_info in data_store.REL_DB.ListDescendantPathInfos(
          client_id, path_type, components
      ):
        if path_info.HasField("directory") and path_info.directory:
          continue

        client_paths.append(db.ClientPath.FromPathInfo(client_id, path_info))

    archive_generator = utils.StreamingZipGenerator(
        compression=zipfile.ZIP_DEFLATED
    )
    for chunk in file_store.StreamFilesChunks(
        client_paths, max_timestamp=timestamp
    ):
      if chunk.chunk_index == 0:
        content_path = os.path.join(path_prefix, chunk.client_path.vfs_path)
        # TODO(user): Export meaningful file metadata.
        st = os.stat_result((0o644, 0, 0, 0, 0, 0, chunk.total_size, 0, 0, 0))
        yield archive_generator.WriteFileHeader(content_path, st=st)

      yield archive_generator.WriteFileChunk(chunk.data)

      if chunk.chunk_index == chunk.total_chunks - 1:
        yield archive_generator.WriteFileFooter()

    yield archive_generator.Close()

  def _WrapContentGenerator(
      self,
      generator: Iterator[utils.StreamingZipGenerator],
      args: vfs_pb2.ApiGetVfsFilesArchiveArgs,
      username: str,
  ) -> Iterator[utils.StreamingZipGenerator]:
    if args.file_path:
      path_type, components = rdf_objects.ParseCategorizedPath(args.file_path)
      vfs_file_ref = objects_pb2.VfsFileReference(
          client_id=args.client_id,
          path_type=path_type,
          path_components=components,
      )
    else:
      vfs_file_ref = objects_pb2.VfsFileReference(client_id=args.client_id)

    object_reference = objects_pb2.ObjectReference(
        reference_type=objects_pb2.ObjectReference.Type.VFS_FILE,
        vfs_file=vfs_file_ref,
    )
    try:
      for item in generator:
        yield item
      notification.Notify(
          username,
          objects_pb2.UserNotification.Type.TYPE_FILE_ARCHIVE_GENERATED,
          "Downloaded an archive of folder %s from client %s."
          % (args.file_path, args.client_id),
          object_reference,
      )

    except Exception as e:
      notification.Notify(
          username,
          objects_pb2.UserNotification.Type.TYPE_FILE_ARCHIVE_GENERATION_FAILED,
          "Archive generation failed for folder %s on client %s: %s"
          % (args.file_path, args.client_id, e),
          object_reference,
      )

      raise

  def Handle(
      self,
      args: vfs_pb2.ApiGetVfsFilesArchiveArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_call_handler_base.ApiBinaryStream:
    assert context is not None

    path = args.file_path
    if not path:
      start_paths = ["fs/os", "fs/tsk", "registry", "temp", "fs/ntfs"]
      prefix = "vfs_" + re.sub("[^0-9a-zA-Z]", "_", args.client_id)
    else:
      ValidateVfsPath(path)
      if path.rstrip("/") == "fs":
        start_paths = ["fs/os", "fs/tsk", "fs/ntfs"]
      else:
        start_paths = [path]
      prefix = "vfs_" + re.sub(
          "[^0-9a-zA-Z]", "_", args.client_id + "_" + path
      ).strip("_")

    if args.HasField("timestamp"):
      timestamp = rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
          args.timestamp
      )
    else:
      timestamp = None

    content_generator = self._WrapContentGenerator(
        self._GenerateContent(args.client_id, start_paths, prefix, timestamp),
        args,
        context.username,
    )
    return api_call_handler_base.ApiBinaryStream(
        prefix + ".zip", content_generator=content_generator
    )


# TODO: Temporary copy of migration function due to cyclic
# dependency.
def ToProtoApiAff4ObjectRepresentation(
    rdf: ApiAff4ObjectRepresentation,
) -> vfs_pb2.ApiAff4ObjectRepresentation:
  return rdf.AsPrimitiveProto()
