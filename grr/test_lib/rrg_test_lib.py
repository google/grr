#!/usr/bin/env python
"""Helpers for testing RRG-related code."""

from collections.abc import Mapping
import contextlib
import hashlib
import logging
import pathlib
import re
import stat
import traceback
from typing import Any, Callable, Sequence, Union
from unittest import mock

from google.protobuf import any_pb2
from google.protobuf import timestamp_pb2
from google.protobuf import descriptor as descriptor_pb2
from google.protobuf import message as message_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_server import data_store
from grr_response_server import fleetspeak_connector
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server import sinks
from grr_response_server import worker_lib
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import mem as db_mem
from fleetspeak.src.common.proto.fleetspeak import common_pb2
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg import blob_pb2 as rrg_blob_pb2
from grr_response_proto.rrg import fs_pb2 as rrg_fs_pb2
from grr_response_proto.rrg import winreg_pb2 as rrg_winreg_pb2
from grr_response_proto.rrg.action import get_file_contents_pb2 as rrg_get_file_contents_pb2
from grr_response_proto.rrg.action import get_file_metadata_pb2 as rrg_get_file_metadata_pb2
from grr_response_proto.rrg.action import get_file_sha256_pb2 as rrg_get_file_sha256_pb2
from grr_response_proto.rrg.action import get_winreg_value_pb2 as rrg_get_winreg_value_pb2
from grr_response_proto.rrg.action import list_winreg_keys_pb2 as rrg_list_winreg_keys_pb2
from grr_response_proto.rrg.action import list_winreg_values_pb2 as rrg_list_winreg_values_pb2


class Session:
  """Fake Python-only RRG session that aggregates replies and parcels."""

  args: any_pb2.Any

  replies: list[message_pb2.Message]

  def __init__(self, request: rrg_pb2.Request) -> None:
    self.args = request.args
    self.replies = list()
    self.parcels = dict()

    self.filters: Sequence[rrg_pb2.Filter] = request.filters
    self.filtered_out_count = 0

  def Reply(self, item: message_pb2.Message):
    for item_filter in self.filters:
      if not _EvalFilter(item_filter, item):
        self.filtered_out_count += 1
        return

    # We use a copy to avoid callers mutating the items afterwards.
    item_copy = item.__class__()
    item_copy.CopyFrom(item)
    self.replies.append(item_copy)

  def Send(self, sink: rrg_pb2.Sink, item: message_pb2.Message):
    # We use a copy to avoid callers mutating the items afterwards.
    item_copy = item.__class__()
    item_copy.CopyFrom(item)
    self.parcels.setdefault(sink, []).append(item_copy)


