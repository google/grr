#!/usr/bin/env python
"""API handlers for dealing with files in a client's virtual file system."""

import csv
import logging
import os
import re
import StringIO
import zipfile

from grr import config
from grr.lib import rdfvalue

from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import objects as rdf_objects
from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api import vfs_pb2
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server import data_store_utils
from grr.server.grr_response_server import flow
from grr.server.grr_response_server.aff4_objects import aff4_grr
from grr.server.grr_response_server.aff4_objects import standard as aff4_standard
from grr.server.grr_response_server.flows.general import filesystem
from grr.server.grr_response_server.flows.general import transfer
from grr.server.grr_response_server.gui import api_call_handler_base

from grr.server.grr_response_server.gui.api_plugins import client

# Files can only be accessed if their first path component is from this list.
ROOT_FILES_WHITELIST = ["fs", "registry", "temp"]


def ValidateVfsPath(path):
  """Validates a VFS path."""

  components = (path or "").lstrip("/").split("/")
  if not components:
    raise ValueError(
        "Empty path is not a valid path: %s." % utils.SmartStr(path))

  if components[0] not in ROOT_FILES_WHITELIST:
    raise ValueError("First path component was '%s', but has to be one of %s" %
                     (utils.SmartStr(components[0]),
                      ", ".join(ROOT_FILES_WHITELIST)))

  return True


class FileContentNotFoundError(api_call_handler_base.ResourceNotFoundError):
  """Raised when the content for a specific file could not be found."""


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

  def InitFromAff4Object(self, aff4_obj, aff4_cls, attr_blacklist):
    """Initializes the current instance from an Aff4Object.

    Iterates over all attributes of the Aff4Object defined by a given class
    and adds a representation of them to the current instance.

    Args:
      aff4_obj: An Aff4Object to take the attributes from.
      aff4_cls: A class in the inheritance hierarchy of the Aff4Object
        defining which attributes to take.
      attr_blacklist: A list of already added attributes as to not add
        attributes multiple times.

    Returns:
      A reference to the current instance.
    """
    self.name = str(aff4_cls.__name__)
    self.attributes = []

    schema = aff4_cls.SchemaCls
    for name, attribute in sorted(schema.__dict__.items()):
      if not isinstance(attribute, aff4.Attribute):
        continue

      if name in attr_blacklist:
        continue

      attr_repr = ApiAff4ObjectAttribute()
      attr_repr.name = name
      attr_repr.description = attribute.description
      attr_repr.values = []

      values = list(aff4_obj.GetValuesForAttribute(attribute))
      for value in values:
        # This value is really a LazyDecoder() instance. We need to get at the
        # real data here.
        # TODO(user): Change GetValuesForAttribute to resolve
        # lazy decoders and directly yield the rdf value.
        if hasattr(value, "ToRDFValue"):
          value = value.ToRDFValue()

        value_repr = ApiAff4ObjectAttributeValue()
        value_repr.type = value.__class__.__name__
        value_repr.age = value.age
        value_repr.value = value
        attr_repr.values.append(value_repr)

      if attr_repr.values:
        self.attributes.append(attr_repr)

    return self


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

  def InitFromAff4Object(self, aff4_obj):
    """Initializes the current instance from an Aff4Object.

    Iterates the inheritance hierarchy of the given Aff4Object and adds a
    ApiAff4ObjectType for each class found in the hierarchy.

    Args:
      aff4_obj: An Aff4Object as source for the initialization.

    Returns:
      A reference to the current instance.
    """
    attr_blacklist = []  # We use this to show attributes only once.

    self.types = []
    for aff4_cls in aff4_obj.__class__.__mro__:
      if not hasattr(aff4_cls, "SchemaCls"):
        continue

      type_repr = ApiAff4ObjectType().InitFromAff4Object(
          aff4_obj, aff4_cls, attr_blacklist)

      if type_repr.attributes:
        self.types.append(type_repr)

      # Add all attribute names from this type representation to the
      # blacklist to not add them to the result again.
      attr_blacklist.extend([attr.name for attr in type_repr.attributes])

    return self


