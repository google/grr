#!/usr/bin/env python
"""HTTP API connector implementation."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import json
import logging


from future.moves.urllib import parse as urlparse
from future.utils import iterkeys

import requests

from werkzeug import routing

from google.protobuf import json_format
from google.protobuf import symbol_database
from grr_api_client import connector
from grr_api_client import errors
from grr_api_client import utils

from grr_response_proto.api import reflection_pb2

logger = logging.getLogger(__name__)


class Error(Exception):
  """Base error class for HTTP connector."""


class HttpConnector(connector.Connector):
  """API connector implementation that works through HTTP API."""

  JSON_PREFIX = ")]}\'\n"
  DEFAULT_PAGE_SIZE = 50
  DEFAULT_BINARY_CHUNK_SIZE = 66560

  def __init__(self,
               api_endpoint=None,
               auth=None,
               proxies=None,
               verify=True,
               cert=None,
               trust_env=True,
               page_size=None):
    super(HttpConnector, self).__init__()

    self.api_endpoint = api_endpoint
    self.auth = auth
    self.proxies = proxies
    self.verify = verify
    self.cert = cert
    self.trust_env = trust_env
    self._page_size = page_size or self.DEFAULT_PAGE_SIZE

    self.csrf_token = None
    self.api_methods = {}

  def _GetCSRFToken(self):
    logger.debug("Fetching CSRF token from %s...", self.api_endpoint)

    with requests.Session() as session:
      session.trust_env = self.trust_env
      index_response = session.get(
          self.api_endpoint,
          auth=self.auth,
          proxies=self.proxies,
          verify=self.verify,
          cert=self.cert)

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

    with requests.Session() as session:
      session.trust_env = self.trust_env
      response = session.get(
          url,
          headers=headers,
          cookies=cookies,
          auth=self.auth,
          proxies=self.proxies,
          verify=self.verify,
          cert=self.cert)
    self._CheckResponseStatus(response)

    json_str = response.content[len(self.JSON_PREFIX):]

    # Register descriptors in the database, so that all API-related
    # protos are recognized when Any messages are unpacked.
    utils.RegisterProtoDescriptors(symbol_database.Default())

    proto = reflection_pb2.ApiListApiMethodsResult()
    json_format.Parse(json_str, proto, ignore_unknown_fields=True)

    routing_rules = []

    self.api_methods = {}
    for method in proto.items:
      if not method.http_route.startswith("/api/v2/"):
        method.http_route = method.http_route.replace("/api/", "/api/v2/", 1)

      self.api_methods[method.name] = method
      routing_rules.append(
          routing.Rule(
              method.http_route,
              methods=method.http_methods,
              endpoint=method.name))

    self.handlers_map = routing.Map(routing_rules)

    parsed_endpoint_url = urlparse.urlparse(self.api_endpoint)
    self.urls = self.handlers_map.bind(
        parsed_endpoint_url.netloc, url_scheme=parsed_endpoint_url.scheme)

  def _InitializeIfNeeded(self):
    if not self.csrf_token:
      self.csrf_token = self._GetCSRFToken()
    if not self.api_methods:
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
          path_params[field.name] = self._CoerceValueToQueryStringType(
              field, value)

    url = self.urls.build(handler_name, path_params, force_external=True)

    method = None
    for rule in self.handlers_map.iter_rules():
      if rule.endpoint == handler_name:
        method = [m for m in rule.methods if m != "HEAD"][0]

    if not method:
      raise RuntimeError("Can't find method for %s" % handler_name)

    return method, url, list(iterkeys(path_params))

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

    with requests.Session() as session:
      session.trust_env = self.trust_env
      options = session.merge_environment_settings(
          prepped_request.url, self.proxies or {}, None, self.verify, self.cert)
      response = session.send(prepped_request, **options)

    self._CheckResponseStatus(response)

    content = response.content
    json_str = content[len(self.JSON_PREFIX):]

    if method_descriptor.result_type_descriptor.name:
      default_value = method_descriptor.result_type_descriptor.default
      result = utils.TypeUrlToMessage(default_value.type_url)
      json_format.Parse(json_str, result, ignore_unknown_fields=True)
      return result

  def SendStreamingRequest(self, handler_name, args):
    self._InitializeIfNeeded()
    method_descriptor = self.api_methods[handler_name]

    request = self.BuildRequest(method_descriptor.name, args)
    prepped_request = request.prepare()

    session = requests.Session()
    session.trust_env = self.trust_env
    options = session.merge_environment_settings(
        prepped_request.url, self.proxies or {}, None, self.verify, self.cert)
    options["stream"] = True
    response = session.send(prepped_request, **options)
    self._CheckResponseStatus(response)

    def GenerateChunks():
      for chunk in response.iter_content(self.DEFAULT_BINARY_CHUNK_SIZE):
        yield chunk

    def Close():
      response.close()
      session.close()

    return utils.BinaryChunkIterator(chunks=GenerateChunks(), on_close=Close)
