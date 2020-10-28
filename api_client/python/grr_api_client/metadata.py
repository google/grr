#!/usr/bin/env python
"""Metadata-related part of GRR API client library."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json
from typing import Dict, Any

from grr_api_client import context as api_context
from grr_response_proto.api import metadata_pb2


def GetOpenApiDescription(
    context: api_context.GrrApiContext = None,) -> Dict[str, Any]:
  """Returns the OpenAPI description of the GRR API as a dictionary."""
  if not context:
    raise ValueError("context can't be empty")

  openapi_proto = context.SendRequest("GetOpenApiDescription", None)
  if not isinstance(openapi_proto, metadata_pb2.ApiGetGrrVersionResult):
    raise TypeError(f"Unexpected response type: {type(openapi_proto)}")

  openapi_json = openapi_proto.openapi_description

  return json.loads(openapi_json)
