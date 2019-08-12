#!/usr/bin/env python
"""Registry for parsers and abstract classes for basic parser functionality."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.parsers import abstract
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.util import precondition


class CommandParser(abstract.SingleResponseParser):
  """Abstract parser for processing command output.

  Must implement the Parse function.

  """

  # TODO(hanuszczak): This should probably be abstract or private.
  def Parse(self, cmd, args, stdout, stderr, return_val, knowledge_base):
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
        knowledge_base=knowledge_base)

  def CheckReturn(self, cmd, return_val):
    """Raise if return value is bad."""
    if return_val != 0:
      message = ("Parsing output of command '{command}' failed, as command had "
                 "{code} return code")
      raise abstract.ParseError(message.format(command=cmd, code=return_val))


# TODO(hanuszczak): This class should be removed - subclasses should implement
# `MultiFileParser` directly.
class FileMultiParser(abstract.MultiFileParser):
  """Abstract parser for processing files output."""

  # TODO(hanuszczak): Make this abstract.
  def ParseMultiple(self, stats, file_objects, knowledge_base):
    raise NotImplementedError()

  def ParseFiles(self, knowledge_base, pathspecs, filedescs):
    # TODO(hanuszczak): See analogous comment in `FileParser`.
    stat_entries = [rdf_client_fs.StatEntry(pathspec=_) for _ in pathspecs]
    return self.ParseMultiple(stat_entries, filedescs, knowledge_base)


class WMIQueryParser(abstract.MultiResponseParser):
  """Abstract parser for processing WMI query output."""

  # TODO(hanuszczak): Make this abstract.
  def ParseMultiple(self, result_dicts):
    """Take the output of the query, and yield RDFValues."""

  def ParseResponses(self, knowledge_base, responses):
    del knowledge_base  # Unused.
    precondition.AssertIterableType(responses, rdf_protodict.Dict)

    return self.ParseMultiple(responses)


class RegistryValueParser(abstract.SingleResponseParser):
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


class RegistryParser(abstract.SingleResponseParser):
  """Abstract parser for processing Registry values."""

  # TODO(hanuszczak): Make this abstract.
  # TODO(hanuszczak): Make order of arguments consistent with other methods.
  def Parse(self, stat, knowledge_base):
    """Take the stat, and yield RDFValues."""

  def ParseResponse(self, knowledge_base, response, path_type):
    del path_type  # Unused.
    precondition.AssertType(response, rdf_client_fs.StatEntry)

    return self.Parse(response, knowledge_base)


class RegistryMultiParser(abstract.MultiResponseParser):
  """Abstract parser for processing registry values."""

  # TODO(hanuszczak): Make this abstract.
  def ParseMultiple(self, stats, knowledge_base):
    raise NotImplementedError()

  def ParseResponses(self, knowledge_base, responses):
    precondition.AssertIterableType(responses, rdf_client_fs.StatEntry)

    return self.ParseMultiple(responses, knowledge_base)


class GrepParser(abstract.SingleResponseParser):
  """Parser for the results of grep artifacts."""

  # TODO(hanuszczak): Make this abstract.
  # TODO(hanuszczak): Make order of arguments consistent with other methods.
  def Parse(self, response, knowledge_base):
    """Parse the FileFinderResult.matches."""

  def ParseResponse(self, knowledge_base, response, path_type):
    del path_type  # Unused.
    precondition.AssertType(response, rdf_file_finder.FileFinderResult)

    return self.Parse(response, knowledge_base)


class ArtifactFilesParser(abstract.SingleResponseParser):
  """Abstract parser for processing artifact files."""

  # TODO(hanuszczak): Make this abstract.
  def Parse(self, persistence, knowledge_base, download_pathtype):
    """Parse artifact files."""

  def ParseResponse(self, knowledge_base, response, path_type):
    # TODO(hanuszczak): What is the expected type of `response` here?
    return self.Parse(response, knowledge_base, path_type)


class ArtifactFilesMultiParser(abstract.MultiResponseParser):
  """Abstract multi-parser for processing artifact files."""

  # TODO(hanuszczak: Make this abstract.
  def ParseMultiple(self, stat_entries, knowledge_base):
    """Parse artifact files."""

  def ParseResponses(self, knowledge_base, responses):
    precondition.AssertIterableType(responses, rdf_client_fs.StatEntry)
    return self.ParseMultiple(responses, knowledge_base)
