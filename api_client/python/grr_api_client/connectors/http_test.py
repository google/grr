#!/usr/bin/env python
import io
from unittest import mock

from absl.testing import absltest
from google.protobuf import json_format
import requests

from grr_api_client.connectors import http
from grr_response_proto.api import flow_pb2
from grr_response_proto.api import metadata_pb2
from grr_response_proto.api import reflection_pb2


class VersionTupleTest(absltest.TestCase):

  def testFromJson(self):
    version = http.VersionTuple.FromJson("""
    {
      "major": 2,
      "minor": 7,
      "revision": 1,
      "release": 8
    }
    """)
    self.assertEqual(version.major, 2)
    self.assertEqual(version.minor, 7)
    self.assertEqual(version.revision, 1)
    self.assertEqual(version.release, 8)

  def testFromProto(self):
    proto = metadata_pb2.ApiGetGrrVersionResult()
    proto.major = 2
    proto.minor = 7
    proto.revision = 1
    proto.release = 8

    version = http.VersionTuple.FromProto(proto)
    self.assertEqual(version.major, 2)
    self.assertEqual(version.minor, 7)
    self.assertEqual(version.revision, 1)
    self.assertEqual(version.release, 8)

  def testFromString(self):
    version = http.VersionTuple.FromString("2.7.1.post8")
    self.assertEqual(version.major, 2)
    self.assertEqual(version.minor, 7)
    self.assertEqual(version.revision, 1)
    self.assertEqual(version.release, 8)

  def testFromStringRaisesOnIncorrectFormat(self):
    with self.assertRaises(ValueError):
      http.VersionTuple.FromString("foo.bar.quux")


class HttpConnectorTest(absltest.TestCase):

  def testServerVersionStripsJsonPrefix(self):
    connector = http.HttpConnector(
        api_endpoint="http://localhost:8000", validate_version=False
    )
    response = requests.Response()
    response.status_code = 200
    response.raw = io.BytesIO(
        b")]}'\n" + b'{"major": 2, "minor": 7, "revision": 1, "release": 8}'
    )
    with mock.patch.object(
        connector.session,
        "get",
        autospec=True,
        spec_set=True,
        return_value=response,
    ):
      self.assertEqual(
          connector.server_version,
          http.VersionTuple(major=2, minor=7, revision=1, release=8),
      )

  def testServerVersionDoesNotStripExtraPrefixCharacters(self):
    connector = http.HttpConnector(
        api_endpoint="http://localhost:8000", validate_version=False
    )
    response = requests.Response()
    response.status_code = 200
    response.raw = io.BytesIO(b")]}'\n" + b'}{"major": 2}')
    with mock.patch.object(
        connector.session,
        "get",
        autospec=True,
        spec_set=True,
        return_value=response,
    ):
      with self.assertRaises(json_format.ParseError):
        _ = connector.server_version

  def testBuildRequestWithNoneAndProtoArgs(self):
    connector = http.HttpConnector(
        api_endpoint="http://localhost:8000", validate_version=False
    )
    csrf_response = requests.Response()
    csrf_response.status_code = 200
    csrf_response.cookies.set("csrftoken", "test-csrf")

    methods_proto = reflection_pb2.ApiListApiMethodsResult()
    version_method = methods_proto.items.add()
    version_method.name = "GetGrrVersion"
    version_method.http_route = "/api/v2/metadata/version"
    version_method.http_methods.extend(["GET", "HEAD"])

    flow_method = methods_proto.items.add()
    flow_method.name = "GetFlow"
    flow_method.http_route = "/api/v2/clients/<client_id>/flows/<flow_id>"
    flow_method.http_methods.extend(["GET", "HEAD"])

    methods_response = requests.Response()
    methods_response.status_code = 200
    methods_response.raw = io.BytesIO(
        http.HttpConnector.JSON_PREFIX.encode("utf-8")
        + json_format.MessageToJson(methods_proto).encode("utf-8")
    )

    with mock.patch.object(
        connector.session,
        "get",
        autospec=True,
        spec_set=True,
        side_effect=[csrf_response, methods_response],
    ):
      version_request = connector.BuildRequest("GetGrrVersion", None)
      flow_request = connector.BuildRequest(
          "GetFlow",
          flow_pb2.ApiGetFlowArgs(client_id="C.1234", flow_id="F:ABCD"),
      )

    self.assertEqual(version_request.method, "GET")
    self.assertEqual(
        version_request.url, "http://localhost:8000/api/v2/metadata/version"
    )
    self.assertEqual(flow_request.method, "GET")
    self.assertEqual(
        flow_request.url,
        "http://localhost:8000/api/v2/clients/C.1234/flows/F:ABCD",
    )
    self.assertEqual(flow_request.params, {})


if __name__ == "__main__":
  absltest.main()
