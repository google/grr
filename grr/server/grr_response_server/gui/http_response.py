#!/usr/bin/env python
# Lint as: python3
"""Api call context used during the request/response handling."""

from typing import Optional

from werkzeug import wrappers as werkzeug_wrappers

from grr_response_server.gui import api_call_context


class HttpResponse(werkzeug_wrappers.Response):
  """HTTP response object to be used in GRR."""

  def __init__(self,
               *args,
               context: Optional[api_call_context.ApiCallContext] = None,
               **kwargs):
    super(HttpResponse, self).__init__(*args, **kwargs)
    self.context = context
