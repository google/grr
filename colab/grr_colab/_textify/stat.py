#!/usr/bin/env python
"""Module that contains converters into human readable format of stat data."""
import os
import stat

import humanize

from grr_response_proto import jobs_pb2


def size(stat_entry: jobs_pb2.StatEntry) -> str:
  return humanize.naturalsize(stat_entry.st_size, binary=True)


def icon(stat_entry: jobs_pb2.StatEntry) -> str:
  if stat.S_ISDIR(stat_entry.st_mode):
    return '📂'
  elif _is_symlink(stat_entry):
    return '🔗'
  return '📄'


def name(stat_entry: jobs_pb2.StatEntry) -> str:
  filename = os.path.basename(os.path.normpath(stat_entry.pathspec.path))
  if _is_symlink(stat_entry):
    return '{} -> {}'.format(filename, stat_entry.symlink)
  return filename


def mode(stat_entry: jobs_pb2.StatEntry) -> str:
  return stat.filemode(stat_entry.st_mode)


def _is_symlink(stat_entry: jobs_pb2.StatEntry) -> bool:
  return stat.S_ISLNK(stat_entry.st_mode) or bool(stat_entry.symlink)
