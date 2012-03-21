#!/usr/bin/env python
#
# Copyright 2012 Google Inc.
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


"""Parser for OSX quarantine sqlite files."""


__program__ = "osx_quarantine.py"

import datetime
import glob
import locale
import sys


from grr.parsers import sqlite_file


class OSXQuarantineEvents(sqlite_file.SQLiteFile):
  """Class for handling the parsing of a OSX quarantine events.

    Use as:
      c = OSXQuarantineEvents(open('com.apple.LaunchServices.QuarantineEvents'))
      for event in c.Parse():
        print event
  """
  # OSX Timestamp is seconds since January 1st 2001.
  EVENTS_QUERY = ("select (LSQuarantineTimeStamp+978328800)*1e6,"
                  "LSQuarantineAgentBundleIdentifier,  LSQuarantineAgentName,"
                  "LSQuarantineDataURLString,  LSQuarantineSenderName,"
                  "LSQuarantineSenderAddress,  LSQuarantineTypeNumber,"
                  "LSQuarantineOriginTitle,  LSQuarantineOriginURLString,"
                  "LSQuarantineOriginAlias "
                  "from LSQuarantineEvent "
                  "ORDER BY LSQuarantineTimeStamp"
                 )

  def Parse(self):
    """Iterator returning dict for each entry in history."""
    for data in self.Query(self.EVENTS_QUERY):
      (timestamp, agent_bundle_identifier, agent_name, url, sender,
       sender_address, type_number, title, referrer, referrer_alias) = data
      yield [timestamp, "OSX_QUARANTINE", url, referrer, title, agent_name,
             agent_bundle_identifier, sender, sender_address, type_number,
             referrer_alias]


def main(argv):
  if len(argv) < 2:
    print "Usage: %s com.apple.LaunchServices.QuarantineEvents" % __program__
    sys.exit(1)

  encoding = locale.getpreferredencoding()

  if encoding.upper() != "UTF-8":
    print "%s requires an UTF-8 capable console/terminal" % __program__
    sys.exit(1)

  files_to_process = []
  for input_glob in argv[1:]:
    files_to_process += glob.glob(input_glob)

  for input_file in files_to_process:
    events = OSXQuarantineEvents(open(input_file))

    for data in events.Parse():
      timestamp, entry_type, url, data1, data2, data3, _, _, _, _, _ = data
      try:
        date_string = datetime.datetime(1970, 1, 1)
        date_string += datetime.timedelta(microseconds=timestamp)
        date_string = u"%s+00:00" % (date_string)
      except TypeError:
        date_string = timestamp
      except ValueError:
        date_string = timestamp

      output_string = u"%s\t%s\t%s\t%s\t%s\t%s" % (
          date_string, entry_type, url, data1, data2, data3)

      print output_string.encode("UTF-8")


if __name__ == "__main__":
  main(sys.argv)
