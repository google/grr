#!/usr/bin/env python
"""Generic parsers (for GRR server and client code)."""
from typing import Iterator
from typing import Text
from typing import Type
from typing import TypeVar

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


_P = TypeVar("_P", bound=Parser)


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
    return any(self.SingleResponseParserTypes())

  def SingleResponseParsers(self) -> Iterator[SingleResponseParser[_RDFValue]]:
    return self._CreateSupportedParsers(SINGLE_RESPONSE_PARSER_FACTORY)

  def SingleResponseParserNames(self) -> Iterator[str]:
    return self._SupportedNames(SINGLE_RESPONSE_PARSER_FACTORY)

  def SingleResponseParserTypes(
      self) -> Iterator[Type[SingleResponseParser[_RDFValue]]]:
    return self._SupportedTypes(SINGLE_RESPONSE_PARSER_FACTORY)

  def HasMultiResponseParsers(self) -> bool:
    return any(self.MultiResponseParserTypes())

  def MultiResponseParsers(self) -> Iterator[MultiResponseParser[_RDFValue]]:
    return self._CreateSupportedParsers(MULTI_RESPONSE_PARSER_FACTORY)

  def MultiResponseParserNames(self) -> Iterator[str]:
    return self._SupportedNames(MULTI_RESPONSE_PARSER_FACTORY)

  def MultiResponseParserTypes(
      self) -> Iterator[Type[MultiResponseParser[_RDFValue]]]:
    return self._SupportedTypes(MULTI_RESPONSE_PARSER_FACTORY)

  def HasSingleFileParsers(self) -> bool:
    return any(self.SingleFileParserTypes())

  def SingleFileParsers(self) -> Iterator[SingleFileParser[_RDFValue]]:
    return self._CreateSupportedParsers(SINGLE_FILE_PARSER_FACTORY)

  def SingleFileParserNames(self) -> Iterator[str]:
    return self._SupportedNames(SINGLE_FILE_PARSER_FACTORY)

  def SingleFileParserTypes(
      self) -> Iterator[Type[SingleFileParser[_RDFValue]]]:
    return self._SupportedTypes(SINGLE_FILE_PARSER_FACTORY)

  def HasMultiFileParsers(self) -> bool:
    return any(self.MultiFileParserTypes())

  def MultiFileParsers(self) -> Iterator[MultiFileParser[_RDFValue]]:
    return self._CreateSupportedParsers(MULTI_FILE_PARSER_FACTORY)

  def MultiFileParserNames(self) -> Iterator[str]:
    return self._SupportedNames(MULTI_FILE_PARSER_FACTORY)

  def MultiFileParserTypes(self) -> Iterator[Type[MultiFileParser[_RDFValue]]]:
    return self._SupportedTypes(MULTI_FILE_PARSER_FACTORY)

  def AllParserTypes(self) -> Iterator[Type[Parser[_RDFValue]]]:
    """Returns all known parser types applicable for the artifact."""
    return collection.Flatten([
        self.SingleResponseParserTypes(),
        self.MultiResponseParserTypes(),
        self.SingleFileParserTypes(),
        self.MultiFileParserTypes(),
    ])

  def _CreateSupportedParsers(self, fac: _Factory[_P]) -> Iterator[_P]:
    for name in self._SupportedNames(fac):
      yield fac.Create(name)

  def _SupportedTypes(self, fac: _Factory[_P]) -> Iterator[Type[_P]]:
    for name in self._SupportedNames(fac):
      yield fac.GetType(name)

  def _SupportedNames(self, fac: _Factory[_P]) -> Iterator[str]:
    for name in fac.Names():
      cls = fac.GetType(name)
      if self._artifact_name in cls.supported_artifacts:
        yield name
