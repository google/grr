#!/usr/bin/env python
"""Tests for API value renderers."""



# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.gui import api_value_renderers

from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.proto import tests_pb2


class ApiRDFProtoStructRendererSample(rdfvalue.RDFProtoStruct):
  protobuf = tests_pb2.ApiRDFProtoStructRendererSample


class ApiRDFProtoStructRendererTest(test_lib.GRRBaseTest):
  """Test for ApiRDFProtoStructRenderer."""

  def testRendersProtoStructWithoutListsWithoutTypeInfo(self):
    sample = ApiRDFProtoStructRendererSample(
        index=0, values=["foo", "bar"])

    renderer = api_value_renderers.ApiRDFProtoStructRenderer(
        limit_lists=0)
    data = renderer.RenderValue(sample)
    self.assertEqual(data, dict(index=0, values="<lists are omitted>"))

  def testRendersProtoStructWithoutListsLimitWithoutTypeInfo(self):
    sample = ApiRDFProtoStructRendererSample(
        index=0, values=["foo", "bar"])

    renderer = api_value_renderers.ApiRDFProtoStructRenderer(
        limit_lists=-1)
    data = renderer.RenderValue(sample)
    self.assertEqual(data, dict(index=0, values=["foo", "bar"]))

  def testRendersProtoStructWithListsLimitWithoutTypeInfo(self):
    sample = ApiRDFProtoStructRendererSample(
        index=0, values=["foo", "bar"])

    renderer = api_value_renderers.ApiRDFProtoStructRenderer(
        limit_lists=1)
    data = renderer.RenderValue(sample)
    self.assertEqual(
        data, dict(index=0, values=["foo", "<more items available>"]))

  def testRendersProtoStructWithoutListsWithTypeInfo(self):
    sample = ApiRDFProtoStructRendererSample(
        index=0, values=["foo", "bar"])

    renderer = api_value_renderers.ApiRDFProtoStructRenderer(
        limit_lists=0, with_types=True)
    data = renderer.RenderValue(sample)
    self.assertEqual(data,
                     {"age": 0,
                      "mro": ["ApiRDFProtoStructRendererSample",
                              "RDFProtoStruct",
                              "RDFStruct",
                              "RDFValue",
                              "object"],
                      "type": "ApiRDFProtoStructRendererSample",
                      "value": {"index": {"age": 0,
                                          "mro": ["int", "object"],
                                          "type": "int",
                                          "value": 0},
                                "values": "<lists are omitted>"}})

  def testRendersProtoStructWithoutListsLimitWithTypeInfo(self):
    sample = ApiRDFProtoStructRendererSample(
        index=0, values=["foo", "bar"])

    renderer = api_value_renderers.ApiRDFProtoStructRenderer(
        limit_lists=-1, with_types=True)
    data = renderer.RenderValue(sample)

    self.assertEqual(data,
                     {"age": 0,
                      "mro": ["ApiRDFProtoStructRendererSample",
                              "RDFProtoStruct",
                              "RDFStruct",
                              "RDFValue",
                              "object"],
                      "type": "ApiRDFProtoStructRendererSample",
                      "value": {"index": {"age": 0,
                                          "mro": ["int", "object"],
                                          "type": "int",
                                          "value": 0},
                                "values": [
                                    {"age": 0,
                                     "mro": ["unicode", "basestring", "object"],
                                     "type": "unicode",
                                     "value": "foo"},
                                    {"age": 0,
                                     "mro": ["unicode", "basestring", "object"],
                                     "type": "unicode",
                                     "value": "bar"}]}})

  def testRendersProtoStructWithListsLimitWithTypeInfo(self):
    sample = ApiRDFProtoStructRendererSample(
        index=0, values=["foo", "bar"])

    renderer = api_value_renderers.ApiRDFProtoStructRenderer(
        limit_lists=1, with_types=True)
    data = renderer.RenderValue(sample)

    self.assertEqual(data,
                     {"age": 0,
                      "mro": [
                          "ApiRDFProtoStructRendererSample",
                          "RDFProtoStruct",
                          "RDFStruct",
                          "RDFValue",
                          "object"],
                      "type": "ApiRDFProtoStructRendererSample",
                      "value": {
                          "index": {"age": 0,
                                    "mro": ["int", "object"],
                                    "type": "int",
                                    "value": 0
                                   },
                          "values": [
                              {
                                  "age": 0,
                                  "mro": ["unicode", "basestring", "object"],
                                  "type": "unicode",
                                  "value": u"foo"
                                  },
                              {
                                  "url": "to/be/implemented",
                                  "age": 0,
                                  "mro": ["FetchMoreLink"],
                                  "type": "FetchMoreLink"}]}})


class ApiGrrMessageRendererTest(test_lib.GRRBaseTest):
  """Test for ApiGrrMessageRenderer."""

  def testRendersGrrMessagePayloadAsStructuredData(self):
    sample = rdfvalue.GrrMessage(
      task_id=42,
      payload=ApiRDFProtoStructRendererSample(
        index=0, values=["foo", "bar"]))

    renderer = api_value_renderers.ApiGrrMessageRenderer()
    data = renderer.RenderValue(sample)
    self.assertEqual(data, {
      "payload_type": "ApiRDFProtoStructRendererSample",
      "payload": {
        "index": 0,
        "values": ["foo", "bar"]
        },
      "task_id": 42
    })


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
