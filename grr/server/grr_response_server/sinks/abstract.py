#!/usr/bin/env python
"""A module with definition of the sink interface.

See documentation for the root `sinks` module for more details.
"""

import abc
from collections.abc import Sequence

from grr_response_proto import rrg_pb2


class Sink(abc.ABC):
  """An interface that all sinks should implement."""

  @abc.abstractmethod
  def Accept(self, client_id: str, parcel: rrg_pb2.Parcel) -> None:
    """Processes the given parcel.

    Args:
      client_id: An identifier of the client from which the message came.
      parcel: A parcel to process.
    """

  # TODO: Make `AcceptMany abstract and provide default
  # implementation for the `Accept` method.
  def AcceptMany(
      self,
      client_id: str,
      parcels: Sequence[rrg_pb2.Parcel],
  ) -> None:
    """Processes given parcels.

    Args:
      client_id: An identifier of the client from which the messages came.
      parcels: Parcels to process.
    """
    for parcel in parcels:
      self.Accept(client_id, parcel)
