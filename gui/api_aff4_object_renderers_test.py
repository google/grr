#!/usr/bin/env python
"""This modules contains tests for RESTful API renderers."""



# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.gui import api_aff4_object_renderers

from grr.lib import aff4
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib


class ApiAFF4ObjectRendererTest(test_lib.GRRBaseTest):
  """Test for ApiAFF4ObjectRenderer."""

  def setUp(self):
    super(ApiAFF4ObjectRendererTest, self).setUp()

    # Create empty AFF4Volume object.
    with test_lib.FakeTime(42):
      with aff4.FACTORY.Create("aff4:/tmp/foo/bar", "AFF4Volume",
                               token=self.token) as _:
        pass

    self.fd = aff4.FACTORY.Open("aff4:/tmp/foo/bar", token=self.token)
    self.renderer = api_aff4_object_renderers.ApiAFF4ObjectRenderer()

  def testRendersAff4Volume(self):
    data = self.renderer.RenderObject(self.fd,
                                      rdfvalue.ApiAFF4ObjectRendererArgs())

    self.assertEqual(data,
                     {"age_policy": "NEWEST_TIME",
                      "attributes": {"aff4:type": "AFF4Volume",
                                     "metadata:last": 42000000},
                      "urn": "aff4:/tmp/foo/bar",
                      "aff4_class": "AFF4Volume"})

  def testRendersAff4VolumeWithTypeInfo(self):
    data = self.renderer.RenderObject(
        self.fd, rdfvalue.ApiAFF4ObjectRendererArgs(type_info="WITH_TYPES"))

    self.assertEqual(data,
                     {"age_policy": "NEWEST_TIME",
                      "attributes": {
                          "aff4:type": {
                              "age": 42,
                              "mro": ["RDFString",
                                      "RDFBytes",
                                      "RDFValue",
                                      "object"],
                              "type": "RDFString",
                              "value": "AFF4Volume"},
                          "metadata:last": {
                              "age": 42,
                              "mro": ["RDFDatetime",
                                      "RDFInteger",
                                      "RDFString",
                                      "RDFBytes",
                                      "RDFValue",
                                      "object"],
                              "type": "RDFDatetime",
                              "value": 42000000}
                      },
                      "urn": "aff4:/tmp/foo/bar",
                      "aff4_class": "AFF4Volume"})

  def testRenderersAff4VolumeWithTypeInfoAndDescriptions(self):
    data = self.renderer.RenderObject(
        self.fd,
        rdfvalue.ApiAFF4ObjectRendererArgs(type_info="WITH_TYPES_AND_METADATA"))

    self.assertEqual(data,
                     {
                         "age_policy": "NEWEST_TIME",
                         "attributes": {
                             "aff4:type": {
                                 "age": 42,
                                 "mro": ["RDFString",
                                         "RDFBytes",
                                         "RDFValue",
                                         "object"],
                                 "type": "RDFString",
                                 "value": "AFF4Volume"},
                             "metadata:last": {
                                 "age": 42,
                                 "mro": ["RDFDatetime",
                                         "RDFInteger",
                                         "RDFString",
                                         "RDFBytes",
                                         "RDFValue",
                                         "object"],
                                 "type": "RDFDatetime",
                                 "value": 42000000}
                         },
                         "urn": "aff4:/tmp/foo/bar",
                         "aff4_class": "AFF4Volume",
                         "metadata": {
                             "aff4:type": {
                                 "description": "The name of the "
                                                "AFF4Object derived class."},
                             "metadata:last": {
                                 "description": "The last time any "
                                                "attribute of this "
                                                "object was written."}
                         }
                     })


