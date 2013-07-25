#!/usr/bin/env python
"""Registry for parsers and abstract classes for basic parser functionality."""

from grr.lib import registry


class Error(Exception):
  """Base error class."""


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


class CommandParser(Parser):
  """Abstract parser for processing command output.

  Must implement the Parse function.

  """

  def Parse(self, cmd, args, stdout, stderr, return_val, time_taken):
    """Take the output of the command run, and yield RDFValues."""

  def CheckReturn(self, cmd, return_val):
    """Raise if return value is bad."""
    if return_val != 0:
      raise CommandFailedError("Parsing output of Command %s failed, as "
                               "command had %s return code" % (cmd, return_val))


class WMIQueryParser(Parser):
  """Abstract parser for processing WMI query output."""

  def Parse(self, query, result_dict):
    """Take the output of the query, and yield RDFValues."""
