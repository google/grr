#!/usr/bin/env python
# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Parser for Google chrome/chromium History files."""


__program__ = "chrome_history.py"

import datetime
import glob
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

  def Parse(self):
    """Iterator returning dict for each entry in history."""
    for timestamp, url, title, typed_count in self.Query(self.VISITS_QUERY):
      if not isinstance(timestamp, long) or timestamp < 11644473600000000:
        timestamp = 0
      else:
        # convert microseconds since Jan 1, 1601 00:00:00 to
        # microseconds since Jan 1, 1970 00:00:00
        timestamp -= 11644473600000000

      yield [timestamp, "CHROME_VISIT", url, title, typed_count, ""]

    for timestamp, url, path, received_bytes, total_bytes in self.Query(
        self.DOWNLOADS_QUERY):
      if not isinstance(timestamp, int):
        timestamp = 0
      else:
        # convert seconds since Jan 1, 1970 00:00:00 to
        # microseconds since Jan 1, 1970 00:00:00
        timestamp *= 1000000

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

