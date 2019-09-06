#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Module that contains converters into human readable format of stat data."""

from __future__ import absolute_import
from __future__ import division

from __future__ import print_function
from __future__ import unicode_literals

import os
import stat

import humanize
from typing import Text

from grr_response_proto import jobs_pb2


def size(stat_entry):
  return humanize.naturalsize(stat_entry.st_size, binary=True)


def icon(stat_entry):
  if stat.S_ISDIR(stat_entry.st_mode):
    return '📂'
  elif _is_symlink(stat_entry):
    return '🔗'
  return '📄'


def name(stat_entry):
  filename = os.path.basename(os.path.normpath(stat_entry.pathspec.path))
  if _is_symlink(stat_entry):
    return '{} -> {}'.format(filename, stat_entry.symlink)
  return filename


def mode(stat_entry):
  return mode_from_bitmask(stat_entry.st_mode)


def mode_from_bitmask(st_mode):
  """Represents stat mode of a file in UNIX-like format.

  Args:
    st_mode: Stat mode of a file.

  Returns:
    Stat mode of a file in UNIX-like format.
  """
  file_types = {
      stat.S_IFDIR: 'd',
      stat.S_IFCHR: 'c',
      stat.S_IFBLK: 'b',
      stat.S_IFREG: '-',
      stat.S_IFIFO: 'p',
      stat.S_IFLNK: 'l',
      stat.S_IFSOCK: 's',
  }
  file_type = file_types[stat.S_IFMT(st_mode)]

  permissions = ''

  permissions += 'r' if st_mode & stat.S_IRUSR else '-'
  permissions += 'w' if st_mode & stat.S_IWUSR else '-'
  if st_mode & stat.S_ISUID:
    permissions += 's' if st_mode & stat.S_IXUSR else 'S'
  else:
    permissions += 'x' if st_mode & stat.S_IXUSR else '-'

  permissions += 'r' if st_mode & stat.S_IRGRP else '-'
  permissions += 'w' if st_mode & stat.S_IWGRP else '-'
  if st_mode & stat.S_ISGID:
    permissions += 's' if st_mode & stat.S_IXGRP else 'S'
  else:
    permissions += 'x' if st_mode & stat.S_IXGRP else '-'

  permissions += 'r' if st_mode & stat.S_IROTH else '-'
  permissions += 'w' if st_mode & stat.S_IWOTH else '-'
  if st_mode & stat.S_ISVTX:
    permissions += 't' if st_mode & stat.S_IXOTH else 'T'
  else:
    permissions += 'x' if st_mode & stat.S_IXOTH else '-'

  return file_type + permissions


def _is_symlink(stat_entry):
  return stat.S_ISLNK(stat_entry.st_mode) or bool(stat_entry.symlink)