class ApiFile(rdf_structs.RDFProtoStruct):
  protobuf = vfs_pb2.ApiFile
  rdf_deps = [
      ApiAff4ObjectRepresentation,
      crypto.Hash,
      rdfvalue.RDFDatetime,
      rdf_client.StatEntry,
  ]

  def InitFromAff4Object(self, file_obj, stat_entry=None, with_details=False):
    """Initializes the current instance from an Aff4Stream.

    Args:
      file_obj: An Aff4Stream representing a file.
      stat_entry: An optional stat entry object to be use. If none is provided,
        the one stored in the AFF4 data store is used.
      with_details: True if all details of the Aff4Object should be included,
        false otherwise.

    Returns:
      A reference to the current instance.
    """
    self.name = file_obj.urn.Basename()
    self.path = "/".join(file_obj.urn.Path().split("/")[2:])
    self.is_directory = "Container" in file_obj.behaviours
    self.hash = file_obj.Get(file_obj.Schema.HASH, None)

    if stat_entry is not None:
      stat = stat_entry
    else:
      stat = file_obj.Get(file_obj.Schema.STAT)

    if stat:
      self.stat = stat

    if not self.is_directory:
      try:
        self.last_collected = file_obj.GetContentAge()
      except AttributeError:
        # Defensive approach - in case file-like object doesn't have
        # GetContentAge defined.
        logging.debug("File-like object %s doesn't have GetContentAge defined.",
                      file_obj.__class__.__name__)

      if self.last_collected:
        self.last_collected_size = file_obj.Get(file_obj.Schema.SIZE)

    type_obj = file_obj.Get(file_obj.Schema.TYPE)
    if type_obj is not None:
      self.type = type_obj
      self.age = type_obj.age
      # Without self.Set self.age would reference "age" attribute instead of a
      # protobuf field.
      self.Set("age", type_obj.age)

    if with_details:
      self.details = ApiAff4ObjectRepresentation().InitFromAff4Object(file_obj)

    return self


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


class ApiGetFileDetailsHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves the details of a given file."""

  args_type = ApiGetFileDetailsArgs
  result_type = ApiGetFileDetailsResult

  def Handle(self, args, token=None):
    ValidateVfsPath(args.file_path)

    if args.timestamp:
      age = args.timestamp
    else:
      age = aff4.ALL_TIMES

    file_obj = aff4.FACTORY.Open(
        args.client_id.ToClientURN().Add(args.file_path),
        mode="r",
        age=age,
        token=token)

    if data_store.RelationalDBReadEnabled(category="vfs"):
      # These are not really "files" so they cannot be stored in the database
      # but they still can be queried so we need to return something. Sometimes
      # they contain a trailing slash so we need to take care of that.
      #
      # TODO(hanuszczak): Require VFS paths to be normalized so that trailing
      # slash is either forbidden or mandatory.
      if args.file_path.endswith("/"):
        args.file_path = args.file_path[:-1]
      if args.file_path in ["fs", "registry", "temp", "fs/os", "fs/tsk"]:
        api_file = ApiFile()
        api_file.name = api_file.path = args.file_path
        api_file.is_directory = True
        return ApiGetFileDetailsResult(file=api_file)

      path_type, components = rdf_objects.ParseCategorizedPath(args.file_path)

      # TODO(hanuszczak): The tests passed even without support for timestamp
      # filtering. The test suite should be probably improved in that regard.
      path_id = rdf_objects.PathID(components)
      path_info = data_store.REL_DB.FindPathInfoByPathID(
          str(args.client_id), path_type, path_id, timestamp=args.timestamp)

      if path_info:
        stat_entry = path_info.stat_entry
      else:
        stat_entry = rdf_client.StatEntry()
    else:
      stat_entry = None

    return ApiGetFileDetailsResult(file=ApiFile().InitFromAff4Object(
        file_obj, stat_entry=stat_entry, with_details=True))


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
    client_id = args.client_id.ToClientURN()

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

    if data_store_utils.GetClientOs(client_id, token=token) == "Windows":
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

  def _HandleRelational(self, args, token=None):
    client_id = args.client_id.ToClientURN()

    if not args.file_path or args.file_path == "/":
      return self._GetRootChildren(args, token=token)

    if args.file_path == "fs":
      return self._GetFilesystemChildren(args)

    path_type, components = rdf_objects.ParseCategorizedPath(args.file_path)
    path_id = rdf_objects.PathID(components)

    child_path_ids = data_store.REL_DB.FindDescendentPathIDs(
        client_id=client_id.Basename(),
        path_type=path_type,
        path_id=path_id,
        max_depth=1)

    child_path_infos = data_store.REL_DB.FindPathInfosByPathIDs(
        client_id=client_id.Basename(),
        path_type=path_type,
        path_ids=child_path_ids).values()

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
      child_item.stat = child_path_info.stat_entry

      # The `age` field collides with RDF `age` pseudo-property so `Set` lets us
      # set the right thing.
      child_item.Set("age", child_path_info.last_path_history_timestamp)

      items.append(child_item)

    # TODO(hanuszczak): Instead of getting the whole list from the database and
    # then filtering the results we should do the filtering directly in the
    # database query.
    if args.filter:
      pattern = re.compile(args.filter, re.IGNORECASE)
      is_matching = lambda item: pattern.search(item.name)
      items = filter(is_matching, items)

    items.sort(key=lambda item: item.path)

    if args.count:
      items = items[args.offset:args.offset + args.count]
    else:
      items = items[args.offset:]

    return ApiListFilesResult(items=items)

  def Handle(self, args, token=None):
    if data_store.RelationalDBReadEnabled(category="vfs"):
      return self._HandleRelational(args, token=token)

    path = args.file_path
    if not path:
      path = "/"

    # We allow querying root path ("/") to get a list of whitelisted
    # root entries. In all other cases we have to validate the path.
    if path != "/":
      ValidateVfsPath(args.file_path)

    if args.timestamp:
      age = args.timestamp
    else:
      age = aff4.NEWEST_TIME

    directory = aff4.FACTORY.Open(
        args.client_id.ToClientURN().Add(path), mode="r", token=token).Upgrade(
            aff4_standard.VFSDirectory)

    if args.directories_only:
      children = [
          ch for ch in directory.OpenChildren(age=age)
          if "Container" in ch.behaviours
      ]
    else:
      children = [ch for ch in directory.OpenChildren(age=age)]

    # If we are reading the root file content, a whitelist applies.
    if path == "/":
      children = [
          ch for ch in children if ch.urn.Basename() in ROOT_FILES_WHITELIST
      ]

    # Apply the filter.
    if args.filter:
      pattern = re.compile(args.filter, re.IGNORECASE)
      children = [ch for ch in children if pattern.search(ch.urn.Basename())]

    # Apply sorting.
    # TODO(user): add sort attribute.
    children = sorted(children, key=lambda ch: ch.urn.Basename())

    # Apply offset and count.
    if args.count:
      children = children[args.offset:args.offset + args.count]
    else:
      children = children[args.offset:]

    return ApiListFilesResult(
        items=[ApiFile().InitFromAff4Object(c) for c in children])


class ApiGetFileTextArgs(rdf_structs.RDFProtoStruct):
  protobuf = vfs_pb2.ApiGetFileTextArgs
  rdf_deps = [
      client.ApiClientId,
      rdfvalue.RDFDatetime,
  ]


class ApiGetFileTextResult(rdf_structs.RDFProtoStruct):
  protobuf = vfs_pb2.ApiGetFileTextResult


def _Aff4Size(aff4_obj):
  """Retrieves the total size in bytes of an AFF4 object.

  Args:
    aff4_obj: An AFF4 stream instance to retrieve size for.

  Returns:
    An integer representing number of bytes.

  Raises:
    TypeError: If `aff4_obj` is not an instance of AFF4 stream.
  """
  if not isinstance(aff4_obj, aff4.AFF4Stream):
    message = "Expected an instance of `%s` but received `%s`"
    raise TypeError(message % (aff4.AFF4Stream, type(aff4_obj)))

  return int(aff4_obj.Get(aff4_obj.Schema.SIZE))


def _Aff4Read(aff4_obj, offset, length):
  """Reads contents of given AFF4 file.

  Args:
    aff4_obj: An AFF4 stream instance to retrieve contents for.
    offset: An offset to start the reading from.
    length: A number of bytes to read. Reads the whole file if 0.

  Returns:
    Contents of specified AFF4 stream.

  Raises:
    TypeError: If `aff4_obj` is not an instance of AFF4 stream.
  """
  length = length or (_Aff4Size(aff4_obj) - offset)

  aff4_obj.Seek(offset)
  return aff4_obj.Read(length)


class ApiGetFileTextHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves the text for a given file."""

  args_type = ApiGetFileTextArgs
  result_type = ApiGetFileTextResult

  def Handle(self, args, token=None):
    ValidateVfsPath(args.file_path)

    if args.timestamp:
      age = args.timestamp
    else:
      age = aff4.NEWEST_TIME

    try:
      file_obj = aff4.FACTORY.Open(
          args.client_id.ToClientURN().Add(args.file_path),
          aff4_type=aff4.AFF4Stream,
          mode="r",
          age=age,
          token=token)

      file_content_missing = not file_obj.GetContentAge()
    except aff4.InstantiationError:
      file_content_missing = True

    if file_content_missing:
      raise FileContentNotFoundError(
          "File %s with timestamp %s wasn't found on client %s" %
          (utils.SmartStr(args.file_path), utils.SmartStr(args.timestamp),
           utils.SmartStr(args.client_id)))

    byte_content = _Aff4Read(file_obj, offset=args.offset, length=args.length)

    if args.encoding:
      encoding = args.encoding.name.lower()
    else:
      encoding = ApiGetFileTextArgs.Encoding.UTF_8.name.lower()

    text_content = self._Decode(encoding, byte_content)

    return ApiGetFileTextResult(
        total_size=_Aff4Size(file_obj), content=text_content)

  def _Decode(self, codec_name, data):
    """Decode data with the given codec name."""
    try:
      return data.decode(codec_name, "replace")
    except LookupError:
      raise RuntimeError("Codec could not be found.")
    except AssertionError:
      raise RuntimeError("Codec failed to decode")


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

  def _GenerateFile(self, aff4_stream, offset, length):
    aff4_stream.Seek(offset)
    for start in range(offset, offset + length, self.CHUNK_SIZE):
      yield aff4_stream.Read(min(self.CHUNK_SIZE, offset + length - start))

  def Handle(self, args, token=None):
    ValidateVfsPath(args.file_path)

    if args.timestamp:
      age = args.timestamp
    else:
      age = aff4.NEWEST_TIME

    try:
      file_obj = aff4.FACTORY.Open(
          args.client_id.ToClientURN().Add(args.file_path),
          aff4_type=aff4.AFF4Stream,
          mode="r",
          age=age,
          token=token)

      file_content_missing = not file_obj.GetContentAge()
    except aff4.InstantiationError:
      file_content_missing = True

    if file_content_missing:
      raise FileContentNotFoundError(
          "File %s with timestamp %s wasn't found on client %s" %
          (utils.SmartStr(args.file_path), utils.SmartStr(args.timestamp),
           utils.SmartStr(args.client_id)))

    total_size = _Aff4Size(file_obj)
    if not args.length:
      args.length = total_size - args.offset
    else:
      # Make sure args.length is in the allowed range.
      args.length = min(abs(args.length), total_size - args.offset)

    generator = self._GenerateFile(file_obj, args.offset, args.length)

    return api_call_handler_base.ApiBinaryStream(
        filename=file_obj.urn.Basename(),
        content_generator=generator,
        content_length=args.length)


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

    fd = aff4.FACTORY.Open(
        args.client_id.ToClientURN().Add(args.file_path),
        mode="r",
        age=aff4.ALL_TIMES,
        token=token)

    type_values = list(fd.GetValuesForAttribute(fd.Schema.TYPE))
    return ApiGetFileVersionTimesResult(
        times=sorted([t.age for t in type_values], reverse=True))


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

    encodings = sorted(ApiGetFileTextArgs.Encoding.enum_dict.keys())

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

  def Handle(self, args, token=None):
    ValidateVfsPath(args.file_path)

    aff4_path = args.client_id.ToClientURN().Add(args.file_path)
    fd = aff4.FACTORY.Open(aff4_path, token=token)

    if args.max_depth == 1:
      flow_args = filesystem.ListDirectoryArgs(pathspec=fd.real_pathspec)

      flow_urn = flow.GRRFlow.StartFlow(
          client_id=args.client_id.ToClientURN(),
          flow_name=filesystem.ListDirectory.__name__,
          args=flow_args,
          notify_to_user=args.notify_user,
          token=token)

    else:
      flow_args = filesystem.RecursiveListDirectoryArgs(
          pathspec=fd.real_pathspec, max_depth=args.max_depth)

      flow_urn = flow.GRRFlow.StartFlow(
          client_id=args.client_id.ToClientURN(),
          flow_name=filesystem.RecursiveListDirectory.__name__,
          args=flow_args,
          notify_to_user=args.notify_user,
          token=token)

    return ApiCreateVfsRefreshOperationResult(operation_id=str(flow_urn))