def ExecuteFlow(
    client_id: str,
    flow_cls: type[flow_base.FlowBase],
    flow_args: rdf_structs.RDFProtoStruct,
    handlers: Mapping["rrg_pb2.Action", Callable[[Session], None]],
) -> str:
  """Create and execute flow on the given RRG client.

  Args:
    client_id: Identifier of a RRG client.
    flow_cls: Flow class to execute.
    flow_args: Argument to execute the flow with.
    handlers: Fake action handlers to use for invoking RRG actions.

  Returns:
    Identifier of the launched flow.
  """
  worker = worker_lib.GRRWorker()

  requests: list[rrg_pb2.Request] = []

  class MockFleetspeakOutgoing:
    """`connector.OutgoingConnection` that does not use real network."""

    def InsertMessage(self, message: common_pb2.Message, **kwargs) -> None:
      """Inserts a message to be sent to a Fleetspeak agent."""
      del kwargs  # Unused.

      if message.destination.service_name != "RRG":
        raise RuntimeError(
            f"Unexpected message service: {message.destination.service_name}",
        )
      if message.message_type != "rrg.Request":
        raise RuntimeError(
            f"Unexpected message type: {message.message_type}",
        )

      request = rrg_pb2.Request()
      if not message.data.Unpack(request):
        raise RuntimeError(
            f"Unexpected message request: {message.data}",
        )

      requests.append(request)

  class MockFleetspeakConnector:
    """`connector.ServiceClient` with mocked output channel."""

    def __init__(self):
      self.outgoing = MockFleetspeakOutgoing()

  exit_stack = contextlib.ExitStack()

  # Ideally, we should not really mock anything out but GRR's insistence on
  # using global variables for everything forces us to do so. This is the same
  # thing `fleetspeak_test_lib` does.
  exit_stack.enter_context(
      mock.patch.object(
          target=fleetspeak_connector,
          attribute="CONN",
          new=MockFleetspeakConnector(),
      )
  )

  data_store.REL_DB.RegisterFlowProcessingHandler(worker.ProcessFlow)
  exit_stack.callback(data_store.REL_DB.UnregisterFlowProcessingHandler)

  with exit_stack:
    flow_id = flow.StartFlow(
        client_id=client_id,
        flow_cls=flow_cls,
        flow_args=flow_args,
    )

    # Starting the flow also invokes its `Start` method which may fail for
    # various reasons. Thus, before we start processing any requests, we need to
    # verify that the flow did not fail or terminate immediately if it did.
    flow_obj = data_store.REL_DB.ReadFlowObject(
        client_id=client_id,
        flow_id=flow_id,
    )
    if flow_obj.flow_state == flows_pb2.Flow.FlowState.ERROR:
      return flow_id

    # The outer loop simulates the "on server" processing whereas the inner loop
    # simulates the "on endpoint" processing. This outer loop will finish only
    # after both the "server" and the "endpoint" have no work to do anymore.
    #
    # Note that we want to trigger the outerloop at least once even if there is
    # no work to be carried on the "endpoint" as the `Start` method might have
    # spawned subflows which need to be executed (and these in turn can spawn
    # more flows or invoke agent actions).
    while True:
      # First, we want to process all the requests "sent" to the endpoint using
      # the handlers that are given to us. Note that requests may not belong to
      # the flow we started above but to any of the child flows spawned by it.
      while requests:
        request = requests.pop(0)

        try:
          handler = handlers[request.action]
        except KeyError:
          raise RuntimeError(
              f"Missing handler for {rrg_pb2.Action.Name(request.action)!r}",
          ) from None

        flow_status = flows_pb2.FlowStatus()
        flow_status.client_id = client_id
        flow_status.flow_id = db_utils.IntToFlowID(request.flow_id)
        flow_status.request_id = request.request_id

        session = Session(request)

        try:
          handler(session)
        except Exception as error:  # pylint: disable=broad-exception-caught
          flow_status.status = flows_pb2.FlowStatus.ERROR
          if isinstance(error, AssertionError) and not str(error):
            # We treat `AssertionError` separately as stringifying it yields an
            # empty string if no custom message was attached. So for them, we
            # use the `traceback` module to get messy but more helpful error.
            flow_status.error_message = traceback.format_exc()
          else:
            flow_status.error_message = str(error)
        else:
          flow_status.status = flows_pb2.FlowStatus.OK

        for sink, parcel_payloads in session.parcels.items():
          for parcel_payload in parcel_payloads:
            parcel = rrg_pb2.Parcel()
            parcel.sink = sink
            parcel.payload.Pack(parcel_payload)

            try:
              sinks.Accept(client_id, parcel)
            except Exception as error:  # pylint: disable=broad-exception-caught
              # We set the error only if no error has been observed so far.
              if flow_status.status == flows_pb2.FlowStatus.OK:
                flow_status.status = flows_pb2.FlowStatus.ERROR
                flow_status.error_message = str(error)

        # Response identifiers start at 1 (for whatever reason) and status is
        # the last one.
        flow_status.response_id = len(session.replies) + 1

        flow_responses = []

        for i, reply in enumerate(session.replies, start=1):
          flow_response = flows_pb2.FlowResponse()
          flow_response.client_id = client_id
          flow_response.flow_id = db_utils.IntToFlowID(request.flow_id)
          flow_response.request_id = request.request_id
          flow_response.response_id = i
          flow_response.any_payload.Pack(reply)

          flow_responses.append(flow_response)

        flow_responses.append(flow_status)

        data_store.REL_DB.WriteFlowResponses(flow_responses)

      # We finished work on the "endpoint" and written all flow responses. Now
      # the worker needs to finish processing all through appropriate flow state
      # methods.
      #
      # The deadline of 10 seconds is arbitrary, it is just what the original
      # `flow_test_lib` uses.
      assert isinstance(data_store.REL_DB, db.DatabaseValidationWrapper)
      assert isinstance(data_store.REL_DB.delegate, db_mem.InMemoryDB)
      data_store.REL_DB.delegate.WaitUntilNoFlowsToProcess(
          timeout=rdfvalue.Duration.From(10, rdfvalue.MINUTES),
      )

      # If we processed all the flows and there is no work to be done on the
      # "endpoint" we are done.
      if not requests:
        break

  return flow_id


