#!/usr/bin/env python
"""Parser for IE index.dat files.

Note that this is a very naive and incomplete implementation and should be
replaced with a more intelligent one. Do not implement anything based on this
code, it is a placeholder for something real.

For anyone who wants a useful reference, see this:
http://heanet.dl.sourceforge.net/project/libmsiecf/Documentation/MSIE%20Cache%20
File%20format/MSIE%20Cache%20File%20%28index.dat%29%20format.pdf
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import operator
import struct
from future.moves.urllib import parse as urlparse

from grr_response_core.lib import parser
from grr_response_core.lib.rdfvalues import webhistory as rdf_webhistory

# Difference between 1 Jan 1601 and 1 Jan 1970.
WIN_UNIX_DIFF_MSECS = 11644473600 * 1e6


class IEHistoryParser(parser.FileParser):
  """Parse IE index.dat files into BrowserHistoryItem objects."""

  output_types = ["BrowserHistoryItem"]
  supported_artifacts = ["InternetExplorerHistory"]

  def Parse(self, stat, file_object, knowledge_base):
    """Parse the History file."""
    _, _ = stat, knowledge_base
    # TODO(user): Convert this to use the far more intelligent plaso parser.
    ie = IEParser(file_object)
    for dat in ie.Parse():
      yield rdf_webhistory.BrowserHistoryItem(
          url=dat["url"],
          domain=urlparse.urlparse(dat["url"]).netloc,
          access_time=dat.get("mtime"),
          program_name="Internet Explorer",
          source_urn=file_object.urn)


class IEParser(object):
  """Parser object for index.dat files.

  The file format for IE index.dat files is somewhat poorly documented.
  The following implementation is based on information from:

  http://www.forensicswiki.org/wiki/Internet_Explorer_History_File_Format

  Returns results in chronological order based on mtime
  """

  FILE_HEADER = b"Client UrlCache MMF Ver 5.2"
  BLOCK_SIZE = 0x80

  def __init__(self, input_obj):
    """Initialize.

    Args:
      input_obj: A file like object to read the index.dat from.
    """
    self._file = input_obj
    self._entries = []

  def Parse(self):
    """Parse the file."""
    if not self._file:
      logging.error("Couldn't open file")
      return

    # Limit read size to 5MB.
    self.input_dat = self._file.read(1024 * 1024 * 5)
    if not self.input_dat.startswith(self.FILE_HEADER):
      logging.error("Invalid index.dat file %s", self._file)
      return

    # Events aren't time ordered in the history file, so we collect them all
    # then sort.
    events = []
    for event in self._DoParse():
      events.append(event)

    for event in sorted(events, key=operator.itemgetter("mtime")):
      yield event

  def _GetRecord(self, offset, record_size):
    """Retrieve a single record from the file.

    Args:
      offset: offset from start of input_dat where header starts
      record_size: length of the header according to file (untrusted)

    Returns:
      A dict containing a single browser history record.
    """
    record_header = "<4sLQQL"
    get4 = lambda x: struct.unpack("<L", self.input_dat[x:x + 4])[0]
    url_offset = struct.unpack("B", self.input_dat[offset + 52:offset + 53])[0]
    if url_offset in [0xFF, 0xFE]:
      return None
    data_offset = get4(offset + 68)
    data_size = get4(offset + 72)
    start_pos = offset + data_offset
    data = struct.unpack("{0}s".format(data_size),
                         self.input_dat[start_pos:start_pos + data_size])[0]
    fmt = record_header
    unknown_size = url_offset - struct.calcsize(fmt)
    fmt += "{0}s".format(unknown_size)
    fmt += "{0}s".format(record_size - struct.calcsize(fmt))
    dat = struct.unpack(fmt, self.input_dat[offset:offset + record_size])
    header, blocks, mtime, ctime, ftime, _, url = dat
    url = url.split(b"\x00")[0]
    if mtime:
      mtime = mtime // 10 - WIN_UNIX_DIFF_MSECS
    if ctime:
      ctime = ctime // 10 - WIN_UNIX_DIFF_MSECS
    return {
        "header": header,  # the header
        "blocks": blocks,  # number of blocks
        "urloffset": url_offset,  # offset of URL in file
        "data_offset": data_offset,  # offset for start of data
        "data_size": data_size,  # size of data
        "data": data,  # actual data
        "mtime": mtime,  # modified time
        "ctime": ctime,  # created time
        "ftime": ftime,  # file time
        "url": url  # the url visited
    }

  def _DoParse(self):
    """Parse a file for history records yielding dicts.

    Yields:
      Dicts containing browser history
    """
    get4 = lambda x: struct.unpack("<L", self.input_dat[x:x + 4])[0]
    filesize = get4(0x1c)
    offset = get4(0x20)
    coffset = offset
    while coffset < filesize:
      etype = struct.unpack("4s", self.input_dat[coffset:coffset + 4])[0]
      if etype == "REDR":
        pass
      elif etype in ["URL "]:
        # Found a valid record
        reclen = get4(coffset + 4) * self.BLOCK_SIZE
        yield self._GetRecord(coffset, reclen)
      coffset += self.BLOCK_SIZE
