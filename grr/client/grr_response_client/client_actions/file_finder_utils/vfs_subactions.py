#!/usr/bin/env python
# Lint as: python3
"""Implementation of client-side file-finder subactions."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import stat
from typing import Callable, Optional

from grr_response_client import actions
from grr_response_client import client_utils_common
from grr_response_client import vfs
from grr_response_client.client_actions.file_finder_utils import uploading
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder


class Action(metaclass=abc.ABCMeta):
  """An abstract class for subactions of the client-side file-finder."""

  def __init__(self, action: actions.ActionPlugin):
    self._action = action

  @abc.abstractmethod
  def __call__(self, stat_entry: rdf_client_fs.StatEntry,
               fd: vfs.VFSHandler) -> rdf_file_finder.FileFinderResult:
    """Executes the action on a given file.

    Args:
      stat_entry: StatEntry including PathSpec of the file to be processed.
      fd: file descriptor of the file to be processed. The file descriptor is
        expected to be at position 0 and will be read from for most Actions.

    Returns:
      FileFinderResult filled with (meta)data of the file.
    """
    pass


class StatAction(Action):
  """Implementation of the stat subaction.

  This subaction just gathers basic metadata information about the specified
  file (such as size, modification time, extended attributes and flags.
  """

  def __init__(
      self,
      flow,
      opts: Optional[rdf_file_finder.FileFinderStatActionOptions] = None):
    super().__init__(flow)
    del opts  # Unused.

  def __call__(self, stat_entry: rdf_client_fs.StatEntry,
               fd: vfs.VFSHandler) -> rdf_file_finder.FileFinderResult:
    return rdf_file_finder.FileFinderResult(stat_entry=stat_entry)


class HashAction(Action):
  """Implementation of the hash subaction.

  This subaction returns results of various hashing algorithms applied to the
  specified file. Additionally it also gathers basic information about the
  hashed file.
  """

  def __init__(self, flow, opts: rdf_file_finder.FileFinderHashActionOptions):
    super().__init__(flow)
    self._opts = opts

  def __call__(self, stat_entry: rdf_client_fs.StatEntry,
               fd: vfs.VFSHandler) -> rdf_file_finder.FileFinderResult:
    result = StatAction(self._action)(stat_entry, fd)

    # stat_entry.st_mode has StatMode type.
    if stat.S_ISDIR(int(stat_entry.st_mode)):
      return result

    policy = self._opts.oversized_file_policy

    if stat_entry.st_size <= self._opts.max_size:
      result.hash_entry = _HashEntry(stat_entry, fd, self._action.Progress)
    elif policy == self._opts.OversizedFilePolicy.HASH_TRUNCATED:
      # self._opts.max_size has a type ByteSize - hence we have to convert it
      # an int before passing to _HashEntry.
      result.hash_entry = _HashEntry(
          stat_entry,
          fd,
          max_size=int(self._opts.max_size),
          progress=self._action.Progress)
    # else: Skip due to OversizedFilePolicy.SKIP.

    return result


class DownloadAction(Action):
  """Implementation of the download subaction.

  This subaction sends a specified file to the server and returns a handle to
  its stored version. Additionally it also gathers basic metadata about the
  file.
  """

  def __init__(self, flow,
               opts: rdf_file_finder.FileFinderDownloadActionOptions):
    super().__init__(flow)
    self._opts = opts

  def __call__(self, stat_entry: rdf_client_fs.StatEntry,
               fd: vfs.VFSHandler) -> rdf_file_finder.FileFinderResult:
    result = StatAction(self._action)(stat_entry, fd)

    # stat_entry.st_mode has StatMode type.
    if stat.S_ISDIR(int(stat_entry.st_mode)):
      return result

    policy = self._opts.oversized_file_policy
    max_size = self._opts.max_size
    truncate = policy == self._opts.OversizedFilePolicy.DOWNLOAD_TRUNCATED

    if stat_entry.st_size <= max_size or truncate:
      result.transferred_file = self._UploadFilePath(fd, truncate=truncate)
    elif policy == self._opts.OversizedFilePolicy.HASH_TRUNCATED:
      result.hash_entry = _HashEntry(
          stat_entry, fd, self._action.Progress, max_size=max_size)
    # else: Skip due to OversizedFilePolicy.SKIP.

    return result

  def _UploadFilePath(self, fd, truncate):
    max_size = self._opts.max_size if truncate else None
    chunk_size = self._opts.chunk_size

    uploader = uploading.TransferStoreUploader(
        self._action, chunk_size=chunk_size)
    return uploader.UploadFile(fd, amount=max_size)


def _HashEntry(stat_entry: rdf_client_fs.StatEntry,
               fd: vfs.VFSHandler,
               progress: Callable[[], None],
               max_size: Optional[int] = None) -> Optional[rdf_crypto.Hash]:
  hasher = client_utils_common.MultiHasher(progress=progress)
  try:
    hasher.HashFile(fd, max_size or stat_entry.st_size)
    return hasher.GetHashObject()
  except IOError:
    return None
