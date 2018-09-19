#!/usr/bin/env python
"""Registry for parsers and abstract classes for basic parser functionality."""
from __future__ import unicode_literals

import abc
import types


from future.utils import with_metaclass

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
# For CronTabFile, an artifact output type. pylint: disable=unused-import
from grr_response_core.lib.rdfvalues import cronjobs as rdf_cronjobs
# pylint: enable=unused-import
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import rekall_types as rdf_rekall_types


class Error(Exception):
  """Base error class."""


class ParserDefinitionError(Exception):
  """A parser was defined badly."""


class CommandFailedError(Error):
  """An error that gets raised due to the command failing."""


class ParseError(Error):
  """An error that gets raised due to the parsing of the output failing."""


# TODO(hanuszczak): `pytype` does not understand `with_metaclass`.
# pytype: disable=ignored-abstractmethod
class SingleResponseParser(with_metaclass(abc.ABCMeta)):
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
    """


# pytype: enable=ignored-abstractmethod


class Parser(with_metaclass(registry.MetaclassRegistry, object)):
  """A class for looking up parsers.

  Parsers may be in other libraries or third party code, this class keeps
  references to each of them so they can be called by name by the artifacts.
  """

  # A list of string identifiers for artifacts that this parser can process.
  supported_artifacts = []

  # Any knowledgebase dependencies required by the parser. Dependencies required
  # by the artifact itself will be inferred from the artifact definition.
  knowledgebase_dependencies = []

  # The semantic types that can be produced by this parser.
  output_types = []

  # If set to true results for this parser must collected and processed in one
  # go. This allows parsers to combine the results of multiple files/registry
  # keys. It is disabled by default as it is more efficient to stream and parse
  # results one at a time when this is not necessary.
  process_together = False

  @classmethod
  def GetClassesByArtifact(cls, artifact_name):
    """Get the classes that support parsing a given artifact."""
    return [
        cls.classes[c] for c in cls.classes
        if artifact_name in cls.classes[c].supported_artifacts
    ]

  @classmethod
  def GetDescription(cls):
    if cls.__doc__:
      return cls.__doc__.split("\n")[0]
    else:
      return ""

  # Additional validation code can be put in this function. This will only be
  # run in tests.
  @classmethod
  def Validate(cls, supported_artifact_objects):
    pass


# TODO(hanuszczak): This class should implement only one interface.
class CommandParser(Parser, SingleResponseParser):
  """Abstract parser for processing command output.

  Must implement the Parse function.

  """

  # Prevents this from automatically registering.
  __abstract = True  # pylint: disable=g-bad-name

  # TODO(hanuszczak): This should probably be abstract or private.
  def Parse(self, cmd, args, stdout, stderr, return_val, time_taken,
            knowledge_base):
    """Take the output of the command run, and yield RDFValues."""

  def ParseResponse(self, knowledge_base, response, path_type):
    del path_type  # Unused.
    utils.AssertType(response, rdf_client_action.ExecuteResponse)

    return self.Parse(
        cmd=response.request.cmd,
        args=response.request.args,
        stdout=response.stdout,
        stderr=response.stderr,
        return_val=response.exit_status,
        time_taken=response.time_used,
        knowledge_base=knowledge_base)

  def CheckReturn(self, cmd, return_val):
    """Raise if return value is bad."""
    if return_val != 0:
      raise CommandFailedError("Parsing output of Command %s failed, as "
                               "command had %s return code" % (cmd, return_val))


# TODO(hanuszczak): This class should implement only one interface.
class FileParser(Parser, SingleResponseParser):
  """Abstract parser for processing files output.

  Must implement the Parse function.
  """

  # Prevents this from automatically registering.
  __abstract = True  # pylint: disable=g-bad-name

  def __init__(self, fopen=None):
    """Initializes the file parser object.

    Args:
      fopen: A function that returns file-like object for given pathspec.
    """
    # TODO(hanuszczak): Define clear interface for file-like objects.
    if fopen is not None:
      utils.AssertType(fopen, types.FunctionType)
    self._fopen = fopen

  # TODO(hanuszczak): Make this abstract.
  # TODO(hanuszczak): Remove `knowledge_base` argument.
  # TODO(hanuszczak): Replace `stat` with `pathspec` argument.
  def Parse(self, stat, file_object, knowledge_base):
    """Take the file data, and yield RDFValues."""

  def ParseMultiple(self, stats, file_objects, knowledge_base):
    """Take the file data, and yield RDFValues."""

  def ParseResponse(self, knowledge_base, response, path_type):
    del path_type  # Unused.
    utils.AssertType(response, rdf_client_fs.StatEntry)

    # TODO(hanuszczak): This is a temporary hack to avoid rewriting hundreds of
    # tests for file parser. Once the tests are adapted to use the new API, the
    # constructor should be disallowed to take `None` as file opener as soon as
    # possible.
    if self._fopen is None:
      raise AssertionError("Parser constructed without file opening function")

    with self._fopen(response.pathspec) as filedesc:
      return self.Parse(response, filedesc, knowledge_base)


# TODO(hanuszczak): This class should implement only one interface.
class WMIQueryParser(Parser, SingleResponseParser):
  """Abstract parser for processing WMI query output."""

  # TODO(hanuszczak): Make this abstract.
  def Parse(self, result_dict):
    """Take the output of the query, and yield RDFValues."""

  def ParseResponse(self, knowledge_base, response, path_type):
    del knowledge_base, path_type  # Unused.
    utils.AssertType(response, rdf_protodict.Dict)

    return self.Parse(response)


# TODO(hanuszczak): This class should implement only one interface.
class RegistryValueParser(Parser, SingleResponseParser):
  """Abstract parser for processing Registry values."""

  # TODO(hanuszczak): Make this abstract.
  # TODO(hanuszczak): Make order of arguments consistent with other methods.
  def Parse(self, stat, knowledge_base):
    """Take the stat, and yield RDFValues."""

  def ParseResponse(self, knowledge_base, response, path_type):
    del path_type  # Unused.
    # TODO(hanuszczak): Why some of the registry value parsers anticipate string
    # response? This is stupid.
    utils.AssertType(response, (rdf_client_fs.StatEntry, rdfvalue.RDFString))

    return self.Parse(response, knowledge_base)


# TODO(hanuszczak): This class should implement only one interface.
class RegistryParser(Parser, SingleResponseParser):
  """Abstract parser for processing Registry values."""

  def ParseMultiple(self, stats, knowledge_base):
    """Parse multiple results in a single call."""

  # TODO(hanuszczak): Make this abstract.
  # TODO(hanuszczak): Make order of arguments consistent with other methods.
  def Parse(self, stat, knowledge_base):
    """Take the stat, and yield RDFValues."""

  def ParseResponse(self, knowledge_base, response, path_type):
    del path_type  # Unused.
    utils.AssertType(response, rdf_client_fs.StatEntry)

    return self.Parse(response, knowledge_base)


# TODO(hanuszczak): This class should implement only one interface.
class GrepParser(Parser, SingleResponseParser):
  """Parser for the results of grep artifacts."""

  # TODO(hanuszczak): Make this abstract.
  # TODO(hanuszczak): Make order of arguments consistent with other methods.
  def Parse(self, response, knowledge_base):
    """Parse the FileFinderResult.matches."""

  def ParseResponse(self, knowledge_base, response, path_type):
    del path_type  # Unused.
    utils.AssertType(response, rdf_file_finder.FileFinderResult)

    return self.Parse(response, knowledge_base)


# TODO(hanuszczak): This class should implement only one interface.
class ArtifactFilesParser(Parser, SingleResponseParser):
  """Abstract parser for processing artifact files."""

  # TODO(hanuszczak): Make this abstract.
  def Parse(self, persistence, knowledge_base, download_pathtype):
    """Parse artifact files."""

  def ParseResponse(self, knowledge_base, response, path_type):
    # TODO(hanuszczak): What is the expected type of `response` here?
    return self.Parse(response, knowledge_base, path_type)


# TODO(hanuszczak): This class should implement only one interface.
class RekallPluginParser(Parser, SingleResponseParser):
  """Parses Rekall responses."""

  # TODO(hanuszczak): Declare abstract `Parse` method.

  def ParseResponse(self, knowledge_base, response, path_type):
    del path_type  # Unused.
    utils.AssertType(response, rdf_rekall_types.RekallResponse)

    return self.Parse(response, knowledge_base)