class ApiGetVfsRefreshOperationStateArgs(rdf_structs.RDFProtoStruct):
  """Arguments for checking a refresh operation."""
  protobuf = vfs_pb2.ApiGetVfsRefreshOperationStateArgs
  rdf_deps = [
      client.ApiClientId,
  ]


class ApiGetVfsRefreshOperationStateResult(rdf_structs.RDFProtoStruct):
  """Indicates the state of a refresh operation."""
  protobuf = vfs_pb2.ApiGetVfsRefreshOperationStateResult


class ApiGetVfsRefreshOperationStateHandler(
    api_call_handler_base.ApiCallHandler):
  """Retrieves the state of the refresh operation specified."""

  args_type = ApiGetVfsRefreshOperationStateArgs
  result_type = ApiGetVfsRefreshOperationStateResult

  def Handle(self, args, token=None):
    flow_obj = aff4.FACTORY.Open(args.operation_id, token=token)

    if not isinstance(flow_obj, (filesystem.RecursiveListDirectory,
                                 filesystem.ListDirectory)):
      raise VfsRefreshOperationNotFoundError(
          "Operation with id %s not found" % args.operation_id)

    complete = not flow_obj.GetRunner().IsRunning()
    result = ApiGetVfsRefreshOperationStateResult()
    if complete:
      result.state = ApiGetVfsRefreshOperationStateResult.State.FINISHED
    else:
      result.state = ApiGetVfsRefreshOperationStateResult.State.RUNNING

    return result


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

    folder_urn = args.client_id.ToClientURN().Add(args.file_path)
    items = self.GetTimelineItems(folder_urn, token=token)
    return ApiGetVfsTimelineResult(items=items)

  @staticmethod
  def GetTimelineItems(folder_urn, token=None):
    """Retrieves the timeline items for a given folder.

    The timeline consists of items indicating a state change of a file. To
    construct the timeline, MAC times are used. Whenever a timestamp on a
    file changes, a corresponding timeline item is created.

    Args:
      folder_urn: The urn of the target folder.
      token: The user token.

    Returns:
      A list of timeline items, each consisting of a file path, a timestamp
      and an action describing the nature of the file change.
    """
    child_urns = []
    for _, children in aff4.FACTORY.RecursiveMultiListChildren(folder_urn):
      child_urns.extend(children)

    # Get the stats attributes for all clients.
    attribute = aff4.Attribute.GetAttributeByName("stat")
    items = []
    for subject, values in data_store.DB.MultiResolvePrefix(
        child_urns, attribute.predicate,
        timestamp=data_store.DB.ALL_TIMESTAMPS):
      for _, serialized, _ in values:
        stat = rdf_client.StatEntry.FromSerializedString(serialized)

        # Add a new event for each MAC time if it exists.
        for c in "mac":
          timestamp = getattr(stat, "st_%stime" % c)
          if timestamp is None:
            continue

          item = ApiVfsTimelineItem()
          item.timestamp = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(timestamp)

          # Remove aff4:/<client_id> to have a more concise path to the
          # subject.
          item.file_path = "/".join(str(subject).split("/")[2:])
          if c == "m":
            item.action = ApiVfsTimelineItem.FileActionType.MODIFICATION
          elif c == "a":
            item.action = ApiVfsTimelineItem.FileActionType.ACCESS
          elif c == "c":
            item.action = ApiVfsTimelineItem.FileActionType.METADATA_CHANGED

          items.append(item)

    return sorted(items, key=lambda x: x.timestamp, reverse=True)