def FakePosixFileHandlers(
    filesystem: dict[str, Union[bytes, str, dict[None, None]]],
) -> Mapping["rrg_pb2.Action", Callable[[Session], None]]:
  """Action handlers that emulate given POSIX file hierarchy.

  Args:
    filesystem: A mapping from paths to file contents to use.

  Returns:
    A handlers that can be supplied to the `ExecuteFlow` helper.
  """
  # We need lambda as otherwise pytype sees it as type, not callable.
  path_cls = lambda path: pathlib.PurePosixPath(path)  # pylint: disable=unnecessary-lambda
  return FakeFileHandlers(path_cls, filesystem)


def FakeWindowsFileHandlers(
    filesystem: dict[str, Union[bytes, str, dict[None, None]]],
) -> Mapping["rrg_pb2.Action", Callable[[Session], None]]:
  """Action handlers that emulate given Windows file hierarchy.

  Args:
    filesystem: A mapping from paths to file contents to use.

  Returns:
    A handlers that can be supplied to the `ExecuteFlow` helper.
  """
  # We need lambda as otherwise pytype sees it as type, not callable.
  path_cls = lambda path: pathlib.PureWindowsPath(path)  # pylint: disable=unnecessary-lambda
  return FakeFileHandlers(path_cls, filesystem)


