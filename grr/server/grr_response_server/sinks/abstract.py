#!/usr/bin/env python
"""A module with definition of the sink interface.

See documentation for the root `sinks` module for more details.
"""

import abc

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
