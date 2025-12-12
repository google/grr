#!/usr/bin/env python
"""Utility functions and classes for GRR API client library."""

from collections.abc import Callable, Iterator
import io
import itertools
import struct
import time
from typing import Any, IO, TypeVar, Union

from cryptography.hazmat.primitives.ciphers import aead

from google.protobuf import any_pb2
from google.protobuf import wrappers_pb2
from google.protobuf import descriptor
from google.protobuf import message
from google.protobuf import symbol_database
from grr_api_client import errors
from grr_response_proto import containers_pb2
from grr_response_proto import crowdstrike_pb2
from grr_response_proto import deprecated_pb2
from grr_response_proto import dummy_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import large_file_pb2
from grr_response_proto import osquery_pb2
from grr_response_proto import pipes_pb2
from grr_response_proto import read_low_level_pb2
from grr_response_proto import timeline_pb2
from grr_response_proto.api import artifact_pb2
from grr_response_proto.api import client_pb2
from grr_response_proto.api import config_pb2
from grr_response_proto.api import cron_pb2
from grr_response_proto.api import flow_pb2
from grr_response_proto.api import hunt_pb2
from grr_response_proto.api import metadata_pb2
from grr_response_proto.api import output_plugin_pb2
from grr_response_proto.api import reflection_pb2
from grr_response_proto.api import signed_commands_pb2
from grr_response_proto.api import user_pb2
from grr_response_proto.api import vfs_pb2
from grr_response_proto.api import yara_pb2


class ProtobufTypeNotFound(errors.Error):
  pass


_T = TypeVar("_T")


class ItemsIterator(Iterator[_T]):
  """Iterator object with a total_count property."""

  def __init__(
      self,
      items: Iterator[_T],
      total_count: int,
  ) -> None:
    super().__init__()

    self.items = items
    self.total_count = total_count

  def __iter__(self) -> Iterator[_T]:
    for i in self.items:
      yield i

  def __next__(self) -> _T:
    return next(self.items)


_T1 = TypeVar("_T1")
_T2 = TypeVar("_T2")


def MapItemsIterator(
    function: Callable[[_T1], _T2],
    items: ItemsIterator[_T1],
) -> ItemsIterator[_T2]:
  """Maps ItemsIterator via given function."""
  return ItemsIterator(
      items=map(function, items), total_count=items.total_count
  )


class BinaryChunkIterator:
  """Iterator object for binary streams."""

  chunks: Iterator[bytes]

  def __init__(self, chunks: Iterator[bytes]) -> None:
    super().__init__()

    self.chunks = chunks

  def __iter__(self) -> Iterator[bytes]:
    for c in self.chunks:
      yield c

  def __next__(self) -> bytes:
    return next(self.chunks)

  def WriteToStream(self, out: IO[bytes]) -> None:
    for c in self:
      out.write(c)

  def WriteToFile(self, file_name: str) -> None:
    with open(file_name, "wb") as fd:
      self.WriteToStream(fd)

  def DecodeCrowdStrikeQuarantineEncoding(self) -> "BinaryChunkIterator":
    """Decodes Crowdstrike quarantine file."""

    def DecoderGenerator() -> Iterator[bytes]:
      for index, chunk in enumerate(self):
        if index == 0:
          if len(chunk) < 12:
            raise ValueError(
                "Unsupported chunk size, chunks need to be at least 12 bytes"
            )

          if chunk[0:4] != b"CSQD":
            raise ValueError(
                "File does not start with Crowdstrike quarantine identifier"
            )

          # TODO: Add a check if the actual file size matches the
          # value in chunk[4:12].

          # The remainder of the first chunk belongs to the actual file.
          chunk = chunk[12:]

        yield Xor(chunk, 0x7E)

    return BinaryChunkIterator(DecoderGenerator())


# Default poll interval in seconds.
DEFAULT_POLL_INTERVAL: int = 15

# Default poll timeout in seconds.
DEFAULT_POLL_TIMEOUT: int = 3600


def Poll(
    generator: Callable[[], _T],
    condition: Callable[[_T], bool],
    interval: int = DEFAULT_POLL_INTERVAL,
    timeout: int = DEFAULT_POLL_TIMEOUT,
) -> _T:
  """Periodically calls generator function until a condition is satisfied."""
  started = time.time()
  while True:
    obj = generator()
    check_result = condition(obj)
    if check_result:
      return obj

    if timeout and (time.time() - started) > timeout:
      raise errors.PollTimeoutError(
          "Polling on %s timed out after %ds." % (obj, timeout)
      )
    time.sleep(interval)


