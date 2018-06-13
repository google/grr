#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""Parser for Mozilla Firefox3 3 History files."""

__program__ = "firefox3_history.py"

import datetime
import glob
import locale
import sys
import urlparse


from grr.lib import parser
from grr.lib.parsers import sqlite_file
from grr.lib.rdfvalues import webhistory as rdf_webhistory


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
          source_urn=file_object.urn,
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


def main(argv):
  if len(argv) < 2:
    print "Usage: %s places.sqlite" % __program__
    sys.exit(1)

  encoding = locale.getpreferredencoding()

  if encoding.upper() != "UTF-8":
    print "%s requires an UTF-8 capable console/terminal" % __program__
    sys.exit(1)

  files_to_process = []
  for input_glob in argv[1:]:
    files_to_process += glob.glob(input_glob)

  for input_file in files_to_process:
    firefox3 = Firefox3History(open(input_file, "rb"))

    for timestamp, entry_type, url, title in firefox3.Parse():
      try:
        date_string = datetime.datetime(1970, 1, 1)
        date_string += datetime.timedelta(microseconds=timestamp)
        date_string = u"%s +00:00" % (date_string)
      except TypeError:
        date_string = timestamp
      except ValueError:
        date_string = timestamp

      output_string = "%s\t%s\t%s\t%s" % (date_string, entry_type, url, title)

      print output_string.encode("UTF-8")


if __name__ == "__main__":
  main(sys.argv)
