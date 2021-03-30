#!/usr/bin/env python
"""Module that contains API to perform filesystem operations on a GRR client."""
import io
from typing import Text, Sequence

from google.protobuf import message
from grr_api_client import client
from grr_api_client import errors as api_errors
from grr_colab import _timeout
from grr_colab import errors
from grr_colab import representer
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

  def __init__(self, client_: client.Client,
               path_type: jobs_pb2.PathSpec.PathType) -> None:
    self._client = client_
    self._path_type = path_type

  @property
  def id(self) -> Text:
    return self._client.client_id

  @property
  def cached(self) -> vfs.VFS:
    return vfs.VFS(self._client, self._path_type)

  def ls(self, path: Text, max_depth: int = 1) -> Sequence[jobs_pb2.StatEntry]:
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
    return representer.StatEntryList([_.payload for _ in ls.ListResults()])

  def glob(self, path: Text) -> Sequence[jobs_pb2.StatEntry]:
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
    return representer.StatEntryList([_.payload for _ in glob.ListResults()])

  def grep(self, path: Text,
           pattern: bytes) -> Sequence[jobs_pb2.BufferReference]:
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

    results = [_first_match(result.payload) for result in ff.ListResults()]
    return representer.BufferReferenceList(results)

  def fgrep(self, path: Text,
            literal: bytes) -> Sequence[jobs_pb2.BufferReference]:
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

    results = [_first_match(result.payload) for result in ff.ListResults()]
    return representer.BufferReferenceList(results)

  def wget(self, path: Text) -> Text:
    """Downloads a file and returns a link to it.

    Args:
      path: A path to download.

    Returns:
      A link to the file.
    """
    self._collect_file(path)
    return self.cached.wget(path)

  def open(self, path: Text) -> io.BufferedIOBase:
    """Opens a file object corresponding to the given path on the client.

    The returned file object is read-only.

    Args:
      path: A path to the file to open.

    Returns:
      A file-like object (implementing standard IO interface).
    """
    self._collect_file(path)
    return self.cached.open(path)

  def _collect_file(self, path: Text) -> None:
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


def _first_match(result: message.Message) -> jobs_pb2.BufferReference:
  """Returns first match of a file finder result.

  Args:
    result: A file finder result message.

  Raises:
    IndexError: If given result does not have any matches.
    TypeError: If given result message is not a file finder result.
  """
  if not isinstance(result, flows_pb2.FileFinderResult):
    raise TypeError(f'Unexpected flow result type: {type(result)}')

  return result.matches[0]
