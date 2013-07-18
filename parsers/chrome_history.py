#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.

"""Parser for Google chrome/chromium History files."""


__program__ = "chrome_history.py"

import datetime
import glob
import itertools
import locale
import sys


from grr.parsers import sqlite_file


class ChromeParser(sqlite_file.SQLiteFile):
  """Class for handling the parsing of a Chrome history file.

    Use as:
      c = ChromeParser(open('History'))
      for hist in c.Parse():
        print hist
  """
  VISITS_QUERY = ("SELECT visits.visit_time, urls.url, urls.title, "
                  "urls.typed_count "
                  "FROM urls, visits "
                  "WHERE urls.id = visits.url;")

  DOWNLOADS_QUERY = ("SELECT downloads.start_time, downloads.url, "
                     "downloads.full_path, downloads.received_bytes, "
                     "downloads.total_bytes "
                     "FROM downloads;")

  # This is the newer form of downloads, introduced circa Mar 2013.
  DOWNLOADS_QUERY_2 = ("SELECT downloads.start_time, downloads_url_chains.url,"
                       "downloads.target_path, downloads.received_bytes,"
                       "downloads.total_bytes "
                       "FROM downloads, downloads_url_chains "
                       "WHERE downloads.id = downloads_url_chains.id;")

  # Time diff to convert microseconds since Jan 1, 1601 00:00:00 to
  # microseconds since Jan 1, 1970 00:00:00
  TIME_CONV_CONST = 11644473600000000

  def Parse(self):
    """Iterator returning dict for each entry in history."""
    for timestamp, url, title, typed_count in self.Query(self.VISITS_QUERY):
      if not isinstance(timestamp, long) or timestamp < 11644473600000000:
        timestamp = 0
      else:

        timestamp -= self.TIME_CONV_CONST

      yield [timestamp, "CHROME_VISIT", url, title, typed_count, ""]

    # Query for old style and newstyle downloads storage.
    query_iter = itertools.chain(self.Query(self.DOWNLOADS_QUERY),
                                 self.Query(self.DOWNLOADS_QUERY_2))

    for timestamp, url, path, received_bytes, total_bytes in query_iter:

      if isinstance(timestamp, int):
        # convert seconds since Jan 1, 1970 00:00:00 to
        # microseconds since Jan 1, 1970 00:00:00
        timestamp *= 1000000
      elif isinstance(timestamp, long):
        timestamp -= self.TIME_CONV_CONST
      else:
        timestamp = 0

      yield [timestamp, "CHROME_DOWNLOAD", url, path, received_bytes,
             total_bytes]


def main(argv):
  if len(argv) < 2:
    print "Usage: %s History" % __program__
    sys.exit(1)

  encoding = locale.getpreferredencoding()

  if encoding.upper() != "UTF-8":
    print "%s requires an UTF-8 capable console/terminal" % __program__
    sys.exit(1)

  files_to_process = []
  for input_glob in argv[1:]:
    files_to_process += glob.glob(input_glob)

  for input_file in files_to_process:
    chrome = ChromeParser(open(input_file))

    for timestamp, entry_type, url, data1, data2, data3 in chrome.Parse():
      try:
        date_string = datetime.datetime(1970, 1, 1)
        date_string += datetime.timedelta(microseconds=timestamp)
        date_string = u"%s +00:00" % (date_string)
      except TypeError:
        date_string = timestamp
      except ValueError:
        date_string = timestamp

      output_string = u"%s\t%s\t%s\t%s\t%s\t%s" % (
          date_string, entry_type, url, data1, data2, data3)

      print output_string.encode("UTF-8")


if __name__ == "__main__":
  main(sys.argv)

