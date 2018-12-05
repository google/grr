#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for grr_response_client.client_actions.plist."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os


from grr_response_client.client_actions import plist
from grr_response_core.lib import flags
from grr_response_core.lib import plist as plist_lib
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import plist as rdf_plist
from grr.test_lib import client_test_lib
from grr.test_lib import test_lib

# This variable holds the same contents as the ondisk test plist
test_plist_dict = {
    "date": 978307200000000,
    "nested1": {
        "nested11": {
            "data113": b"\xde\xad\xbe\xef",
            "key111": "value111",
            "key112": "value112"
        }
    },
    "numbers": [1, "2", "3"]
}

# y Safari History plist
safari_plist_dict = {
    "WebHistoryDates": [
        {
            "": "http://www.google.com",
            "title": "Google",
            "lastVisited": "374606652.9",
            "visitCount": 2
        },
        {
            "": "http://www.apple.com",
            "title": "Apple",
            "lastVisited": "374606652.9",
            "visitCount": 1
        },
    ],
    "WebHistoryFileVersion":
        1,
}


class PlistTest(client_test_lib.EmptyActionTest):

  def testParseFilter(self):
    queries = [
        (u'bla is "red"', True),
        (u'bla.bla is "red"', True),
        (u'bla."bla bliek" is "red"', True),
        (u'bla.bla bliek is "red"', False),
    ]
    for query, result in queries:
      if result:
        plist_lib.PlistFilterParser(query).Parse()
      else:
        filter_parser = plist_lib.PlistFilterParser(query)
        self.assertRaises(Exception, filter_parser.Parse)

  def testMatches(self):
    query = u'"nested1"."nested11"."key112" contains "value112"'
    parser = plist_lib.PlistFilterParser(query).Parse()
    matcher = parser.Compile(plist_lib.PlistFilterImplementation)
    self.assertEqual(matcher.Matches(test_plist_dict), True)

  def testActionFullRetrievalOfAPlist(self):
    results = self._RunQuery(query="", context="")
    if not results:
      raise Exception("no results were found...")
    self.assertDictEqual(results[0][0].ToDict(), test_plist_dict)

  def testActionSingleValueRetrieval(self):
    results = self._RunQuery(query="", context="date")
    if not results:
      raise Exception("no results were found...")
    self.assertEqual(results[0][0], 978307200000000)

  def testActionFilteredValueRetrieval(self):
    # Numbers does NOT contain a 2, but a "2", this should return nothing
    results = self._RunQuery(query=u"numbers contains 2", context="")
    self.assertListEqual(list(list(results)[0]), [])
    # This one should return the full dict
    results = self._RunQuery(query=u"numbers contains '2'", context="")
    self.assertEqual(results[0][0], test_plist_dict)

    # SAFARI PLIST
    results = self._RunQuery(
        plist_file="History.plist",
        query='title contains "oogle"',
        context="WebHistoryDates")
    self.assertEqual(results[0][0], safari_plist_dict["WebHistoryDates"][0])

    # And now SAFARI XML
    results = self._RunQuery(
        plist_file="History.xml.plist",
        query='title contains "oogle"',
        context="WebHistoryDates")
    self.assertEqual(results[0][0], safari_plist_dict["WebHistoryDates"][0])

  def testActionNonexistantFile(self):
    self.assertRaises(
        IOError,
        self._RunQuery,
        query="",
        context="",
        plist_file="nonexistantfile")

  def testActionInvalidFile(self):
    self.assertRaises(
        Exception, self._RunQuery, query="", context="", plist_file="History")

  def _RunQuery(self, plist_file="test.plist", query=u"", context=""):
    path = os.path.join(self.base_path, plist_file)
    pathspec = rdf_paths.PathSpec(
        path=path, pathtype=rdf_paths.PathSpec.PathType.OS)
    plistrequest = rdf_plist.PlistRequest()
    plistrequest.query = query
    plistrequest.context = context
    plistrequest.pathspec = pathspec
    return self.RunAction(plist.PlistQuery, plistrequest)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
