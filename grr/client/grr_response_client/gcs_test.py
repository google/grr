#!/usr/bin/env python
import io
import time
from unittest import mock

from absl.testing import absltest
import portpicker
from requests import exceptions
import responses

from grr_response_client import gcs
from grr.test_lib import gcs_test_lib


class UploadSessionTest(absltest.TestCase):

  def testOpenIncorrectURL(self):
    unused_port = portpicker.pick_unused_port()

    with self.assertRaises(gcs.RequestError) as context:
      gcs.UploadSession.Open(f"https://localhost:{unused_port}")

    cause = context.exception.__cause__
    self.assertIsInstance(cause, exceptions.ConnectionError)

  @responses.activate
  def testOpenIncorrectResponseStatus(self):
    responses.add(responses.POST, "https://foo.bar/quux", status=404)

    with self.assertRaisesRegex(gcs.ResponseError, "Unexpected status"):
      gcs.UploadSession.Open("https://foo.bar/quux")

  @responses.activate
  def testOpenIncorrectResponseHeader(self):
    responses.add(responses.POST, "https://foo.bar/quux", status=201)

    with self.assertRaisesRegex(gcs.ResponseError, "Missing session URI"):
      gcs.UploadSession.Open("https://foo.bar/quux")

  @responses.activate
  def testOpen(self):
    response = responses.Response(responses.POST, "https://foo.bar/quux")
    response.status = 201
    response.headers = {
        "Location": "https://quux.thud/blargh",
    }
    responses.add(response)

    session = gcs.UploadSession.Open("https://foo.bar/quux")
    self.assertEqual(session.uri, "https://quux.thud/blargh")

  def testSendFileTransmissionFailure(self):
    unused_port = portpicker.pick_unused_port()

    session = gcs.UploadSession(f"https://localhost:{unused_port}")

    opts = gcs.UploadSession.Opts()
    opts.retry_chunk_attempts = 1
    opts.retry_chunk_init_delay = 0.0

    with self.assertRaises(gcs.RequestError) as context:
      session.SendFile(io.BytesIO(b"foobar"), opts=opts)

    cause = context.exception.__cause__
    self.assertIsInstance(cause, exceptions.ConnectionError)

  @responses.activate
  def testSendFileInterrupted(self):
    responses.add(responses.PUT, "https://foo.bar/quux", status=503)

    opts = gcs.UploadSession.Opts()
    opts.retry_chunk_attempts = 1
    opts.retry_chunk_init_delay = 0.0

    session = gcs.UploadSession("https://foo.bar/quux")

    with self.assertRaises(gcs.InterruptedResponseError):
      session.SendFile(io.BytesIO(b"foobar"), opts=opts)

  @responses.activate
  def testSendFileCancelledUpload(self):
    responses.add(responses.PUT, "https://foo.bar/quux", status=499)

    session = gcs.UploadSession("https://foo.bar/quux")

    with self.assertRaises(gcs.ResponseError):
      session.SendFile(io.BytesIO(b"foobar"))

  @responses.activate
  def testSendFileIncorrectResponseLastChunk(self):
    responses.add(responses.PUT, "https://foo.bar/quux", status=301)

    session = gcs.UploadSession("https://foo.bar/quux")

    opts = gcs.UploadSession.Opts()
    opts.chunk_size = 1024

    with self.assertRaisesRegex(gcs.ResponseError, "final chunk"):
      session.SendFile(io.BytesIO(b"foobar"), opts=opts)

  @responses.activate
  def testSendFileIncorrectResponseIntermediateChunk(self):
    responses.add(responses.PUT, "https://foo.bar/quux", status=301)

    session = gcs.UploadSession("https://foo.bar/quux")

    opts = gcs.UploadSession.Opts()
    opts.chunk_size = 1

    with self.assertRaisesRegex(gcs.ResponseError, "mid chunk"):
      session.SendFile(io.BytesIO(b"foobar"), opts=opts)

  @responses.activate
  def testSendFileEmpty(self):
    handler = gcs_test_lib.FakeUploadHandler()
    responses.add_callback(responses.PUT, "https://foo.bar/qux", handler)

    session = gcs.UploadSession("https://foo.bar/qux")
    session.SendFile(io.BytesIO(b""))

    self.assertEqual(handler.content, b"")

  @responses.activate
  def testSendFileSingleChunk(self):
    handler = gcs_test_lib.FakeUploadHandler()
    responses.add_callback(responses.PUT, "https://foo.bar/qux", handler)

    content = b"foobar"

    opts = gcs.UploadSession.Opts()
    opts.chunk_size = len(content)

    session = gcs.UploadSession("https://foo.bar/qux")
    session.SendFile(io.BytesIO(content), opts=opts)

    self.assertEqual(handler.content, content)

  @responses.activate
  def testSendFileMultipleChunks(self):
    handler = gcs_test_lib.FakeUploadHandler()
    responses.add_callback(responses.PUT, "https://foo.bar/qux", handler)

    opts = gcs.UploadSession.Opts()
    opts.chunk_size = 1

    session = gcs.UploadSession("https://foo.bar/qux")
    session.SendFile(io.BytesIO(b"foobar"), opts=opts)

    self.assertEqual(handler.content, b"foobar")

  @responses.activate
  def testSendFileRetrySuccess(self):
    handler = gcs_test_lib.FakeUploadHandler()
    responses.add(responses.PUT, "https://foo.bar/qux", status=502)
    responses.add(responses.PUT, "https://foo.bar/qux", status=503)
    responses.add(responses.PUT, "https://foo.bar/qux", status=504)
    responses.add_callback(responses.PUT, "https://foo.bar/qux", handler)

    opts = gcs.UploadSession.Opts()
    opts.chunk_size = 1
    opts.retry_chunk_attempts = 4
    opts.retry_chunk_init_delay = 0.0

    session = gcs.UploadSession("https://foo.bar/qux")
    session.SendFile(io.BytesIO(b"foobar"), opts=opts)

    self.assertEqual(handler.content, b"foobar")

  @responses.activate
  def testSendFileRetryFailure(self):
    handler = gcs_test_lib.FakeUploadHandler()
    responses.add(responses.PUT, "https://foo.bar/qux", status=502)
    responses.add(responses.PUT, "https://foo.bar/qux", status=503)
    responses.add(responses.PUT, "https://foo.bar/qux", status=504)
    responses.add_callback(responses.PUT, "https://foo.bar/qux", handler)

    opts = gcs.UploadSession.Opts()
    opts.chunk_size = 1
    opts.retry_chunk_attempts = 3
    opts.retry_chunk_init_delay = 0.0

    session = gcs.UploadSession("https://foo.bar/qux")

    with self.assertRaises(gcs.InterruptedResponseError) as context:
      session.SendFile(io.BytesIO(b"foobar"), opts=opts)

    self.assertEqual(context.exception.response.status_code, 504)

  @responses.activate
  def testSendFileChunkProgress(self):
    data = b"foobar"

    handler = gcs_test_lib.FakeUploadHandler()
    responses.add_callback(responses.PUT, "https://foo.bar/qux", handler)

    counter = 0

    def Progress() -> None:
      nonlocal counter
      counter += 1

    opts = gcs.UploadSession.Opts()
    opts.chunk_size = 1
    opts.progress_callback = Progress

    session = gcs.UploadSession("https://foo.bar/qux")
    session.SendFile(io.BytesIO(data), opts=opts)

    self.assertGreaterEqual(counter, len(data))

  @responses.activate
  @mock.patch.object(time, "sleep", lambda _: None)
  def testSendFileRetryProgress(self):
    responses.add(responses.PUT, "https://foo.bar/qux", status=503)

    counter = 0

    def Progress() -> None:
      nonlocal counter
      counter += 1

    opts = gcs.UploadSession.Opts()
    opts.retry_chunk_attempts = 2
    opts.retry_chunk_init_delay = 10.0
    opts.progress_interval = 1.0
    opts.progress_callback = Progress

    session = gcs.UploadSession("https://foo.bar/qux")

    with self.assertRaises(gcs.InterruptedResponseError):
      session.SendFile(io.BytesIO(b"foobar"), opts=opts)

    # We should sleep for 10 seconds and do progress calls every second, so it
    # should be called at least 10 times.
    self.assertGreaterEqual(counter, 10)


if __name__ == "__main__":
  absltest.main()
