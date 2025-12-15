#!/usr/bin/env python
"""HTTP API connector implementation."""

from collections.abc import Iterable, Iterator
import contextlib
import json
import logging
import re
from typing import Any, NamedTuple, Optional, Union
from urllib import parse as urlparse

import pkg_resources
import requests
from werkzeug import routing

from google.protobuf import descriptor
from google.protobuf import json_format
from google.protobuf import message
from google.protobuf import symbol_database
from grr_api_client import errors
from grr_api_client import utils
from grr_api_client.connectors import abstract
from grr_response_proto.api import metadata_pb2
from grr_response_proto.api import reflection_pb2

logger = logging.getLogger(__name__)


_VERSION_STRING_PATTERN = re.compile(r"(\d+)\.(\d+)\.(\d+)\.post(\d+)")


class VersionTuple(NamedTuple):
  """A tuple that represents the GRR's version metadata."""

  major: int
  minor: int
  revision: int
  release: int

  @classmethod
  def FromJson(
      cls,
      json_str: str,
  ) -> "VersionTuple":
    """Creates a version tuple from a JSON response.

    The JSON response must be serialized variant of the `ApiGetGrrVersionResult`
    message.

    Args:
      json_str: A string object with version information JSON data.

    Returns:
      Parsed version tuple.
    """
    result = metadata_pb2.ApiGetGrrVersionResult()
    json_format.Parse(json_str, result, ignore_unknown_fields=True)

    return cls.FromProto(result)

  @classmethod
  def FromProto(
      cls,
      proto: metadata_pb2.ApiGetGrrVersionResult,
  ) -> "VersionTuple":
    """Creates a version tuple from a server response.

    Args:
      proto: A server response with version information.

    Returns:
      Parsed version tuple.
    """
    return VersionTuple(
        major=proto.major,
        minor=proto.minor,
        revision=proto.revision,
        release=proto.release)

  @classmethod
  def FromString(cls, string: str) -> "VersionTuple":
    """Creates a version tuple from a version string (like '1.3.3.post7').

    Args:
      string: A version string.

    Returns:
      Parsed version tuple.
    """
    match = _VERSION_STRING_PATTERN.match(string)
    if match is None:
      raise ValueError(f"Incorrect version string: {string!r}")

    return VersionTuple(
        major=int(match[1]),
        minor=int(match[2]),
        revision=int(match[3]),
        # TODO(hanuszczak): Replace with `str.removeprefix` once we support only
        # Python 3.9+.
        release=int(match[4][len("post"):] if match[4]
                    .startswith("post") else match[4]))


class Error(Exception):
  """Base error class for HTTP connector."""


