#!/usr/bin/env python
"""Parser for Mozilla Firefox3 3 History files."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


from future.moves.urllib import parse as urlparse
from past.builtins import long

from grr_response_core.lib import parser
from grr_response_core.lib.parsers import sqlite_file
from grr_response_core.lib.rdfvalues import webhistory as rdf_webhistory


class FirefoxHistoryParser(parser.FileParser):
  """Parse Chrome history files into BrowserHistoryItem objects."""

  output_types = ["BrowserHistoryItem"]
  supported_artifacts = ["FirefoxHistory"]

  def Parse(self, stat, file_object, knowledge_base):
    """Parse the History file."""
    _, _ = stat, knowledge_base
    # TODO(user): Convert this to use the far more intelligent plaso parser.
    ff = Firefox3History(file_object)
    for timestamp, unused_entry_type, url, title in ff.Parse():
      yield rdf_webhistory.BrowserHistoryItem(
          url=url,
          domain=urlparse.urlparse(url).netloc,
          access_time=timestamp,
          program_name="Firefox",
          source_path=file_object.Path(),
          title=title)


class Firefox3History(sqlite_file.SQLiteFile):
  """Class for handling the parsing of a Firefox 3 history file (places.sqlite).

    Use as:
      c = Firefox3History(open('places.sqlite'))
      for hist in c.Parse():
        print hist

  Returns results in chronological order
  """
  VISITS_QUERY = ("SELECT moz_historyvisits.visit_date, moz_places.url,"
                  " moz_places.title "
                  "FROM moz_places, moz_historyvisits "
                  "WHERE moz_places.id = moz_historyvisits.place_id "
                  "ORDER BY moz_historyvisits.visit_date ASC;")

  def Parse(self):
    """Iterator returning dict for each entry in history."""
    for timestamp, url, title in self.Query(self.VISITS_QUERY):
      if not isinstance(timestamp, (long, int)):
        timestamp = 0

      yield [timestamp, "FIREFOX3_VISIT", url, title]
