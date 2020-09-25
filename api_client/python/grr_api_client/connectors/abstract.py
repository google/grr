#!/usr/bin/env python
"""API connector base class definition."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
from typing import Optional

from google.protobuf import message
from grr_api_client import utils


class Connector(abc.ABC):
  """An abstract GRR connector class."""

  @property
  @abc.abstractmethod
  def page_size(self) -> int:
    raise NotImplementedError()

  @abc.abstractmethod
  def SendRequest(
      self,
      handler_name: str,
      args: message.Message,
  ) -> Optional[message.Message]:
    """Sends a request to the GRR server.

    Args:
      handler_name: A handler to which the request should be delivered to.
      args: Arguments of the request to pass to the handler.

    Returns:
      A response from the server (if any).
    """
    raise NotImplementedError()

  @abc.abstractmethod
  def SendStreamingRequest(
      self,
      handler_name: str,
      args: message.Message,
  ) -> utils.BinaryChunkIterator:
    """Sends a streaming request to the GRR server.

    Args:
      handler_name: A handler to which the request should be delivered to.
      args: Arguments of the request to pass to the handler.

    Returns:
      An iterator over binary chunks that the server responded with.
    """
    raise NotImplementedError()
