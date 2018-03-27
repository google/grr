#!/usr/bin/env python
"""Implementation of client-side file-finder subactions."""

import abc

from grr_response_client import client_utils
from grr_response_client import client_utils_common
from grr_response_client.client_actions.file_finder_utils import uploading
from grr.lib.rdfvalues import paths as rdf_paths


class Action(object):
  """An abstract class for subactions of the client-side file-finder.

  Attributes:
    flow: A parent flow action that spawned the subaction.
  """

  __metaclass__ = abc.ABCMeta

  def __init__(self, flow):
    self.flow = flow

  @abc.abstractmethod
  def Execute(self, filepath, result):
    """Executes the action on a given path.

    Concrete action implementations should return results by filling-in
    appropriate fields of the result instance.

    Args:
      filepath: A path to the file on which the action is going to be performed.
      result: An `FileFinderResult` instance to fill-in.
    """
    pass


class StatAction(Action):
  """Implementation of the stat subaction.

  This subaction just gathers basic metadata information about the specified
  file (such as size, modification time, extended attributes and flags.

  Attributes:
    flow: A parent flow action that spawned the subaction.
    opts: A `FileFinderStatActionOptions` instance.
  """

  def __init__(self, flow, opts):
    super(StatAction, self).__init__(flow)
    self.opts = opts

  def Execute(self, filepath, result):
    stat_cache = self.flow.stat_cache

    stat = stat_cache.Get(filepath, follow_symlink=self.opts.resolve_links)
    result.stat_entry = _StatEntry(stat, ext_attrs=self.opts.collect_ext_attrs)


class HashAction(Action):
  """Implementation of the hash subaction.

  This subaction returns results of various hashing algorithms applied to the
  specified file. Additionally it also gathers basic information about the
  hashed file.

  Attributes:
    flow: A parent flow action that spawned the subaction.
    opts: A `FileFinderHashActionOptions` instance.
  """

  def __init__(self, flow, opts):
    super(HashAction, self).__init__(flow)
    self.opts = opts

  def Execute(self, filepath, result):
    stat = self.flow.stat_cache.Get(filepath, follow_symlink=True)
    result.stat_entry = _StatEntry(stat, ext_attrs=self.opts.collect_ext_attrs)

    if stat.IsDirectory():
      return

    policy = self.opts.oversized_file_policy
    max_size = self.opts.max_size
    if stat.GetSize() <= self.opts.max_size:
      result.hash_entry = _HashEntry(stat, self.flow)
    elif policy == self.opts.OversizedFilePolicy.HASH_TRUNCATED:
      result.hash_entry = _HashEntry(stat, self.flow, max_size=max_size)
    elif policy == self.opts.OversizedFilePolicy.SKIP:
      return
    else:
      raise ValueError("Unknown oversized file policy: %s" % policy)


class DownloadAction(Action):
  """Implementation of the download subaction.

  This subaction sends a specified file to the server and returns a handle to
  its stored version. Additionally it also gathers basic metadata about the
  file.

  Attributes:
    flow: A parent flow action that spawned the subaction.
    opts: A `FileFinderDownloadActionOptions` instance.
  """

  def __init__(self, flow, opts):
    super(DownloadAction, self).__init__(flow)
    self.opts = opts

  def Execute(self, filepath, result):
    stat = self.flow.stat_cache.Get(filepath, follow_symlink=True)
    result.stat_entry = _StatEntry(stat, ext_attrs=self.opts.collect_ext_attrs)

    if stat.IsDirectory():
      return

    policy = self.opts.oversized_file_policy
    max_size = self.opts.max_size
    if stat.GetSize() <= max_size:
      result.transferred_file = self._UploadFilePath(filepath)
    elif policy == self.opts.OversizedFilePolicy.DOWNLOAD_TRUNCATED:
      result.transferred_file = self._UploadFilePath(filepath, truncate=True)
    elif policy == self.opts.OversizedFilePolicy.HASH_TRUNCATED:
      result.hash_entry = _HashEntry(stat, self.flow, max_size=max_size)
    elif policy == self.opts.OversizedFilePolicy.SKIP:
      return
    else:
      raise ValueError("Unknown oversized file policy: %s" % policy)

  def _UploadFilePath(self, filepath, truncate=False):
    max_size = self.opts.max_size if truncate else None
    chunk_size = self.opts.chunk_size

    uploader = uploading.TransferStoreUploader(self.flow, chunk_size=chunk_size)
    return uploader.UploadFilePath(filepath, amount=max_size)


def _StatEntry(stat, ext_attrs):
  pathspec = rdf_paths.PathSpec(
      pathtype=rdf_paths.PathSpec.PathType.OS,
      path=client_utils.LocalPathToCanonicalPath(stat.GetPath()),
      path_options=rdf_paths.PathSpec.Options.CASE_LITERAL)
  return client_utils.StatEntryFromStat(stat, pathspec, ext_attrs=ext_attrs)


def _HashEntry(stat, flow, max_size=None):
  hasher = client_utils_common.MultiHasher(progress=flow.Progress)
  try:
    hasher.HashFilePath(stat.GetPath(), max_size or stat.GetSize())
    return hasher.GetHashObject()
  except IOError:
    return None
