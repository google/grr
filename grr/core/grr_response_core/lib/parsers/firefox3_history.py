#!/usr/bin/env python
"""Parser for Mozilla Firefox3 3 History files."""
from __future__ import absolute_import
from __future__ import division

from __future__ import print_function
from __future__ import unicode_literals

from future.moves.urllib import parse as urlparse
from past.builtins import long
from typing import IO
from typing import Iterator
from typing import Tuple

from grr_response_core.lib import parsers
from grr_response_core.lib.rdfvalues import webhistory as rdf_webhistory
from grr_response_core.lib.util import sqlite


class FirefoxHistoryParser(parsers.SingleFileParser):
  """Parse Chrome history files into BrowserHistoryItem objects."""

  output_types = [rdf_webhistory.BrowserHistoryItem]
  supported_artifacts = ["FirefoxHistory"]

  def ParseFile(self, knowledge_base, pathspec, filedesc):
    del knowledge_base  # Unused.

    # TODO(user): Convert this to use the far more intelligent plaso parser.
    ff = Firefox3History()
    for timestamp, unused_entry_type, url, title in ff.Parse(filedesc):
      yield rdf_webhistory.BrowserHistoryItem(
          url=url,
          domain=urlparse.urlparse(url).netloc,
          access_time=timestamp,
          program_name="Firefox",
          source_path=pathspec.CollapsePath(),
          title=title)


# TODO(hanuszczak): This should not be a class.
class Firefox3History(object):
  """Class for handling the parsing of a Firefox 3 history file."""

  VISITS_QUERY = ("SELECT moz_historyvisits.visit_date, moz_places.url,"
                  " moz_places.title "
                  "FROM moz_places, moz_historyvisits "
                  "WHERE moz_places.id = moz_historyvisits.place_id "
                  "ORDER BY moz_historyvisits.visit_date ASC;")

  # TODO(hanuszczak): This should return well-structured data.
  def Parse(self, filedesc):  # pylint: disable=g-bare-generic
    """Iterator returning dict for each entry in history."""
    with sqlite.IOConnection(filedesc) as conn:
      for timestamp, url, title in conn.Query(self.VISITS_QUERY):
        if not isinstance(timestamp, (long, int)):
          timestamp = 0

        yield timestamp, "FIREFOX3_VISIT", url, title
