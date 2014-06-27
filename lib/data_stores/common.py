#!/usr/bin/env python
"""This file contains various utility classes used by GRR."""


import re

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
  result = re.sub(
      r"\W", lambda x: "%%%02X" % ord(x.group(0)),
      name, flags=re.UNICODE).rstrip("/")

  # Some filesystems are not able to represent unicode chars.
  return utils.SmartStr(result)


def ResolveSubjectDestination(subject):
  """Returns the database filename where the subject will be stored.

  Args:
   subject: The subject.

  Returns:
   The subject's database file name.
  """
  subject = utils.SmartUnicode(subject)
  # Blobs have their own files, while everything else
  # goes to the top directory.
  prefixes = ["aff4:/blobs/", "aff4:/"]
  for prefix in prefixes:
    if subject.startswith(prefix):
      subject = subject[len(prefix):]
      if subject:
        top = subject.split("/", 1)[0]
        if top:
          return top
        else:
          return prefix
      else:
        return prefix

  # No matching prefix.
  return subject

