#!/usr/bin/env python
"""Unprivileged memory RPC client code."""

import abc
from typing import TypeVar, Generic, Iterable

from grr_response_client.unprivileged import communication
from grr_response_client.unprivileged.proto import memory_pb2


class ConnectionWrapper:
  """Wraps a connection, adding protobuf serialization of messages."""

  def __init__(self, connection: communication.Connection):
    self._connection = connection

  def Send(self, request: memory_pb2.Request) -> None:
    self._connection.Send(
        communication.Message(request.SerializeToString(), b""))

  def Recv(self) -> memory_pb2.Response:
    raw_response, _ = self._connection.Recv()
    response = memory_pb2.Response()
    response.ParseFromString(raw_response)
    return response


class Error(Exception):
  """Base class for exceptions in this module."""
  pass


class OperationError(Exception):
  """Error while executing the operation."""

  def __init__(self, message: str, formatted_exception: str):
    """Constructor.

    Args:
      message: the exception message
      formatted_exception: the remote exception formatted using
        traceback.format_exc()
    """
    super().__init__(message)
    self.formatted_exception = formatted_exception


RequestType = TypeVar("RequestType")
ResponseType = TypeVar("ResponseType")


class OperationHandler(abc.ABC, Generic[RequestType, ResponseType]):
  """Base class for RPC handlers."""

  def __init__(self, connection: ConnectionWrapper):
    self._connection = connection

  def Run(self, request: RequestType) -> ResponseType:
    self._connection.Send(self.PackRequest(request))
    packed_response = self._connection.Recv()

    if packed_response.HasField("exception"):
      raise OperationError(packed_response.exception.message,
                           packed_response.exception.formatted_exception)
    else:
      response = self.UnpackResponse(packed_response)
      return response

  @abc.abstractmethod
  def UnpackResponse(self, response: memory_pb2.Response) -> ResponseType:
    """Extracts an inner Response message from a response message."""
    pass

  @abc.abstractmethod
  def PackRequest(self, request: RequestType) -> memory_pb2.Request:
    """Packs an inner Request message into a request message."""
    pass


class UploadSignatureHandler(
    OperationHandler[memory_pb2.UploadSignatureRequest,
                     memory_pb2.UploadSignatureResponse]):
  """Implements the UploadSignature RPC."""

  def UnpackResponse(
      self,
      response: memory_pb2.Response) -> memory_pb2.UploadSignatureResponse:
    return response.upload_signature_response

  def PackRequest(
      self, request: memory_pb2.UploadSignatureRequest) -> memory_pb2.Request:
    return memory_pb2.Request(upload_signature_request=request)


class ProcessScanHandler(OperationHandler[memory_pb2.ProcessScanRequest,
                                          memory_pb2.ProcessScanResponse]):
  """Implements the ProcessScan RPC."""

  def UnpackResponse(
      self, response: memory_pb2.Response) -> memory_pb2.ProcessScanResponse:
    return response.process_scan_response

  def PackRequest(self,
                  request: memory_pb2.ProcessScanRequest) -> memory_pb2.Request:
    return memory_pb2.Request(process_scan_request=request)


class Client:
  """Client for the RPC memory service."""

  def __init__(self, connection: communication.Connection):
    self._connection = ConnectionWrapper(connection)

  def UploadSignature(self, yara_signature: str):
    """Uploads a yara signature to be used for this connection."""
    request = memory_pb2.UploadSignatureRequest(yara_signature=yara_signature)
    UploadSignatureHandler(self._connection).Run(request)

  def ProcessScan(self, serialized_file_descriptor: int,
                  chunks: Iterable[memory_pb2.Chunk],
                  timeout_seconds: int) -> memory_pb2.ProcessScanResponse:
    """Scans process memory.

    Args:
      serialized_file_descriptor: Serialized file descriptor for the process
        memory. The file descriptor must be accessible by the server process.
      chunks: Chunks (offset, size) to scan.
      timeout_seconds: Timeout in seconds.

    Returns:
      A `ScanResult` proto.
    """
    request = memory_pb2.ProcessScanRequest(
        serialized_file_descriptor=serialized_file_descriptor,
        chunks=chunks,
        timeout_seconds=timeout_seconds)
    response = ProcessScanHandler(self._connection).Run(request)
    return response


def CreateMemoryClient(connection: communication.Connection) -> Client:
  """Creates a memory client."""
  return Client(connection)
