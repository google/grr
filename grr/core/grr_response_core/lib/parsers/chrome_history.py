#!/usr/bin/env python
"""Parser for Google chrome/chromium History files."""
from __future__ import absolute_import
from __future__ import division

from __future__ import print_function
from __future__ import unicode_literals

import logging

from future.moves.urllib import parse as urlparse
from past.builtins import long
import sqlite3
from typing import IO
from typing import Iterator
from typing import Tuple

from grr_response_core.lib import parsers
from grr_response_core.lib.rdfvalues import webhistory as rdf_webhistory
from grr_response_core.lib.util import sqlite


class ChromeHistoryParser(parsers.SingleFileParser):
  """Parse Chrome history files into BrowserHistoryItem objects."""

  output_types = [rdf_webhistory.BrowserHistoryItem]
  supported_artifacts = ["ChromeHistory"]

  def ParseFile(self, knowledge_base, pathspec, filedesc):
    del knowledge_base  # Unused.

    # TODO(user): Convert this to use the far more intelligent plaso parser.
    chrome = ChromeParser()
    for timestamp, entry_type, url, data1, _, _ in chrome.Parse(filedesc):
      if entry_type == "CHROME_DOWNLOAD":
        yield rdf_webhistory.BrowserHistoryItem(
            url=url,
            domain=urlparse.urlparse(url).netloc,
            access_time=timestamp,
            program_name="Chrome",
            source_path=pathspec.CollapsePath(),
            download_path=data1)
      elif entry_type == "CHROME_VISIT":
        yield rdf_webhistory.BrowserHistoryItem(
            url=url,
            domain=urlparse.urlparse(url).netloc,
            access_time=timestamp,
            program_name="Chrome",
            source_path=pathspec.CollapsePath(),
            title=data1)


# TODO(hanuszczak): This shouldn't be a class, just a `Parse` function taking
# history file as input.
class ChromeParser(object):
  """Class for handling the parsing of a Chrome history file."""
  VISITS_QUERY = ("SELECT visits.visit_time, urls.url, urls.title, "
                  "urls.typed_count "
                  "FROM urls, visits "
                  "WHERE urls.id = visits.url "
                  "ORDER BY visits.visit_time ASC;")

  # TODO(hanuszczak): Do we need to maintain code that is supposed to work with
  # Chrome history format from 2013?

  # We use DESC here so we can pop off the end of the list and interleave with
  # visits to maintain time order.
  DOWNLOADS_QUERY = ("SELECT downloads.start_time, downloads.url, "
                     "downloads.full_path, downloads.received_bytes, "
                     "downloads.total_bytes "
                     "FROM downloads "
                     "ORDER BY downloads.start_time DESC;")

  # This is the newer form of downloads, introduced circa Mar 2013.
  DOWNLOADS_QUERY_2 = ("SELECT downloads.start_time, downloads_url_chains.url,"
                       "downloads.target_path, downloads.received_bytes,"
                       "downloads.total_bytes "
                       "FROM downloads, downloads_url_chains "
                       "WHERE downloads.id = downloads_url_chains.id "
                       "ORDER BY downloads.start_time DESC;")

  # Time diff to convert microseconds since Jan 1, 1601 00:00:00 to
  # microseconds since Jan 1, 1970 00:00:00
  TIME_CONV_CONST = 11644473600000000

  def ConvertTimestamp(self, timestamp):
    if not isinstance(timestamp, (long, int)):
      timestamp = 0
    elif timestamp > 11644473600000000:
      timestamp -= self.TIME_CONV_CONST
    elif timestamp < 631152000000000:  # 01-01-1900 00:00:00
      # This means we got seconds since Jan 1, 1970, we need microseconds.
      timestamp *= 1000000
    return timestamp

  # TODO(hanuszczak): This function should return a well-structured data instead
  # of a tuple of 6 elements (of which 2 of them are never used).
  def Parse(self, filedesc):  # pylint: disable=g-bare-generic
    """Iterator returning a list for each entry in history.

    We store all the download events in an array (choosing this over visits
    since there are likely to be less of them). We later interleave them with
    visit events to get an overall correct time order.

    Args:
      filedesc: A file-like object

    Yields:
      a list of attributes for each entry
    """
    with sqlite.IOConnection(filedesc) as conn:
      # Query for old style and newstyle downloads storage.
      rows = []

      try:
        rows.extend(conn.Query(self.DOWNLOADS_QUERY))
      except sqlite3.Error as error:
        logging.warning("Chrome history database error: %s", error)

      try:
        rows.extend(conn.Query(self.DOWNLOADS_QUERY_2))
      except sqlite3.Error as error:
        logging.warning("Chrome history database error: %s", error)

      results = []
      for timestamp, url, path, received_bytes, total_bytes in rows:
        timestamp = self.ConvertTimestamp(timestamp)
        results.append((timestamp, "CHROME_DOWNLOAD", url, path, received_bytes,
                        total_bytes))

      for timestamp, url, title, typed_count in conn.Query(self.VISITS_QUERY):
        timestamp = self.ConvertTimestamp(timestamp)
        results.append((timestamp, "CHROME_VISIT", url, title, typed_count, ""))

    results.sort(key=lambda it: it[0])
    for it in results:
      yield it
