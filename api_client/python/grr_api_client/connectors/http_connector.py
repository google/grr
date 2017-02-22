#!/usr/bin/env python
"""HTTP API connector implementation."""

import collections
import json
import urlparse

import requests

from werkzeug import routing

from google.protobuf import wrappers_pb2

from google.protobuf import json_format
from google.protobuf import symbol_database

import logging

from grr_api_client import connector
from grr_api_client import errors
from grr_api_client import utils

from grr.client.components.rekall_support import rekall_pb2

from grr.proto import api_pb2
from grr.proto import flows_pb2
from grr.proto import jobs_pb2

logger = logging.getLogger(__name__)


class Error(Exception):
  """Base error class for HTTP connector."""


class HttpConnector(connector.Connector):
  """API connector implementation that works through HTTP API."""

  JSON_PREFIX = ")]}\'\n"
  DEFAULT_PAGE_SIZE = 50
  DEFAULT_BINARY_CHUNK_SIZE = 66560

  def __init__(self, api_endpoint=None, auth=None, page_size=None):
    super(HttpConnector, self).__init__()

    self.api_endpoint = api_endpoint
    self.auth = auth
    self._page_size = page_size or self.DEFAULT_PAGE_SIZE

    self.csrf_token = None

  def _GetCSRFToken(self):
    logger.debug("Fetching CSRF token from %s...", self.api_endpoint)

    index_response = requests.get(self.api_endpoint, auth=self.auth)
    self._CheckResponseStatus(index_response)

    csrf_token = index_response.cookies.get("csrftoken")

    if not csrf_token:
      raise RuntimeError("Can't get CSRF token.")

    logger.debug("Got CSRF token: %s", csrf_token)

    return csrf_token

  def _FetchRoutingMap(self):
    headers = {
        "x-csrftoken": self.csrf_token,
        "x-requested-with": "XMLHttpRequest"
    }
    cookies = {"csrftoken": self.csrf_token}

    url = "%s/%s" % (self.api_endpoint.strip("/"),
                     "api/v2/reflection/api-methods")
    response = requests.get(
        url, headers=headers, cookies=cookies, auth=self.auth)
    self._CheckResponseStatus(response)

    json_str = response.content[len(self.JSON_PREFIX):]

    db = symbol_database.Default()
    # Register descriptors in the database, so that all API-related
    # protos are recognized when Any messages are unpacked.
    db.RegisterFileDescriptor(api_pb2.DESCRIPTOR)
    db.RegisterFileDescriptor(flows_pb2.DESCRIPTOR)
    db.RegisterFileDescriptor(jobs_pb2.DESCRIPTOR)
    db.RegisterFileDescriptor(wrappers_pb2.DESCRIPTOR)
    db.RegisterFileDescriptor(rekall_pb2.DESCRIPTOR)

    proto = api_pb2.ApiListApiMethodsResult()
    json_format.Parse(json_str, proto)

    routing_rules = []

    self.api_methods = {}
    for method in proto.items:
      if not method.http_route.startswith("/api/v2/"):
        method.http_route = method.http_route.replace("/api/", "/api/v2/")

      self.api_methods[method.name] = method
      routing_rules.append(
          routing.Rule(
              method.http_route,
              methods=method.http_methods,
              endpoint=method.name))

    self.handlers_map = routing.Map(routing_rules)

    parsed_endpoint_url = urlparse.urlparse(self.api_endpoint)
    self.urls = self.handlers_map.bind(parsed_endpoint_url.netloc, "/")

  def _InitializeIfNeeded(self):
    if not self.csrf_token:
      self.csrf_token = self._GetCSRFToken()
      self._FetchRoutingMap()

  def _CoerceValueToQueryStringType(self, field, value):
    if isinstance(value, bool):
      value = int(value)
    elif field.enum_type:
      value = field.enum_type.values_by_number[value].name.lower()

    return value

  def _GetMethodUrlAndPathParamsNames(self, handler_name, args):
    path_params = {}
    if args:
      for field, value in args.ListFields():
        if self.handlers_map.is_endpoint_expecting(handler_name, field.name):
          path_params[field.name] = self._CoerceValueToQueryStringType(field,
                                                                       value)

    url = self.urls.build(handler_name, path_params, force_external=True)

    method = None
    for rule in self.handlers_map.iter_rules():
      if rule.endpoint == handler_name:
        method = [m for m in rule.methods if m != "HEAD"][0]

    if not method:
      raise RuntimeError("Can't find method for %s" % handler_name)

    return method, url, path_params.keys()

  def _ArgsToQueryParams(self, args, exclude_names):
    if not args:
      return {}

    # Using OrderedDict guarantess stable order of query parameters in the
    # generated URLs.
    result = collections.OrderedDict()
    for field, value in sorted(args.ListFields(), key=lambda f: f[0].name):
      if field.name not in exclude_names:
        result[field.name] = self._CoerceValueToQueryStringType(field, value)

    return result

  def _ArgsToBody(self, args, exclude_names):
    if not args:
      return None

    args_copy = utils.CopyProto(args)

    for name in exclude_names:
      args_copy.ClearField(name)

    return json_format.MessageToJson(args_copy)

  def _CheckResponseStatus(self, response):
    if response.status_code == 200:
      return

    content = response.content
    json_str = content[len(self.JSON_PREFIX):]

    try:
      parsed_json = json.loads(json_str)
      message = parsed_json["message"]
    except (ValueError, KeyError):
      message = content

    if response.status_code == 403:
      raise errors.AccessForbiddenError(message)
    elif response.status_code == 404:
      raise errors.ResourceNotFoundError(message)
    elif response.status_code == 501:
      raise errors.ApiNotImplementedError(message)
    else:
      raise errors.UnknownError(message)

  def BuildRequest(self, method_name, args):
    self._InitializeIfNeeded()
    method, url, path_params_names = self._GetMethodUrlAndPathParamsNames(
        method_name, args)

    if method == "GET":
      body = None
      query_params = self._ArgsToQueryParams(args, path_params_names)
    else:
      body = self._ArgsToBody(args, path_params_names)
      query_params = {}

    headers = {
        "x-csrftoken": self.csrf_token,
        "x-requested-with": "XMLHttpRequest"
    }
    cookies = {"csrftoken": self.csrf_token}
    logger.debug("%s request: %s (query: %s, body: %s, headers %s)", method,
                 url, query_params, body, headers)
    return requests.Request(
        method,
        url,
        data=body,
        params=query_params,
        headers=headers,
        cookies=cookies,
        auth=self.auth)

  @property
  def page_size(self):
    return self._page_size

  def SendRequest(self, handler_name, args):
    self._InitializeIfNeeded()
    method_descriptor = self.api_methods[handler_name]

    request = self.BuildRequest(method_descriptor.name, args)
    prepped_request = request.prepare()

    session = requests.Session()
    response = session.send(prepped_request)
    self._CheckResponseStatus(response)

    content = response.content
    json_str = content[len(self.JSON_PREFIX):]

    logger.debug("%s response (%s, %d):\n%s", request.method, request.url,
                 response.status_code, content)

    if method_descriptor.result_type_descriptor.name:
      default_value = method_descriptor.result_type_descriptor.default
      result = utils.TypeUrlToMessage(default_value.type_url)
      json_format.Parse(json_str, result)
      return result

  def SendStreamingRequest(self, handler_name, args):
    self._InitializeIfNeeded()
    method_descriptor = self.api_methods[handler_name]

    request = self.BuildRequest(method_descriptor.name, args)
    prepped_request = request.prepare()

    session = requests.Session()
    response = session.send(prepped_request, stream=True)
    self._CheckResponseStatus(response)

    def GenerateChunks():
      for chunk in response.iter_content(self.DEFAULT_BINARY_CHUNK_SIZE):
        yield chunk

    return utils.BinaryChunkIterator(
        chunks=GenerateChunks(), on_close=response.close)