AFF4_PREFIX = "aff4:/"


def UrnStringToClientId(urn: str) -> str:
  """Converts given URN string to a client id string."""
  if urn.startswith(AFF4_PREFIX):
    urn = urn[len(AFF4_PREFIX) :]

  components = urn.split("/")
  return components[0]


def UrnStringToHuntId(urn: str) -> str:
  """Converts given URN string to a flow id string."""
  if urn.startswith(AFF4_PREFIX):
    urn = urn[len(AFF4_PREFIX) :]

  components = urn.split("/")
  if len(components) != 2 or components[0] != "hunts":
    raise ValueError("Invalid hunt URN: %s" % urn)

  return components[-1]


TYPE_URL_PREFIX: str = "type.googleapis.com/"
GRR_PACKAGE_NAME: str = metadata_pb2.DESCRIPTOR.package


def GetTypeUrl(proto: message.Message) -> str:
  """Returns type URL for a given proto."""

  return TYPE_URL_PREFIX + proto.DESCRIPTOR.full_name


def TypeUrlToMessage(type_url: str) -> message.Message:
  """Returns a message instance corresponding to a given type URL."""

  if not type_url.startswith(TYPE_URL_PREFIX):
    raise ValueError(
        "Type URL has to start with a prefix %s: %s"
        % (TYPE_URL_PREFIX, type_url)
    )

  full_name = type_url[len(TYPE_URL_PREFIX) :]

  # In open-source, proto files used not to have a package specified. Because
  # the API can be used with some legacy flows and hunts as well, we need to
  # make sure that we are still able to work with the old data.
  #
  # After some grace period, this code should be removed.
  if not full_name.startswith(GRR_PACKAGE_NAME):
    full_name = f"{GRR_PACKAGE_NAME}.{full_name}"

  try:
    return symbol_database.Default().GetSymbol(full_name)()
  except KeyError as e:
    raise ProtobufTypeNotFound(str(e))


_M = TypeVar("_M", bound=message.Message)


def CopyProto(proto: _M) -> _M:
  new_proto = proto.__class__()
  new_proto.ParseFromString(proto.SerializeToString())
  return new_proto


class UnknownProtobuf(object):
  """An unknown protobuf message."""

  def __init__(
      self,
      proto_type: str,
      proto_any: any_pb2.Any,
  ) -> None:
    super().__init__()

    self.type = proto_type  # type: str
    self.original_value = proto_any  # type: any_pb2.Any


def UnpackAny(
    proto_any: any_pb2.Any,
) -> Union[UnknownProtobuf, message.Message]:
  try:
    proto = TypeUrlToMessage(proto_any.type_url)
  except ProtobufTypeNotFound as e:
    return UnknownProtobuf(str(e), proto_any)

  proto_any.Unpack(proto)
  return proto


def MessageToFlatDict(
    msg: message.Message,
    transform: Callable[[descriptor.FieldDescriptor, Any], Any],
) -> dict[str, Any]:
  """Converts the given Protocol Buffers message to a flat dictionary.

  Fields of nested messages will be represented through keys of a path with
  dots. Consider the following Protocol Buffers message:

      foo {
          bar: 42
          baz {
              quux: "thud"
          }
      }

  Its representation as a flat Python dictionary is the following:

      { "foo.bar": 42, "foo.baz.quux": "thud" }

  Args:
    msg: A message to convert.
    transform: A transformation to apply to primitive values.

  Returns:
    A flat dictionary corresponding to the given message.
  """
  # Using ordered dictionary guarantees stable order of fields in the result.
  result = dict()

  def Recurse(msg: message.Message, prev: tuple[str, ...]) -> None:
    fields = sorted(msg.ListFields(), key=lambda field: field[0].name)
    for field, value in fields:
      curr = prev + (field.name,)
      if field.type == descriptor.FieldDescriptor.TYPE_MESSAGE:
        Recurse(value, curr)
      else:
        result[".".join(curr)] = transform(field, value)

  Recurse(msg, ())

  return result