def FakeFileHandlers(
    path_cls: Callable[[str], pathlib.Path],
    filesystem: dict[str, Union[bytes, str, dict[None, None]]],
) -> Mapping["rrg_pb2.Action", Callable[[Session], None]]:
  """Action handlers that emulate given file hierarchy.

  Args:
    path_cls: Path type to use (POSIX or Windows).
    filesystem: A mapping from paths to file contents to use.

  Returns:
    A handlers that can be supplied to the `ExecuteFlow` helper.
  """
  trie = {}

  for path, content in filesystem.items():
    path = path_cls(path)
    if not path.is_absolute():
      raise ValueError(f"Relative path: '{path}'")

    trie_node = trie
    for part in path.parent.parts:
      if part not in trie_node:
        trie_node[part] = dict()
      if not isinstance(trie_node[part], dict):
        raise ValueError(f"'{part}' of '{path}' not a directory")

      trie_node = trie_node[part]

    trie_node[path.name] = content

  timestamp = timestamp_pb2.Timestamp()
  timestamp.GetCurrentTime()

  def GetFileMetadataHandler(session: Session) -> None:
    args = rrg_get_file_metadata_pb2.Args()
    if not session.args.Unpack(args):
      raise RuntimeError(f"Invalid session arguments: {session.args}")

    def Walk(trie_node: Any, path: pathlib.PurePath, depth: int) -> None:
      result = rrg_get_file_metadata_pb2.Result()
      result.path.raw_bytes = str(path).encode("utf-8")
      result.metadata.unix_ino = id(trie_node)

      if depth > args.max_depth:
        return
      if not re.search(args.path_pruning_regex, str(path)):
        return

      if isinstance(trie_node, bytes):
        result.metadata.type = rrg_fs_pb2.FileMetadata.FILE
        result.metadata.size = len(trie_node)
        result.metadata.unix_mode |= stat.S_IFREG

        if args.md5:
          result.md5 = hashlib.md5(trie_node).digest()
        if args.sha1:
          result.sha1 = hashlib.sha1(trie_node).digest()
        if args.sha256:
          result.sha256 = hashlib.sha256(trie_node).digest()

      elif isinstance(trie_node, str):
        result.metadata.type = rrg_fs_pb2.FileMetadata.SYMLINK
        result.metadata.size = len(trie_node)
        result.metadata.unix_mode |= stat.S_IFLNK
        result.symlink.raw_bytes = trie_node.encode("utf-8")

      elif isinstance(trie_node, dict):
        result.metadata.type = rrg_fs_pb2.FileMetadata.DIR
        result.metadata.unix_mode |= stat.S_IFDIR

        for part in trie_node:
          Walk(trie_node=trie_node[part], path=path / part, depth=depth + 1)

      else:
        # We verified content type above.
        raise AssertionError(f"Impossible trie node type: {type(trie_node)}")

      result.metadata.access_time.CopyFrom(timestamp)
      result.metadata.modification_time.CopyFrom(timestamp)
      result.metadata.creation_time.CopyFrom(timestamp)

      if args.contents_regex:
        if not isinstance(trie_node, bytes):
          return
        if re.search(args.contents_regex.encode(), trie_node) is None:
          return

      session.Reply(result)

    for path in args.paths:
      path = path_cls(path.raw_bytes.decode("utf-8"))

      trie_node = trie
      try:
        for part in path.parts:
          trie_node = trie_node[part]
      except KeyError:
        logging.error("File does not exist: %r", path)
        continue

      Walk(trie_node, path, depth=0)

  def GetFileContentsHandler(session: Session) -> None:
    args = rrg_get_file_contents_pb2.Args()
    if not session.args.Unpack(args):
      raise RuntimeError(f"Invalid session arguments: {session.args}")

    for path in args.paths:
      result = rrg_get_file_contents_pb2.Result()
      result.path.CopyFrom(path)

      try:
        content = filesystem[path.raw_bytes.decode("utf-8")]
        if isinstance(content, str):
          content = filesystem[content]
          # TODO: Add support for non-absolute symlinks.
          # TODO: Add support for recursive symlinks.
          assert isinstance(content, bytes)
      except KeyError:
        result.error = "open failed"
        session.Reply(result)
        return

      offset = args.offset
      if args.length:
        content = content[offset : offset + args.length]
      else:
        content = content[offset:]

      while content:
        blob = rrg_blob_pb2.Blob()
        blob.data = content[:_MAX_BLOB_LEN]
        session.Send(rrg_pb2.Sink.BLOB, blob)

        result.offset = offset
        result.length = len(blob.data)
        result.blob_sha256 = hashlib.sha256(blob.data).digest()
        session.Reply(result)

        offset += _MAX_BLOB_LEN
        content = content[_MAX_BLOB_LEN:]

  def GetFileSha256Handler(session: Session) -> None:
    args = rrg_get_file_sha256_pb2.Args()
    if not session.args.Unpack(args):
      raise RuntimeError(f"Invalid session arguments: {session.args}")

    content = filesystem[args.path.raw_bytes.decode("utf-8")]
    if isinstance(content, str):
      content = filesystem[content]
      # TODO: Add support for non-absolute symlinks.
      # TODO: Add support for recursive symlinks.
      assert isinstance(content, bytes)

    if args.length:
      content = content[args.offset : args.offset + args.length]
    else:
      content = content[args.offset :]

    result = rrg_get_file_sha256_pb2.Result()
    result.path.CopyFrom(args.path)
    result.offset = args.offset
    result.length = len(content)
    result.sha256 = hashlib.sha256(content).digest()
    session.Reply(result)

  return {
      rrg_pb2.Action.GET_FILE_METADATA: GetFileMetadataHandler,
      rrg_pb2.Action.GET_FILE_CONTENTS: GetFileContentsHandler,
      rrg_pb2.Action.GET_FILE_SHA256: GetFileSha256Handler,
  }


