#!/usr/bin/env python
"""API handlers for dealing with files in a client's virtual file system."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import itertools
import os
import re
import zipfile

from future.builtins import filter
from future.builtins import int
from future.builtins import range
from future.builtins import str
from future.utils import iterkeys
from future.utils import itervalues

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util import context
from grr_response_core.lib.util.compat import csv
from grr_response_proto.api import vfs_pb2
from grr_response_server import data_store
from grr_response_server import data_store_utils
from grr_response_server import decoders
from grr_response_server import file_store
from grr_response_server import flow
from grr_response_server import notification
from grr_response_server.databases import db
from grr_response_server.flows.general import filesystem
from grr_response_server.flows.general import transfer
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui.api_plugins import client
from grr_response_server.rdfvalues import objects as rdf_objects

# Files can only be accessed if their first path component is from this list.
ROOT_FILES_WHITELIST = ["fs", "registry", "temp"]


def ValidateVfsPath(path):
  """Validates a VFS path."""

  components = (path or "").lstrip("/").split("/")
  if not components:
    raise ValueError("Empty path is not a valid path: %s." % path)

  if components[0] not in ROOT_FILES_WHITELIST:
    raise ValueError("First path component was '%s', but has to be one of %s" %
                     (components[0], ", ".join(ROOT_FILES_WHITELIST)))

  return True


class FileNotFoundError(api_call_handler_base.ResourceNotFoundError):
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
        client_id=client_id, path_type=path_type, path=path)
    super(FileNotFoundError, self).__init__(message)


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
      message = ("Content for {} file with path '{}' and timestamp '{}' for "
                 "client '{}' not found")
      message = message.format(path_type, path, timestamp, client_id)

    super(FileContentNotFoundError, self).__init__(message)


class VfsRefreshOperationNotFoundError(
    api_call_handler_base.ResourceNotFoundError):
  """Raised when a vfs refresh operation could not be found."""


class VfsFileContentUpdateNotFoundError(
    api_call_handler_base.ResourceNotFoundError):
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
  definied by a certain class of the inheritance hierarchy of the Aff4Object.
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
    super(ApiFile, self).__init__(*args, **kwargs)
    try:
      self.age = kwargs["age"]
    except KeyError:
      self.age = rdfvalue.RDFDatetime.Now()


class ApiGetFileDetailsArgs(rdf_structs.RDFProtoStruct):
  protobuf = vfs_pb2.ApiGetFileDetailsArgs
  rdf_deps = [
      client.ApiClientId,
      rdfvalue.RDFDatetime,
  ]


class ApiGetFileDetailsResult(rdf_structs.RDFProtoStruct):
  protobuf = vfs_pb2.ApiGetFileDetailsResult
  rdf_deps = [
      ApiFile,
  ]


def _GenerateApiFileDetails(path_infos):
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
    v.Set("type", compatibility.GetName(value.__class__))
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
          _Value(pi.timestamp, rdfvalue.RDFInteger(pi.hash_entry.num_bytes)))
    if pi.stat_entry:
      stat_attrs.append(_Value(pi.timestamp, pi.stat_entry))

      if pi.stat_entry.pathspec:
        pathspec_attrs.append(_Value(pi.timestamp, pi.stat_entry.pathspec))

  return ApiAff4ObjectRepresentation(types=[
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
  ])


class ApiGetFileDetailsHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves the details of a given file."""

  args_type = ApiGetFileDetailsArgs
  result_type = ApiGetFileDetailsResult

  def Handle(self, args, token=None):
    ValidateVfsPath(args.file_path)

    # Directories are not really "files" so they cannot be stored in the
    # database but they still can be queried so we need to return something.
    # Sometimes they contain a trailing slash so we need to take care of that.
    #
    # TODO(hanuszczak): Require VFS paths to be normalized so that trailing
    # slash is either forbidden or mandatory.
    if args.file_path.endswith("/"):
      args.file_path = args.file_path[:-1]
    if args.file_path in ["fs", "registry", "temp", "fs/os", "fs/tsk"]:
      api_file = ApiFile(
          name=args.file_path,
          path=args.file_path,
          is_directory=True,
          details=_GenerateApiFileDetails([]))
      return ApiGetFileDetailsResult(file=api_file)

    path_type, components = rdf_objects.ParseCategorizedPath(args.file_path)

    client_id = str(args.client_id)

    try:
      path_info = data_store.REL_DB.ReadPathInfo(
          client_id=client_id,
          path_type=path_type,
          components=components,
          timestamp=args.timestamp)
    except db.UnknownPathError:
      raise FileNotFoundError(
          client_id=client_id, path_type=path_type, components=components)

    last_collection_pi = file_store.GetLastCollectionPathInfo(
        db.ClientPath.FromPathInfo(client_id, path_info),
        max_timestamp=args.timestamp)

    history = data_store.REL_DB.ReadPathInfoHistory(
        client_id=client_id,
        path_type=path_type,
        components=components,
        cutoff=args.timestamp)
    history.reverse()

    # It might be the case that we do not have any history about the file, but
    # we have some information because it is an implicit path.
    if not history:
      history = [path_info]

    file_obj = ApiFile(
        name=components[-1],
        path=rdf_objects.ToCategorizedPath(path_type, components),
        stat=path_info.stat_entry,
        hash=path_info.hash_entry,
        details=_GenerateApiFileDetails(history),
        is_directory=path_info.directory,
        age=path_info.timestamp,
    )

    if last_collection_pi:
      file_obj.last_collected = last_collection_pi.timestamp
      file_obj.last_collected_size = last_collection_pi.hash_entry.num_bytes

    return ApiGetFileDetailsResult(file=file_obj)


