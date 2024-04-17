#!/usr/bin/env python
"""A testing utilities to simplify test code working with sinks."""

import collections
from typing import Sequence

from grr_response_server import sinks
from grr_response_proto import rrg_pb2


class FakeSink(sinks.Sink):
  """A fake sink implementation that accumulates parcels in-memory.

  Accumulated parcels can then be inspected in test cases.
  """

  def __init__(self):
    super().__init__()
    self._parcels: dict[str, list[rrg_pb2.Parcel]] = collections.defaultdict(
        list
    )

  def Parcels(self, client_id: str) -> Sequence[rrg_pb2.Parcel]:
    """Returns the list of parcels accumulated for the specified client.

    Args:
      client_id: An identifier of the client for which to retrieve parcels for.

    Returns:
      A list of parcels for the specified client.
    """
    return self._parcels[client_id]

  # TODO: Add the `@override` annotation [1] once we can use
  # Python 3.12 features.
  #
  # [1]: https://peps.python.org/pep-0698/
  def Accept(self, client_id: str, parcel: rrg_pb2.Parcel) -> None:
    self._parcels[client_id].append(parcel)
