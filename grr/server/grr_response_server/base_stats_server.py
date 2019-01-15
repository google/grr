#!/usr/bin/env python
"""Abstract base class for serving statistics."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc


from future.utils import with_metaclass


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
    super(PortInUseError,
          self).__init__("Port {} is already in use.".format(port))
    self.port = port


class BaseStatsServer(with_metaclass(abc.ABCMeta, object)):
  """Abstract base class for statistics server.

  Attributes:
    port: The TCP port that the server should listen to.
  """

  def __init__(self, port):
    """Instantiates a new BaseStatsServer.

    Args:
      port: The TCP port that the server should listen to.
    """
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