class ApiListFilesArgs(rdf_structs.RDFProtoStruct):
  protobuf = vfs_pb2.ApiListFilesArgs
  rdf_deps = [
      client.ApiClientId,
      rdfvalue.RDFDatetime,
  ]


class ApiListFilesResult(rdf_structs.RDFProtoStruct):
  protobuf = vfs_pb2.ApiListFilesResult
  rdf_deps = [
      ApiFile,
  ]


class ApiListFilesHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves the child files for a given file."""

  args_type = ApiListFilesArgs
  result_type = ApiListFilesResult

  def _GetRootChildren(self, args, token=None):
    client_id = str(args.client_id)

    items = []

    fs_item = ApiFile()
    fs_item.name = "fs"
    fs_item.path = "fs"
    fs_item.is_directory = True
    items.append(fs_item)

    temp_item = ApiFile()
    temp_item.name = "temp"
    temp_item.path = "temp"
    temp_item.is_directory = True
    items.append(temp_item)

    if data_store_utils.GetClientOs(client_id) == "Windows":
      registry_item = ApiFile()
      registry_item.name = "registry"
      registry_item.path = "registry"
      registry_item.is_directory = True
      items.append(registry_item)

    if args.count:
      items = items[args.offset:args.offset + args.count]
    else:
      items = items[args.offset:]

    return ApiListFilesResult(items=items)

  def _GetFilesystemChildren(self, args):
    items = []

    os_item = ApiFile()
    os_item.name = "os"
    os_item.path = "fs/os"
    os_item.is_directory = True
    items.append(os_item)

    tsk_item = ApiFile()
    tsk_item.name = "tsk"
    tsk_item.path = "fs/tsk"
    tsk_item.is_directory = True
    items.append(tsk_item)

    if args.count:
      items = items[args.offset:args.offset + args.count]
    else:
      items = items[args.offset:]

    return ApiListFilesResult(items=items)

  def Handle(self, args, token=None):
    if not args.file_path or args.file_path == "/":
      return self._GetRootChildren(args, token=token)

    if args.file_path == "fs":
      return self._GetFilesystemChildren(args)

    path_type, components = rdf_objects.ParseCategorizedPath(args.file_path)

    child_path_infos = data_store.REL_DB.ListChildPathInfos(
        client_id=args.client_id.ToString(),
        path_type=path_type,
        components=components,
        timestamp=args.timestamp)

    items = []

    for child_path_info in child_path_infos:
      if args.directories_only and not child_path_info.directory:
        continue

      child_item = ApiFile()
      child_item.name = child_path_info.basename

      if path_type == rdf_objects.PathInfo.PathType.OS:
        prefix = "fs/os/"
      elif path_type == rdf_objects.PathInfo.PathType.TSK:
        prefix = "fs/tsk/"
      elif path_type == rdf_objects.PathInfo.PathType.REGISTRY:
        prefix = "registry/"
      elif path_type == rdf_objects.PathInfo.PathType.TEMP:
        prefix = "temp/"

      child_item.path = prefix + "/".join(child_path_info.components)

      # TODO(hanuszczak): `PathInfo#directory` tells us whether given path has
      # ever been observed as a directory. Is this what we want here or should
      # we use `st_mode` information instead?
      child_item.is_directory = child_path_info.directory
      if child_path_info.stat_entry:
        child_item.stat = child_path_info.stat_entry
      child_item.age = child_path_info.timestamp

      if child_path_info.last_hash_entry_timestamp:
        child_item.last_collected = child_path_info.last_hash_entry_timestamp
        child_item.last_collected_size = child_path_info.hash_entry.num_bytes

      items.append(child_item)

    # TODO(hanuszczak): Instead of getting the whole list from the database and
    # then filtering the results we should do the filtering directly in the
    # database query.
    if args.filter:
      pattern = re.compile(args.filter, re.IGNORECASE)
      is_matching = lambda item: pattern.search(item.name)
      items = list(filter(is_matching, items))

    items.sort(key=lambda item: item.path)

    if args.count:
      items = items[args.offset:args.offset + args.count]
    else:
      items = items[args.offset:]

    return ApiListFilesResult(items=items)


class ApiGetFileTextArgs(rdf_structs.RDFProtoStruct):
  protobuf = vfs_pb2.ApiGetFileTextArgs
  rdf_deps = [
      client.ApiClientId,
      rdfvalue.RDFDatetime,
  ]


class ApiGetFileTextResult(rdf_structs.RDFProtoStruct):
  protobuf = vfs_pb2.ApiGetFileTextResult


class ApiGetFileTextHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves the text for a given file."""

  args_type = ApiGetFileTextArgs
  result_type = ApiGetFileTextResult

  def _Decode(self, codec_name, data):
    """Decode data with the given codec name."""
    try:
      return data.decode(codec_name, "replace")
    except LookupError:
      raise RuntimeError("Codec could not be found.")
    except AssertionError:
      raise RuntimeError("Codec failed to decode")

  def Handle(self, args, token=None):
    ValidateVfsPath(args.file_path)

    path_type, components = rdf_objects.ParseCategorizedPath(args.file_path)
    client_path = db.ClientPath(str(args.client_id), path_type, components)

    try:
      fd = file_store.OpenFile(client_path, max_timestamp=args.timestamp)
    except file_store.FileHasNoContentError:
      raise FileContentNotFoundError(args.client_id, path_type, components,
                                     args.timestamp)

    fd.seek(args.offset)
    # No need to protect against args.length == 0 case and large files:
    # file_store logic has all necessary checks in place.
    byte_content = fd.read(args.length or None)

    if args.encoding:
      encoding = args.encoding.name.lower()
    else:
      encoding = ApiGetFileTextArgs.Encoding.UTF_8.name.lower()

    text_content = self._Decode(encoding, byte_content)

    return ApiGetFileTextResult(total_size=fd.size, content=text_content)


