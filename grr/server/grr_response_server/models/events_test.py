#!/usr/bin/env python
from absl.testing import absltest

from grr_response_proto import objects_pb2
from grr_response_server.gui import http_request
from grr_response_server.gui import http_response
from grr_response_server.models import events


class APIAuditEntryFromHttpRequestResponseTest(absltest.TestCase):

  def testBaseFields(self):
    request = http_request.HttpRequest.from_values(
        "/bar?foo=baz", "http://example.com/test"
    )
    request.user = "testuser"

    response = http_response.HttpResponse(
        status=42,
        headers={"X-API-Method": "TestMethod"},
    )

    expected = objects_pb2.APIAuditEntry(
        http_request_path="/bar?foo=baz",  # Includes query string.
        router_method_name="TestMethod",
        username="testuser",
        response_code=objects_pb2.APIAuditEntry.Code.ERROR,
    )

    result = events.APIAuditEntryFromHttpRequestResponse(request, response)
    self.assertEqual(expected, result)

  def testStatus(self):
    request = http_request.HttpRequest({})
    request.user = "needs_to_be_set"

    # Make sure we always test everything in the dict
    for status, want_code in events._HTTP_STATUS_TO_CODE.items():
      response = http_response.HttpResponse(status=status)
      result = events.APIAuditEntryFromHttpRequestResponse(request, response)
      self.assertEqual(want_code, result.response_code)

  def testStatusDefault(self):
    request = http_request.HttpRequest({})
    request.user = "needs_to_be_set"
    response = http_response.HttpResponse(status=42)
    result = events.APIAuditEntryFromHttpRequestResponse(request, response)
    self.assertEqual(objects_pb2.APIAuditEntry.Code.ERROR, result.response_code)


if __name__ == "__main__":
  absltest.main()
