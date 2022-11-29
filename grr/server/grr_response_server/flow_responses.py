#!/usr/bin/env python
"""The class encapsulating flow responses."""

from typing import Iterable, Iterator, Optional, TypeVar

from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects


T = TypeVar("T")


class Responses(Iterable[T]):
  """An object encapsulating all the responses to a request."""

  def __init__(self):
    self.status: Optional[rdf_flow_objects.FlowStatus] = None
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

  # TODO: Remove after support for Python 2 is dropped.
  __nonzero__ = __bool__


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