class ApiGetFileBlobArgs(rdf_structs.RDFProtoStruct):
  protobuf = vfs_pb2.ApiGetFileBlobArgs
  rdf_deps = [
      client.ApiClientId,
      rdfvalue.RDFDatetime,
  ]


class ApiGetFileBlobHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves the byte content for a given file."""

  args_type = ApiGetFileBlobArgs
  CHUNK_SIZE = 1024 * 1024 * 4

  def _GenerateFile(self, file_obj, offset, length):
    file_obj.seek(offset)
    for start in range(offset, offset + length, self.CHUNK_SIZE):
      yield file_obj.read(min(self.CHUNK_SIZE, offset + length - start))

  def _WrapContentGenerator(self, generator, args, username):
    try:
      for item in generator:
        yield item
    except Exception as e:
      path_type, components = rdf_objects.ParseCategorizedPath(args.file_path)
      vfs_file_ref = rdf_objects.VfsFileReference(
          client_id=args.client_id,
          path_type=path_type,
          path_components=components)
      object_reference = rdf_objects.ObjectReference(
          reference_type=rdf_objects.ObjectReference.Type.VFS_FILE,
          vfs_file=vfs_file_ref)

      notification.Notify(
          username,
          rdf_objects.UserNotification.Type.TYPE_FILE_BLOB_FETCH_FAILED,
          "File blob fetch failed for path %s on client %s: %s" %
          (args.client_id, args.file_path, e), object_reference)
      raise

  def Handle(self, args, token=None):
    ValidateVfsPath(args.file_path)

    path_type, components = rdf_objects.ParseCategorizedPath(args.file_path)
    client_path = db.ClientPath(str(args.client_id), path_type, components)

    try:
      file_obj = file_store.OpenFile(client_path, max_timestamp=args.timestamp)
    except file_store.FileNotFoundError:
      raise FileNotFoundError(args.client_id, path_type, components)
    except file_store.FileHasNoContentError:
      raise FileContentNotFoundError(args.client_id, path_type, components,
                                     args.timestamp)

    size = max(0, file_obj.size - args.offset)
    if args.length and args.length < size:
      size = args.length

    generator = self._WrapContentGenerator(
        self._GenerateFile(file_obj, args.offset, size), args, token.username)
    return api_call_handler_base.ApiBinaryStream(
        filename=components[-1],
        content_generator=generator,
        content_length=size)


class ApiGetFileVersionTimesArgs(rdf_structs.RDFProtoStruct):
  protobuf = vfs_pb2.ApiGetFileVersionTimesArgs
  rdf_deps = [
      client.ApiClientId,
  ]


class ApiGetFileVersionTimesResult(rdf_structs.RDFProtoStruct):
  protobuf = vfs_pb2.ApiGetFileVersionTimesResult
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


class ApiGetFileVersionTimesHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves the list of version times of the given file."""

  args_type = ApiGetFileVersionTimesArgs
  result_type = ApiGetFileVersionTimesResult

  def Handle(self, args, token=None):
    ValidateVfsPath(args.file_path)

    try:
      path_type, components = rdf_objects.ParseCategorizedPath(
          args.file_path.rstrip("/"))
    except ValueError:
      # If the path does not point to a file (i.e. "fs"), just return an
      # empty response.
      return ApiGetFileVersionTimesResult(times=[])

    history = data_store.REL_DB.ReadPathInfoHistory(
        str(args.client_id), path_type, components)
    times = reversed([pi.timestamp for pi in history])

    return ApiGetFileVersionTimesResult(times=times)


