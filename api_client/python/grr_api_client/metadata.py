#!/usr/bin/env python
"""Metadata-related part of GRR API client library."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json


def GetOpenApiDescription(as_string=False, context=None):
  if not context:
    raise ValueError("context can't be empty")

  openapi_proto = context.SendRequest("GetOpenApiDescription", None)
  openapi_json = openapi_proto.openapi_description

  if as_string:
    return openapi_json

  return json.loads(openapi_json)
