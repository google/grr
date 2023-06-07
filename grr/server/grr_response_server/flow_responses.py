#!/usr/bin/env python
"""The class encapsulating flow responses."""

from typing import Any, Iterable, Iterator, Optional, Sequence, TypeVar

from google.protobuf import any_pb2
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects


T = TypeVar("T")


class Responses(Iterable[T]):
  """An object encapsulating all the responses to a request."""

  def __init__(self):
    self.status: Optional[rdf_flow_objects.FlowStatus] = None
    self.request_data: Optional[Any] = None
    self.success = True
    self.request = None
    self.responses = []

  @classmethod
  def FromResponses(cls, request=None, responses=None) -> "Responses":
    """Creates a Responses object from new style flow request and responses."""
    res = cls()
    res.request = request
    if request:
      res.request_data = request.request_data

    for r in responses or []:
      if isinstance(r, rdf_flow_objects.FlowResponse):
        res.responses.append(r.payload)
      elif isinstance(r, rdf_flow_objects.FlowStatus):
        res.status = r
        res.success = r.status == "OK"
      elif isinstance(r, rdf_flow_objects.FlowIterator):
        pass
      else:
        raise TypeError("Got unexpected response type: %s" % type(r))
    return res

  # `pytype` for whatever cryptic reason fails with `name-error` when checking
  # this method's signature, so we disable it.
  # pytype: disable=name-error
  @classmethod
  def FromResponsesProto2Any(
      cls,
      responses: Sequence[rdf_flow_objects.FlowMessage],
  ) -> "Responses[any_pb2.Any]":
    # pytype: enable=name-error
    """Creates a `Response` object from raw flow responses.

    Unlike the `Responses.FromResponses` method, this method does not use any
    RDF-value magic to deserialize `Any` messages on the fly. Instead, it just
    passes raw `Any` message as it is stored in the `any_payload` field of the
    `FlowResponse` message.

    Args:
      responses: Flow responses from which to construct this object.

    Returns:
      Wrapped flow responses.
    """
    result = Responses()

    for response in responses:
      if isinstance(response, rdf_flow_objects.FlowStatus):
        if result.status is not None:
          raise ValueError(f"Duplicated status response: {response}")

        if response.status == rdf_flow_objects.FlowStatus.Status.OK:
          result.success = True
        else:
          result.success = False

        result.status = response
      elif isinstance(response, rdf_flow_objects.FlowResponse):
        result.responses.append(response.any_payload.AsPrimitiveProto())
      else:
        # Note that this also covers `FlowIterator`—it is a legacy class that
        # should no longer be used and new state methods (that are expected to
        # trigger this code path) should not rely on it.
        raise TypeError(f"Unexpected response: {response}")

    if result.status is None:
      raise ValueError("Missing status response")

    return result

  def __iter__(self) -> Iterator[T]:
    return iter(self.responses)

  def First(self) -> Optional[T]:
    """A convenience method to return the first response."""
    for x in self:
      return x

  def __len__(self) -> int:
    return len(self.responses)

  def __bool__(self) -> bool:
    return bool(self.responses)


class FakeResponses(Responses):
  """An object which emulates the responses.

  This is only used internally to call a state method inline.
  """

  def __init__(self, messages, request_data):
    super().__init__()
    self.success = True
    self.responses = messages or []
    self.request_data = request_data
    self.iterator = None