class ApiGetFileDownloadCommandArgs(rdf_structs.RDFProtoStruct):
  protobuf = vfs_pb2.ApiGetFileDownloadCommandArgs
  rdf_deps = [
      client.ApiClientId,
  ]


class ApiGetFileDownloadCommandResult(rdf_structs.RDFProtoStruct):
  protobuf = vfs_pb2.ApiGetFileDownloadCommandResult


class ApiGetFileDownloadCommandHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves the export command for a given file."""

  args_type = ApiGetFileDownloadCommandArgs
  result_type = ApiGetFileDownloadCommandResult

  def Handle(self, args, token=None):
    ValidateVfsPath(args.file_path)

    output_fname = os.path.basename(args.file_path)

    code_to_execute = (
        """grrapi.Client("%s").File(r\"\"\"%s\"\"\").GetBlob()."""
        """WriteToFile("./%s")""") % (args.client_id, args.file_path,
                                      output_fname)

    export_command = u" ".join([
        config.CONFIG["AdminUI.export_command"], "--exec_code",
        utils.ShellQuote(code_to_execute)
    ])

    return ApiGetFileDownloadCommandResult(command=export_command)


class ApiListKnownEncodingsResult(rdf_structs.RDFProtoStruct):
  protobuf = vfs_pb2.ApiListKnownEncodingsResult


class ApiListKnownEncodingsHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves available file encodings."""

  result_type = ApiListKnownEncodingsResult

  def Handle(self, args, token=None):

    encodings = sorted(iterkeys(ApiGetFileTextArgs.Encoding.enum_dict))

    return ApiListKnownEncodingsResult(encodings=encodings)


class ApiCreateVfsRefreshOperationArgs(rdf_structs.RDFProtoStruct):
  """Arguments for updating a VFS path."""
  protobuf = vfs_pb2.ApiCreateVfsRefreshOperationArgs
  rdf_deps = [
      client.ApiClientId,
  ]


class ApiCreateVfsRefreshOperationResult(rdf_structs.RDFProtoStruct):
  """Can be immediately returned to poll the status."""
  protobuf = vfs_pb2.ApiCreateVfsRefreshOperationResult


class ApiCreateVfsRefreshOperationHandler(api_call_handler_base.ApiCallHandler):
  """Creates a new refresh operation for a given VFS path.

  This effectively triggers a refresh of a given VFS path. Refresh status
  can be monitored by polling the returned URL of the operation.
  """

  args_type = ApiCreateVfsRefreshOperationArgs
  result_type = ApiCreateVfsRefreshOperationResult

  def _FindPathspec(self, args):
    path_type, components = rdf_objects.ParseCategorizedPath(
        args.file_path.rstrip("/"))

    components_copy = components[:]
    all_components = []
    while components_copy:
      all_components.append(components_copy)
      components_copy = components_copy[:-1]

    res = data_store.REL_DB.ReadPathInfos(
        str(args.client_id), path_type, all_components)

    for k in sorted(res, key=len, reverse=True):
      path_info = res[k]
      if path_info is None:
        raise FileNotFoundError(args.client_id, path_type, components)
      if path_info.stat_entry and path_info.stat_entry.pathspec:
        ps = path_info.stat_entry.pathspec

        if len(k) < len(components):
          new_path = utils.JoinPath(*components[len(k):])
          ps.Append(
              rdf_paths.PathSpec(path=new_path, pathtype=ps.last.pathtype))
        return ps

    # We don't have any pathspec in the database so we just send the path we
    # have with the correct path type and hope for the best.
    pathspec = rdf_paths.PathSpec(path="/" + "/".join(components))

    if path_type == rdf_objects.PathInfo.PathType.TSK:
      pathspec.pathtype = pathspec.PathType.TSK
    elif path_type == rdf_objects.PathInfo.PathType.OS:
      pathspec.pathtype = pathspec.PathType.OS
    elif path_type == rdf_objects.PathInfo.PathType.REGISTRY:
      pathspec.pathtype = pathspec.PathType.REGISTRY
    elif path_type == rdf_objects.PathInfo.PathType.TEMP:
      pathspec.pathtype = pathspec.PathType.TMPFILE
    else:
      raise ValueError("Invalid path_type: %r" % self.path_type)

    return pathspec

  def Handle(self, args, token=None):
    if args.max_depth == 1:
      flow_args = filesystem.ListDirectoryArgs(
          pathspec=self._FindPathspec(args))
      flow_cls = filesystem.ListDirectory
    else:
      flow_args = filesystem.RecursiveListDirectoryArgs(
          pathspec=self._FindPathspec(args), max_depth=args.max_depth)
      flow_cls = filesystem.RecursiveListDirectory

    flow_id = flow.StartFlow(
        client_id=str(args.client_id),
        flow_cls=flow_cls,
        flow_args=flow_args,
        creator=token.username if token else None)

    return ApiCreateVfsRefreshOperationResult(operation_id=flow_id)


class ApiGetVfsRefreshOperationStateArgs(rdf_structs.RDFProtoStruct):
  """Arguments for checking a refresh operation."""
  protobuf = vfs_pb2.ApiGetVfsRefreshOperationStateArgs
  rdf_deps = [
      client.ApiClientId,
  ]


class ApiGetVfsRefreshOperationStateResult(rdf_structs.RDFProtoStruct):
  """Indicates the state of a refresh operation."""
  protobuf = vfs_pb2.ApiGetVfsRefreshOperationStateResult


class ApiGetVfsRefreshOperationStateHandler(api_call_handler_base.ApiCallHandler
                                           ):
  """Retrieves the state of the refresh operation specified."""

  args_type = ApiGetVfsRefreshOperationStateArgs
  result_type = ApiGetVfsRefreshOperationStateResult

  def _RaiseOperationNotFoundError(self, args):
    raise VfsRefreshOperationNotFoundError("Operation with id %s not found" %
                                           args.operation_id)

  def Handle(self, args, token=None):
    try:
      rdf_flow = data_store.REL_DB.ReadFlowObject(
          str(args.client_id), str(args.operation_id))
    except db.UnknownFlowError:
      self._RaiseOperationNotFoundError(args)

    if rdf_flow.flow_class_name not in [
        "RecursiveListDirectory", "ListDirectory"
    ]:
      self._RaiseOperationNotFoundError(args)

    complete = rdf_flow.flow_state != "RUNNING"
    result = ApiGetVfsRefreshOperationStateResult()
    if complete:
      result.state = ApiGetVfsRefreshOperationStateResult.State.FINISHED
    else:
      result.state = ApiGetVfsRefreshOperationStateResult.State.RUNNING

    return result


def _GetTimelineStatEntries(api_client_id, file_path, with_history=True):
  """Gets timeline entries from REL_DB."""
  path_type, components = rdf_objects.ParseCategorizedPath(file_path)

  client_id = str(api_client_id)

  try:
    root_path_info = data_store.REL_DB.ReadPathInfo(client_id, path_type,
                                                    components)
  except db.UnknownPathError:
    return

  path_infos = []
  for path_info in itertools.chain(
      [root_path_info],
      data_store.REL_DB.ListDescendantPathInfos(client_id, path_type,
                                                components),
  ):
    # TODO(user): this is to keep the compatibility with current
    # AFF4 implementation. Check if this check is needed.
    if path_info.directory:
      continue

    categorized_path = rdf_objects.ToCategorizedPath(path_info.path_type,
                                                     path_info.components)
    if with_history:
      path_infos.append(path_info)
    else:
      yield categorized_path, path_info.stat_entry, path_info.hash_entry

  if with_history:
    hist_path_infos = data_store.REL_DB.ReadPathInfosHistories(
        client_id, path_type, [tuple(pi.components) for pi in path_infos])
    for path_info in itertools.chain.from_iterable(itervalues(hist_path_infos)):
      categorized_path = rdf_objects.ToCategorizedPath(path_info.path_type,
                                                       path_info.components)
      yield categorized_path, path_info.stat_entry, path_info.hash_entry


def _GetTimelineItems(client_id, file_path):
  """Gets timeline items for a given client id and path."""

  items = []

  for file_path, stat_entry, _ in _GetTimelineStatEntries(
      client_id, file_path, with_history=True):

    # It may be that for a given timestamp only hash entry is available, we're
    # skipping those.
    if stat_entry is None:
      continue

    # Add a new event for each MAC time if it exists.
    for c in "mac":
      timestamp = getattr(stat_entry, "st_%stime" % c)
      if timestamp is None:
        continue

      item = ApiVfsTimelineItem(timestamp=timestamp)

      # Remove aff4:/<client_id> to have a more concise path to the
      # subject.
      item.file_path = file_path
      if c == "m":
        item.action = ApiVfsTimelineItem.FileActionType.MODIFICATION
      elif c == "a":
        item.action = ApiVfsTimelineItem.FileActionType.ACCESS
      elif c == "c":
        item.action = ApiVfsTimelineItem.FileActionType.METADATA_CHANGED

      items.append(item)

  return sorted(items, key=lambda x: x.timestamp, reverse=True)


class ApiVfsTimelineItem(rdf_structs.RDFProtoStruct):
  protobuf = vfs_pb2.ApiVfsTimelineItem
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


class ApiGetVfsTimelineArgs(rdf_structs.RDFProtoStruct):
  protobuf = vfs_pb2.ApiGetVfsTimelineArgs
  rdf_deps = [
      client.ApiClientId,
  ]


class ApiGetVfsTimelineResult(rdf_structs.RDFProtoStruct):
  protobuf = vfs_pb2.ApiGetVfsTimelineResult
  rdf_deps = [
      ApiVfsTimelineItem,
  ]


class ApiGetVfsTimelineHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves the timeline for a given file path."""

  args_type = ApiGetVfsTimelineArgs
  result_type = ApiGetVfsTimelineResult

  def Handle(self, args, token=None):
    ValidateVfsPath(args.file_path)

    items = _GetTimelineItems(args.client_id, args.file_path)
    return ApiGetVfsTimelineResult(items=items)


