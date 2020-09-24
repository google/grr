#!/usr/bin/env python
# Lint as: python3
"""Generic parsers (for GRR server and client code)."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import Any
from typing import Iterator
from typing import Text

from grr_response_core.lib import factory
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.parsers import abstract
from grr_response_core.lib.util import collection
from grr_response_core.lib.util import precondition

ParseError = abstract.ParseError

Parser = abstract.Parser
SingleResponseParser = abstract.SingleResponseParser
SingleFileParser = abstract.SingleFileParser
MultiResponseParser = abstract.MultiResponseParser
MultiFileParser = abstract.MultiFileParser

_Factory = factory.Factory
_RDFValue = rdfvalue.RDFValue

SINGLE_RESPONSE_PARSER_FACTORY: _Factory[SingleResponseParser[_RDFValue]] = (
    _Factory(SingleResponseParser[_RDFValue]))

MULTI_RESPONSE_PARSER_FACTORY: _Factory[MultiResponseParser[_RDFValue]] = (
    _Factory(MultiResponseParser[_RDFValue]))

SINGLE_FILE_PARSER_FACTORY: _Factory[SingleFileParser[_RDFValue]] = (
    _Factory(SingleFileParser[_RDFValue]))

MULTI_FILE_PARSER_FACTORY: _Factory[MultiFileParser[_RDFValue]] = (
    _Factory(MultiFileParser[_RDFValue]))


class ArtifactParserFactory(object):
  """A factory wrapper class that yields parsers for specific artifact."""

  def __init__(self, artifact_name: Text) -> None:
    """Initializes the artifact parser factory.

    Args:
      artifact_name: A name of the artifact this factory is supposed to provide
        parser instances for.
    """
    precondition.AssertType(artifact_name, Text)
    self._artifact_name = artifact_name

  def HasParsers(self) -> bool:
    return (self.HasSingleResponseParsers() or self.HasMultiResponseParsers() or
            self.HasSingleFileParsers() or self.HasMultiFileParsers())

  def HasSingleResponseParsers(self) -> bool:
    return any(self.SingleResponseParsers())

  def SingleResponseParsers(self) -> Iterator[SingleResponseParser[_RDFValue]]:
    # TODO: Apparently, pytype does not understand that we use
    # `filter` from the `future` package (which returns an iterator), instead of
    # builtin one which in Python 2 returns lists.
    return filter(self._IsSupported, SINGLE_RESPONSE_PARSER_FACTORY.CreateAll())  # pytype: disable=bad-return-type

  def HasMultiResponseParsers(self) -> bool:
    return any(self.MultiResponseParsers())

  def MultiResponseParsers(self) -> Iterator[MultiResponseParser[_RDFValue]]:
    # TODO: See above.
    return filter(self._IsSupported, MULTI_RESPONSE_PARSER_FACTORY.CreateAll())  # pytype: disable=bad-return-type

  def HasSingleFileParsers(self) -> bool:
    return any(self.SingleFileParsers())

  def SingleFileParsers(self) -> Iterator[SingleFileParser[_RDFValue]]:
    # TODO: See above.
    return filter(self._IsSupported, SINGLE_FILE_PARSER_FACTORY.CreateAll())  # pytype: disable=bad-return-type

  def HasMultiFileParsers(self) -> bool:
    return any(self.MultiFileParsers())

  def MultiFileParsers(self) -> Iterator[MultiFileParser[_RDFValue]]:
    # TODO: See above.
    return filter(self._IsSupported, MULTI_FILE_PARSER_FACTORY.CreateAll())  # pytype: disable=bad-return-type

  # TODO(hanuszczak): It is unclear whether this method has a right to exist. It
  # is not possible to properly type it, since parser in general do not have any
  # common interface. It should be considered to be a temporary hack to get rid
  # of metaclass registries and is only used to generate descriptors for all
  # parsers, but some better approach needs to be devised in the future.
  def AllParsers(self) -> Iterator[Parser[_RDFValue]]:
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

  # TODO(hanuszczak): Figure out why pytype complains if a type variable is used
  # here.
  def _IsSupported(self, parser_obj: Parser[Any]) -> bool:
    return self._artifact_name in parser_obj.supported_artifacts