class ApiGetVfsTimelineAsCsvArgs(rdf_structs.RDFProtoStruct):
  protobuf = vfs_pb2.ApiGetVfsTimelineAsCsvArgs
  rdf_deps = [
      client.ApiClientId,
  ]


class ApiGetVfsTimelineAsCsvHandler(api_call_handler_base.ApiCallHandler):
  """Exports the timeline for a given file path."""

  args_type = ApiGetVfsTimelineAsCsvArgs
  CHUNK_SIZE = 1000

  def _GenerateExport(self, items):
    fd = StringIO.StringIO()
    writer = csv.writer(fd)

    # Write header. Since we do not stick to a specific timeline format, we
    # can export a format suited for TimeSketch import.
    writer.writerow(["Timestamp", "Datetime", "Message", "Timestamp_desc"])

    for start in range(0, len(items), self.CHUNK_SIZE):
      for item in items[start:start + self.CHUNK_SIZE]:
        writer.writerow([
            item.timestamp.AsMicrosecondsSinceEpoch(), item.timestamp,
            utils.SmartStr(item.file_path), item.action
        ])

      yield fd.getvalue()
      fd.truncate(size=0)

  def Handle(self, args, token=None):
    ValidateVfsPath(args.file_path)

    folder_urn = args.client_id.ToClientURN().Add(args.file_path)
    items = ApiGetVfsTimelineHandler.GetTimelineItems(folder_urn, token=token)

    return api_call_handler_base.ApiBinaryStream(
        "%s_%s_timeline" % (args.client_id,
                            utils.SmartStr(folder_urn.Basename())),
        content_generator=self._GenerateExport(items))


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
    ValidateVfsPath(args.file_path)

    aff4_path = args.client_id.ToClientURN().Add(args.file_path)
    fd = aff4.FACTORY.Open(
        aff4_path, aff4_type=aff4_grr.VFSFile, mode="rw", token=token)
    flow_urn = fd.Update(priority=rdf_flows.GrrMessage.Priority.HIGH_PRIORITY)

    return ApiUpdateVfsFileContentResult(operation_id=str(flow_urn))


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
      flow_obj = aff4.FACTORY.Open(
          args.operation_id, aff4_type=transfer.MultiGetFile, token=token)
      complete = not flow_obj.GetRunner().IsRunning()
    except aff4.InstantiationError:
      raise VfsFileContentUpdateNotFoundError(
          "Operation with id %s not found" % args.operation_id)

    result = ApiGetVfsFileContentUpdateStateResult()
    if complete:
      result.state = ApiGetVfsFileContentUpdateStateResult.State.FINISHED
    else:
      result.state = ApiGetVfsFileContentUpdateStateResult.State.RUNNING

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

  def _StreamFds(self, archive_generator, prefix, fds, token=None):
    prev_fd = None
    for fd, chunk, exception in aff4.AFF4Stream.MultiStream(fds):
      if exception:
        logging.exception(exception)
        continue

      if prev_fd != fd:
        if prev_fd:
          yield archive_generator.WriteFileFooter()
        prev_fd = fd

        components = fd.urn.Split()
        # Skipping first component: client id.
        content_path = os.path.join(prefix, *components[1:])
        # TODO(user): Export meaningful file metadata.
        st = os.stat_result((0644, 0, 0, 0, 0, 0, fd.size, 0, 0, 0))
        yield archive_generator.WriteFileHeader(content_path, st=st)

      yield archive_generator.WriteFileChunk(chunk)

    if prev_fd:
      yield archive_generator.WriteFileFooter()

  def _GenerateContent(self, start_urns, prefix, age, token=None):
    archive_generator = utils.StreamingZipGenerator(
        compression=zipfile.ZIP_DEFLATED)
    folders_urns = set(start_urns)

    while folders_urns:
      next_urns = set()
      for _, children in aff4.FACTORY.MultiListChildren(folders_urns):
        for urn in children:
          next_urns.add(urn)

      download_fds = set()
      folders_urns = set()
      for fd in aff4.FACTORY.MultiOpen(next_urns, token=token):
        if isinstance(fd, aff4.AFF4Stream):
          download_fds.add(fd)
        elif "Container" in fd.behaviours:
          folders_urns.add(fd.urn)

      if download_fds:
        if age != aff4.NEWEST_TIME:
          urns = [fd.urn for fd in download_fds]
          # We need to reopen the files with the actual age
          # requested. We can't do this in the call above since
          # indexes are stored with the latest timestamp of an object
          # only so adding the age above will potentially ignore
          # some of the indexes.
          download_fds = list(
              aff4.FACTORY.MultiOpen(urns, age=age, token=token))

        for chunk in self._StreamFds(
            archive_generator, prefix, download_fds, token=token):
          yield chunk

    yield archive_generator.Close()

  def Handle(self, args, token=None):
    client_urn = args.client_id.ToClientURN()
    path = args.file_path
    if not path:
      start_urns = [client_urn.Add(p) for p in ROOT_FILES_WHITELIST]
      prefix = "vfs_" + re.sub("[^0-9a-zA-Z]", "_",
                               utils.SmartStr(args.client_id))
    else:
      ValidateVfsPath(args.file_path)
      start_urns = [client_urn.Add(args.file_path)]
      prefix = "vfs_" + re.sub("[^0-9a-zA-Z]", "_",
                               start_urns[0].Path()).strip("_")

    if args.timestamp:
      age = args.timestamp
    else:
      age = aff4.NEWEST_TIME

    content_generator = self._GenerateContent(
        start_urns, prefix, age=age, token=token)
    return api_call_handler_base.ApiBinaryStream(
        prefix + ".zip", content_generator=content_generator)