class ApiGetVfsTimelineAsCsvArgs(rdf_structs.RDFProtoStruct):
  protobuf = vfs_pb2.ApiGetVfsTimelineAsCsvArgs
  rdf_deps = [
      client.ApiClientId,
  ]


class ApiGetVfsTimelineAsCsvHandler(api_call_handler_base.ApiCallHandler):
  """Exports the timeline for a given file path."""

  args_type = ApiGetVfsTimelineAsCsvArgs
  CHUNK_SIZE = 1000

  def _GenerateDefaultExport(self, items):
    writer = csv.Writer()

    # Write header. Since we do not stick to a specific timeline format, we
    # can export a format suited for TimeSketch import.
    writer.WriteRow([u"Timestamp", u"Datetime", u"Message", u"Timestamp_desc"])

    for start in range(0, len(items), self.CHUNK_SIZE):
      for item in items[start:start + self.CHUNK_SIZE]:
        writer.WriteRow([
            str(item.timestamp.AsMicrosecondsSinceEpoch()),
            str(item.timestamp),
            item.file_path,
            str(item.action),
        ])

      yield writer.Content().encode("utf-8")
      writer = csv.Writer()

  def _HandleDefaultFormat(self, args):
    items = _GetTimelineItems(args.client_id, args.file_path)
    return api_call_handler_base.ApiBinaryStream(
        "%s_%s_timeline" % (args.client_id, os.path.basename(args.file_path)),
        content_generator=self._GenerateDefaultExport(items))

  def _GenerateBodyExport(self, file_infos):
    for path, st, hash_v in file_infos:
      if st is None:
        continue

      writer = csv.Writer(delimiter=u"|")

      if hash_v and hash_v.md5:
        hash_str = hash_v.md5.HexDigest()
      else:
        hash_str = u""

      # Details about Body format:
      # https://wiki.sleuthkit.org/index.php?title=Body_file
      # MD5|name|inode|mode_as_string|UID|GID|size|atime|mtime|ctime|crtime
      writer.WriteRow([
          hash_str,
          path,
          str(st.st_ino),
          str(st.st_mode),
          str(st.st_uid),
          str(st.st_gid),
          str(st.st_size),
          str(int(st.st_atime or 0)),
          str(int(st.st_mtime or 0)),
          str(int(st.st_ctime or 0)),
          str(int(st.st_crtime or 0)),
      ])

      yield writer.Content().encode("utf-8")

  def _HandleBodyFormat(self, args):
    file_infos = _GetTimelineStatEntries(
        args.client_id, args.file_path, with_history=False)
    return api_call_handler_base.ApiBinaryStream(
        "%s_%s_timeline" % (args.client_id, os.path.basename(args.file_path)),
        content_generator=self._GenerateBodyExport(file_infos))

  def Handle(self, args, token=None):
    ValidateVfsPath(args.file_path)

    if args.format == args.Format.UNSET or args.format == args.Format.GRR:
      return self._HandleDefaultFormat(args)
    elif args.format == args.Format.BODY:
      return self._HandleBodyFormat(args)
    else:
      raise ValueError("Unexpected file format: %s" % args.format)


