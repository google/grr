#!/usr/bin/env python
"""Generic parsers (for GRR server and client code)."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

from future.builtins import filter
from typing import Iterator
from typing import Text

from grr_response_core.lib import factory
from grr_response_core.lib.parsers import abstract
from grr_response_core.lib.util import collection
from grr_response_core.lib.util import precondition

ParseError = abstract.ParseError

Parser = abstract.Parser
SingleResponseParser = abstract.SingleResponseParser
SingleFileParser = abstract.SingleFileParser
MultiResponseParser = abstract.MultiResponseParser
MultiFileParser = abstract.MultiFileParser

SINGLE_RESPONSE_PARSER_FACTORY = factory.Factory(SingleResponseParser)
MULTI_RESPONSE_PARSER_FACTORY = factory.Factory(MultiResponseParser)
SINGLE_FILE_PARSER_FACTORY = factory.Factory(SingleFileParser)
MULTI_FILE_PARSER_FACTORY = factory.Factory(MultiFileParser)


class ArtifactParserFactory(object):
  """A factory wrapper class that yields parsers for specific artifact."""

  def __init__(self, artifact_name):
    """Initializes the artifact parser factory.

    Args:
      artifact_name: A name of the artifact this factory is supposed to provide
        parser instances for.
    """
    precondition.AssertType(artifact_name, Text)
    self._artifact_name = artifact_name

  def HasParsers(self):
    return (self.HasSingleResponseParsers() or self.HasMultiResponseParsers() or
            self.HasSingleFileParsers() or self.HasMultiFileParsers())

  def HasSingleResponseParsers(self):
    return any(self.SingleResponseParsers())

  def SingleResponseParsers(self):
    # TODO: Apparently, pytype does not understand that we use
    # `filter` from the `future` package (which returns an iterator), instead of
    # builtin one which in Python 2 returns lists.
    return filter(self._IsSupported, SINGLE_RESPONSE_PARSER_FACTORY.CreateAll())  # pytype: disable=bad-return-type

  def HasMultiResponseParsers(self):
    return any(self.MultiResponseParsers())

  def MultiResponseParsers(self):
    # TODO: See above.
    return filter(self._IsSupported, MULTI_RESPONSE_PARSER_FACTORY.CreateAll())  # pytype: disable=bad-return-type

  def HasSingleFileParsers(self):
    return any(self.SingleFileParsers())

  def SingleFileParsers(self):
    # TODO: See above.
    return filter(self._IsSupported, SINGLE_FILE_PARSER_FACTORY.CreateAll())  # pytype: disable=bad-return-type

  def HasMultiFileParsers(self):
    return any(self.MultiFileParsers())

  def MultiFileParsers(self):
    # TODO: See above.
    return filter(self._IsSupported, MULTI_FILE_PARSER_FACTORY.CreateAll())  # pytype: disable=bad-return-type

  # TODO(hanuszczak): It is unclear whether this method has a right to exist. It
  # is not possible to properly type it, since parser in general do not have any
  # common interface. It should be considered to be a temporary hack to get rid
  # of metaclass registries and is only used to generate descriptors for all
  # parsers, but some better approach needs to be devised in the future.
  def AllParsers(self):
    """Retrieves all known parser applicable for the artifact.

    Returns:
      An iterator over parser instances.
    """
    return collection.Flatten([
        self.SingleResponseParsers(),
        self.MultiResponseParsers(),
        self.SingleFileParsers(),
        self.MultiFileParsers(),
    ])

  def _IsSupported(self, parser_obj):
    return self._artifact_name in parser_obj.supported_artifacts
