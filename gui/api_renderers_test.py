#!/usr/bin/env python
"""This modules contains tests for RESTful API renderers."""



import json

from grr.gui import runtests_test

from grr.lib import aff4
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib


class ApiRendererTest(test_lib.GRRSeleniumTest):
  """Base class for API renderers test."""

  def setUp(self):
    super(ApiRendererTest, self).setUp()

    # Request root page to get CSRF cookie.
    self.Open("/")

  def GetJsonData(self, url):
    """Parses JSON data returned when querying given url."""

    self.Open(url)
    data = self.driver.find_element_by_tag_name("body").text
    return json.loads(data)


class AFF4ObjectApiRendererTest(ApiRendererTest):
  """Test for AFF4ObjectApiRendererTest."""

  def setUp(self):
    super(AFF4ObjectApiRendererTest, self).setUp()

    # Create empty AFF4Volume object.
    with test_lib.FakeTime(42):
      with aff4.FACTORY.Create("aff4:/tmp/foo/bar", "AFF4Volume",
                               token=self.token) as _:
        pass

  def testRendersAff4Volume(self):
    data = self.GetJsonData("/api/aff4/tmp/foo/bar")
    self.assertEqual(data,
                     {"age_policy": "NEWEST_TIME",
                      "attributes": {"aff4:type": "AFF4Volume",
                                     "metadata:last": 42000000},
                      "urn": "aff4:/tmp/foo/bar",
                      "aff4_class": "AFF4Volume"})

  def testRendersAff4VolumeWithTypeInfo(self):
    data = self.GetJsonData("/api/aff4/tmp/foo/bar?with_type_info=1")
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
    data = self.GetJsonData("/api/aff4/tmp/foo/bar?with_type_info=1"
                            "&with_descriptors=1")
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


class RDFValueCollectionApiRendererTest(ApiRendererTest):
  """Test for RDFValueCollectionApiRenderer."""

  def setUp(self):
    super(RDFValueCollectionApiRendererTest, self).setUp()

    with test_lib.FakeTime(42):
      with aff4.FACTORY.Create("aff4:/tmp/foo/bar", "RDFValueCollection",
                               token=self.token) as fd:
        for i in range(10):
          fd.Add(rdfvalue.PathSpec(path="/var/os/tmp-%d" % i,
                                   pathtype="OS"))

  def testRendersSampleCollection(self):
    data = self.GetJsonData("/api/aff4/tmp/foo/bar")

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
    data = self.GetJsonData("/api/aff4/tmp/foo/bar?count=2")

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
    data = self.GetJsonData("/api/aff4/tmp/foo/bar?offset=8")

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
    data = self.GetJsonData("/api/aff4/tmp/foo/bar?offset=3&count=2")

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
    data = self.GetJsonData("/api/aff4/tmp/foo/bar?"
                            "count=2&with_total_count=1")

    self.assertEqual(data["aff4_class"], "RDFValueCollection")
    self.assertEqual(len(data["items"]), 2)
    self.assertEqual(data["total_count"], 10)

  def testRendersSampleCollectionWithFilter(self):
    data = self.GetJsonData("/api/aff4/tmp/foo/bar?filter=/var/os/tmp-9")

    self.assertEqual(data["aff4_class"], "RDFValueCollection")
    self.assertEqual(len(data["items"]), 1)
    self.assertEqual(data["items"][0],
                     {"path": "/var/os/tmp-9",
                      "pathtype": "OS"})

  def testRendersSampleCollectionWithFilterAndOffsetAndCount(self):
    data = self.GetJsonData("/api/aff4/tmp/foo/bar?"
                            "filter=/var/os/tmp&offset=2&count=2")

    self.assertEqual(data["aff4_class"], "RDFValueCollection")
    self.assertEqual(len(data["items"]), 2)
    self.assertEqual(data["items"][0],
                     {"path": "/var/os/tmp-2",
                      "pathtype": "OS"})
    self.assertEqual(data["items"][1],
                     {"path": "/var/os/tmp-3",
                      "pathtype": "OS"})


class VFSGRRClientApiRendererTest(ApiRendererTest):

  def setUp(self):
    super(VFSGRRClientApiRendererTest, self).setUp()

    with self.ACLChecksDisabled():
      self.client_id = self.SetupClients(1)[0]

  def testRendersClientSummaryInAdditionToClientObject(self):
    data = self.GetJsonData("/api/aff4/" + self.client_id.Basename())

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
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
