#!/usr/bin/env python
"""Test standard RDFValues."""

from grr.lib.rdfvalues import standard as rdf_standard
from grr.lib.rdfvalues import test_base


class URITests(test_base.RDFValueTestCase):
  """Test URI proto."""

  rdfvalue_class = rdf_standard.URI

  def GenerateSample(self, number=0):
    return rdf_standard.URI(transport="http", host="%s.example.com" % number)

  def testURI(self):
    sample = rdf_standard.URI(transport="http", host="google.com",
                              path="/index", query="q=hi", fragment="anchor1")
    self.assertEqual(sample.transport, "http")
    self.assertEqual(sample.host, "google.com")
    self.assertEqual(sample.path, "/index")
    self.assertEqual(sample.query, "q=hi")
    self.assertEqual(sample.fragment, "anchor1")

    url = "http://google.com/index?q=hi#anchor1"
    self.assertEqual(sample.SerializeToString(), url)

  def testParseFromString(self):
    sample = rdf_standard.URI()
    url = "http://google.com:443/search?query=hi#anchor2"
    sample.ParseFromString(url)

    self.assertEqual(sample.transport, "http")
    self.assertEqual(sample.host, "google.com:443")
    self.assertEqual(sample.path, "/search")
    self.assertEqual(sample.query, "query=hi")
    self.assertEqual(sample.fragment, "anchor2")

    self.assertEqual(sample.SerializeToString(), url)

