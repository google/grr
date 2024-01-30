#!/usr/bin/env python
"""Provides path-related data models and helpers."""

from typing import Iterable, Optional
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
