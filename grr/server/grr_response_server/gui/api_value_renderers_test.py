#!/usr/bin/env python
"""Tests for API value renderers."""

import base64

from absl import app
from absl.testing import absltest

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import tests_pb2
from grr_response_server.gui import api_value_renderers
from grr.test_lib import test_lib


class ApiRDFProtoStructRendererSample(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.ApiRDFProtoStructRendererSample


class ApiAnyValueRendererTest(absltest.TestCase):

  def testRenderValueSimple(self):
    value = rdf_client.User()
    value.username = "foobar"

    renderer = api_value_renderers.ApiAnyValueRenderer()
    rendered = renderer.RenderValue(rdf_structs.AnyValue.Pack(value))

    self.assertEqual(
        rendered, {
            "type": "User",
            "value": {
                "username": {
                    "type": "unicode",
                    "value": "foobar",
                },
            },
        })

  def testRenderValueNotExisting(self):
    value = rdf_structs.AnyValue()
    value.type_url = "type.googleapis.com/foo.bar.Quux"
    value.value = b"foobarbaz"

    renderer = api_value_renderers.ApiAnyValueRenderer()
    rendered = renderer.RenderValue(value)

    self.assertEqual(
        rendered, {
            "type": "AnyValue",
            "value": {
                "type_url": {
                    "type": "unicode",
                    "value": value.type_url,
                },
                "value": {
                    "type": "bytes",
                    "value": base64.b64encode(b"foobarbaz").decode("ascii"),
                },
            },
        })


class ApiRDFProtoStructRendererTest(test_lib.GRRBaseTest):
  """Test for ApiRDFProtoStructRenderer."""

  def testRendersProtoStructWithoutLists(self):
    sample = ApiRDFProtoStructRendererSample(index=0, values=["foo", "bar"])

    renderer = api_value_renderers.ApiRDFProtoStructRenderer(limit_lists=0)
    data = renderer.RenderValue(sample)
    self.assertEqual(
        data, {
            "type": "ApiRDFProtoStructRendererSample",
            "value": {
                "index": {
                    "type": "long",
                    "value": 0
                },
                "values": "<lists are omitted>"
            }
        })

  def testRendersProtoStructWithoutListsLimit(self):
    sample = ApiRDFProtoStructRendererSample(index=0, values=["foo", "bar"])

    renderer = api_value_renderers.ApiRDFProtoStructRenderer(limit_lists=-1)
    data = renderer.RenderValue(sample)

    self.assertEqual(
        data, {
            "type": "ApiRDFProtoStructRendererSample",
            "value": {
                "index": {
                    "type": "long",
                    "value": 0
                },
                "values": [{
                    "type": "unicode",
                    "value": "foo"
                }, {
                    "type": "unicode",
                    "value": "bar"
                }]
            }
        })

  def testRendersProtoStructWithListsLimit(self):
    sample = ApiRDFProtoStructRendererSample(index=0, values=["foo", "bar"])

    renderer = api_value_renderers.ApiRDFProtoStructRenderer(limit_lists=1)
    data = renderer.RenderValue(sample)

    self.assertEqual(
        data, {
            "type": "ApiRDFProtoStructRendererSample",
            "value": {
                "index": {
                    "type": "long",
                    "value": 0
                },
                "values": [{
                    "type": "unicode",
                    "value": u"foo"
                }, {
                    "url": "to/be/implemented",
                    "type": "FetchMoreLink"
                }]
            }
        })


class ApiGrrMessageRendererTest(test_lib.GRRBaseTest):
  """Test for ApiGrrMessageRenderer."""

  def testRendersGrrMessagePayloadAsStructuredData(self):
    sample = rdf_flows.GrrMessage(
        task_id=42,
        payload=ApiRDFProtoStructRendererSample(
            index=43, values=["foo", "bar"]))

    renderer = api_value_renderers.ApiGrrMessageRenderer()
    data = renderer.RenderValue(sample)

    model_data = {
        "type": "GrrMessage",
        "value": {
            "task_id": {
                "type": "long",
                "value": 42
            },
            "payload_type": {
                "type": "unicode",
                "value": "ApiRDFProtoStructRendererSample"
            },
            "payload": {
                "type": "ApiRDFProtoStructRendererSample",
                "value": {
                    "index": {
                        "type": "long",
                        "value": 43
                    },
                    "values": [{
                        "type": "unicode",
                        "value": "foo"
                    }, {
                        "type": "unicode",
                        "value": "bar"
                    }]
                }
            }
        }
    }

    self.assertEqual(data, model_data)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
