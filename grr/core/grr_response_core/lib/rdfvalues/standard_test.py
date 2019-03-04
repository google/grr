#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Test standard RDFValues."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app

from grr_response_core.lib.rdfvalues import standard as rdf_standard
from grr_response_core.lib.rdfvalues import test_base as rdf_test_base
from grr.test_lib import test_lib


class URITests(rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  """Test URI proto."""

  rdfvalue_class = rdf_standard.URI

  def GenerateSample(self, number=0):
    return rdf_standard.URI(transport="http", host="%s.example.com" % number)

  def testURI(self):
    sample = rdf_standard.URI(
        transport="http",
        host="google.com",
        path="/index",
        query="q=hi",
        fragment="anchor1")
    self.assertEqual(sample.transport, "http")
    self.assertEqual(sample.host, "google.com")
    self.assertEqual(sample.path, "/index")
    self.assertEqual(sample.query, "q=hi")
    self.assertEqual(sample.fragment, "anchor1")

  def testHumanReadable(self):
    sample = rdf_standard.URI()
    url = "http://google.com:443/search?query=hi#anchor2"
    sample.ParseFromHumanReadable(url)

    self.assertEqual(sample.transport, "http")
    self.assertEqual(sample.host, "google.com:443")
    self.assertEqual(sample.path, "/search")
    self.assertEqual(sample.query, "query=hi")
    self.assertEqual(sample.fragment, "anchor2")

    self.assertEqual(sample.SerializeToHumanReadable(), url)

  def testByteString(self):
    raw_uri = "http://gógiel.pl:1337/znajdź?frazę=🦋#nagłówek"

    uri = rdf_standard.URI()
    uri.ParseFromString(raw_uri.encode("utf-8"))

    self.assertEqual(uri.transport, "http")
    self.assertEqual(uri.host, "gógiel.pl:1337")
    self.assertEqual(uri.path, "/znajdź")
    self.assertEqual(uri.query, "frazę=🦋")
    self.assertEqual(uri.fragment, "nagłówek")

    self.assertEqual(uri.FromSerializedString(uri.SerializeToString()), uri)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
