#!/usr/bin/env python
"""API handlers for dealing with files in a client's virtual file system."""

import re

from grr.gui import api_call_handler_base

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.flows.general import filesystem
from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import api_pb2


CATEGORY = "Files"


class VfsRefreshOperationNotFoundError(
    api_call_handler_base.ResourceNotFoundError):
  """Raised when a vfs refresh operation could not be found."""


class ApiFile(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiFile

  def InitFromAff4Object(self, file_obj, with_details=False):
    """Initializes the current instance from an Aff4Stream.

    Args:
      file_obj: An Aff4Stream representing a file.
      with_details: True if all details of the Aff4Object should be included,
        false otherwise.

    Returns:
      A reference to the current instance.
    """
    self.name = file_obj.urn.Basename()
    self.path = "/".join(file_obj.urn.Path().split("/")[2:])
    self.size = file_obj.Get(file_obj.Schema.SIZE)
    self.is_directory = "Container" in file_obj.behaviours
    self.hash = file_obj.Get(file_obj.Schema.HASH, None)
    self.last_downloaded = 0  # TODO(user): add method to Schema here

    type_obj = file_obj.Get(file_obj.Schema.TYPE)
    if type_obj is not None:
      self.type = type_obj
      self.age = type_obj.age

    if with_details:
      self.details = ApiAff4ObjectRepresentation().InitFromAff4Object(
          file_obj)

    return self


class ApiAff4ObjectRepresentation(rdf_structs.RDFProtoStruct):
  """A proto-based representation of an Aff4Object used to render responses.

  ApiAff4ObjectRepresentation contains all attributes of an Aff4Object,
  structured by type. If an attribute is found multiple times, it is only
  added once at the type where it is first encountered.
  """
  protobuf = api_pb2.ApiAff4ObjectRepresentation

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


class ApiAff4ObjectType(rdf_structs.RDFProtoStruct):
  """A representation of parts of an Aff4Object.

  ApiAff4ObjectType represents a subset of all attributes of an Aff4Object
  definied by a certain class of the inheritance hierarchy of the Aff4Object.
  """
  protobuf = api_pb2.ApiAff4ObjectType

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


class ApiAff4ObjectAttribute(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiAff4ObjectAttribute


class ApiAff4ObjectAttributeValue(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiAff4ObjectAttributeValue

  def GetValueClass(self):
    try:
      return rdfvalue.RDFValue.GetPlugin(self.type)
    except KeyError:
      raise ValueError("No class found for type %s." % self.type)


class ApiGetFileDetailsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetFileDetailsArgs


class ApiGetFileDetailsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetFileDetailsResult


class ApiGetFileDetailsHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves the details of a given file."""

  category = CATEGORY

  args_type = ApiGetFileDetailsArgs
  result_type = ApiGetFileDetailsResult

  def Handle(self, args, token=None):
    age = args.timestamp
    if not age:
      age = rdfvalue.RDFDatetime().Now()
    else:
      age = rdfvalue.RDFDatetime(age)

    file_obj = aff4.FACTORY.Open(args.client_id.Add(args.file_path),
                                 mode="r", age=age, token=token)

    return ApiGetFileDetailsResult(
        file=ApiFile().InitFromAff4Object(file_obj, with_details=True))


class ApiGetFileListArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetFileListArgs


class ApiGetFileListResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetFileListResult


class ApiGetFileListHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves the child files for a given file."""

  category = CATEGORY

  args_type = ApiGetFileListArgs
  result_type = ApiGetFileListResult
  root_files_whitelist = ["fs"]

  def Handle(self, args, token=None):
    path = args.file_path
    if not path:
      path = "/"

    directory = aff4.FACTORY.Open(args.client_id.Add(path), mode="r",
                                  token=token).Upgrade("VFSDirectory")

    if args.directories_only:
      children = [ch for ch in directory.OpenChildren()
                  if "Container" in ch.behaviours]
    else:
      children = [ch for ch in directory.OpenChildren()]

    # If we are reading the root file content, a whitelist applies.
    if path == "/":
      children = [ch for ch in children
                  if ch.urn.Basename() in self.root_files_whitelist]

    # Apply the filter.
    if args.filter:
      pattern = re.compile(args.filter, re.IGNORECASE)
      children = [ch for ch in children
                  if pattern.search(ch.urn.Basename())]

    # Apply sorting.
    # TODO(user): add sort attribute.
    children = sorted(children, key=lambda ch: ch.urn.Basename())

    # Apply offset and count.
    if args.count:
      children = children[args.offset:args.offset + args.count]
    else:
      children = children[args.offset:]

    return ApiGetFileListResult(
        items=[ApiFile().InitFromAff4Object(c) for c in children])


class ApiGetFileTextArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetFileTextArgs


class ApiGetFileTextResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetFileTextResult


class Aff4FileReaderMixin(object):
  """A helper to read a buffer from an AFF4 object."""

  def GetTotalSize(self, aff4_obj):
    return int(aff4_obj.Get(aff4_obj.Schema.SIZE))

  def Read(self, aff4_obj, offset, length):
    if not length:
      length = self.GetTotalSize(aff4_obj) - offset

    aff4_obj.Seek(offset)
    return aff4_obj.Read(length)


class ApiGetFileTextHandler(api_call_handler_base.ApiCallHandler,
                            Aff4FileReaderMixin):
  """Retrieves the text for a given file."""

  category = CATEGORY

  args_type = ApiGetFileTextArgs
  result_type = ApiGetFileTextResult

  def Handle(self, args, token=None):
    if not args.timestamp:
      age = rdfvalue.RDFDatetime().Now()
    else:
      age = rdfvalue.RDFDatetime(args.timestamp)

    file_obj = aff4.FACTORY.Open(args.client_id.Add(args.file_path),
                                 aff4_type="AFF4Stream", mode="r",
                                 age=age, token=token)

    byte_content = self.Read(file_obj, args.offset, args.length)

    if args.encoding:
      encoding = args.encoding.name.lower()
    else:
      encoding = ApiGetFileTextArgs.Encoding.UTF_8.name.lower()

    text_content = self._Decode(encoding, byte_content)

    return ApiGetFileTextResult(
        total_size=self.GetTotalSize(file_obj),
        content=text_content)

  def _Decode(self, codec_name, data):
    """Decode data with the given codec name."""
    try:
      return data.decode(codec_name, "replace")
    except LookupError:
      raise RuntimeError("Codec could not be found.")
    except AssertionError:
      raise RuntimeError("Codec failed to decode")


class ApiGetFileBlobArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetFileBlobArgs


class ApiGetFileBlobResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetFileBlobResult


class ApiGetFileBlobHandler(api_call_handler_base.ApiCallHandler,
                            Aff4FileReaderMixin):
  """Retrieves the byte content for a given file."""

  category = CATEGORY

  args_type = ApiGetFileBlobArgs
  result_type = ApiGetFileBlobResult
  chunk_size = 1024 * 1024

  def Handle(self, args, token=None):
    if not args.timestamp:
      age = rdfvalue.RDFDatetime().Now()
    else:
      age = rdfvalue.RDFDatetime(args.timestamp)

    file_obj = aff4.FACTORY.Open(args.client_id.Add(args.file_path),
                                 aff4_type="AFF4Stream", mode="r",
                                 age=age, token=token)

    byte_content = self.Read(file_obj, args.offset, args.length)

    return ApiGetFileBlobResult(
        total_size=self.GetTotalSize(file_obj),
        content=byte_content)


class ApiGetFileVersionTimesArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetFileVersionTimesArgs


class ApiGetFileVersionTimesResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetFileVersionTimesResult


class ApiGetFileVersionTimesHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves the list of version times of the given file."""

  category = CATEGORY

  args_type = ApiGetFileVersionTimesArgs
  result_type = ApiGetFileVersionTimesResult

  def Handle(self, args, token=None):
    fd = aff4.FACTORY.Open(args.client_id.Add(args.file_path), mode="r",
                           age=aff4.ALL_TIMES, token=token)

    type_values = list(fd.GetValuesForAttribute(fd.Schema.TYPE))

    return ApiGetFileVersionTimesResult(
        times=[t.age for t in type_values])


class ApiGetFileDownloadCommandArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetFileDownloadCommandArgs


class ApiGetFileDownloadCommandResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetFileDownloadCommandResult


class ApiGetFileDownloadCommandHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves the export command for a given file."""

  category = CATEGORY

  args_type = ApiGetFileDownloadCommandArgs
  result_type = ApiGetFileDownloadCommandResult

  def Handle(self, args, token=None):
    aff4_path = args.client_id.Add(args.file_path)

    export_command = u" ".join([
        config_lib.CONFIG["AdminUI.export_command"],
        "--username", utils.ShellQuote(token.username),
        "file",
        "--path", utils.ShellQuote(aff4_path),
        "--output", "."])

    return ApiGetFileDownloadCommandResult(
        command=export_command)


class ApiListKnownEncodingsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListKnownEncodingsResult


class ApiListKnownEncodingsHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves available file encodings."""

  category = CATEGORY

  result_type = ApiListKnownEncodingsResult

  def Handle(self, args, token=None):

    encodings = sorted(ApiGetFileTextArgs.Encoding.enum_dict.keys())

    return ApiListKnownEncodingsResult(
        encodings=encodings)


class ApiCreateVfsRefreshOperationArgs(rdf_structs.RDFProtoStruct):
  """Arguments for updating a VFS path."""
  protobuf = api_pb2.ApiCreateVfsRefreshOperationArgs


class ApiCreateVfsRefreshOperationResult(rdf_structs.RDFProtoStruct):
  """Can be immediately returned to poll the status."""
  protobuf = api_pb2.ApiCreateVfsRefreshOperationResult


class ApiCreateVfsRefreshOperationHandler(
    api_call_handler_base.ApiCallHandler):
  """Creates a new refresh operation for a given VFS path.

  This effectively triggers a refresh of a given VFS path. Refresh status
  can be monitored by polling the returned URL of the operation.
  """

  category = CATEGORY
  args_type = ApiCreateVfsRefreshOperationArgs
  result_type = ApiCreateVfsRefreshOperationResult

  def Handle(self, args, token=None):
    aff4_path = args.client_id.Add(args.file_path)
    fd = aff4.FACTORY.Open(aff4_path, token=token)

    flow_args = filesystem.RecursiveListDirectoryArgs(
        pathspec=fd.real_pathspec,
        max_depth=args.max_depth)

    flow_urn = flow.GRRFlow.StartFlow(
        client_id=args.client_id,
        flow_name="RecursiveListDirectory",
        args=flow_args,
        notify_to_user=args.notify_user,
        token=token)

    return ApiCreateVfsRefreshOperationResult(
        operation_id=str(flow_urn))


class ApiGetVfsRefreshOperationStateArgs(rdf_structs.RDFProtoStruct):
  """Arguments for checking a refresh operation."""
  protobuf = api_pb2.ApiGetVfsRefreshOperationStateArgs


class ApiGetVfsRefreshOperationStateResult(rdf_structs.RDFProtoStruct):
  """Indicates the state of a refresh operation."""
  protobuf = api_pb2.ApiGetVfsRefreshOperationStateResult


class GetVfsRefreshOperationStateHandler(
    api_call_handler_base.ApiCallHandler):
  """Retrieves the state of the refresh operation specified."""

  category = CATEGORY
  args_type = ApiGetVfsRefreshOperationStateArgs
  result_type = ApiGetVfsRefreshOperationStateResult

  def Handle(self, args, token=None):
    try:
      flow_obj = aff4.FACTORY.Open(args.operation_id,
                                   aff4_type="RecursiveListDirectory",
                                   token=token)
      complete = not flow_obj.GetRunner().IsRunning()
    except aff4.InstantiationError:
      raise VfsRefreshOperationNotFoundError(
          "Operation with id %s not found" % args.operation_id)

    result = ApiGetVfsRefreshOperationStateResult()
    if complete:
      result.state = ApiGetVfsRefreshOperationStateResult.State.FINISHED
    else:
      result.state = ApiGetVfsRefreshOperationStateResult.State.RUNNING

    return result

