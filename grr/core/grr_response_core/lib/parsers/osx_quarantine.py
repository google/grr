#!/usr/bin/env python
"""Parser for OSX quarantine sqlite files."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


from grr_response_core.lib.parsers import sqlite_file


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
                  "ORDER BY LSQuarantineTimeStamp")

  def Parse(self):
    """Iterator returning dict for each entry in history."""
    for data in self.Query(self.EVENTS_QUERY):
      (timestamp, agent_bundle_identifier, agent_name, url, sender,
       sender_address, type_number, title, referrer, referrer_alias) = data
      yield [
          timestamp, "OSX_QUARANTINE", url, referrer, title, agent_name,
          agent_bundle_identifier, sender, sender_address, type_number,
          referrer_alias
      ]
