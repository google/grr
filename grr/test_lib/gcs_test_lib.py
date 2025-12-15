#!/usr/bin/env python
"""A module with test utilities for working with Google Cloud Storage."""
import io
import re
from typing import Any

import requests


class FakeUploadHandler:
  """A fake handler for upload session requests.

  This class tries to provide a very simple emulation of the server part of the
  resumable upload protocol [1]. Note that this is only an extremely primitive
  realisation of it unlikely to cover all the quirks, making this suitable only
  for unit testing purposes.

  [1]: https://cloud.google.com/storage/docs/performing-resumable-uploads
  """

  CONTENT_RANGE_REGEX = re.compile(
      r"bytes (?P<first>\d+)-(?P<last>\d+)/(?P<total>\d+|\*)")

  def __init__(self):
    super().__init__()
    self._buf = io.BytesIO()

  @property
  def content(self) -> bytes:
    return self._buf.getvalue()

  def __call__(self, request: requests.PreparedRequest) -> tuple[int, Any, str]:
    chunk = request.body or b""
    headers = request.headers

    if int(headers["Content-Length"]) != len(chunk):
      return 400, {}, "invalid content length"

    content_range = re.match(self.CONTENT_RANGE_REGEX, headers["Content-Range"])
    if content_range is None:
      return 400, {}, "invalid content range"

    first = self._buf.tell()
    self._buf.write(chunk)
    last = max(self._buf.tell() - 1, first)  # `max` to account for empty chunk.

    if int(content_range["first"]) != first:
      return 400, {}, "incorrect first byte offset"

    if int(content_range["last"]) != last:
      return 400, {}, "incorrect last byte offset"

    if content_range["total"] == "*":
      return 308, {}, "resume incomplete"
    elif int(content_range["total"]) == len(self._buf.getvalue()):
      return 201, {}, "created"
    else:
      return 400, {}, "incorrect number of total bytes"
