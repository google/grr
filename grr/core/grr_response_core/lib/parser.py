#!/usr/bin/env python
"""Registry for parsers and abstract classes for basic parser functionality."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc


from future.utils import with_metaclass

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
# For CronTabFile, an artifact output type. pylint: disable=unused-import
from grr_response_core.lib.rdfvalues import cronjobs as rdf_cronjobs
# pylint: enable=unused-import
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import rekall_types as rdf_rekall_types
from grr_response_core.lib.util import precondition


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


class SingleFileParser(with_metaclass(abc.ABCMeta)):
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
    """


class MultiResponseParser(with_metaclass(abc.ABCMeta)):
  """An interface for parsers requiring all replies in order to parse them."""

  @abc.abstractmethod
  def ParseResponses(self, knowledge_base, responses):
    """Parse responses from the client.

    Args:
      knowledge_base: A knowledgebase for the client that provided responses.
      responses: A list of RDF values with results of artifact collection.
    """


class MultiFileParser(with_metaclass(abc.ABCMeta)):
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

  @classmethod
  def GetClassesByArtifact(cls, artifact_name):
    """Get the classes that support parsing a given artifact."""
    return [
        cls.classes[c]
        for c in cls.classes
        if artifact_name in cls.classes[c].supported_artifacts
    ]

  @classmethod
  def GetDescription(cls):
    if cls.__doc__:
      return cls.__doc__.split("\n")[0]
    else:
      return ""


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
    precondition.AssertType(response, rdf_client_action.ExecuteResponse)

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


# TODO(hanuszczak): This class should be removed - subclasses should implement
# `SingleFileParser` directly.
class FileParser(Parser, SingleFileParser):
  """Abstract parser for processing files output.

  Must implement the Parse function.
  """

  # Prevents this from automatically registering.
  __abstract = True  # pylint: disable=g-bad-name

  # TODO(hanuszczak): Make this abstract.
  # TODO(hanuszczak): Remove `knowledge_base` argument.
  # TODO(hanuszczak): Replace `stat` with `pathspec` argument.
  def Parse(self, stat, file_object, knowledge_base):
    """Take the file data, and yield RDFValues."""

  def ParseFile(self, knowledge_base, pathspec, filedesc):
    # TODO(hanuszczak): Here we create a dummy stat entry - all implementations
    # of this class care only about the `pathspec` attribute anyway. This method
    # should be gone once all subclasses implement `SingleFileParser` directly.
    stat_entry = rdf_client_fs.StatEntry(pathspec=pathspec)
    return self.Parse(stat_entry, filedesc, knowledge_base)


# TODO(hanuszczak): This class should be removed - subclasses should implement
# `MultiFileParser` directly.
class FileMultiParser(Parser, MultiFileParser):
  """Abstract parser for processing files output."""

  # TODO(hanuszczak): Make this abstract.
  def ParseMultiple(self, stats, file_objects, knowledge_base):
    raise NotImplementedError()

  def ParseFiles(self, knowledge_base, pathspecs, filedescs):
    # TODO(hanuszczak): See analogous comment in `FileParser`.
    stat_entries = [rdf_client_fs.StatEntry(pathspec=_) for _ in pathspecs]
    return self.ParseMultiple(stat_entries, filedescs, knowledge_base)


# TODO(hanuszczak): This class should implement only one interface.
class WMIQueryParser(Parser, SingleResponseParser):
  """Abstract parser for processing WMI query output."""

  # TODO(hanuszczak): Make this abstract.
  def Parse(self, result_dict):
    """Take the output of the query, and yield RDFValues."""

  def ParseResponse(self, knowledge_base, response, path_type):
    del knowledge_base, path_type  # Unused.
    precondition.AssertType(response, rdf_protodict.Dict)

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
    precondition.AssertType(response,
                            (rdf_client_fs.StatEntry, rdfvalue.RDFString))

    return self.Parse(response, knowledge_base)


# TODO(hanuszczak): This class should implement only one interface.
class RegistryParser(Parser, SingleResponseParser):
  """Abstract parser for processing Registry values."""

  # TODO(hanuszczak): Make this abstract.
  # TODO(hanuszczak): Make order of arguments consistent with other methods.
  def Parse(self, stat, knowledge_base):
    """Take the stat, and yield RDFValues."""

  def ParseResponse(self, knowledge_base, response, path_type):
    del path_type  # Unused.
    precondition.AssertType(response, rdf_client_fs.StatEntry)

    return self.Parse(response, knowledge_base)


# TODO(hanuszczak): This class should implement only one interface.
class RegistryMultiParser(Parser, MultiResponseParser):
  """Abstract parser for processing registry values."""

  # TODO(hanuszczak): Make this abstract.
  def ParseMultiple(self, stats, knowledge_base):
    raise NotImplementedError()

  def ParseResponses(self, knowledge_base, responses):
    precondition.AssertIterableType(responses, rdf_client_fs.StatEntry)

    return self.ParseMultiple(responses, knowledge_base)


# TODO(hanuszczak): This class should implement only one interface.
class GrepParser(Parser, SingleResponseParser):
  """Parser for the results of grep artifacts."""

  # TODO(hanuszczak): Make this abstract.
  # TODO(hanuszczak): Make order of arguments consistent with other methods.
  def Parse(self, response, knowledge_base):
    """Parse the FileFinderResult.matches."""

  def ParseResponse(self, knowledge_base, response, path_type):
    del path_type  # Unused.
    precondition.AssertType(response, rdf_file_finder.FileFinderResult)

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
class ArtifactFilesMultiParser(Parser, MultiResponseParser):
  """Abstract multi-parser for processing artifact files."""

  # TODO(hanuszczak: Make this abstract.
  def ParseMultiple(self, stat_entries, knowledge_base):
    """Parse artifact files."""

  def ParseResponses(self, knowledge_base, responses):
    precondition.AssertIterableType(responses, rdf_client_fs.StatEntry)
    return self.ParseMultiple(responses, knowledge_base)


# TODO(hanuszczak): This class should implement only one interface.
class RekallPluginParser(Parser, SingleResponseParser):
  """Parses Rekall responses."""

  # TODO(hanuszczak): Declare abstract `Parse` method.

  def ParseResponse(self, knowledge_base, response, path_type):
    del path_type  # Unused.
    precondition.AssertType(response, rdf_rekall_types.RekallResponse)

    return self.Parse(response, knowledge_base)