class HttpConnector(abstract.Connector):
  """API connector implementation that works through HTTP API."""

  JSON_PREFIX = ")]}\'\n"
  DEFAULT_PAGE_SIZE = 50
  DEFAULT_BINARY_CHUNK_SIZE = 66560

  def __init__(
      self,
      api_endpoint: str,
      auth: Optional[tuple[str, str]] = None,
      proxies: Optional[dict[str, str]] = None,
      verify: Optional[bool] = None,
      cert: Optional[str] = None,
      trust_env: Optional[bool] = None,
      page_size: Optional[int] = None,
      validate_version: Optional[bool] = None,
  ):
    super().__init__()

    if verify is None:
      verify = True

    if trust_env is None:
      trust_env = True

    if page_size is None:
      page_size = self.DEFAULT_PAGE_SIZE

    if validate_version is None:
      validate_version = True

    self.api_endpoint: str = api_endpoint
    self.proxies: Optional[dict[str, str]] = proxies
    self.verify: bool = verify
    self.cert: Optional[str] = cert
    self._page_size: int = page_size
    self.session = requests.Session()
    self.session.auth = auth
    self.session.cert = cert
    self.session.proxies = proxies
    self.session.trust_env = trust_env
    self.session.verify = verify

    self.csrf_token: Optional[str] = None
    self.api_methods: dict[str, reflection_pb2.ApiMethod] = {}

    self._server_version: Optional[VersionTuple] = None
    self._api_client_version: Optional[VersionTuple] = None

    if validate_version:
      self._ValidateVersion()

  def _GetCSRFToken(self) -> Optional[str]:
    logger.debug("Fetching CSRF token from %s...", self.api_endpoint)

    index_response = self.session.get(self.api_endpoint)

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
    response = self.session.get(
        url,
        headers=headers,
        cookies=cookies,
    )
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
        raise ValueError(
            f"Method {method.name} has an unexpected HTTP route:"
            f" {method.http_route}"
        )

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

  def _FetchVersion(self) -> Optional[VersionTuple]:
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

    response = self.session.get(
        url=f"{self.api_endpoint}/api/v2/metadata/version",
        headers=headers,
        cookies=cookies,
    )

    try:
      self._CheckResponseStatus(response)
    except errors.Error:
      return None

    json_str = response.content.decode("utf-8").lstrip(self.JSON_PREFIX)
    return VersionTuple.FromJson(json_str)

  def _InitializeIfNeeded(self):
    if not self.csrf_token:
      self.csrf_token = self._GetCSRFToken()
    if not self.api_methods:
      self._FetchRoutingMap()

  def _CoerceValueToQueryStringType(
      self,
      field: descriptor.FieldDescriptor,
      value: Any,
  ) -> Union[int, str]:
    if isinstance(value, bool):
      value = int(value)
    elif field.enum_type:
      value = field.enum_type.values_by_number[value].name

    return value

  def _GetMethodUrlAndPathParamsNames(
      self,
      handler_name: str,
      args: message.Message,
  ) -> tuple[reflection_pb2.ApiMethod, str, Iterable[str]]:
    path_params = {}  # Dict[str, Union[int, str]]
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

  def _ArgsToQueryParams(
      self,
      args: Optional[message.Message],
      exclude_names: Iterable[str],
  ) -> dict[str, Union[int, str]]:
    if args is None:
      return {}

    result = utils.MessageToFlatDict(args, self._CoerceValueToQueryStringType)
    for name in exclude_names:
      del result[name]

    return result

  def _ArgsToBody(
      self,
      args: Optional[message.Message],
      exclude_names: Iterable[str],
  ) -> Optional[str]:
    if args is None:
      return None

    args_copy = utils.CopyProto(args)

    for name in exclude_names:
      args_copy.ClearField(name)

    return json_format.MessageToJson(args_copy)

  def _CheckResponseStatus(self, response: requests.Response):
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
    elif response.status_code == 429:
      raise errors.ResourceExhaustedError(json_message)
    elif response.status_code == 501:
      raise errors.ApiNotImplementedError(json_message)
    else:
      raise errors.UnknownError(json_message)

  def BuildRequest(
      self,
      method_name: str,
      args: Optional[message.Message],
  ) -> requests.Request:
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
    )

  @property
  def page_size(self) -> int:
    return self._page_size

  def SendRequest(
      self,
      handler_name: str,
      args: Optional[message.Message],
  ) -> Optional[message.Message]:
    self._InitializeIfNeeded()
    method_descriptor = self.api_methods[handler_name]

    request = self.BuildRequest(method_descriptor.name, args)
    prepped_request = self.session.prepare_request(request)

    options = self.session.merge_environment_settings(
        prepped_request.url, self.proxies or {}, None, self.verify, self.cert
    )
    response = self.session.send(prepped_request, **options)

    self._CheckResponseStatus(response)

    content = response.content
    json_str = content[len(self.JSON_PREFIX):]

    if method_descriptor.result_type_url:
      result = utils.TypeUrlToMessage(method_descriptor.result_type_url)
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
    prepped_request = self.session.prepare_request(request)

    options = self.session.merge_environment_settings(
        prepped_request.url, self.proxies or {}, None, self.verify, self.cert
    )
    options["stream"] = True
    response = self.session.send(prepped_request, **options)
    self._CheckResponseStatus(response)

    def GenerateChunks() -> Iterator[bytes]:
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
      self._server_version = self._FetchVersion()

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

      self._api_client_version = VersionTuple.FromString(distribution.version)

    return self._api_client_version
