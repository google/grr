#!/usr/bin/env python
"""Abstract base class for serving statistics."""

import abc


class PortInUseError(Exception):
  """Error thrown when a server tries to bind to a used port.

  Attributes:
    port: The port being used.
  """

  def __init__(self, port):
    """Instantiates a new PortInUseError.

    Args:
      port: The port being used.
    """
    super().__init__("Port {} is already in use.".format(port))
    self.port = port


class BaseStatsServer(metaclass=abc.ABCMeta):
  """Abstract base class for statistics server.

  Attributes:
    address: The IP address of the server to bind.
    port: The TCP port that the server should listen to.
  """

  def __init__(self, address, port):
    """Instantiates a new BaseStatsServer.

    Args:
      address: The IP address of the server to bind.
      port: The TCP port that the server should listen to.
    """
    self.address = address
    self.port = port

  @abc.abstractmethod
  def Start(self):
    """Starts serving statistics.

    Raises:
      PortInUseError: The given port is already used.
    """
    raise NotImplementedError()

  @abc.abstractmethod
  def Stop(self):
    """Stops serving statistics."""
    raise NotImplementedError()
