#!/usr/bin/env python
"""HTTP API connector implementation."""

import json
import urlparse

import requests

from werkzeug import routing

from google.protobuf import message

import logging

from grr.gui.api_client import connector
from grr.gui.api_client import utils
from grr.proto import semantic_pb2

logger = logging.getLogger(__name__)


class HttpConnector(connector.Connector):
  """API connector implementation that works through HTTP API."""

  class ResponseFormat(object):
    JSON = 0
    TYPED_JSON = 1

  HANDLERS_MAP = routing.Map([
      routing.Rule("/api/clients",
                   methods=["GET"],
                   endpoint="SearchClients"),
      routing.Rule("/api/clients/<client_id>",
                   methods=["GET"],
                   endpoint="GetClient"),
      routing.Rule("/api/clients/<client_id>/flows",
                   methods=["GET"],
                   endpoint="ListFlows"),
      routing.Rule("/api/clients/<client_id>/flows",
                   methods=["POST"],
                   endpoint="CreateFlow"),
  ])

  JSON_PREFIX = ")]}\'\n"
  DEFAULT_PAGE_SIZE = 50

  def __init__(self,
               api_endpoint=None,
               auth=None,
               response_format=ResponseFormat.JSON,
               page_size=None):
    super(HttpConnector, self).__init__()

    self.api_endpoint = api_endpoint
    self.auth = auth
    self.response_format = response_format
    self.page_size = page_size or self.DEFAULT_PAGE_SIZE

    self.csrf_token = None

    parsed_url = urlparse.urlparse(api_endpoint)
    self.urls = self.HANDLERS_MAP.bind(parsed_url.netloc, "/")

  def _GetCSRFToken(self):
    logger.debug("Fetching CSRF token from %s...", self.api_endpoint)

    index_response = requests.get(self.api_endpoint, auth=self.auth)
    csrf_token = index_response.cookies.get("csrftoken")

    if not csrf_token:
      raise RuntimeError("Can't get CSRF token.")

    logger.debug("Got CSRF token: %s", csrf_token)

    return csrf_token

  def _GetMethodUrlAndQueryParams(self, handler_name, args):
    path_params = {}
    query_params = {}
    for field, value in args.ListFields():
      if self.HANDLERS_MAP.is_endpoint_expecting(handler_name, field.name):
        path_params[field.name] = value
      else:
        query_params[field.name] = value

    url = self.urls.build(handler_name, path_params, force_external=True)

    method = None
    for rule in self.HANDLERS_MAP.iter_rules():
      if rule.endpoint == handler_name:
        method = [m for m in rule.methods if m != "HEAD"][0]

    if not method:
      raise RuntimeError("Can't find method for %s" % handler_name)

    return method, url, query_params

  def _QueryParamsToBody(self, query_params):
    result = {}
    for k, v in query_params.items():
      result[k] = self._ToJSON(v)

    return result

  def _ToJSON(self, value):
    if isinstance(value, semantic_pb2.AnyValue):
      proto = utils.TypeUrlToMessage(value.type_url)
      proto.ParseFromString(value.value)
      return self._ToJSON(proto)
    elif isinstance(value, message.Message):
      result = {}
      for descriptor, value in value.ListFields():
        result[descriptor.name] = self._ToJSON(value)
      return result
    else:
      return value

  def SendRequest(self, handler_name, args):
    if not self.csrf_token:
      self.csrf_token = self._GetCSRFToken()

    headers = {
        "x-csrftoken": self.csrf_token,
        "x-requested-with": "XMLHttpRequest"
    }
    cookies = {"csrftoken": self.csrf_token}

    method, url, query_params = self._GetMethodUrlAndQueryParams(handler_name,
                                                                 args)

    body = None
    if method != "GET":
      body = self._QueryParamsToBody(query_params)
      query_params = {}

    if self.response_format == self.ResponseFormat.JSON:
      query_params["strip_type_info"] = "1"

    logger.debug("%s request: %s (query: %s, body: %s, headers %s)", method,
                 url, query_params, body, headers)
    request = requests.Request(method,
                               url,
                               json=body,
                               params=query_params,
                               headers=headers,
                               cookies=cookies)
    prepped_request = request.prepare()

    session = requests.Session()
    response = session.send(prepped_request)
    content = response.content

    logger.debug("%s response (%s, %d):\n%s", method, url, response.status_code,
                 content)
    if content[:len(self.JSON_PREFIX)] != self.JSON_PREFIX:
      raise RuntimeError("JSON prefix %s is not in response:\n%s" %
                         (self.JSON_PREFIX, content))

    json_str = content[len(self.JSON_PREFIX):]
    parsed_json = json.loads(json_str)

    if response.status_code == 200:
      return parsed_json
    else:
      raise RuntimeError("Server error: " + parsed_json["message"])

  def SendIteratorRequest(self, handler_name, args):
    response = self.SendRequest(handler_name, args)

    total_count = None
    try:
      total_count = response["total_count"]
    except KeyError:
      pass

    return utils.ItemsIterator(items=response["items"], total_count=total_count)

  def GetDataAttribute(self, data, attribute_name):
    if self.response_format == self.ResponseFormat.JSON:
      return data[attribute_name]
    elif self.response_format == self.ResponseFormat.TYPED_JSON:
      return data[attribute_name]["value"]
    else:
      raise RuntimeError("Unexpected response_format: %d", self.response_format)
