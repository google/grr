#!/usr/bin/env python
"""A module with definition of the decoder interface."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc

from future.utils import with_metaclass


class AbstractDecoder(with_metaclass(abc.ABCMeta, object)):
  """An abstract interface that all decoders should implement."""

  # A decoder name used to uniquely identify it.
  NAME = None

  @abc.abstractmethod
  def Check(self, filedesc):
    """Checks whether given decoder is applicable to the given file.

    Args:
      filedesc: A file-like object to check.

    Returns:
      `True` if the decoder is able to handle the file, `False` otherwise.
    """

  @abc.abstractmethod
  def Decode(self, filedesc):
    """Decodes the specified file.

    Args:
      filedesc: A file-like object to decode.

    Yields:
      A chunks of `bytes` of the decoded file.
    """
