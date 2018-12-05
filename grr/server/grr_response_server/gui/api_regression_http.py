#!/usr/bin/env python
"""Base test classes for API handlers tests."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

# pylint:mode=test

import json
import logging
import os
import threading

import portpicker
import requests

from google.protobuf import json_format

from grr_api_client.connectors import http_connector
from grr_response_core.lib import flags
from grr_response_core.lib import utils
from grr_response_server import data_store
from grr_response_server import gui
from grr_response_server.gui import api_auth_manager
from grr_response_server.gui import api_call_router
from grr_response_server.gui import api_value_renderers
from grr_response_server.gui import http_api
from grr_response_server.gui import wsgiapp_testlib
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib

DOCUMENT_ROOT = os.path.join(os.path.dirname(gui.__file__), "static")

_HTTP_ENDPOINTS = {}
_HTTP_ENDPOINTS_LOCK = threading.RLock()


class HttpApiRegressionTestMixinBase(object):
  """Load only API E2E test cases."""

  api_version = None
  read_from_relational_db = False
  _get_connector_lock = threading.RLock()

  @staticmethod
  def GetConnector(api_version):
    if api_version not in [1, 2]:
      raise ValueError("api_version may be 1 or 2 only")

    with _HTTP_ENDPOINTS_LOCK:
      if api_version not in _HTTP_ENDPOINTS:
        port = portpicker.pick_unused_port()
        logging.info("Picked free AdminUI port %d.", port)

        # Force creation of new APIAuthorizationManager.
        api_auth_manager.APIACLInit.InitApiAuthManager()

        trd = wsgiapp_testlib.ServerThread(
            port, name="ApiRegressionHttpConnectorV%d" % api_version)
        trd.StartAndWaitUntilServing()

        _HTTP_ENDPOINTS[api_version] = "http://localhost:%d" % port

      return http_connector.HttpConnector(
          api_endpoint=_HTTP_ENDPOINTS[api_version])

  def setUp(self):
    super(HttpApiRegressionTestMixinBase, self).setUp()
    self.connector = self.GetConnector(self.__class__.api_version)

    if (not getattr(self, "aff4_only_test", False) and
        self.__class__.read_from_relational_db):
      self.db_config_overrider = test_lib.ConfigOverrider({
          "Database.useForReads": True,
          "Database.useForReads.cronjobs": True,
      })
      self.db_config_overrider.Start()
    else:
      self.db_config_overrider = None

  def tearDown(self):
    super(HttpApiRegressionTestMixinBase, self).tearDown()
    if self.db_config_overrider:
      self.db_config_overrider.Stop()

  def _ParseJSON(self, json_str):
    """Parses response JSON."""

    xssi_prefix = ")]}'\n"
    if json_str.startswith(xssi_prefix):
      json_str = json_str[len(xssi_prefix):]

    return json.loads(json_str)

  def _PrepareV1Request(self, method, args=None):
    """Prepares API v1 request for a given method and args."""

    args_proto = None
    if args:
      args_proto = args.AsPrimitiveProto()
    request = self.connector.BuildRequest(method, args_proto)
    request.url = request.url.replace("/api/v2/", "/api/")
    if args and request.data:
      body_proto = args.__class__().AsPrimitiveProto()
      json_format.Parse(request.data, body_proto)
      body_args = args.__class__()
      body_args.ParseFromString(body_proto.SerializeToString())
      request.data = json.dumps(
          api_value_renderers.StripTypeInfo(
              api_value_renderers.RenderValue(body_args)),
          cls=http_api.JSONEncoderWithRDFPrimitivesSupport)

    prepped_request = request.prepare()

    return request, prepped_request

  def _PrepareV2Request(self, method, args=None):
    """Prepares API v2 request for a given method and args."""

    args_proto = None
    if args:
      args_proto = args.AsPrimitiveProto()
    request = self.connector.BuildRequest(method, args_proto)
    prepped_request = request.prepare()

    return request, prepped_request

  def HandleCheck(self, method_metadata, args=None, replace=None):
    """Does regression check for given method, args and a replace function."""

    if not replace:
      raise ValueError("replace can't be None")

    if self.__class__.api_version == 1:
      request, prepped_request = self._PrepareV1Request(
          method_metadata.name, args=args)
    elif self.__class__.api_version == 2:
      request, prepped_request = self._PrepareV2Request(
          method_metadata.name, args=args)
    else:
      raise ValueError(
          "api_version may be only 1 or 2, not %d" % flags.FLAGS.api_version)

    session = requests.Session()
    response = session.send(prepped_request)

    check_result = {
        "url": replace(prepped_request.path_url),
        "method": request.method
    }

    if request.data:
      request_payload = self._ParseJSON(replace(request.data))
      if request_payload:
        check_result["request_payload"] = request_payload

    if (method_metadata.result_type == api_call_router.RouterMethodMetadata
        .BINARY_STREAM_RESULT_TYPE):
      check_result["response"] = replace(utils.SmartUnicode(response.content))
    else:
      check_result["response"] = self._ParseJSON(replace(response.content))

    if self.__class__.api_version == 1:
      stripped_response = api_value_renderers.StripTypeInfo(
          check_result["response"])
      if stripped_response != check_result["response"]:
        check_result["type_stripped_response"] = stripped_response

    return check_result


class HttpApiV1RegressionTestMixin(HttpApiRegressionTestMixinBase):
  """Test class for HTTP v1 protocol."""

  connection_type = "http_v1"
  skip_legacy_dynamic_proto_tests = False
  api_version = 1

  def testRelationalDBReadsDisabled(self):
    self.assertFalse(data_store.RelationalDBReadEnabled())

  @property
  def output_file_name(self):
    return os.path.join(DOCUMENT_ROOT,
                        "angular-components/docs/api-docs-examples.json")


class HttpApiV2RegressionTestMixin(HttpApiRegressionTestMixinBase):
  """Test class for HTTP v2 protocol."""

  connection_type = "http_v2"
  skip_legacy_dynamic_proto_tests = True
  api_version = 2

  def testRelationalDBReadsDisabled(self):
    self.assertFalse(data_store.RelationalDBReadEnabled())

  @property
  def output_file_name(self):
    return os.path.join(DOCUMENT_ROOT,
                        "angular-components/docs/api-v2-docs-examples.json")


class HttpApiV2RelationalDBRegressionTestMixin(HttpApiRegressionTestMixinBase):
  """Test class for HTTP v2 protocol with Database.useForReads=True."""

  read_from_relational_db = True
  connection_type = "http_v2_rel_db"
  use_golden_files_of = "http_v2"
  skip_legacy_dynamic_proto_tests = True
  api_version = 2

  def testRelationalDBReadsEnabled(self):
    if not getattr(self, "aff4_only_test", False):
      self.assertTrue(data_store.RelationalDBReadEnabled())

  @property
  def output_file_name(self):
    return os.path.join(DOCUMENT_ROOT,
                        "angular-components/docs/api-v2-docs-examples.json")


class HttpApiV2RelationalFlowsRegressionTestMixin(
    db_test_lib.RelationalDBEnabledMixin, HttpApiRegressionTestMixinBase):
  """Test class for HTTP v2 protocol with relational flows enabled."""

  read_from_relational_db = True
  relational_db_flows = True
  connection_type = "http_v2_rel_flows"
  use_golden_files_of = "http_v2"
  skip_legacy_dynamic_proto_tests = True
  api_version = 2

  def testRelationalDBReadsEnabled(self):
    if not getattr(self, "aff4_only_test", False):
      self.assertTrue(data_store.RelationalDBReadEnabled())

  @property
  def output_file_name(self):
    return os.path.join(DOCUMENT_ROOT,
                        "angular-components/docs/api-v2-docs-examples.json")
