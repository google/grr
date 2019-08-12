#!/usr/bin/env python
"""Module that contains API to perform filesystem operations on a GRR client."""

from __future__ import absolute_import
from __future__ import division

from __future__ import print_function
from __future__ import unicode_literals

import io

from typing import Text, Sequence

from grr_api_client import client
from grr_api_client import errors as api_errors
from grr_colab import _timeout
from grr_colab import errors
from grr_colab import vfs
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2


class FileSystem(object):
  """Wrapper for filesystem operations on GRR Client.

  Attributes:
    id: Id of the client.
    cached: A VFS instance that allows to work with filesystem data saved on the
      server that may not be up-to-date but is a way faster.
  """

  def __init__(self, client_,
               path_type):
    self._client = client_
    self._path_type = path_type

  @property
  def id(self):
    return self._client.client_id

  @property
  def cached(self):
    return vfs.VFS(self._client)

  def ls(self, path, max_depth = 1):
    """Lists contents of a given directory.

    Args:
      path: A path to the directory to list the contents of.
      max_depth: Max depth of subdirectories to explore. If max_depth is >1,
        then the results will also include the contents of subdirectories (and
        sub-subdirectories and so on).

    Returns:
      A sequence of stat entries.
    """
    if max_depth > 1:
      args = flows_pb2.RecursiveListDirectoryArgs()
      args.pathspec.path = path
      args.pathspec.pathtype = self._path_type
      args.max_depth = max_depth

      try:
        ls = self._client.CreateFlow(name='RecursiveListDirectory', args=args)
      except api_errors.AccessForbiddenError as e:
        raise errors.ApprovalMissingError(self.id, e)

    else:
      args = flows_pb2.ListDirectoryArgs()
      args.pathspec.path = path
      args.pathspec.pathtype = self._path_type

      try:
        ls = self._client.CreateFlow(name='ListDirectory', args=args)
      except api_errors.AccessForbiddenError as e:
        raise errors.ApprovalMissingError(self.id, e)

    _timeout.await_flow(ls)
    return [_.payload for _ in ls.ListResults()]

  def glob(self, path):
    """Globs for files on the given client.

    Args:
      path: A glob expression (that may include `*` and `**`).

    Returns:
      A sequence of stat entries to the found files.
    """
    args = flows_pb2.GlobArgs()
    args.paths.append(path)
    args.pathtype = self._path_type

    try:
      glob = self._client.CreateFlow(name='Glob', args=args)
    except api_errors.AccessForbiddenError as e:
      raise errors.ApprovalMissingError(self.id, e)

    _timeout.await_flow(glob)
    return [_.payload for _ in glob.ListResults()]

  def grep(self, path,
           pattern):
    """Greps for given content on the specified path.

    Args:
      path: A path to a file to be searched.
      pattern: A regular expression on search for.

    Returns:
      A list of buffer references to the matched content.
    """
    args = flows_pb2.FileFinderArgs()
    args.paths.append(path)
    args.pathtype = self._path_type

    cond = args.conditions.add()
    cond.condition_type = \
      flows_pb2.FileFinderCondition.Type.CONTENTS_REGEX_MATCH
    cond.contents_regex_match.mode = \
      flows_pb2.FileFinderContentsRegexMatchCondition.ALL_HITS
    cond.contents_regex_match.regex = pattern

    args.action.action_type = flows_pb2.FileFinderAction.Action.STAT

    try:
      ff = self._client.CreateFlow(name='FileFinder', args=args)
    except api_errors.AccessForbiddenError as e:
      raise errors.ApprovalMissingError(self.id, e)

    _timeout.await_flow(ff)
    return [list(_.payload.matches)[0] for _ in ff.ListResults()]

  def fgrep(self, path,
            literal):
    """Greps for given content on the specified path.

    Args:
      path: A path to a file to be searched.
      literal: A literal expression on search for.

    Returns:
      A list of buffer references to the matched content.
    """
    args = flows_pb2.FileFinderArgs()
    args.paths.append(path)
    args.pathtype = self._path_type

    cond = args.conditions.add()
    cond.condition_type = \
      flows_pb2.FileFinderCondition.Type.CONTENTS_LITERAL_MATCH
    cond.contents_literal_match.mode = \
      flows_pb2.FileFinderContentsLiteralMatchCondition.Mode.ALL_HITS
    cond.contents_literal_match.literal = literal

    args.action.action_type = flows_pb2.FileFinderAction.Action.STAT

    try:
      ff = self._client.CreateFlow(name='FileFinder', args=args)
    except api_errors.AccessForbiddenError as e:
      raise errors.ApprovalMissingError(self.id, e)

    _timeout.await_flow(ff)
    return [list(_.payload.matches)[0] for _ in ff.ListResults()]

  def wget(self, path):
    """Downloads a file and returns a link to it.

    Args:
      path: A path to download.

    Returns:
      A link to the file.
    """
    self._collect_file(path)
    return self.cached.wget(path)

  def open(self, path):
    """Opens a file object corresponding to the given path on the client.

    The returned file object is read-only.

    Args:
      path: A path to the file to open.

    Returns:
      A file-like object (implementing standard IO interface).
    """
    self._collect_file(path)
    return self.cached.open(path)

  def _collect_file(self, path):
    """Save file from client to VFS.

    Args:
      path: A path to the file to collect.

    Returns:
      Nothing.
    """
    args = flows_pb2.GetFileArgs()
    args.pathspec.path = path
    args.pathspec.pathtype = self._path_type

    try:
      gf = self._client.CreateFlow(name='GetFile', args=args)
    except api_errors.AccessForbiddenError as e:
      raise errors.ApprovalMissingError(self.id, e)

    _timeout.await_flow(gf)