def FakeWinregHandlers(
    winreg: dict["rrg_winreg_pb2.PredefinedKey", dict[str, Any]],
) -> Mapping["rrg_pb2.Action", Callable[[Session], None]]:
  """Action handlers that emulate given Windows Registry structure.

  Args:
    winreg: A trie representing Windows Registry contents.

  Returns:
    Handlers that can be supplied to the `ExecuteFlow` helper.
  """

  def Value(value: Any) -> rrg_winreg_pb2.Value:
    result = rrg_winreg_pb2.Value()

    if isinstance(value, str):
      result.string = value
    elif isinstance(value, bytes):
      result.bytes = value
    elif isinstance(value, int):
      result.uint32 = value
    else:
      raise ValueError(f"Unexpected value type: {type(value)}")

    return result

  def GetWinregValueHandler(session: Session) -> None:
    args = rrg_get_winreg_value_pb2.Args()
    if not session.args.Unpack(args):
      raise RuntimeError(f"Invalid session arguments: {session.args}")

    key = winreg[args.root]
    for key_part in args.key.split("\\"):
      key = key[key_part]

    result = rrg_get_winreg_value_pb2.Result()
    result.root = args.root
    result.key = args.key
    result.value.name = args.name

    if args.name in key:
      result.value.MergeFrom(Value(key[args.name]))
    elif not args.name:
      # Windows always has a default empty string (if not set otherwise) as key
      # default value, so we provide it as well.
      result.value.MergeFrom(Value(""))

    session.Reply(result)

  def ListWinregValuesHandler(session: Session) -> None:
    args = rrg_list_winreg_values_pb2.Args()
    if not session.args.Unpack(args):
      raise RuntimeError(f"Invalid session arguments: {session.args}")

    key = winreg[args.root]
    for key_part in args.key.split("\\"):
      key = key[key_part]

    if not isinstance(key, dict):
      raise RuntimeError(f"Invalid registry key: {args.key}")

    def Walk(trie_node: Any, key: str, depth: int) -> None:
      if depth > args.max_depth:
        return

      # Windows always has a default empty string (if not set otherwise) as key
      # default value, so we use such a singleton dict as a base.
      for name, content in ({"": ""} | trie_node).items():
        if isinstance(content, dict):
          Walk(trie_node=content, key=f"{key}\\{name}", depth=depth + 1)
          continue

        result = rrg_list_winreg_values_pb2.Result()
        result.root = args.root
        result.key = key
        result.value.name = name
        result.value.MergeFrom(Value(content))

        session.Reply(result)

    Walk(key, args.key, depth=0)

  def ListWinregKeysHandler(session: Session) -> None:
    args = rrg_list_winreg_keys_pb2.Args()
    if not session.args.Unpack(args):
      raise RuntimeError(f"Invalid session arguments: {session.args}")

    key = winreg[args.root]
    for key_part in args.key.split("\\"):
      key = key[key_part]

    if not isinstance(key, dict):
      raise RuntimeError(f"Invalid registry key: {args.key}")

    def Walk(trie_node: Any, subkey: list[str]) -> None:
      # We still want to return direct entries if `args.max_depth` is not set,
      # so we `or 1`.
      if len(subkey) + 1 > (args.max_depth or 1):
        return

      for name, content in trie_node.items():
        if not isinstance(content, dict):
          continue

        result = rrg_list_winreg_keys_pb2.Result()
        result.root = args.root
        result.key = args.key
        result.subkey = "\\".join(subkey + [name])

        session.Reply(result)

        Walk(trie_node=content, subkey=subkey + [name])

    Walk(key, [])

  return {
      rrg_pb2.Action.GET_WINREG_VALUE: GetWinregValueHandler,
      rrg_pb2.Action.LIST_WINREG_VALUES: ListWinregValuesHandler,
      rrg_pb2.Action.LIST_WINREG_KEYS: ListWinregKeysHandler,
  }


