#!/usr/bin/env python
"""Registry for parsers and abstract classes for basic parser functionality."""

from grr.lib import registry


class Error(Exception):
  """Base error class."""


class ParserDefinitionError(Exception):
  """A parser was defined badly."""


class CommandFailedError(Error):
  """An error that gets raised due to the command failing."""


class ParseError(Error):
  """An error that gets raised due to the parsing of the output failing."""


class Parser(object):
  """A class for looking up parsers.

  Parsers may be in other libraries or third party code, this class keeps
  references to each of them so they can be called by name by the artifacts.
  """
  __metaclass__ = registry.MetaclassRegistry

  # A list of string identifiers for artifacts that this parser can process.
  supported_artifacts = []

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
    return [cls.classes[c] for c in cls.classes if artifact_name in
            cls.classes[c].supported_artifacts]


class CommandParser(Parser):
  """Abstract parser for processing command output.

  Must implement the Parse function.

  """

  # Prevents this from automatically registering.
  __abstract = True  # pylint: disable=g-bad-name

  def Parse(self, cmd, args, stdout, stderr, return_val, time_taken,
            knowledge_base):
    """Take the output of the command run, and yield RDFValues."""

  def CheckReturn(self, cmd, return_val):
    """Raise if return value is bad."""
    if return_val != 0:
      raise CommandFailedError("Parsing output of Command %s failed, as "
                               "command had %s return code" % (cmd, return_val))


class WMIQueryParser(Parser):
  """Abstract parser for processing WMI query output."""

  def Parse(self, query, result_dict, knowledge_base):
    """Take the output of the query, and yield RDFValues."""


class RegistryValueParser(Parser):
  """Abstract parser for processing Registry values."""

  def Parse(self, stat, knowledge_base):
    """Take the stat, and yield RDFValues."""


class RegistryParser(Parser):
  """Abstract parser for processing Registry values."""

  def ParseMultiple(self, stats, knowledge_base):
    """Parse multiple results in a single call."""

  def Parse(self, stat, knowledge_base):
    """Take the stat, and yield RDFValues."""
