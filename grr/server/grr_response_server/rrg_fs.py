#!/usr/bin/env python
"""Utilities for working with filesystem through RRG."""

import stat

from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_proto.rrg import fs_pb2 as rrg_fs_pb2


def StatEntry(metadata: rrg_fs_pb2.FileMetadata) -> jobs_pb2.StatEntry:
  """Creates a GRR `StatEntry` object corresponding to the given file metadata.

  Args:
    metadata: File metadata as reported by RRG.

  Returns:
    A standard GRR `StatEntry` object.
  """
  result = jobs_pb2.StatEntry()
  result.st_size = metadata.size

  if metadata.type == rrg_fs_pb2.FileMetadata.Type.FILE:
    result.st_mode |= stat.S_IFREG
  elif metadata.type == rrg_fs_pb2.FileMetadata.Type.DIR:
    result.st_mode |= stat.S_IFDIR
  elif metadata.type == rrg_fs_pb2.FileMetadata.Type.SYMLINK:
    result.st_mode |= stat.S_IFLNK
  else:
    raise ValueError(f"Invalid type: {metadata.type}")

  if metadata.access_time.seconds:
    result.st_atime = metadata.access_time.seconds
  if metadata.modification_time.seconds:
    result.st_mtime = metadata.modification_time.seconds
  if metadata.creation_time.seconds:
    result.st_btime = metadata.creation_time.seconds

  if metadata.unix_dev:
    result.st_dev = metadata.unix_dev
  if metadata.unix_ino:
    result.st_ino = metadata.unix_ino
  if metadata.unix_mode:
    result.st_mode |= metadata.unix_mode
  if metadata.unix_nlink:
    result.st_nlink = metadata.unix_nlink
  if metadata.unix_uid:
    result.st_uid = metadata.unix_uid
  if metadata.unix_gid:
    result.st_gid = metadata.unix_gid
  if metadata.unix_rdev:
    result.st_rdev = metadata.unix_rdev
  if metadata.unix_blksize:
    result.st_blksize = metadata.unix_blksize
  if metadata.unix_blocks:
    result.st_blocks = metadata.unix_blocks

  return result


def PathInfo(metadata: rrg_fs_pb2.FileMetadata) -> objects_pb2.PathInfo:
  result = objects_pb2.PathInfo()
  result.stat_entry.CopyFrom(StatEntry(metadata))
  result.directory = metadata.type == rrg_fs_pb2.FileMetadata.DIR

  return result