def _EvalFilter(
    item_filter: rrg_pb2.Filter,
    item: message_pb2.Message,
) -> bool:
  """Evaluates RRG filter for the given message."""
  for item_cond in item_filter.conditions:
    if _EvalCondition(item_cond, item):
      return True

  return False


def _EvalCondition(
    item_cond: rrg_pb2.Condition,
    item: message_pb2.Message,
) -> bool:
  """Evaluates RRG condition for the given message."""
  if not item_cond.field:
    raise RuntimeError("No field")

  field_value = item
  field_desc: descriptor_pb2.FieldDescriptor

  for field in item_cond.field:
    field_desc = field_value.DESCRIPTOR.fields_by_number[field]
    field_value = getattr(field_value, field_desc.name)

  result: bool

  if item_cond.HasField("bool_equal"):
    assert field_desc.type == descriptor_pb2.FieldDescriptor.TYPE_BOOL
    assert isinstance(field_value, bool)
    result = field_value == item_cond.bool_equal
  elif item_cond.HasField("string_equal"):
    assert field_desc.type == descriptor_pb2.FieldDescriptor.TYPE_STRING
    assert isinstance(field_value, str)
    result = field_value == item_cond.string_equal
  elif item_cond.HasField("string_match"):
    assert isinstance(field_value, str)
    assert field_desc.type == descriptor_pb2.FieldDescriptor.TYPE_STRING
    result = re.match(item_cond.string_match, field_value) is not None
  elif item_cond.HasField("bytes_equal"):
    assert field_desc.type == descriptor_pb2.FieldDescriptor.TYPE_BYTES
    assert isinstance(field_value, bytes)
    result = field_value == item_cond.bytes_equal
  elif item_cond.HasField("bytes_match"):
    assert field_desc.type == descriptor_pb2.FieldDescriptor.TYPE_BYTES
    assert isinstance(field_value, bytes)
    result = re.match(item_cond.bytes_match.encode(), field_value) is not None
  elif item_cond.HasField("uint64_equal"):
    assert field_desc.type in [
        descriptor_pb2.FieldDescriptor.TYPE_UINT32,
        descriptor_pb2.FieldDescriptor.TYPE_UINT64,
    ]
    assert isinstance(field_value, int)
    result = field_value == item_cond.uint64_equal
  elif item_cond.HasField("uint64_less"):
    assert field_desc.type in [
        descriptor_pb2.FieldDescriptor.TYPE_UINT32,
        descriptor_pb2.FieldDescriptor.TYPE_UINT64,
    ]
    assert isinstance(field_value, int)
    result = field_value < item_cond.uint64_less
  elif item_cond.HasField("int64_equal"):
    assert field_desc.type in [
        descriptor_pb2.FieldDescriptor.TYPE_INT32,
        descriptor_pb2.FieldDescriptor.TYPE_INT64,
    ]
    assert isinstance(field_value, int)
    result = field_value == item_cond.int64_equal
  elif item_cond.HasField("int64_less"):
    assert field_desc.type in [
        descriptor_pb2.FieldDescriptor.TYPE_INT32,
        descriptor_pb2.FieldDescriptor.TYPE_INT64,
    ]
    assert isinstance(field_value, int)
    result = field_value < item_cond.int64_less
  else:
    raise RuntimeError("No condition operator")

  if item_cond.negated:
    result = not result

  return result


# Value used by RRG.
_MAX_BLOB_LEN = 2 * 1024 * 1024
