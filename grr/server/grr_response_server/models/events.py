#!/usr/bin/env python
"""Event related helpers."""

from grr_response_proto import objects_pb2
from grr_response_server.gui import http_request
from grr_response_server.gui import http_response

_HTTP_STATUS_TO_CODE = {
    200: objects_pb2.APIAuditEntry.Code.OK,
    403: objects_pb2.APIAuditEntry.Code.FORBIDDEN,
    404: objects_pb2.APIAuditEntry.Code.NOT_FOUND,
    500: objects_pb2.APIAuditEntry.Code.ERROR,
    501: objects_pb2.APIAuditEntry.Code.NOT_IMPLEMENTED,
}


def APIAuditEntryFromHttpRequestResponse(
    request: http_request.HttpRequest,
    response: http_response.HttpResponse,
) -> objects_pb2.APIAuditEntry:
  response_code = _HTTP_STATUS_TO_CODE.get(
      response.status_code, objects_pb2.APIAuditEntry.Code.ERROR
  )

  return objects_pb2.APIAuditEntry(
      http_request_path=request.full_path,  # Includes query string.
      router_method_name=response.headers.get("X-API-Method", ""),
      username=request.user,
      response_code=response_code,
  )
