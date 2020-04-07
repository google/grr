#!/usr/bin/env python
# Lint as: python3
"""A module with utilities for working with the Sleuthkit's body format."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import csv
import io
import stat

from typing import Iterator

from grr_response_core.lib.rdfvalues import timeline as rdf_timeline

DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1 MiB.


def Stream(
    entries,
    chunk_size = DEFAULT_CHUNK_SIZE,
):
  """Streams chunks of a Sleuthkit's body file (from a stream of entries).

  Args:
    entries: A stream of timeline entries.,
    chunk_size: An (optional) size of the output chunk. Note that chunks are
      going to be slightly bigger than this value, but the difference should be
      negligible.

  Yields:
    Chunks of the body file.
  """
  buf = io.StringIO()

  columns = [
      "md5",
      "path",
      "ino",
      "mode",
      "uid",
      "gid",
      "size",
      "atime",
      "mtime",
      "ctime",
      "crtime",
  ]

  # TODO: Remove pytype suppression after Python 2 is no longer
  # supported.
  # pytype: disable=module-attr,wrong-arg-types
  writer = csv.DictWriter(buf, columns, delimiter="|", lineterminator="\n")

  for entry in entries:
    writer.writerow({
        "md5": 0,
        "path": entry.path.decode("utf-8", "surrogateescape"),
        "ino": entry.ino,
        "mode": stat.filemode(entry.mode),
        "uid": entry.uid,
        "gid": entry.gid,
        "size": entry.size,
        "atime": entry.atime_ns // 10**9,
        "mtime": entry.mtime_ns // 10**9,
        "ctime": entry.ctime_ns // 10**9,
        "crtime": 0,
    })

    content = buf.getvalue()
    if len(content) > chunk_size:
      yield content.encode("utf-8")
      buf.truncate(0)
      buf.seek(0, io.SEEK_SET)
  # pytype: enable=module-attr,wrong-arg-types

  content = buf.getvalue()
  if content:
    yield content.encode("utf-8")
