#!/usr/bin/env python
"""Abstracts encryption and authentication."""

import zlib

from google.protobuf import message as protobuf_message

from grr_response_proto import jobs_pb2


class UnpackError(Exception):
  pass


# The old agent has a message list size limit of 1 MiB. However, it is possible
# for a single message to exceed that and there is no strict limit enforcement
# on that, although most actions cap it 1-4 MiB. But some use bigger caps, e.g.
# `ExecuteBinaryCommand` limit stdout and stderr to 10 MiB which totals 20 MiB.
# Our database implementations cannot handle messages bigger than 16 MiB anyway
# (and in fact will fail even at smaller payloads), so we use that as the upper
# limit.
_UNCOMPRESSED_MESSAGE_LIST_BYTE_LIMIT = 16 * 1024 * 1024  # 16 MiB.


def PackMessageList(
    message_list: jobs_pb2.MessageList,
    packed_message_list: jobs_pb2.PackedMessageList,
) -> None:
  """Packs the `MessageList` into the `PackedMessageList` proto."""
  # By default uncompress
  uncompressed_data = message_list.SerializeToString()
  packed_message_list.message_list = uncompressed_data

  compressed_data = zlib.compress(uncompressed_data)

  # Only compress if it buys us something.
  if len(compressed_data) < len(uncompressed_data):
    packed_message_list.compression = jobs_pb2.PackedMessageList.ZCOMPRESSION
    packed_message_list.message_list = compressed_data


def UnpackMessageList(
    packed_message_list: jobs_pb2.PackedMessageList,
) -> jobs_pb2.MessageList:
  """Unpacks the message data from packed_message_list.

  Args:
    packed_message_list: A PackedMessageList rdfvalue with some data in it.

  Returns:
    a MessageList proto.

  Raises:
    UnpackError: If unpacking fails.
  """
  compression = packed_message_list.compression
  if compression == jobs_pb2.PackedMessageList.UNCOMPRESSED:
    data = packed_message_list.message_list

  elif compression == jobs_pb2.PackedMessageList.ZCOMPRESSION:
    decompressor = zlib.decompressobj()
    try:
      data = decompressor.decompress(
          packed_message_list.message_list,
          max_length=_UNCOMPRESSED_MESSAGE_LIST_BYTE_LIMIT,
      )
    except zlib.error as e:
      raise UnpackError("Failed to decompress") from e

    # We use `==` rather than `>` as this is how capping using `max_length`
    # works. The limit is rather arbitrary anyway, so 1 byte in any direction
    # should not matter much.
    if len(data) == _UNCOMPRESSED_MESSAGE_LIST_BYTE_LIMIT:
      raise UnpackError(
          "Uncompressed message size limit reached "
          f"({_UNCOMPRESSED_MESSAGE_LIST_BYTE_LIMIT} bytes)"
      )
    # The streaming decompressor does not error when it reached the end of the
    # input while still expecting more (so that it is possible to continuously
    # feed it). Because we know there is no more data incoming, we just verify
    # whether the decompressor expects more or not.
    if not decompressor.eof:
      raise UnpackError("Incomplete message list")
  else:
    raise UnpackError("Compression scheme not supported")

  result = jobs_pb2.MessageList()
  try:
    result.ParseFromString(data)
  except protobuf_message.DecodeError as error:
    raise UnpackError("Failed to parse") from error

  return result
