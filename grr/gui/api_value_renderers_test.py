#!/usr/bin/env python
"""Tests for API value renderers."""



from grr.gui import api_value_renderers

from grr.lib import flags
from grr.lib import test_lib
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import tests_pb2


class ApiRDFProtoStructRendererSample(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.ApiRDFProtoStructRendererSample


class ApiRDFProtoStructRendererTest(test_lib.GRRBaseTest):
  """Test for ApiRDFProtoStructRenderer."""

  def testRendersProtoStructWithoutLists(self):
    sample = ApiRDFProtoStructRendererSample(index=0, values=["foo", "bar"])

    renderer = api_value_renderers.ApiRDFProtoStructRenderer(limit_lists=0)
    data = renderer.RenderValue(sample)
    self.assertEqual(data, {"age": 0,
                            "type": "ApiRDFProtoStructRendererSample",
                            "value": {
                                "index": {
                                    "age": 0,
                                    "type": "long",
                                    "value": 0
                                },
                                "values": "<lists are omitted>"
                            }})

  def testRendersProtoStructWithoutListsLimit(self):
    sample = ApiRDFProtoStructRendererSample(index=0, values=["foo", "bar"])

    renderer = api_value_renderers.ApiRDFProtoStructRenderer(limit_lists=-1)
    data = renderer.RenderValue(sample)

    self.assertEqual(data, {"age": 0,
                            "type": "ApiRDFProtoStructRendererSample",
                            "value": {"index": {"age": 0,
                                                "type": "long",
                                                "value": 0},
                                      "values": [
                                          {"age": 0,
                                           "type": "unicode",
                                           "value": "foo"}, {"age": 0,
                                                             "type": "unicode",
                                                             "value": "bar"}
                                      ]}})

  def testRendersProtoStructWithListsLimit(self):
    sample = ApiRDFProtoStructRendererSample(index=0, values=["foo", "bar"])

    renderer = api_value_renderers.ApiRDFProtoStructRenderer(limit_lists=1)
    data = renderer.RenderValue(sample)

    self.assertEqual(data, {"age": 0,
                            "type": "ApiRDFProtoStructRendererSample",
                            "value": {
                                "index": {"age": 0,
                                          "type": "long",
                                          "value": 0},
                                "values": [
                                    {
                                        "age": 0,
                                        "type": "unicode",
                                        "value": u"foo"
                                    }, {
                                        "url": "to/be/implemented",
                                        "age": 0,
                                        "type": "FetchMoreLink"
                                    }
                                ]
                            }})


class ApiGrrMessageRendererTest(test_lib.GRRBaseTest):
  """Test for ApiGrrMessageRenderer."""

  def testRendersGrrMessagePayloadAsStructuredData(self):
    sample = rdf_flows.GrrMessage(task_id=42,
                                  payload=ApiRDFProtoStructRendererSample(
                                      index=43, values=["foo", "bar"]))

    renderer = api_value_renderers.ApiGrrMessageRenderer()
    data = renderer.RenderValue(sample)

    model_data = {"age": 0,
                  "type": "GrrMessage",
                  "value": {
                      "task_id": {
                          "age": 0,
                          "type": "long",
                          "value": 42
                      },
                      "payload_type": {
                          "age": 0,
                          "type": "unicode",
                          "value": "ApiRDFProtoStructRendererSample"
                      },
                      "payload": {
                          "age": 0,
                          "type": "ApiRDFProtoStructRendererSample",
                          "value": {
                              "index": {
                                  "age": 0,
                                  "type": "long",
                                  "value": 43
                              },
                              "values": [
                                  {
                                      "age": 0,
                                      "type": "unicode",
                                      "value": "foo"
                                  }, {
                                      "age": 0,
                                      "type": "unicode",
                                      "value": "bar"
                                  }
                              ]
                          }
                      }
                  }}

    self.assertEqual(data, model_data)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
