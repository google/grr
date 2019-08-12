#!/usr/bin/env python
"""Registry for parsers and abstract classes for basic parser functionality."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import abc

from future.utils import with_metaclass
from typing import Optional
from typing import Text


class ParseError(Exception):
  """A class for errors raised when parsers encounter problems when parsing.

  Attributes:
    cause: An optional exception that caused this exception to be raised.
  """

  def __init__(self, message, cause = None):
    """Initializes the error.

    Args:
      message: A message string explaining why the exception was raised.
      cause: An optional exception that caused this exception to be raised.

    Returns:
      Nothing.
    """
    if cause is not None:
      message = "{message}: {cause}".format(message=message, cause=cause)

    super(ParseError, self).__init__(message)
    self.cause = cause


class Parser(with_metaclass(abc.ABCMeta)):
  """A base interface for all parsers types."""

  # TODO(hanuszczak): Once support for Python 2 is dropped, properties below can
  # be defined as abstract, ensuring that all subclasses really define them.

  # TODO(hanuszczak): It would be better if parsers identified types that they
  # can parse rather than declare supported artifacts (which are defined in a
  # completely different place, in an external repository). Then parser can have
  # well-defined types.

  # A list of string identifiers for artifacts that this parser can process.
  supported_artifacts = []

  # Any knowledgebase dependencies required by the parser. Dependencies required
  # by the artifact itself will be inferred from the artifact definition.
  knowledgebase_dependencies = []

  # TODO(hanuszczak): Parser should have well defined types and what they can
  # return should be defined statically. Moreover, it is not possible to enforce
  # that parser really yields what `output_types` specified so this serves no
  # purpose other than documentation.
  #
  # There is only one parser that returns more than one type of value, so maybe
  # it should be re-evaluated whether this field actually makes sense.

  # The semantic types that can be produced by this parser.
  output_types = []


class SingleResponseParser(Parser):
  """An abstract class for parsers that are able to parse individual replies."""

  # TODO(hanuszczak): `path_type` is part of the signature only because one of
  # the parser classes needs that (`ArtifactFilesParser`). This is a very poor
  # design and some other way to avoid having this parameter should be devised.
  @abc.abstractmethod
  def ParseResponse(self, knowledge_base, response, path_type):
    """Parse a single response from the client.

    Args:
      knowledge_base: A knowledgebase for the client that provided the response.
      response: An RDF value representing the result of artifact collection.
      path_type: A path type information used by the `ArtifactFilesParser`.

    Raises:
      ParseError: If parser is not able to parse the response.
    """


class SingleFileParser(Parser):
  """An interface for parsers that read file content."""

  # TODO(hanuszczak): Define a clear file reader interface.

  @abc.abstractmethod
  def ParseFile(self, knowledge_base, pathspec, filedesc):
    """Parses a single file from the client.

    Args:
      knowledge_base: A knowledgebase for the client to whom the file belongs.
      pathspec: A pathspec corresponding to the parsed file.
      filedesc: A file-like object to parse.

    Yields:
      RDF values with parsed data.

    Raises:
      ParseError: If parser is not able to parse the file.
    """


class MultiResponseParser(Parser):
  """An interface for parsers requiring all replies in order to parse them."""

  @abc.abstractmethod
  def ParseResponses(self, knowledge_base, responses):
    """Parse responses from the client.

    Args:
      knowledge_base: A knowledgebase for the client that provided responses.
      responses: A list of RDF values with results of artifact collection.

    Raises:
      ParseError: If parser is not able to parse the responses.
    """


class MultiFileParser(Parser):
  """An interface for parsers that need to read content of multiple files."""

  # TODO(hanuszczak): The file interface mentioned above should also have
  # `pathspec` property. With the current solution there is no way to enforce
  # on the type level that `pathspecs` and `filedescs` have the same length and
  # there is no clear correlation between the two. One possible solution would
  # be to use a list of pairs but this is ugly to document.

  @abc.abstractmethod
  def ParseFiles(self, knowledge_base, pathspecs, filedescs):
    """Parses multiple files from the client.

    Args:
      knowledge_base: A knowledgebase for the client to whome the files belong.
      pathspecs: A list of pathspecs corresponding to the parsed files.
      filedescs: A list fo file-like objects to parse.

    Yields:
      RDF values with parsed data.

    Raises:
      ParseError: If parser is not able to parse the files.
    """
