#!/usr/bin/env python
"""Generic parsers (for GRR server and client code)."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from future.builtins import filter

from grr_response_core.lib import factory
from grr_response_core.lib import parser
from grr_response_core.lib.util import precondition

SINGLE_RESPONSE_PARSER_FACTORY = factory.Factory(parser.SingleResponseParser)
MULTI_RESPONSE_PARSER_FACTORY = factory.Factory(parser.MultiResponseParser)
SINGLE_FILE_PARSER_FACTORY = factory.Factory(parser.SingleFileParser)
MULTI_FILE_PARSER_FACTORY = factory.Factory(parser.MultiFileParser)


class ArtifactParserFactory(object):
  """A factory wrapper class that yields parsers for specific artifact."""

  def __init__(self, artifact_name):
    """Initializes the artifact parser factory.

    Args:
      artifact_name: A name of the artifact this factory is supposed to provide
        parser instances for.
    """
    precondition.AssertType(artifact_name, unicode)
    self._artifact_name = artifact_name

  def HasSingleResponseParsers(self):
    return any(self.SingleResponseParsers())

  def SingleResponseParsers(self):
    return filter(self._IsSupported, SINGLE_RESPONSE_PARSER_FACTORY.CreateAll())

  def HasMultiResponseParsers(self):
    return any(self.MultiResponseParsers())

  def MultiResponseParsers(self):
    return filter(self._IsSupported, MULTI_RESPONSE_PARSER_FACTORY.CreateAll())

  def HasSingleFileParsers(self):
    return any(self.SingleFileParsers())

  def SingleFileParsers(self):
    return filter(self._IsSupported, SINGLE_FILE_PARSER_FACTORY.CreateAll())

  def HasMultiFileParsers(self):
    return any(self.MultiFileParsers())

  def MultiFileParsers(self):
    return filter(self._IsSupported, MULTI_FILE_PARSER_FACTORY.CreateAll())

  def _IsSupported(self, parser_obj):
    return self._artifact_name in parser_obj.supported_artifacts