class ApiUpdateVfsFileContentArgs(rdf_structs.RDFProtoStruct):
  """Arguments for updating a VFS file."""
  protobuf = vfs_pb2.ApiUpdateVfsFileContentArgs
  rdf_deps = [
      client.ApiClientId,
  ]


class ApiUpdateVfsFileContentResult(rdf_structs.RDFProtoStruct):
  """Can be immediately returned to poll the status."""
  protobuf = vfs_pb2.ApiUpdateVfsFileContentResult


class ApiUpdateVfsFileContentHandler(api_call_handler_base.ApiCallHandler):
  """Creates a file update operation for a given VFS file.

  Triggers a flow to refresh a given VFS file. The refresh status
  can be monitored by polling the operation id.
  """

  args_type = ApiUpdateVfsFileContentArgs
  result_type = ApiUpdateVfsFileContentResult

  def Handle(self, args, token=None):
    path_type, components = rdf_objects.ParseCategorizedPath(args.file_path)

    path_info = data_store.REL_DB.ReadPathInfo(
        str(args.client_id), path_type, components)

    if (not path_info or not path_info.stat_entry or
        not path_info.stat_entry.pathspec):
      raise FileNotFoundError(
          client_id=str(args.client_id),
          path_type=path_type,
          components=components)

    flow_args = transfer.MultiGetFileArgs(
        pathspecs=[path_info.stat_entry.pathspec])
    flow_id = flow.StartFlow(
        client_id=str(args.client_id),
        flow_cls=transfer.MultiGetFile,
        flow_args=flow_args,
        creator=token.username)

    return ApiUpdateVfsFileContentResult(operation_id=flow_id)


class ApiGetVfsFileContentUpdateStateArgs(rdf_structs.RDFProtoStruct):
  """Arguments for checking a file content update operation."""
  protobuf = vfs_pb2.ApiGetVfsFileContentUpdateStateArgs
  rdf_deps = [
      client.ApiClientId,
  ]


class ApiGetVfsFileContentUpdateStateResult(rdf_structs.RDFProtoStruct):
  """Indicates the state of a file content update operation."""
  protobuf = vfs_pb2.ApiGetVfsFileContentUpdateStateResult


class ApiGetVfsFileContentUpdateStateHandler(
    api_call_handler_base.ApiCallHandler):
  """Retrieves the state of the update operation specified."""

  args_type = ApiGetVfsFileContentUpdateStateArgs
  result_type = ApiGetVfsFileContentUpdateStateResult

  def Handle(self, args, token=None):
    try:
      rdf_flow = data_store.REL_DB.ReadFlowObject(
          str(args.client_id), str(args.operation_id))
    except db.UnknownFlowError:
      raise VfsFileContentUpdateNotFoundError("Operation with id %s not found" %
                                              args.operation_id)

    if rdf_flow.flow_class_name != "MultiGetFile":
      raise VfsFileContentUpdateNotFoundError("Operation with id %s not found" %
                                              args.operation_id)

    result = ApiGetVfsFileContentUpdateStateResult()
    if rdf_flow.flow_state == "RUNNING":
      result.state = ApiGetVfsFileContentUpdateStateResult.State.RUNNING
    else:
      result.state = ApiGetVfsFileContentUpdateStateResult.State.FINISHED

    return result


class ApiGetVfsFilesArchiveArgs(rdf_structs.RDFProtoStruct):
  """Arguments for GetVfsFilesArchive handler."""
  protobuf = vfs_pb2.ApiGetVfsFilesArchiveArgs
  rdf_deps = [
      client.ApiClientId,
      rdfvalue.RDFDatetime,
  ]


