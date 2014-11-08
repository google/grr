#!/usr/bin/env python
"""This modules contains tests for RESTful API renderers."""



# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.gui import api_object_renderers

from grr.lib import aff4
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib


class AFF4ObjectApiObjectRendererTest(test_lib.GRRBaseTest):
  """Test for AFF4ObjectApiRendererTest."""

  def setUp(self):
    super(AFF4ObjectApiObjectRendererTest, self).setUp()

    # Create empty AFF4Volume object.
    with test_lib.FakeTime(42):
      with aff4.FACTORY.Create("aff4:/tmp/foo/bar", "AFF4Volume",
                               token=self.token) as _:
        pass

    self.fd = aff4.FACTORY.Open("aff4:/tmp/foo/bar", token=self.token)
    self.renderer = api_object_renderers.AFF4ObjectApiObjectRenderer()

  def testRendersAff4Volume(self):
    data = self.renderer.RenderObject(self.fd, {})
    self.assertEqual(data,
                     {"age_policy": "NEWEST_TIME",
                      "attributes": {"aff4:type": "AFF4Volume",
                                     "metadata:last": 42000000},
                      "urn": "aff4:/tmp/foo/bar",
                      "aff4_class": "AFF4Volume"})

  def testRendersAff4VolumeWithTypeInfo(self):
    data = self.renderer.RenderObject(self.fd, {"with_type_info": True})
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
    data = self.renderer.RenderObject(self.fd, {"with_type_info": True,
                                                "with_descriptors": True})
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
                         "descriptors": {
                             "aff4:type": {
                                 "description": "The name of the "
                                                "AFF4Object derived class."},
                             "metadata:last": {
                                 "description": "The last time any "
                                                "attribute of this "
                                                "object was written."}
                             }
                         })


class RDFValueCollectionApiObjectRendererTest(test_lib.GRRBaseTest):
  """Test for RDFValueCollectionApiRenderer."""

  def setUp(self):
    super(RDFValueCollectionApiObjectRendererTest, self).setUp()

    with test_lib.FakeTime(42):
      with aff4.FACTORY.Create("aff4:/tmp/foo/bar", "RDFValueCollection",
                               token=self.token) as fd:
        for i in range(10):
          fd.Add(rdfvalue.PathSpec(path="/var/os/tmp-%d" % i,
                                   pathtype="OS"))

    self.fd = aff4.FACTORY.Open("aff4:/tmp/foo/bar", token=self.token)
    self.renderer = api_object_renderers.RDFValueCollectionApiObjectRenderer()

  def testRendersSampleCollection(self):
    data = self.renderer.RenderObject(self.fd, {})

    self.assertEqual(data["aff4_class"], "RDFValueCollection")
    self.assertEqual(data["urn"], "aff4:/tmp/foo/bar")
    self.assertEqual(data["offset"], 0)
    self.assertEqual(data["age_policy"], "NEWEST_TIME")
    self.assertEqual(data["attributes"],
                     {"aff4:type": "RDFValueCollection",
                      "aff4:size": 10,
                      "metadata:last": 42000000})

    self.assertEqual(len(data["items"]), 10)
    for i in range(10):
      self.assertEqual(data["items"][i],
                       {"path": "/var/os/tmp-%d" % i,
                        "pathtype": "OS"})

  def testRendersSampleCollectionWithCountParameter(self):
    data = self.renderer.RenderObject(self.fd, {"count": 2})

    self.assertEqual(data["aff4_class"], "RDFValueCollection")
    self.assertEqual(data["urn"], "aff4:/tmp/foo/bar")
    self.assertEqual(data["offset"], 0)
    self.assertEqual(data["age_policy"], "NEWEST_TIME")
    self.assertEqual(data["attributes"],
                     {"aff4:type": "RDFValueCollection",
                      "aff4:size": 10,
                      "metadata:last": 42000000})

    self.assertEqual(len(data["items"]), 2)
    self.assertEqual(data["items"][0],
                     {"path": "/var/os/tmp-0",
                      "pathtype": "OS"})
    self.assertEqual(data["items"][1],
                     {"path": "/var/os/tmp-1",
                      "pathtype": "OS"})

  def testRendersSampleCollectionWithOffsetParameter(self):
    data = self.renderer.RenderObject(self.fd, {"offset": 8})

    self.assertEqual(data["aff4_class"], "RDFValueCollection")
    self.assertEqual(data["urn"], "aff4:/tmp/foo/bar")
    self.assertEqual(data["offset"], 8)
    self.assertEqual(data["age_policy"], "NEWEST_TIME")
    self.assertEqual(data["attributes"],
                     {"aff4:type": "RDFValueCollection",
                      "aff4:size": 10,
                      "metadata:last": 42000000})

    self.assertEqual(len(data["items"]), 2)
    self.assertEqual(data["items"][0],
                     {"path": "/var/os/tmp-8",
                      "pathtype": "OS"})
    self.assertEqual(data["items"][1],
                     {"path": "/var/os/tmp-9",
                      "pathtype": "OS"})

  def testRendersSampleCollectionWithCountAndOffsetParameters(self):
    data = self.renderer.RenderObject(self.fd, {"offset": 3, "count": 2})

    self.assertEqual(data["aff4_class"], "RDFValueCollection")
    self.assertEqual(data["urn"], "aff4:/tmp/foo/bar")
    self.assertEqual(data["offset"], 3)
    self.assertEqual(data["age_policy"], "NEWEST_TIME")
    self.assertEqual(data["attributes"],
                     {"aff4:type": "RDFValueCollection",
                      "aff4:size": 10,
                      "metadata:last": 42000000})

    self.assertEqual(len(data["items"]), 2)
    self.assertEqual(data["items"][0],
                     {"path": "/var/os/tmp-3",
                      "pathtype": "OS"})
    self.assertEqual(data["items"][1],
                     {"path": "/var/os/tmp-4",
                      "pathtype": "OS"})

  def testRendersSampleCollectionWithTotalCountParameter(self):
    data = self.renderer.RenderObject(self.fd, {"count": 2,
                                                "with_total_count": True})

    self.assertEqual(data["aff4_class"], "RDFValueCollection")
    self.assertEqual(len(data["items"]), 2)
    self.assertEqual(data["total_count"], 10)

  def testRendersSampleCollectionWithFilter(self):
    data = self.renderer.RenderObject(self.fd, {"filter": "/var/os/tmp-9"})

    self.assertEqual(data["aff4_class"], "RDFValueCollection")
    self.assertEqual(len(data["items"]), 1)
    self.assertEqual(data["items"][0],
                     {"path": "/var/os/tmp-9",
                      "pathtype": "OS"})

  def testRendersSampleCollectionWithFilterAndOffsetAndCount(self):
    data = self.renderer.RenderObject(self.fd, {"filter": "/var/os/tmp",
                                                "offset": 2, "count": 2})

    self.assertEqual(data["aff4_class"], "RDFValueCollection")
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
    self.renderer = api_object_renderers.VFSGRRClientApiObjectRenderer()

  def testRendersClientSummaryInAdditionToClientObject(self):
    data = self.renderer.RenderObject(self.fd, {})

    self.assertEqual(data["aff4_class"], "VFSGRRClient")
    self.assertEqual(data["summary"], {
        "system_info": {
            "node": "Host-0",
            "version": "",
            "fqdn": "Host-0.example.com"
            },
        "client_id": "aff4:/C.1000000000000000",
        "client_info": {
            "client_name": "GRR Monitor"
            }
        })


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
