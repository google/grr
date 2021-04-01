#!/usr/bin/env python
"""Utilities for working with Google Cloud Storage."""
import pathlib
from typing import Callable
from typing import IO
from typing import Optional

import requests
from requests import exceptions

from grr_response_client import time
from grr_response_core.lib.util import retry


class Error(Exception):
  """A base exception class for all Google Cloud Storage errors."""


class RequestError(Error):
  """An exception class for errors that can occur when making a request."""


class ResponseError(Error):
  """An exception class for errors that can occur when inspecting responses."""

  def __init__(self, message: str, response: requests.Response) -> None:
    """Initializes the error.

    Args:
      message: A message with details about what caused the error.
      response: A spurious response.
    """
    super().__init__(f"{message} ({response.status_code}, '{response.text}')")

    self.response = response


class InterruptedResponseError(ResponseError):
  """An exception class for response errors representing interruptions.

  This kind of exception is raised when server returns a response with an 5XX
  status code. Requests that resulted in such an error can be retried.
  """

  def __init__(self, response: requests.Response) -> None:
    """Initializes the error.

    Args:
      response: A spurious response with details about the interruption.
    """
    super().__init__("Interrupted", response)


class UploadSession(object):
  """A class for session objects that allow to perform resumable uploads."""

  class Opts:
    """Options used for the transfer procedure.

    Attributes:
      chunk_size: The chunk size of the uploaded file (in bytes).
      retry_chunk_attempts: A maximum number of attempts made when uploading a
        chunk.
      retry_chunk_init_delay: An initial delay value for retrying when uploading
        a chunk (in seconds).
      retry_chunk_max_delay: A maximum delay value for retrying when uploading a
        chunk (in seconds).
      retry_chunk_backoff: A backoff multiplayer for extending the delay between
        chunk upload retries.
      progress_callback: A progress function to call periodically when uploading
        the file.
      progress_interval: An upper bound on the time between the calls of the
        progress function (in seconds).
    """
    chunk_size: int = 8 * 1024 * 1024  # 8 MiB.

    retry_chunk_attempts: int = 30
    retry_chunk_init_delay: float = 1.0  # 1 s.
    retry_chunk_max_delay: float = 30 * 60.0  # 30 min.
    retry_chunk_backoff: float = 1.5

    progress_callback: Callable[[], None]
    progress_interval: float = 1.0

    def __init__(self):
      # TODO(hanuszczak): Assigning default value at the class-level makes the
      # Python interpreter treat this property as a bound method making it not
      # invokable. This is not really an issue with data classes, so once we are
      # Python 3.7-only we can migrate away from this workaround.
      self.progress_callback = lambda: None

  def __init__(self, uri: str) -> None:
    """Initializes the upload session.

    Args:
      uri: A session URI
    """
    super().__init__()
    self._uri: str = uri

  @classmethod
  def Open(cls, signed_url: str, timeout: float = 30.0) -> "UploadSession":
    """Opens a new resumable upload session for the specified signed URL.

    Args:
      signed_url: A signed URL pointing where to upload the file.
      timeout: Maximum amount of time to await for connection (in seconds).

    Returns:
      A session object that allows to perform a resumable file upload.

    Raises:
      RequestError: If the provided URL cannot be resolved.
      ResponseError: If the server responded with incorrect header.
    """
    headers = {
        "Content-Length": str(0),
        "Content-Type": "application/octet-stream",
        "x-goog-resumable": "start",
    }

    try:
      response = requests.post(signed_url, headers=headers, timeout=timeout)
    except exceptions.RequestException as error:
      raise RequestError("Transfer initialization failure") from error

    if response.status_code != 201:
      raise ResponseError("Unexpected status", response)

    if "Location" not in response.headers:
      raise ResponseError("Missing session URI", response)

    return cls(response.headers["Location"])

  def SendFile(self, file: IO[bytes], opts: Optional[Opts] = None) -> None:
    """Streams the given file to Google Cloud Storage.

    Args:
      file: A file-like object to send.
      opts: Options used for the transfer procedure.

    Returns:
      Nothing.

    Raises:
      RequestError: If it is not possible to deliver one of the chunks.
      ResponseError: If the server responded with unexpected status.
    """
    if opts is None:
      opts = self.Opts()

    def Sleep(secs: float) -> None:
      time.Sleep(
          secs,
          progress_secs=opts.progress_interval,
          progress_callback=opts.progress_callback)

    retry_opts = retry.Opts()
    retry_opts.attempts = opts.retry_chunk_attempts
    retry_opts.backoff = opts.retry_chunk_backoff
    retry_opts.init_delay_secs = opts.retry_chunk_init_delay
    retry_opts.max_delay_secs = opts.retry_chunk_max_delay
    retry_opts.sleep = Sleep

    offset = 0

    while True:
      chunk = file.read(opts.chunk_size)

      # To determine whether we are at the last chunk we simply check whether
      # the amount of bytes actually read is less than the requested amount.
      # Note that this still works if the last chunk is exactly the requested
      # size in which case the next tick of the loop will send an empty packet
      # finishing the procedure.
      is_last_chunk = len(chunk) < opts.chunk_size

      # The chunk content range according in the HTTP 1.1 syntax [1].
      #
      # During the resumable upload procedure the total size of the file might
      # not be known upfront. Fortunately, it is only required to send the total
      # size only with the last chunk.
      #
      # Because the range is inclusive in general there is no proper way of
      # dealing with empty ranges. This can happen if the file we attempt to
      # send is empty or the total number of bytes of the file is divisible by
      # the chunk size. In such a case we simply make first and last byte equal
      # and hope that the content length header set to 0 is enough to let the
      # server figure out that this range is in face empty (which seems to be
      # the case).
      #
      # [1]: https://tools.ietf.org/html/rfc7233#section-4.2
      chunk_first_byte = offset
      chunk_last_byte = max(offset + len(chunk) - 1, offset)

      if is_last_chunk:
        total_size = offset + len(chunk)
        chunk_range = f"bytes {chunk_first_byte}-{chunk_last_byte}/{total_size}"
      else:
        chunk_range = f"bytes {chunk_first_byte}-{chunk_last_byte}/*"

      headers = {
          "Content-Length": str(len(chunk)),
          "Content-Range": chunk_range,
      }

      # We attempt to retry sending chunks in two scenarios: either we failed to
      # send the request at all (e.g. due to the internet being down) or because
      # there was an interruption error (it is not completely clear when exactly
      # this can occur, but the documentation clearly states that the upload can
      # be resumed in such a case).
      #
      # We should not attempt to retry any other errors. If a response is not
      # correct or expected it likely means that something is seriously wrong
      # and it is better to fail and notify the flow about the problem. It is
      # also possible that the upload process has been cancelled (i.e. by the
      # analyst), in which case further attempts to send the file are futile.
      @retry.On((RequestError, InterruptedResponseError), opts=retry_opts)
      def PutChunk():
        try:
          # We need to set a timeout equal to the requested progress function
          # call interval so that we can call it often enough. In general, if an
          # internet connection is so bad that these requests take more than the
          # frequency of the progress calls, we likely won't be able to send big
          # files in reasonable amount of time anyway.
          response = requests.put(
              self.uri,
              data=chunk,
              headers=headers,
              timeout=opts.progress_interval)
        except exceptions.RequestException as error:
          raise RequestError("Chunk transmission failure") from error

        if 500 <= response.status_code <= 599:
          raise InterruptedResponseError(response)

        if 400 <= response.status_code <= 499:
          raise ResponseError("Cancelled upload session", response)

        if is_last_chunk and response.status_code not in [200, 201]:
          raise ResponseError("Unexpected final chunk response", response)

        if not is_last_chunk and response.status_code != 308:
          raise ResponseError("Unexpected mid chunk response", response)

      PutChunk()

      # TODO: Add support for more detailed progress updates that
      # would include state of the upload.
      opts.progress_callback()

      if is_last_chunk:
        break
      else:
        offset += len(chunk)

  def SendPath(self, path: pathlib.Path, opts: Optional[Opts] = None) -> None:
    """Stream a file at the specified path to Google Cloud Storage.

    Args:
      path: A path to the file to send.
      opts: Options used for the transfer procedure.

    Returns:
      Nothing.

    Raises:
      RequestError: If it is not possible to deliver one of the chunks.
      ResponseError: If the server responded with unexpected status.
    """
    with path.open(mode="rb") as file:
      self.SendFile(file, opts=opts)

  @property
  def uri(self) -> str:
    """A session URI associated with this resumable upload process."""
    return self._uri
