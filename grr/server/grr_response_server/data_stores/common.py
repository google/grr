#!/usr/bin/env python
"""This file contains various utility classes used by GRR data stores."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import os
import re
import stat

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils


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