class ApiGetVfsFilesArchiveHandler(api_call_handler_base.ApiCallHandler):
  """Streams archive with files collected in the VFS of a client."""

  args_type = ApiGetVfsFilesArchiveArgs

  def _GenerateContent(self, client_id, start_paths, timestamp, path_prefix):
    client_paths = []
    for start_path in start_paths:
      path_type, components = rdf_objects.ParseCategorizedPath(start_path)
      for pi in data_store.REL_DB.ListDescendantPathInfos(
          client_id, path_type, components):
        if pi.directory:
          continue

        client_paths.append(db.ClientPath.FromPathInfo(client_id, pi))

    archive_generator = utils.StreamingZipGenerator(
        compression=zipfile.ZIP_DEFLATED)
    for chunk in file_store.StreamFilesChunks(
        client_paths, max_timestamp=timestamp):
      if chunk.chunk_index == 0:
        content_path = os.path.join(path_prefix, chunk.client_path.vfs_path)
        # TODO(user): Export meaningful file metadata.
        st = os.stat_result((0o644, 0, 0, 0, 0, 0, chunk.total_size, 0, 0, 0))
        yield archive_generator.WriteFileHeader(content_path, st=st)

      yield archive_generator.WriteFileChunk(chunk.data)

      if chunk.chunk_index == chunk.total_chunks - 1:
        yield archive_generator.WriteFileFooter()

    yield archive_generator.Close()

  def _WrapContentGenerator(self, generator, args, username):
    if args.file_path:
      path_type, components = rdf_objects.ParseCategorizedPath(args.file_path)
      vfs_file_ref = rdf_objects.VfsFileReference(
          client_id=args.client_id,
          path_type=path_type,
          path_components=components)
    else:
      vfs_file_ref = rdf_objects.VfsFileReference(client_id=args.client_id)

    object_reference = rdf_objects.ObjectReference(
        reference_type=rdf_objects.ObjectReference.Type.VFS_FILE,
        vfs_file=vfs_file_ref)
    try:
      for item in generator:
        yield item
      notification.Notify(
          username,
          rdf_objects.UserNotification.Type.TYPE_FILE_ARCHIVE_GENERATED,
          "Downloaded an archive of folder %s from client %s." %
          (args.file_path, args.client_id), object_reference)

    except Exception as e:
      notification.Notify(
          username,
          rdf_objects.UserNotification.Type.TYPE_FILE_ARCHIVE_GENERATION_FAILED,
          "Archive generation failed for folder %s on client %s: %s" %
          (args.file_path, args.client_id, e), object_reference)

      raise

  def Handle(self, args, token=None):
    client_id = str(args.client_id)
    path = args.file_path
    if not path:
      start_paths = ["fs/os", "fs/tsk", "registry", "temp"]
      prefix = "vfs_" + re.sub("[^0-9a-zA-Z]", "_", client_id)
    else:
      ValidateVfsPath(path)
      if path.rstrip("/") == "fs":
        start_paths = ["fs/os", "fs/tsk"]
      else:
        start_paths = [path]
      prefix = "vfs_" + re.sub("[^0-9a-zA-Z]", "_",
                               client_id + "_" + path).strip("_")

    content_generator = self._WrapContentGenerator(
        self._GenerateContent(client_id, start_paths, args.timestamp, prefix),
        args, token.username)
    return api_call_handler_base.ApiBinaryStream(
        prefix + ".zip", content_generator=content_generator)


class ApiGetFileDecodersArgs(rdf_structs.RDFProtoStruct):

  protobuf = vfs_pb2.ApiGetFileDecodersArgs
  rdf_deps = [
      client.ApiClientId,
  ]


class ApiGetFileDecodersResult(rdf_structs.RDFProtoStruct):

  protobuf = vfs_pb2.ApiGetFileDecodersResult
  rdf_deps = []


class ApiGetFileDecodersHandler(api_call_handler_base.ApiCallHandler):
  """An API handler for listing decoders available for specified file."""

  def Handle(self, args, token=None):
    result = ApiGetFileDecodersResult()

    path_type, components = rdf_objects.ParseCategorizedPath(args.file_path)
    client_path = db.ClientPath(
        client_id=str(args.client_id),
        path_type=path_type,
        components=components)

    for decoder_name in decoders.FACTORY.Names():
      decoder = decoders.FACTORY.Create(decoder_name)

      filedesc = file_store.OpenFile(client_path)
      filectx = context.NullContext(filedesc)

      with filectx as filedesc:
        if decoder.Check(filedesc):
          result.decoder_names.append(decoder_name)

    return result


class ApiGetDecodedFileArgs(rdf_structs.RDFProtoStruct):

  protobuf = vfs_pb2.ApiGetDecodedFileArgs
  rdf_deps = [
      client.ApiClientId,
  ]


class ApiGetDecodedFileHandler(api_call_handler_base.ApiCallHandler):
  """An API handler for decoding specified file."""

  def Handle(self, args, token=None):
    decoder = decoders.FACTORY.Create(args.decoder_name)

    path_type, components = rdf_objects.ParseCategorizedPath(args.file_path)
    client_path = db.ClientPath(str(args.client_id), path_type, components)

    fd = file_store.OpenFile(client_path)
    return api_call_handler_base.ApiBinaryStream(
        filename=client_path.components[-1],
        content_generator=decoder.Decode(fd))
