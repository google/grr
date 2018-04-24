#!/usr/bin/env python
"""This file contains various utility classes used by GRR data stores."""

import collections
import logging
import os
import re
import stat

from grr.lib import rdfvalue
from grr.lib import utils


def ConvertStringToFilename(name):
  """Converts an unicode string to a filesystem safe filename.

  For maximum compatibility we escape all chars which are not alphanumeric (in
  the unicode sense).

  Args:
   name: a unicode string that is part of a subject.

  Returns:
    A safe filename with escaped special chars.
  """
  return re.sub(
      r"\W", lambda x: "%%%02X" % ord(x.group(0)), name,
      flags=re.UNICODE).rstrip("/")


def Components(subject):
  if not isinstance(subject, rdfvalue.RDFURN):
    subject = rdfvalue.RDFURN(subject)

  return subject.Split()


@utils.MemoizeFunction()
def _LiteralPrefix(regex):
  """Returns longest prefix of regex which consists of literal characters."""
  start = list(regex)
  result = []

  while True:
    if not start:
      return "".join(result)
    if start[0] == "\\":
      # A bar \ is a mystery, we do nothing with it.
      if len(start) == 1:
        return "".join(result)
      # A \ followed by certain characters is a special and we don't handle
      # specials.
      if start[1] in "0123456789AbBdDsSwWZ":
        return "".join(result)
      # These are unlikely to appear in a regex, but just in case:
      if start[1] == "a":
        result += "\a"
        start = start[2:]
        continue
      if start[1] == "b":
        result += "\b"
        start = start[2:]
        continue
      if start[1] == "f":
        result += "\f"
        start = start[2:]
        continue
      if start[1] == "n":
        result += "\n"
        start = start[2:]
        continue
      if start[1] == "r":
        result += "\r"
        start = start[2:]
        continue
      if start[1] == "t":
        result += "\t"
        start = start[2:]
        continue
      if start[1] == "v":
        result += "\v"
        start = start[2:]
        continue
      # A \ followed by another character, e.g. '.' is a literal of that
      # character.
      result += start[1]
      start = start[2:]
      continue
    if start[0] in ".^$*+?{}[]|()":
      return "".join(result)
    result += start[0]
    start = start[1:]


KNOWN_PATH_REGEX_PREFIX = "(?P<path>"


def EvaluatePrefix(prefix, path_regex):
  """Estimate if subjects beginning with prefix might match path_regex."""
  if path_regex.match(prefix):
    # The prefix is a match for this regex. We assume regex is sane enough
    # that all extentions of prefix will also match.
    return "MATCH"

  path_regex_string = path_regex.pattern
  if not path_regex_string.startswith(KNOWN_PATH_REGEX_PREFIX):
    # We don't know how to analyze this regex. Assume that extensions of prefix
    # might match the regex.
    logging.warning("Unrecognized regex format, being pessimistic: %s",
                    path_regex_string)
    return "POSSIBLE"

  literal_prefix = _LiteralPrefix(
      path_regex_string[len(KNOWN_PATH_REGEX_PREFIX):])
  if literal_prefix.startswith(prefix):
    # There are extensions of prefix which match regex.
    return "POSSIBLE"

  if prefix.startswith(literal_prefix):
    # It is possible that some extension of prefix will match
    # regex.
    return "POSSIBLE"

  # There is a character in the literal prefix which does not match
  # the corresponding character in prefix. Therefore no match is possible.
  return "NO_MATCH"


def ResolveSubjectDestination(subject, regexes):
  """Returns the directory/filename where the subject will be stored.

  Args:
   subject: The subject.
   regexes: The list of regular expressions by priority.

  Returns:
   File name and directory.
  """
  components = Components(subject)
  if not components:
    # No components to work with.
    return "aff4", ""
  # Make all the components safe to use.
  path = utils.JoinPath(*[ConvertStringToFilename(x) for x in components])
  for route in regexes:
    m = route.match(path)
    if m:
      value = m.group("path")
      if value:
        base = os.path.basename(value)
        dirname = os.path.dirname(value)
        return base, dirname
  # Default value if nothing else matches.
  return "aff4", ""


def MakeDestinationKey(directory, filename):
  """Creates a name that identifies a database file."""
  return utils.SmartStr(utils.JoinPath(directory, filename)).lstrip("/")


def DatabaseDirectorySize(root_path, extension):
  """Compute size (in bytes) and number of files of a file-based data store."""
  directories = collections.deque([root_path])
  total_size = 0
  total_files = 0
  while directories:
    directory = directories.popleft()
    try:
      items = os.listdir(directory)
    except OSError:
      continue
    for comp in items:
      path = os.path.join(directory, comp)
      try:
        statinfo = os.lstat(path)
        if stat.S_ISLNK(statinfo.st_mode):
          continue
        if stat.S_ISDIR(statinfo.st_mode):
          directories.append(path)
        elif stat.S_ISREG(statinfo.st_mode):
          if comp.endswith(extension):
            total_size += statinfo.st_size
            total_files += 1
      except OSError:
        continue
  return total_size, total_files
