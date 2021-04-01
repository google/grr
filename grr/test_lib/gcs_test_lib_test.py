#!/usr/bin/env python
from absl.testing import absltest
import requests
import responses

from grr.test_lib import gcs_test_lib


class FakeUploadHandlerTest(absltest.TestCase):

  @responses.activate
  def testSinglePartUpload(self):
    handler = gcs_test_lib.FakeUploadHandler()
    responses.add_callback(responses.POST, "https://foo.bar/", handler)

    response = requests.post(
        "https://foo.bar/",
        data=b"foobar",
        headers={
            "Content-Length": "6",
            "Content-Range": "bytes 0-5/6",
        })
    self.assertEqual(response.status_code, 201)

    self.assertEqual(handler.content, b"foobar")

  @responses.activate
  def testMultiPartUpload(self):
    handler = gcs_test_lib.FakeUploadHandler()
    responses.add_callback(responses.POST, "https://foo.bar/", handler)

    response = requests.post(
        "https://foo.bar/",
        data=b"foo",
        headers={
            "Content-Length": "3",
            "Content-Range": "bytes 0-2/*",
        })
    self.assertEqual(response.status_code, 308)

    response = requests.post(
        "https://foo.bar/",
        data=b"bar",
        headers={
            "Content-Length": "3",
            "Content-Range": "bytes 3-5/*",
        })
    self.assertEqual(response.status_code, 308)

    response = requests.post(
        "https://foo.bar/",
        data=b"baz",
        headers={
            "Content-Length": "3",
            "Content-Range": "bytes 6-8/9",
        })
    self.assertEqual(response.status_code, 201)

    self.assertEqual(handler.content, b"foobarbaz")

  @responses.activate
  def testInvalidContentLength(self):
    handler = gcs_test_lib.FakeUploadHandler()
    responses.add_callback(responses.POST, "https://foo.bar/", handler)

    # The `requests` package generally provides its own `Content-Length` header
    # calculated based on the attached payload. We work around this by rewriting
    # the value in prepared request.
    request = requests.Request("POST", "https://foo.bar/", data=b"foobar")
    request = request.prepare()
    request.headers["Content-Length"] = "3"
    request.headers["Content-Range"] = "bytes 0-5/6"

    with requests.session() as session:
      response = session.send(request)

    self.assertEqual(response.status_code, 400)
    self.assertEqual(response.text, "invalid content length")

  @responses.activate
  def testInvalidContentRangeSyntax(self):
    handler = gcs_test_lib.FakeUploadHandler()
    responses.add_callback(responses.POST, "https://foo.bar/", handler)

    response = requests.post(
        "https://foo.bar/",
        data=b"foobar",
        headers={
            "Content-Length": "6",
            "Content-Range": "bytes ?-?/?",
        })
    self.assertEqual(response.status_code, 400)
    self.assertEqual(response.text, "invalid content range")

  @responses.activate
  def testInvalidContentRangeFirstByteOffset(self):
    handler = gcs_test_lib.FakeUploadHandler()
    responses.add_callback(responses.POST, "https://foo.bar/", handler)

    response = requests.post(
        "https://foo.bar/",
        data=b"foobar",
        headers={
            "Content-Length": "6",
            "Content-Range": "bytes 3-5/6",
        })
    self.assertEqual(response.status_code, 400)
    self.assertEqual(response.text, "incorrect first byte offset")

  @responses.activate
  def testInvalidContentRangeLastByteOffset(self):
    handler = gcs_test_lib.FakeUploadHandler()
    responses.add_callback(responses.POST, "https://foo.bar/", handler)

    response = requests.post(
        "https://foo.bar/",
        data=b"foobar",
        headers={
            "Content-Length": "6",
            "Content-Range": "bytes 0-10/6",
        })
    self.assertEqual(response.status_code, 400)
    self.assertEqual(response.text, "incorrect last byte offset")

  @responses.activate
  def testIncorrectNumberOfTotalBytes(self):
    handler = gcs_test_lib.FakeUploadHandler()
    responses.add_callback(responses.POST, "https://foo.bar/", handler)

    response = requests.post(
        "https://foo.bar/",
        data=b"foobar",
        headers={
            "Content-Length": "6",
            "Content-Range": "bytes 0-5/11",
        })
    self.assertEqual(response.status_code, 400)
    self.assertEqual(response.text, "incorrect number of total bytes")


if __name__ == "__main__":
  absltest.main()
