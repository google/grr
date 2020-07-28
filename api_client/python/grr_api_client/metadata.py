#!/usr/bin/env python
"""Metadata-related part of GRR API client library."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json


def GetOpenApiDescription(context=None):
  """Returns the OpenAPI description of the GRR API as a dictionary."""
  if not context:
    raise ValueError("context can't be empty")

  open_api_proto = context.SendRequest("GetOpenApiDescription", None)
  open_api_json = open_api_proto.open_api_description

  return json.loads(open_api_json)
