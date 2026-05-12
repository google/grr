#!/usr/bin/env python
"""Provides path-related data models and helpers."""

from collections.abc import Iterable
import stat
from typing import Optional

from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2


def IsRootPathInfo(path_info: objects_pb2.PathInfo) -> bool:
  return not bool(path_info.components)


def GetParentPathInfo(
    path_info: objects_pb2.PathInfo,
) -> Optional[objects_pb2.PathInfo]:
  """Constructs a path info corresponding to the parent of current path.

  The root path (represented by an empty list of components, corresponds to
  `/` on Unix-like systems) does not have a parent.

  Args:
    path_info: (child) Path info to get the parent of.

  Returns:
    Instance of `PathInfo` or `None` if parent does not exist.
  """
  if IsRootPathInfo(path_info):
    return None

  return objects_pb2.PathInfo(
      components=path_info.components[:-1],
      path_type=path_info.path_type,
      directory=True,
  )


def GetAncestorPathInfos(
    path_info: objects_pb2.PathInfo,
) -> Iterable[objects_pb2.PathInfo]:
  """Yields all ancestors of a path.

  The ancestors are returned in order from closest to the farthest one.

  Args:
    path_info: (child) Path info to get the ancestors of.

  Yields:
    Instances of `rdf_objects.PathInfo`.
  """
  current = path_info
  while True:
    current = GetParentPathInfo(current)
    if current is None:
      return
    yield current


_PATH_TYPE_MAP = {
    jobs_pb2.PathSpec.PathType.OS: objects_pb2.PathInfo.PathType.OS,
    jobs_pb2.PathSpec.PathType.TSK: objects_pb2.PathInfo.PathType.TSK,
    jobs_pb2.PathSpec.PathType.REGISTRY: objects_pb2.PathInfo.PathType.REGISTRY,
    jobs_pb2.PathSpec.PathType.TMPFILE: objects_pb2.PathInfo.PathType.TEMP,
    jobs_pb2.PathSpec.PathType.NTFS: objects_pb2.PathInfo.PathType.NTFS,
}


def PathInfoFromPathSpec(pathspec: jobs_pb2.PathSpec) -> objects_pb2.PathInfo:
  """Generates a PathInfo from a PathSpec chain.

  Note that since PathSpec objects may contain more information than what is
  stored in a PathInfo object, we can only create a PathInfo object from a
  PathSpec, never the other way around.

  Args:
    pathspec: Root PathSpec to convert.

  Returns:
    A PathInfo.
  """
  path_type = objects_pb2.PathInfo.PathType.UNSET
  components = []
  current: Optional[jobs_pb2.PathSpec] = pathspec

  # In GRR RDF PathSpec iterable implementation, it flattens the nested_path.
  # We do the same here by traversing the chain.
  while current is not None:
    path = current.path
    if current.offset:
      path += f":{current.offset}"
    if current.stream_name:
      path += f":{current.stream_name}"

    # TODO(hanuszczak): Sometimes the paths start with '/', sometimes they do
    # not (even though they are all supposed to be absolute). If they do start
    # with `/` we get an empty component at the beginning which needs to be
    # removed.
    #
    # It is also possible that path is simply '/' which, if split, yields two
    # empty components. To simplify things we just filter out all empty
    # components. As a side effect we also support pathological cases such as
    # '//foo//bar////baz'.
    #
    # Ideally, pathspec should only allow one format (either with or without
    # leading slash) sanitizing the input as soon as possible.
    components.extend(c for c in path.split("/") if c)

    if current.HasField("nested_path"):
      current = current.nested_path
    else:
      # Found the last element, it determines the path type.
      path_type = _PATH_TYPE_MAP.get(
          current.pathtype, objects_pb2.PathInfo.PathType.UNSET
      )
      break

  return objects_pb2.PathInfo(path_type=path_type, components=components)


def PathInfoFromStatEntry(
    stat_entry: jobs_pb2.StatEntry,
) -> objects_pb2.PathInfo:
  """Generates a PathInfo from a StatEntry.

  Args:
    stat_entry: The StatEntry to convert.

  Returns:
    A PathInfo.
  """
  result = PathInfoFromPathSpec(stat_entry.pathspec)
  result.directory = stat.S_ISDIR(int(stat_entry.st_mode))
  result.stat_entry.CopyFrom(stat_entry)
  return result