def Xor(bytestr: bytes, key: int) -> bytes:
  """Returns a `bytes` object where each byte has been xored with key."""
  return bytes([byte ^ key for byte in bytestr])


class _Unchunked(io.RawIOBase, IO[bytes]):  # pytype: disable=signature-mismatch  # overriding-return-type-checks
  """A raw file-like object that reads chunk stream on demand."""

  def __init__(self, chunks: Iterator[bytes]) -> None:
    """Initializes the object."""
    super().__init__()
    self._chunks = chunks
    self._buf = io.BytesIO()

  def readable(self) -> bool:
    return True

  def readall(self) -> bytes:
    return b"".join(self._chunks)

  def readinto(self, buf: bytearray) -> int:
    if self._buf.tell() == len(self._buf.getbuffer()):
      self._buf.seek(0, io.SEEK_SET)
      self._buf.truncate()
      self._buf.write(next(self._chunks, b""))
      self._buf.seek(0, io.SEEK_SET)

    return self._buf.readinto(buf)


def AEADDecrypt(stream: IO[bytes], key: bytes) -> IO[bytes]:
  """Decrypts given file-like object using AES algorithm in GCM mode.

  Refer to the encryption documentation to learn about the details of the format
  that this function allows to decode.

  Args:
    stream: A file-like object to decrypt.
    key: A secret key used for decrypting the data.

  Returns:
    A file-like object with decrypted data.
  """
  aesgcm = aead.AESGCM(key)

  def Generate() -> Iterator[bytes]:
    # Buffered reader should accept `IO[bytes]` but for now it accepts only
    # `RawIOBase` (which is a concrete base class for all I/O implementations).
    reader = io.BufferedReader(stream)  # pytype: disable=wrong-arg-types

    # We abort early if there is no data in the stream. Otherwise we would try
    # to read nonce and fail.
    if not reader.peek():
      return

    for idx in itertools.count():
      nonce = reader.read(_AEAD_NONCE_SIZE)

      # As long there is some data in the buffer (and there should be because of
      # the initial check) there should be a fixed-size nonce prepended to each
      # chunk.
      if len(nonce) != _AEAD_NONCE_SIZE:
        raise EOFError(f"Incorrect nonce length: {len(nonce)}")

      chunk = reader.read(_AEAD_CHUNK_SIZE + 16)

      # `BufferedReader#peek` will return non-empty byte string if there is more
      # data available in the stream.
      is_last = reader.peek() == b""  # pylint: disable=g-explicit-bool-comparison

      adata = _AEAD_ADATA_FORMAT.pack(idx, is_last)

      yield aesgcm.decrypt(nonce, chunk, adata)

      if is_last:
        break

  return io.BufferedReader(_Unchunked(Generate()))


# We use 12 bytes (96 bits) as it is the recommended IV length by NIST for best
# performance [1]. See AESGCM documentation for more details.
#
# [1]: https://csrc.nist.gov/publications/detail/sp/800-38d/final
_AEAD_NONCE_SIZE = 12

# Because chunk size is crucial to the security of the whole procedure, we don't
# let users pick their own chunk size. Instead, we use a fixed-size chunks of
# 4 mebibytes.
_AEAD_CHUNK_SIZE = 4 * 1024 * 1024

# As associated data for each encrypted chunk we use an integer denoting chunk
# id followed by a byte with information whether this is the last chunk.
_AEAD_ADATA_FORMAT = struct.Struct("!Q?")


def RegisterProtoDescriptors(
    db: symbol_database.SymbolDatabase,
    *additional_descriptors: descriptor.FileDescriptor,
) -> None:
  """Registers all API-related descriptors in a given symbol DB."""
  # keep-sorted start
  db.RegisterFileDescriptor(artifact_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(client_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(config_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(containers_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(cron_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(crowdstrike_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(deprecated_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(dummy_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(flow_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(flows_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(hunt_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(jobs_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(large_file_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(metadata_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(osquery_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(output_plugin_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(pipes_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(read_low_level_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(reflection_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(signed_commands_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(timeline_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(user_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(vfs_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(yara_pb2.DESCRIPTOR)
  # keep-sorted end

  db.RegisterFileDescriptor(
      wrappers_pb2.DESCRIPTOR
  )  # type: ignore[attr-defined]

  for d in additional_descriptors:
    db.RegisterFileDescriptor(d)
