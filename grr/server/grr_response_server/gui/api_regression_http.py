#!/usr/bin/env python
"""Base test classes for API handlers tests."""

import json
import logging
import os
import threading

from absl import flags
import portpicker

from grr_api_client import connectors
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import precondition
from grr_response_server import gui
from grr_response_server.gui import api_auth_manager
from grr_response_server.gui import wsgiapp_testlib

# pylint:mode=test

_HTTP_ENDPOINTS = {}
_HTTP_ENDPOINTS_LOCK = threading.RLock()


class HttpApiRegressionTestMixinBase:
  """Load only API E2E test cases."""

  api_version = None
  _get_connector_lock = threading.RLock()

  @staticmethod
  def GetConnector(api_version):
    if api_version != 2:
      raise ValueError(f"api_version has to be 2, got {api_version}")

    with _HTTP_ENDPOINTS_LOCK:
      if api_version not in _HTTP_ENDPOINTS:
        port = portpicker.pick_unused_port()
        logging.info("Picked free AdminUI port %d.", port)

        # Force creation of new APIAuthorizationManager.
        api_auth_manager.InitializeApiAuthManager()

        trd = wsgiapp_testlib.ServerThread(
            port, name="ApiRegressionHttpConnectorV%d" % api_version
        )
        trd.StartAndWaitUntilServing()

        _HTTP_ENDPOINTS[api_version] = "http://localhost:%d" % port

      return connectors.HttpConnector(api_endpoint=_HTTP_ENDPOINTS[api_version])

  def setUp(self):
    super().setUp()
    self.connector = self.GetConnector(self.__class__.api_version)

  def _ParseJSON(self, json_str):
    """Parses response JSON."""
    precondition.AssertType(json_str, str)

    xssi_prefix = ")]}'\n"
    if json_str.startswith(xssi_prefix):
      json_str = json_str[len(xssi_prefix) :]

    return json.loads(json_str)

  def _PrepareV2Request(self, method, args=None):
    """Prepares API v2 request for a given method and args."""

    if isinstance(args, rdf_structs.RDFProtoStruct):
      args_proto = args.AsPrimitiveProto()
    else:
      args_proto = args

    request = self.connector.BuildRequest(method, args_proto)
    prepped_request = self.connector.session.prepare_request(request)

    return request, prepped_request

  def HandleCheck(self, method_metadata, args=None, replace=None):
    """Does regression check for given method, args and a replace function."""

    if not replace:
      raise ValueError("replace can't be None")

    if self.__class__.api_version == 2:
      request, prepped_request = self._PrepareV2Request(
          method_metadata.name, args=args
      )
    else:
      raise ValueError(
          "api_version may be only 2, not %d" % flags.FLAGS.api_version
      )

    response = self.connector.session.send(prepped_request)

    check_result = {
        "url": replace(prepped_request.path_url),
        "method": request.method,
    }

    if request.data:
      request_payload = self._ParseJSON(replace(request.data))
      if request_payload:
        check_result["request_payload"] = request_payload

    if method_metadata.is_streaming:
      check_result["response"] = replace(utils.SmartUnicode(response.content))
    else:
      content = response.content.decode("utf-8")
      check_result["response"] = self._ParseJSON(replace(content))

    return check_result


class HttpApiV2RelationalDBRegressionTestMixin(HttpApiRegressionTestMixinBase):
  """Test class for HTTP v2 protocol API regression test."""

  connection_type = "http_v2"
  skip_legacy_dynamic_proto_tests = True
  api_version = 2

  @property
  def output_file_name(self):

    return os.path.join(
        os.path.dirname(gui.__file__), "api_regression_golden_http_v2.json"
    )

