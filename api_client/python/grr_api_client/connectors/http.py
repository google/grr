#!/usr/bin/env python
# Lint as: python3
"""HTTP API connector implementation."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import contextlib
import json
import logging
from typing import Optional
from typing import Tuple
from urllib import parse as urlparse

import pkg_resources
import requests

from werkzeug import routing

from google.protobuf import json_format
from google.protobuf import message
from google.protobuf import symbol_database
from grr_api_client import errors
from grr_api_client import utils
from grr_api_client.connectors import abstract
from grr_response_proto.api import metadata_pb2
from grr_response_proto.api import reflection_pb2

logger = logging.getLogger(__name__)


VersionTuple = Tuple[int, int, int, int]


class Error(Exception):
  """Base error class for HTTP connector."""


class HttpConnector(abstract.Connector):
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
               page_size=None,
               validate_version=True):
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

    self._server_version = None  # type: Optional[VersionTuple]
    self._api_client_version = None  # type: Optional[VersionTuple]

    if validate_version:
      self._ValidateVersion()

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

  def _FetchVersion(self) -> Optional[metadata_pb2.ApiGetGrrVersionResult]:
    """Fetches version information about the GRR server.

    Note that it might be the case that the server version is so old that it
    does not have the method for retrieving server version. In such case, the
    method will return `None`.

    Returns:
      A message with version descriptor (if possible).
    """
    headers = {
        "x-csrftoken": self.csrf_token,
        "x-requested-with": "XMLHttpRequest",
    }

    cookies = {
        "csrftoken": self.csrf_token,
    }

    with requests.Session() as session:
      session.trust_env = self.trust_env
      response = session.get(
          url=f"{self.api_endpoint}/api/v2/metadata/version",
          headers=headers,
          cookies=cookies,
          auth=self.auth,
          proxies=self.proxies,
          verify=self.verify,
          cert=self.cert)

    try:
      self._CheckResponseStatus(response)
    except errors.Error:
      return None

    result = metadata_pb2.ApiGetGrrVersionResult()
    json_str = response.content.decode("utf-8").lstrip(self.JSON_PREFIX)
    json_format.Parse(json_str, result, ignore_unknown_fields=True)

    return result

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

    return method, url, list(path_params.keys())

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
      # TODO(hanuszczak): `json` package should not be used.
      parsed_json = json.loads(json_str)
      json_message = (
          parsed_json["message"] + "\n" + parsed_json.get("traceBack", ""))
    except (ValueError, KeyError):
      json_message = content

    if response.status_code == 403:
      raise errors.AccessForbiddenError(json_message)
    elif response.status_code == 404:
      raise errors.ResourceNotFoundError(json_message)
    elif response.status_code == 422:
      raise errors.InvalidArgumentError(json_message)
    elif response.status_code == 501:
      raise errors.ApiNotImplementedError(json_message)
    else:
      raise errors.UnknownError(json_message)

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
  def page_size(self) -> int:
    return self._page_size

  def SendRequest(
      self,
      handler_name: str,
      args: message.Message,
  ) -> Optional[message.Message]:
    self._InitializeIfNeeded()
    method_descriptor = self.api_methods[handler_name]

    request = self.BuildRequest(method_descriptor.name, args)
    prepped_request = request.prepare()

    with requests.Session() as session:
      session.trust_env = self.trust_env
      options = session.merge_environment_settings(prepped_request.url,
                                                   self.proxies or {}, None,
                                                   self.verify, self.cert)
      response = session.send(prepped_request, **options)

    self._CheckResponseStatus(response)

    content = response.content
    json_str = content[len(self.JSON_PREFIX):]

    if method_descriptor.result_type_descriptor.name:
      default_value = method_descriptor.result_type_descriptor.default
      result = utils.TypeUrlToMessage(default_value.type_url)
      json_format.Parse(json_str, result, ignore_unknown_fields=True)
      return result

  def SendStreamingRequest(
      self,
      handler_name: str,
      args: message.Message,
  ) -> utils.BinaryChunkIterator:
    self._InitializeIfNeeded()
    method_descriptor = self.api_methods[handler_name]

    request = self.BuildRequest(method_descriptor.name, args)
    prepped_request = request.prepare()

    session = requests.Session()
    session.trust_env = self.trust_env
    options = session.merge_environment_settings(prepped_request.url,
                                                 self.proxies or {}, None,
                                                 self.verify, self.cert)
    options["stream"] = True
    response = session.send(prepped_request, **options)
    self._CheckResponseStatus(response)

    def GenerateChunks():
      with contextlib.closing(session):
        with contextlib.closing(response):
          for chunk in response.iter_content(self.DEFAULT_BINARY_CHUNK_SIZE):
            yield chunk

    return utils.BinaryChunkIterator(chunks=GenerateChunks())

  def _ValidateVersion(self):
    """Validates that the API client is compatible the GRR server.

    In case version is impossible to validate (e.g. we are not running from
    a PIP package), this function does nothing and skips validation.

    Raises:
      VersionMismatchError: If the API client is incompatible with the server.
    """
    api_client_version = self.api_client_version
    server_version = self.server_version
    if api_client_version is None or server_version is None:
      # If either of the versions is unspecified, we cannot properly validate.
      return

    if api_client_version < server_version:
      raise errors.VersionMismatchError(
          server_version=server_version, api_client_version=api_client_version)

  @property
  def server_version(self) -> Optional[VersionTuple]:
    """Retrieves (lazily) the version server tuple."""
    if self._server_version is None:
      version = self._FetchVersion()
      if version is None:
        return None

      self._server_version = (
          version.major,
          version.minor,
          version.revision,
          version.release,
      )

    return self._server_version

  @property
  def api_client_version(self) -> Optional[VersionTuple]:
    """Retrieves (lazily) the API client version tuple (if possible)."""
    if self._api_client_version is None:
      try:
        distribution = pkg_resources.get_distribution("grr_api_client")
      except pkg_resources.DistributionNotFound:
        # Distribution might not be available if we are not running from within
        # a PIP package. In such case, it is not possible to retrieve version.
        return None

      (major, minor, revision, release) = distribution.version.split(".")
      major, minor, revision = int(major), int(minor), int(revision)
      release = int(release.lstrip("post"))

      self._api_client_version = (major, minor, revision, release)

    return self._api_client_version
