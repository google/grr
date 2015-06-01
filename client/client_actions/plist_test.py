#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2010 Google Inc. All Rights Reserved.

"""Tests for grr.client.client_actions.plist."""



import os


# pylint: disable=unused-import
from grr.client import client_plugins
# pylint: enable=unused-import

from grr.lib import flags
from grr.lib import plist as plist_lib
from grr.lib import test_lib
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import plist as rdf_plist


# This variable holds the same contents as the ondisk test plist
test_plist_dict = {
    "date": 978307200000000,
    "nested1":
        {
            "nested11":
                {
                    "data113": "\xde\xad\xbe\xef",
                    "key111": "value111",
                    "key112": "value112"
                }
        },
    "numbers": [1, "2", "3"]
}

# y Safari History plist
safari_plist_dict = {
    "WebHistoryDates":
        [
            {"": "http://www.google.com",
             "title": "Google",
             "lastVisited": "374606652.9",
             "visitCount": 2},
            {"": "http://www.apple.com",
             "title": "Apple",
             "lastVisited": "374606652.9",
             "visitCount": 1},
        ],
    "WebHistoryFileVersion": 1,
}


class PlistTest(test_lib.EmptyActionTest):

  def testParseFilter(self):
    queries = [
        ('bla is "red"', True),
        ('bla.bla is "red"', True),
        ('bla."bla bliek" is "red"', True),
        ('bla.bla bliek is "red"', False),
    ]
    for query, result in queries:
      if result:
        plist_lib.PlistFilterParser(query).Parse()
      else:
        filter_parser = plist_lib.PlistFilterParser(query)
        self.assertRaises(Exception, filter_parser.Parse)

  def testMatches(self):
    query = '"nested1"."nested11"."key112" contains "value112"'
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
    results = self._RunQuery(query="numbers contains 2", context="")
    self.assertListEqual(list(list(results)[0]), [])
    # This one should return the full dict
    results = self._RunQuery(query="numbers contains '2'", context="")
    self.assertEqual(results[0][0], test_plist_dict)

    # SAFARI PLIST
    results = self._RunQuery(plist="History.plist",
                             query='title contains "oogle"',
                             context="WebHistoryDates")
    self.assertEqual(results[0][0],
                     safari_plist_dict["WebHistoryDates"][0])

    # And now SAFARI XML
    results = self._RunQuery(plist="History.xml.plist",
                             query='title contains "oogle"',
                             context="WebHistoryDates")
    self.assertEqual(results[0][0],
                     safari_plist_dict["WebHistoryDates"][0])

  def testActionNonexistantFile(self):
    self.assertRaises(IOError, self._RunQuery,
                      query="",
                      context="",
                      plist="nonexistantfile")

  def testActionInvalidFile(self):
    self.assertRaises(Exception,
                      self._RunQuery,
                      query="",
                      context="",
                      plist="History")

  def _RunQuery(self, plist="test.plist", query="", context=""):
    path = os.path.join(self.base_path, plist)
    pathspec = rdf_paths.PathSpec(path=path,
                                  pathtype=rdf_paths.PathSpec.PathType.OS)
    plistrequest = rdf_plist.PlistRequest()
    plistrequest.query = query
    plistrequest.context = context
    plistrequest.pathspec = pathspec
    return self.RunAction("PlistQuery", plistrequest)


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