class ApiRDFValueCollectionRendererTest(test_lib.GRRBaseTest):
  """Test for ApiRDFValueCollectionRenderer."""

  def setUp(self):
    super(ApiRDFValueCollectionRendererTest, self).setUp()

    with test_lib.FakeTime(42):
      with aff4.FACTORY.Create("aff4:/tmp/foo/bar", "RDFValueCollection",
                               token=self.token) as fd:
        for i in range(10):
          fd.Add(rdfvalue.PathSpec(path="/var/os/tmp-%d" % i,
                                   pathtype="OS"))

    self.fd = aff4.FACTORY.Open("aff4:/tmp/foo/bar", token=self.token)
    self.renderer = api_aff4_object_renderers.ApiRDFValueCollectionRenderer()

  def testRendersSampleCollection(self):
    data = self.renderer.RenderObject(
        self.fd, rdfvalue.ApiRDFValueCollectionRendererArgs())

    self.assertEqual(data["offset"], 0)
    self.assertEqual(data["count"], 10)

    self.assertEqual(len(data["items"]), 10)
    for i in range(10):
      self.assertEqual(data["items"][i],
                       {"path": "/var/os/tmp-%d" % i,
                        "pathtype": "OS"})

  def testRendersSampleCollectionWithCountParameter(self):
    data = self.renderer.RenderObject(
        self.fd, rdfvalue.ApiRDFValueCollectionRendererArgs(count=2))

    self.assertEqual(data["offset"], 0)
    self.assertEqual(data["count"], 2)

    self.assertEqual(len(data["items"]), 2)
    self.assertEqual(data["items"][0],
                     {"path": "/var/os/tmp-0",
                      "pathtype": "OS"})
    self.assertEqual(data["items"][1],
                     {"path": "/var/os/tmp-1",
                      "pathtype": "OS"})

  def testRendersSampleCollectionWithOffsetParameter(self):
    data = self.renderer.RenderObject(
        self.fd, rdfvalue.ApiRDFValueCollectionRendererArgs(offset=8))

    self.assertEqual(data["offset"], 8)
    self.assertEqual(data["count"], 2)

    self.assertEqual(len(data["items"]), 2)
    self.assertEqual(data["items"][0],
                     {"path": "/var/os/tmp-8",
                      "pathtype": "OS"})
    self.assertEqual(data["items"][1],
                     {"path": "/var/os/tmp-9",
                      "pathtype": "OS"})

  def testRendersSampleCollectionWithCountAndOffsetParameters(self):
    data = self.renderer.RenderObject(
        self.fd, rdfvalue.ApiRDFValueCollectionRendererArgs(offset=3,
                                                            count=2))

    self.assertEqual(data["offset"], 3)
    self.assertEqual(data["count"], 2)

    self.assertEqual(len(data["items"]), 2)
    self.assertEqual(data["items"][0],
                     {"path": "/var/os/tmp-3",
                      "pathtype": "OS"})
    self.assertEqual(data["items"][1],
                     {"path": "/var/os/tmp-4",
                      "pathtype": "OS"})

  def testRendersSampleCollectionWithTotalCountParameter(self):
    data = self.renderer.RenderObject(
        self.fd, rdfvalue.ApiRDFValueCollectionRendererArgs(
            count=2, with_total_count=True))

    self.assertEqual(len(data["items"]), 2)
    self.assertEqual(data["total_count"], 10)

  def testRendersSampleCollectionWithFilter(self):
    data = self.renderer.RenderObject(
        self.fd, rdfvalue.ApiRDFValueCollectionRendererArgs(
            filter="/var/os/tmp-9"))

    self.assertEqual(len(data["items"]), 1)
    self.assertEqual(data["items"][0],
                     {"path": "/var/os/tmp-9",
                      "pathtype": "OS"})

  def testRendersSampleCollectionWithFilterAndOffsetAndCount(self):
    data = self.renderer.RenderObject(
        self.fd, rdfvalue.ApiRDFValueCollectionRendererArgs(
            offset=2, count=2, filter="/var/os/tmp"))

    self.assertEqual(len(data["items"]), 2)
    self.assertEqual(data["items"][0],
                     {"path": "/var/os/tmp-2",
                      "pathtype": "OS"})
    self.assertEqual(data["items"][1],
                     {"path": "/var/os/tmp-3",
                      "pathtype": "OS"})


class VFSGRRClientApiObjectRendererTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(VFSGRRClientApiObjectRendererTest, self).setUp()

    self.client_id = self.SetupClients(1)[0]

    self.fd = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.renderer = api_aff4_object_renderers.VFSGRRClientApiObjectRenderer()

  def testRendersClientSummaryInWithTypeMetadata(self):
    data = self.renderer.RenderObject(self.fd, None)

    self.assertEqual(
        data["summary"]["value"]["system_info"]["value"]["node"]["value"],
        "Host-0")
    self.assertEqual(
        data["summary"]["value"]["system_info"]["value"]["version"]["value"],
        "")
    self.assertEqual(
        data["summary"]["value"]["system_info"]["value"]["fqdn"]["value"],
        "Host-0.example.com")
    self.assertEqual(
        data["summary"]["value"]["client_id"]["value"],
        "aff4:/C.1000000000000000")
    self.assertEqual(
        data["summary"]["value"]["client_info"]["value"]["client_name"][
            "value"],
        "GRR Monitor")
    self.assertEqual(
        data["summary"]["value"]["serial_number"]["value"],
        "")
    self.assertEqual(
        data["summary"]["value"]["system_manufacturer"]["value"],
        "")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
