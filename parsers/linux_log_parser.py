#!/usr/bin/env python
# -*- coding: utf-8 -*-$
#$
# Copyright 2012 Google Inc. All Rights Reserved.
#
# Automated timeline parsers for (currently):
#   wtmp, syslog, dmesg, apache, dpkg, auth
#
# The point here is to create an extensible tool/library
# that can be used to easily add new modules to parse
# log files.
#
# text:
#   syslog dmesg apache dpkg auth
# binary:
#   wtmp
#
"""A simple class that parses Linux log files to provide a timestamp.

A simple log file parser to extract timestamps from various log files
found on a typical Linux box.

The currently supported log files are:
    + syslog
    + dmesg
    + apache
    + dpkg
    + auth

The tool will output the data in the following format:
  time|source|type|message

Where
  time : Time in Epoch (seconds since Jan 1 1970)
  source: From which log file this data comes from
  type: The type of timestamped data
  message: The message extracted/parsed

This first version of the tool does NOT support timezone information,
nor does it support fancy outputting... only one uber standard for all
format exists.... although it is very easy to change that if the request
comes...
"""



import bz2
import calendar
import datetime
import gzip
import logging
import optparse
import os.path
import re
import socket
import struct
import sys
import time
import pytz

_ENTRY_WRITTEN = 'Entry Written'


class Error(Exception):
  """Base error class."""


class OpenFileError(Error):
  """An error that gets raised when there is trouble opening the file."""


class NoTimestampFound(Error):
  """Error that gets raised when an entry contains an empty or zero timestamp.

  Some files may have a faulty timestamp or a non existing one.
  There is no need for the output to include those entries, yet at the same
  time we would like to know if some entries are omitted in the output.

  Therefore the output formatter raise this error if they get a faulty
  or zero entries.
  """


class LogOutputFormatter(object):
  """A base class for formatting output produced by LogParser objects.

  This class exists mostly for documentation purposes. Subclasses should
  override the relevant methods to act on the callbacks.
  """

  def AddEvent(self, event):
    """This should be extended by specific implementations.

    This method takes care of actually outputting each event in
    question.

    Args:
      event: An event object (tuble) that is used to output information
      about the event.

    Raises:
      NoTimestampFound: when there is no timestamp or an error.
    """

  def StartEvent(self):
    """This should be extended by specific implementations.

    This method does all pre-processing or output before each event
    is printed, for instance to surround XML events with tags, etc.

    Returns:
      A string that needs to be prepended to each event.
    """
    return ''

  def EndEvent(self):
    """This should be extended by specific implementations.

    This method does all the post-processing or output after
    each event has been printed, such as closing XML tags, etc.

    Returns:
      A string that needs to be appended to each event.
    """
    return ''

  def CreateHeader(self):
    """This should be extended by specific implementations.

    Depending on the file format of the output it may need
    a header. This method should return a header if one is
    defined in that output format.

    Returns:
      A string containing the header for the output.
    """
    return ''

  def CreateTail(self):
    """This should be extended by specific implementations.

    Depending on the file format of the output it may need
    a footer. This method should return a footer if one is
    defined in that output format.

    Returns:
      A string containing the footer for the output.
    """
    return ''


class L2tCsvFormatter(LogOutputFormatter):
  """A class that defines an output in the l2t_csv format."""

  def CreateHeader(self):
    return ('date,time,timezone,MACB,source,sourcetype,type,user'
            ',host,short,desc,version,filename,inode,notes,format,'
            'extra\n')

  def AddEvent(self, event):
    """Adjust the output to the csv format of log2timeline.

    Args:
      event: A tuble containing the extracted information from
             the event.

    Returns:
      A string in the correct output format.

    Raises:
      NoTimestampFound: when there is no timestamp or an error.
    """
    timestamp, source_name, event_type, event_msg = event

    if not event_type:
      raise NoTimestampFound('Problem with output, no event type'
                             ' given for output')

    if not timestamp:
      raise NoTimestampFound('Empty timestamp value, omitting event in output')

    utc_timestamp = timestamp.astimezone(pytz.utc)

    fields = [utc_timestamp.strftime('%m/%d/%Y'),
              utc_timestamp.strftime('%H:%M:%S'),
              'UTC',
              'MACB',
              'LOG',
              str(source_name),
              str(event_type),
              '-',
              '-',
              str(event_msg),
              str(event_msg),
              '2',
              '-',
              '0',
              '-',
              'linux_log_parser',
              '-']
    return ','.join(fields) + '\n'


class PipeFormatter(LogOutputFormatter):
  """A class that defines the standard output of the tool."""

  DATESTRING = '%Y-%m-%d %H:%M:%S'

  def CreateHeader(self):
    return 'time|epoch|source|type|message\n'

  def AddEvent(self, event):
    """Adjust the output of each event."""
    timestamp, source_name, event_type, event_msg = event

    if not event_type:
      raise NoTimestampFound('Problem with output, no event '
                             'type given for output')

    if not timestamp:
      raise NoTimestampFound('Empty timestamp value, omitting event in output')

    utc_timestamp = timestamp.astimezone(pytz.utc)
    return '%s|%s|%s|%s|%s\n' % (
        utc_timestamp.strftime('%Y-%m-%dT%H:%M:%SZ'),
        int(calendar.timegm(utc_timestamp.timetuple())),
        source_name, event_type, re.sub('\|', '::pipe::', event_msg))


class LogParser(object):
  """A parent class defining a typical log parser.

  This parent class gets inherited from other classes that are parsing
  log files.

  There is one class variables that needs defining:
    NAME - the name of the type of file being parsed, eg. Syslog
  """
  NAME = 'General Log Parser'
  MONTH_DICT = {
      'jan': 1,
      'feb': 2,
      'mar': 3,
      'apr': 4,
      'may': 5,
      'jun': 6,
      'jul': 7,
      'aug': 8,
      'sep': 9,
      'oct': 10,
      'nov': 11,
      'dec': 12}

  #TODO(user): Create a New LogLineParser that abstracts most
  # of the needed functions for parsing simple log files.
  def Parse(self, filehandle, zone=pytz.utc):
    """Verifies and parses the log file and returns timestamps.

    This is the main function of the class, the one that actually
    goes through the log file and parses each line of it to
    produce a parsed line and a timestamp.

    It also tries to verify the file structure and see if the class is capable
    of parsing the file passed to the module. It will do so with series of tests
    that should determine if the file is of the correct structure.

    If the class is not capable of parsing the file passed to it an exception
    should be raised, an exception of the type TypeError that indicates the
    reason why the class does not parse it.

    Args:
      filehandle: A filehandle/file-like-object that is seekable to the file
      needed to be checked.
      zone: the timezone of the file in question (a PyTZ object, which is
      verified by checking if the object has a localize attribute).

    Raises:
      NotImplementedError when not implemented.
    """
    raise NotImplementedError


class DmesgParser(LogParser):
  """Dmesg Parser.

    This is an implementation of a parser for the dmesg file.

    Since dmesg doesn't really store any timestamps within it this class
    uses the file creation time as a start point and then uses the information
    from within the dmesg file to calculate the offset from that creation time.

    That is to say the dmesg file contains a value that represents the number of
    seconds since the file got started, which conincides with the time it got
    created. That date is used in combination with the extracted
    seconds passed value within the logfile to determine the actual
    timestamp of each record/event.

  Example line:
    [   23.099440] type=1400 audit(1319642048.976:14): apparmor="STATUS" \
    operation="profile_load" name="/opt/google/chrome/chrome-sandbox" pid=1365\
    comm="apparmor_parser"
  """
  REG_COMP = re.compile('\[\s+(?P<sec>\d+)\.(?P<ms>\d+)\] (?P<msg>.+)')
  NAME = 'DMESG'

  def Parse(self, filehandle, zone=pytz.utc):
    """Parse a dmesg file."""
    assert hasattr(zone, 'localize')
    m, line = VerifyFirstLine(filehandle, self.REG_COMP, self.NAME)
    logging.debug('[DMESG] Verified, valid integer (%d)', int(m.group('sec')))

    stat_object = os.stat(filehandle.name)
    create_time = stat_object.st_ctime
    file_create = zone.localize(
        datetime.datetime.fromtimestamp(create_time))

    yield self._ParseLine(line, file_create)

    for line in filehandle:
      yield self._ParseLine(line, file_create)

  def _ParseLine(self, line, file_create):
    """Parse a single line and return a timestamp and a msg."""
    m = self.REG_COMP.match(line)

    if m:
      delta = datetime.timedelta(0, int(m.group('sec')), int(m.group('ms')))
      timestamp = file_create + delta

      msg = m.group('msg')
    else:
      logging.debug('[Dmesg] Line not correctly formed <%s>', line.rstrip())
      timestamp = 0
      msg = 'No entry'

    return timestamp, self.NAME, _ENTRY_WRITTEN, msg


class DpkgParser(LogParser):
  """Dpkg log file Parser.

    This class determine if a file is a dpkg file or not, and if it is,
    we will parse it.

  Example line:
    2012-01-10 09:25:26 status unpacked base-files 6.5ubuntu6
  """
  REG_COMP = re.compile("""(?P<year>\d{4})-    # year
                           (?P<month>\d{2})-
                           (?P<day>\d{2})\s
                           (?P<hour>\d{2}):
                           (?P<min>\d{2}):
                           (?P<sec>\d{2})\s
                           (?P<status>\w+)\s
                           (?P<result>.+)$""", re.X)
  DPKG_STATUS = set(['configure', 'install', 'startup', 'status', 'trigproc',
                     'update-alternatives:', 'upgrade'])
  NAME = 'DPKG'

  def Parse(self, filehandle, zone=pytz.utc):
    """Parse a DPKG file."""
    assert hasattr(zone, 'localize')
    m, line = VerifyFirstLine(filehandle, self.REG_COMP, self.NAME)

    if m.group('status') not in self.DPKG_STATUS:
      raise TypeError('[%s] Status not correct <%s?',
                      self.NAME,
                      m.group('status'))

    yield self._ParseLine(line, zone)

    for line in filehandle:
      yield self._ParseLine(line, zone)

  def _ParseLine(self, line, zone):
    """Parse a single line and return a timestamp and a msg."""
    m = self.REG_COMP.match(line)

    if m:
      timestamp = datetime.datetime(int(m.group('year')),
                                    int(m.group('month')),
                                    int(m.group('day')),
                                    int(m.group('hour')),
                                    int(m.group('min')),
                                    int(m.group('sec')),
                                    0)
      timestamp = zone.localize(timestamp)

      msg = '[%s] %s' % (m.group('status'), m.group('result'))
    else:
      logging.debug('[DPKG] Line not correctly formed <%s>', line.rstrip())
      timestamp = 0
      msg = 'No entry'
    return timestamp, self.NAME, _ENTRY_WRITTEN, msg


class ApacheParser(LogParser):
  """Apache parser.

  This verification function reads in a single line from the log file and
  runs it against a regular expression that checks if it fits into an Apache
  log file format.

  An Apache log server line might look like this:
  127.0.0.1 - - [08/Aug/2008:14:56:30 +0000] "OPTIONS * HTTP/1.0" 200 - "-"
  "Apache/2.2.8 (Ubuntu) PHP/5.2.4-2ubuntu5.1 with Suhosin-Patch (internal
  dummy connection)"
  """
  REG_COMP = re.compile("""^(?P<ip>[0-9\.]+)\s
                           (?P<user>[^\s]+)\s
                           (?P<uid>[^\s]+)\s
                           \[(?P<day>\d+)\/
                           (?P<month>\w\w\w)\/
                           (?P<year>\d+):
                           (?P<hour>\d+):
                           (?P<min>\d+):
                           (?P<sec>\d+)\s
                           (?P<tz>[\+\-]\d+)\]\s
                           "(?P<request>[^"]+)"\s
                           (?P<status>\d{3})\s
                           (?P<bytes>[\d-]+)\s
                           "(?P<referer>[^"]+)"\s
                           "(?P<user_agent>[^"]+)".*""", re.X)
  NAME = 'Apache'

  def Parse(self, filehandle, zone=pytz.utc):
    """Parse an Apache log file."""
    assert hasattr(zone, 'localize')
    m, line = VerifyFirstLine(filehandle, self.REG_COMP, self.NAME)

    # check month to see if it exists
    if m.group('month').lower() not in self.MONTH_DICT:
      raise TypeError('Not correctly formed (month value invalid).')

    yield self._ParseLine(line, zone)

    for line in filehandle:
      yield self._ParseLine(line, zone)

  def _ParseLine(self, line, zone):
    """Parse a single line and return a timestamp and a message."""
    m = self.REG_COMP.match(line)

    if m:
      month_use = self.MONTH_DICT.get(m.group('month').lower())
      if month_use is None:
        timestamp = 0
      else:
        timestamp = datetime.datetime(int(m.group('year')),
                                      int(month_use),
                                      int(m.group('day')),
                                      int(m.group('hour')),
                                      int(m.group('min')),
                                      int(m.group('sec')),
                                      0)
        timestamp = zone.localize(timestamp)

      msg = '[%s] %s' % (m.group('status'), m.group('request'))
      if m.group('referer') != '-':
        msg = '%s (referer: %s)' % (msg, m.group('referer'))

      msg = '%s <UA: %s>' % (msg, m.group('user_agent'))
    else:
      logging.debug('[Apache] Line not correctly formed: %s', line.rstrip())
      timestamp = 0
      msg = 'No entry'

    return timestamp, self.NAME, _ENTRY_WRITTEN, msg


class WtmpParser(LogParser):
  """WTMP Parser.

  The WTMP parser reads the binary wtmp file according to the header
  definition, which is roughly this one:
    ("h", "ut_type"),$
    ("i", "ut_pid"),$
    ("32s", "ut_line"),$
    ("4s", "ut_id"),$
    ("32s", "ut_user"),$
    ("256s", "ut_host"),$
    ("i", "ut_exit"),$
    ("i", "ut_session"),$
    ("i", "tv_sec"),$
    ("i", "tv_usec"),$
    ("4i", "ut_addr_v6"),$
    ("20s", "unused"),$

  The verification routine takes one line according to this definition and
  attempts to verify few portions of the line to make sure we do have an
  actual wtmp file on our hand.

  The verification examines the one line read and takes the 'date' portion
  and tries to see if it is within reasonable timeframe.

  A reasonable timeframe is defined as being from 01/06/2002 until one month
  into the future. If the timestamp is within this border, the verification
  will pass.

  After the structure has been verified, the function continues
  on parsing the file, line-by-line.

  This function basically calls the line parser one and
  interprets the results that are stored inside the variable
  self.results, which contains the following entries/fields:
     0: type
     1: pid - of login process
     2: line - device name of TTY dev/
     3: id - terminal name suffix (inittab ID)
     4: user - username
     5: host - host name or IP address, kernel version, ...
     6: exit - exit status of process of a DEAD_PROCESS
     7: session - session ID (used for windowing)
     8: sec - seconds since Epoch
     9: usec - microseconds
    10: IP address (version 6, if version 4, just first field used)

  To match logins with logouts a dictionary is created that keeps tabs
  on all logins and stores information about the user/host with the key
  name of "%s.%s" % (pid,line)

  And when a dead process is encountered there is a check to see if there
  is a match in the login list that matches that criteria, and if so
  a logout is processed.

  Documentation on the format can be found here:
    http://www.kernel.org/doc/man-pages/online/pages/man5/utmp.5.html
    /usr/include/bits/utmp.h
  """
  REG_COMP = re.compile('^\d+$')
  TYPES = ['EMPTY', 'RUN_LVL', 'BOOT_TIME', 'NEW_TIME', 'OLD_TIME',
           'INIT_PROCESS',
           'LOGIN_PROCESS',
           'USER_PROCESS',
           'DEAD_PROCESS',
           'ACCOUNTING']
  UTMP_DEFINITION = [
      ('i', 'ut_type'),
      ('i', 'pid'),
      ('32s', 'line'),
      ('4s', 'id'),
      ('32s', 'user'),
      ('256s', 'host'),
      ('i', 'exit'),
      ('i', 'session'),
      ('i', 'sec'),
      ('i', 'usec'),
      ('i', 'ip_1'),
      ('i', 'ip_2'),
      ('i', 'ip_3'),
      ('i', 'ip_4'),
      ('20s', 'nothing'),
  ]
  DATE_CHECK = int(time.mktime((2002, 1, 6, 0, 0, 0, 0, 0, 0)))
  FORMAT_STRING = ''.join(x for x, _ in UTMP_DEFINITION)
  RECORD_LENGTH = struct.calcsize(FORMAT_STRING)
  NAME = 'UTMP'

  def Parse(self, filehandle, zone=pytz.utc):
    """Parse a UTMP file."""
    assert hasattr(zone, 'localize')
    offset = 0

    # read one line and then
    try:
      line, _ = self._ParseLine(filehandle, offset)
    except IndexError:
      raise TypeError('Not valid UTMP file')
    except struct.error as error_msg:
      logging.debug('[%s] Not valid, error: %s', self.NAME, error_msg.args[0])
      raise TypeError('Not valid UTMP file')

    VerifyRegex(self.REG_COMP, str(line['sec']), self.NAME)

    logging.debug(('[UTMP_VERIFY] Match. That is we have a number (%d), '
                   'indicating a possible UTMP file.'), line['sec'])
    upper_time = int(time.time()) + 60 * 60 * 24 * 30  # 30 days

    if line['sec'] > self.DATE_CHECK and line['sec'] < upper_time:
      login_list = self._PreprocessLogon(filehandle, zone)
    else:
      raise TypeError('Not valid UTMP, time value is not within '
                      'reasonable bounds')
    timestamp = 0
    while True:
      line, offset = self._ParseLine(filehandle, offset)
      if line is None:
        break
      msg = None
      timestamp = datetime.datetime.utcfromtimestamp(int(line['sec']))
      timestamp = zone.localize(timestamp)

      if line['type'] == 'USER_PROCESS':
        ut_user = line['user']
        ut_host = line['host']
        if line['ip_address'] not in ut_host:
          ut_host += ' (%s)' % line['ip_address']
        ut_id = line['id']
        msg_type = 'Logon'
      elif line['type'] == 'DEAD_PROCESS':
        msg_type = 'Logout'
        key = '%s.%s' % (line['pid'], line['id'])
        if key in login_list:
          ut_user, ut_host, ut_id = login_list[key][0:3]
        else:
          timestamp = None
          msg_type = None
          logging.debug('[UTMP] KEY [%s] not in list of prior known logins.',
                        key)
      elif line['type'] == 'RUN_LVL':
        if 'shutdown' in line['user'].lower():
          msg_type = 'Shutdown'
        elif 'runlevel' in line['user'].lower():
          msg_type = 'RunLevel'
          # TODO(user): future versions should deal with this. That is
          # determine which runlevel was switched to (use additional_text
          # to store it in)
        else:
          msg_type = 'Information (runlevel)'

        msg = 'Event <%s>, kernel version: %s (pid %d)' % (line['user'],
                                                           line['host'],
                                                           line['pid'])
      elif line['type'] == 'BOOT_TIME':
        msg_type = 'Reboot'
        msg = 'Event %s, kernel version: %s (pid %d)' % (line['user'],
                                                         line['host'],
                                                         line['pid'])
      else:
        msg_type = line['type']
        ut_id = line['id']
        ut_user = line['user']
        ut_host = line['host']

      if not msg:
        msg = 'User %s [host %s]. PID %s. Event came from %s (id %s)' % (
            ut_user,
            ut_host,
            line['pid'],
            line['id'],
            ut_id)
      yield timestamp, self.NAME, msg_type, msg

  def _ParseLine(self, filehandle, offset):
    """Parses a single line from the wtmp file.

    This method/function reads a single line from the wtmp file and
    parses it.

    The return value will be a tuble object that contains the results.

    The offset to where the line starts in the file is stored within
    self.offset.

    results contains:
       0: type
       1: pid
       2: line
       3: id
       4: user
       5: host
       6: exit
       7: session
       8: sec
       9: usec
      10: IP address

    Args:
      filehandle: A filehandle or a file object to read data from.
      offset: An int offset to where to read the next data entry from.

    Returns:
      The results as a tuble if there is a line to parse, otherwise a
      None object is returned.
    """
    filehandle.seek(offset)

    data = filehandle.read(self.RECORD_LENGTH)

    if not data or len(data) < self.RECORD_LENGTH:
      logging.debug('[%s] No more lines to parse', self.NAME)
      return None, offset

    offset += self.RECORD_LENGTH
    result = {}
    for (_, name), value in zip(self.UTMP_DEFINITION,
                                struct.unpack(self.FORMAT_STRING, data)):
      result[name] = value

    if result['ip_2'] == 0:
      ut_ip = socket.inet_ntoa(struct.pack('i', result['ip_1']))
    else:
      ut_ip = '%s.%s.%s.%s' % (result['ip_1'], result['ip_2'], result['ip_3'],
                               result['ip_4'])
    result['ip_address'] = ut_ip
    result['type'] = self.TYPES[result['ut_type']]

    for fix in ('user', 'line', 'host', 'id'):
      result[fix] = result[fix].split('\x00', 1)[0]

    return result, offset

  def _PreprocessLogon(self, filehandle, zone):
    """Function that parses the entire file and grabs logon information.

    This is a pre-processing function that reads the file's entire content
    to look for logon events and fills up a dictionary with those events
    so that logout events can be successfully recorded.

    Args:
      filehandle: A file object to use to read data from.
      zone: The timezone information for the log file.

    Returns:
      A dict containing the login list.
    """
    logging.debug('[UTMP] Pre-processing login information.')
    filehandle.seek(0)
    offset = 0
    login_list = {}
    try:
      while True:
        record, offset = self._ParseLine(filehandle, offset)
        if not record:
          break
        timestamp = datetime.datetime.fromtimestamp(record['sec'])
        timestamp = zone.localize(timestamp)

        if record['type'] == 'USER_PROCESS':
          key = '%s.%s' % (record['pid'], record['line'])
          login_list[key] = [record['user'], record['host'],
                             record['id'], timestamp]

      filehandle.seek(0)

      return login_list
    except struct.error as error_msg:
      logging.error(('[%s] Error while parsing trying to parse'
                     'line, wrong structure?'), self.NAME)
      logging.error('[%s] Error msg: %s', self.NAME, error_msg.args[0])
      return None


class SyslogParser(LogParser):
  """Syslog Parser.

  If this is a syslog file it will also determine the year the file was
  created and last modified, since syslog doesn't contain that information.

  The year is then used to calculate the actual year the record occured on
  using a simple algorithm (if one call it really an algorithm). That is we
  take the year the file was created, and assume that is a correct year for
  the first entry.

  Then when the file is parsed the current month value is compared to last
  entries month value, and if we see that the current one is less than the
  last one (for example it's now 01 instead of 12 as it was last time) we
  increment the year value.

  Example line:
    Dec  6 10:16:01 vinnuvelin.net CRON[21352]: (root) CMD\
    (touch /var/run/crond.sittercheck)
  """
  REG_COMP = re.compile("""(?P<month>\w+)  # month when event got recorded
                           \s+             #
                           (?P<day>\d+)    # the day (int)
                           \s
                           (?P<hour>\d+)
                           :
                           (?P<min>\d+)
                           :
                           (?P<sec>\d+)
                           \s
                           (?P<host>[^\s]+)
                           \s
                           (?P<msg>.+)""", re.X)
  REG_REPORTER = re.compile("""(?P<reporter>[^\[]+)
                               \[(?P<pid>\d+)\]:
                               \s(?P<msg>.+)""", re.X)
  NAME = 'Syslog'

  def Parse(self, filehandle, zone=pytz.utc):
    """Parse a syslog file."""
    assert hasattr(zone, 'localize')
    m, line = VerifyFirstLine(filehandle, self.REG_COMP, self.NAME)

    if m.group('month').lower() not in self.MONTH_DICT:
      logging.debug('[Syslog] Month value not correctly formed.')
      raise TypeError('Month value not correctly formed')

    stat_object = os.stat(filehandle.name)
    create_time = stat_object.st_ctime
    mod_time = stat_object.st_mtime
    file_create = zone.localize(
        datetime.datetime.fromtimestamp(create_time))
    file_modify = zone.localize(
        datetime.datetime.fromtimestamp(mod_time))

    self.year_use = file_create.year

    # TODO(user): Change this to a proper test that actually tests
    # whether or not this is a file that got rotated in the year after
    # it got created. that is we want to know the file's creation date
    # but when it get's rotated/compressed that date changes, thus
    # needing to have a test that checks that condition
    if (isinstance(filehandle, gzip.GzipFile) and
        file_modify.month == 1 and file_modify.day == 1):
      self.year_use -= 1
      logging.debug('[%s] Reducing year by one (gzipped file'
                    'modified Jan 1...)', self.NAME)

    self.last_month = 0

    yield self._ParseLine(line, zone)

    for line in filehandle:
      yield self._ParseLine(line, zone)

  def _ParseLine(self, line, zone):
    """Parse a single log line of a syslog file.

    Method of calculating the year:
      = determine the year the syslog file was created.
      = save the last entries month value
      = compare last month to current one
      = if last month is more than current month (eg. now 01 used to be 12)
      assume
      year has increased by one.

    Args:
      line: A string containing a single log line.
      zone: The timezone of the log file.

    Returns:
      timestamp: A date from when the entry got written.
      msg: A string containing the parsed log line.
    """
    m = self.REG_COMP.match(line)

    if not m:
      logging.debug(('[%s] Line not correctly formed '
                     '<%s>', self.NAME, line.rstrip()))
      return 0, self.NAME, _ENTRY_WRITTEN, 'No entry'

    month = self.MONTH_DICT.get(m.group('month').lower())
    if month is None:
      logging.debug('[%s] Month badly formed (%s)', self.NAME,
                    m.group('month'))
      return 0, self.NAME, _ENTRY_WRITTEN, 'No entry'

    if self.last_month > month:
      logging.debug('Incrementing year from %d to %d', self.year_use,
                    self.year_use + 1)
      self.year_use += 1

    self.last_month = month
    timestamp = datetime.datetime(int(self.year_use),
                                  int(month),
                                  int(m.group('day')),
                                  int(m.group('hour')),
                                  int(m.group('min')),
                                  int(m.group('sec')),
                                  0)
    timestamp = zone.localize(timestamp)

    reporter, msg_text = self._GetReporter(m.group('msg'))

    msg = '[%s] %s (%s)' % (m.group('host'),
                            reporter,
                            msg_text)

    return timestamp, self.NAME, _ENTRY_WRITTEN, msg

  def _GetReporter(self, line):
    """A method that finds the reporter of a syslog message.

    The input would be a line of the form:
      [REPORTER PID]: MSG

    The method simply grabs the content of the string that is within
    the brackets ([]) and splits it into a PID and a reporter.

    The remainder of the line is simply the message string, or the
    output from that process/reporter and pid.

    Args:
      line: The syslog line that contains the message and
            the reporting process.

    Returns:
      reporter: The reporting process name.
      msg_text: The remainder of the msg text, if no reporter
                can be extracted the msg_text is the whole
                msg that got sent in.
    """
    reporter_match = self.REG_REPORTER.match(line)
    if reporter_match:
      reporter = 'Reporter <%s> PID: %s' % (reporter_match.group('reporter'),
                                            reporter_match.group('pid'))
      msg_text = reporter_match.group('msg')
    else:
      reporter = '<no known reporter>'
      msg_text = line

    return reporter, msg_text


class AuthParser(SyslogParser):
  """Auth log file parser.

  Example line:
    Dec  6 11:39:01 vinnuvelin.net CRON[30933]:
    pam_unix(cron:session): session closed for user root

  The problem with the AUTH file is that it follows the syslog format
  (so we need to parse this one first) and it requires a bit different
  manipulation of the data field.
  """
  REG_COMP = re.compile("""(?P<month>\w+)\s+
                           (?P<day>\d+)\s
                           (?P<hour>\d+):
                           (?P<min>\d+):
                           (?P<sec>\d+)\s
                           (?P<host>[^\s]+)\s
                           (?P<reporter>[^\s]+)\s
                           (?P<msg>.+)""", re.X)
  REG_REPORTER = re.compile("""(?P<reporter>[^\[]+)
                               \[(?P<pid>\d+)\]""", re.X)
  NAME = 'Auth'

  def Parse(self, filehandle, zone=pytz.utc):
    # name needs to be correct too
    name = re.search('auth', filehandle.name, re.IGNORECASE)

    if not name:
      logging.debug('[Auth] Needs to be named \'*auth*\''
                    '(case insensitive though)')
      raise TypeError('Wrong name of the log file.')

    for timestamp, _, entry_type, msg in super(AuthParser, self).Parse(
        filehandle, zone):
      yield timestamp, self.NAME, entry_type, msg

  def _ParseLine(self, line, zone):
    """Parses a single line in the and return a timestamp and a message."""
    m = self.REG_COMP.match(line)

    if not m:
      logging.debug('[Auth] Line not correctly formed <%s>', line.rstrip())
      timestamp = 0
      msg = 'No entry'
    else:
      month_use = self.MONTH_DICT.get(m.group('month').lower())

      if month_use is None:
        logging.debug('[Auth] Month not correctly formed <%s>',
                      m.group('month'))
        timestamp = 0
        msg = 'No entry'
        return 0, self.NAME, _ENTRY_WRITTEN, 'No entry'

      if self.last_month > month_use:
        logging.debug('Incrementing year from %d to %d', self.year_use,
                      self.year_use + 1)
        self.year_use += 1

      self.last_month = month_use

      reporter = self._GetReporter(m.group('reporter'))

      timestamp = datetime.datetime(int(self.year_use),
                                    int(month_use),
                                    int(m.group('day')),
                                    int(m.group('hour')),
                                    int(m.group('min')),
                                    int(m.group('sec')),
                                    0)
      timestamp = zone.localize(timestamp)

      msg = '[%s] Reporter %s Msg: %s' % (m.group('host'),
                                          reporter,
                                          m.group('msg'))

    return timestamp, self.NAME, _ENTRY_WRITTEN, msg

  def _GetReporter(self, line):
    """A simple class to return the reporter/process responsible for the entry.

    Args:
      line: The line itself that contains the message and reporter/process.
    Returns:
      A string with the correct format of the reporter
    """
    reporter_match = self.REG_REPORTER.match(line)
    reporter = ''

    if reporter_match:
      reporter = '<%s> PID: %s' % (reporter_match.group('reporter'),
                                   reporter_match.group('pid'))
    else:
      reporter = '<%s>' % line

    return reporter


def ExtractTimestamps(filehandle, zone=pytz.utc,
                      formatter=PipeFormatter(), out=sys.stdout):
  """Parses log files to extract timestamps from them.

  A simple method designed to parse certain Linux log files to extract
  timestamps from them.

  The method will open up a file and try to extract pertinent
  information from it.

  The currently supported log files are:
    + syslog
    + dmesg
    + apache
    + dpkg
    + auth
    + wtmp

  This function verifies that the file exists, or calls the
  functions that verify that the file exists and opens it up
  and calls the function to verify the timezone settings.

  When both conditions are met the function will try to load up
  all the modules and verify the file against them. If it finds one
  that has the capability to parse the file, it will parse it and
  output the results.

  Args:
    filehandle: A filehandle to the file needed to be parsed.
    zone: A string representing the timezone of the particular log file.
    formatter: An output formatter that takes care of outputting the data.
    out: An object to write output to (by default standard out).
  """

  for module_class in MODULE_SET:
    logging.debug('[LogParser] Loaded module: %s', module_class.__name__)

  out.write(formatter.CreateHeader())
  for module_class in MODULE_SET:
    module = module_class()
    logging.debug('[LogParser] Verifying against: %s', module_class.__name__)
    counter = 0
    try:
      # TODO(user): Refactor into a separate object instead of returning
      # an ever expanding tuble in the near future (current release only
      # contains four entries, but that should expand).
      # This should be due before the next release.
      for event in module.Parse(filehandle, zone):
        try:
          out.write(formatter.StartEvent())
          out.write(formatter.AddEvent(event))
          out.write(formatter.EndEvent())
        except NoTimestampFound as err:
          logging.debug('[LogParser] %s', err)
        counter += 1
      logging.debug('[LogParser] %d lines parsed using %s.', counter,
                    module.__class__.__name__)
      break
    except TypeError as error_msg:
      logging.debug('[LogParser] File not verified (%s)', error_msg)
    except KeyboardInterrupt:
      logging.error('[LogParser] Not able to complete the run, successfully '
                    'parsed %d lines before being killed.', counter)
  out.write(formatter.CreateTail())


def VerifyFirstLine(fileobj, regex, parser_name):
  """Verify the structure of the first line of a log file.

  Args:
    fileobj: A file object pointing to the log file.
    regex: A compiled regular expression to check against.
    parser_name: A string containing the name of the parser in question.

  Returns:
    m: A regular expression match object.
    line: The first line read.
  """
  fileobj.seek(0)
  line = fileobj.readline()
  return VerifyRegex(regex, line, parser_name), line


def VerifyRegex(regex, line, name):
  """Verify the structure of a log line with the use of a regular expression.

  A simple function that takes a precompiled regular expression and a line of
  text and compares it against the regular expression.

  If there is a match it will return the result of the match, otherwise it
  will throw an exception.

  Args:
    regex: A compiled regular expression.
    line: A string that needs to be compared against the regular expression.
    name: The name of the module (for logging purposes)

  Returns:
    The object from the matching operation.

  Raises:
    TypeError: If the regular expression does not match it will throw
               a TypeError exception.
  """
  m = regex.match(line)

  if m is None:
    raise TypeError('Incorrect structure for the module: %s' % name)

  return m


def SmartOpenFile(filename):
  """Verify that the file exists and open it if it does.

  This verification routine simply checks if a file exists, and if one does
  it will further determine if the file has been compressed using supported
  compression, which is currently gzip and bzip2. If the file is compressed
  it will open it using the appropriate compression library, otherwise use the
  standard method of opening a file.

  Args:
    filename: A string containing the full path to the filename to be parsed.

  Raises:
    OpenFileError: If it is unable to open a file.

  Returns:
    The filehandle of the file if it exists and can be opened, otherwise
    it will return None
  """
  if not os.path.isfile(filename):
    raise OpenFileError('File does not exist.')

  logging.debug(('[FILE_VERIFY] The file exists.... let\'s move one '
                 'shall we?'))
  try:
    fh = open(filename, 'rb')

    fh.seek(0)
    test_gzip = fh.read(4)

    gzip_int = 0
    try:
      gzip_int = struct.unpack('i', test_gzip)[0] & 0xFFFFFF
    except struct.error:
      raise OpenFileError('Unable to read the first four bytes, too small?')

    if len(test_gzip) == 4 and gzip_int == 559903:
      logging.debug(('[FILE_VERIFY] File GZIP compressed, using GZIP '
                     'library.'))
      fh.close()
      fh = gzip.open(filename, 'rb')
      fh.seek(0)
      test_gzip_read = fh.read(5)

      if not test_gzip_read:
        logging.debug('[FILE_VERIFY] Problem reading from GZIP file.')

    if len(test_gzip) == 4 and struct.unpack('h', test_gzip[0:2])[0] == 23106:
      logging.debug('[FILE_VERIFY] File BZ2 compressed, using BZ2 library')
      fh.close()

      fh = bz2.BZ2File(filename, 'rb')
      fh.seek(0)
      test_bz2_read = fh.read(5)

      if not test_bz2_read:
        logging.debug('[FILE_VERIFY] Problem reading from BZ2 file.')

  except IOError as err:
    raise OpenFileError('An IOError occured: %s' % err)

  return fh

# a constant that defines all modules used by the tool
MODULE_SET = (DmesgParser,
              DpkgParser,
              ApacheParser,
              WtmpParser,
              AuthParser,
              SyslogParser)


if __name__ == '__main__':
  option_parser = optparse.OptionParser()

  option_parser.add_option('-z', '--zone', dest='tzone', action='store',
                           type='string', default='UTC',
                           help=('Define the timezone of the log file. '
                                 '(-z list to get a list of all available'
                                 ' ones)'))
  option_parser.add_option('-o', '--output', dest='output_method',
                           action='store',
                           type='string', default='pipe',
                           help=('Choose which output method to use '
                                 '(-o list to get a list of available ones).'))
  option_parser.add_option('-d', '--debug', dest='debug', action='store_true',
                           help='Turn on debugging for the tool.',
                           default=False)
  option_parser.add_option('-f', '--file', dest='filename', action='store',
                           metavar='FILE', help='The filename to parse.')
  option_parser.add_option('-w', '--write', dest='out_filename', action='store',
                           metavar='FILE',
                           help='The path to a file to store the results in.')

  options, argv = option_parser.parse_args()

  if options.tzone == 'list':
    for timezone in pytz.all_timezones:
      print timezone
    sys.exit(0)

  if options.out_filename:
    if os.path.isfile(options.out_filename):
      logging.warning('[LogParser] Output file exists, open for appending.')
      out_handle = open(options.out_filename, 'aw')
    else:
      out_handle = open(options.out_filename, 'w')
  else:
    out_handle = sys.stdout

  if options.output_method == 'list':
    valid_outputs = [('pipe', 'Default, simple pipe delimited output.'),
                     ('csv', 'Use the l2t_csv format for log2timeline')]
    print 'Possible output:'
    print '-'*80
    for valid_output in valid_outputs:
      print '%-10s: %s' % valid_output
    print '-'*80
    sys.exit(0)
  elif options.output_method == 'csv':
    output_formatter = L2tCsvFormatter()
  else:
    output_formatter = PipeFormatter()

  if options.debug:
    # configure logging level to debug
    logging.basicConfig(level=logging.DEBUG)
    logging.debug('[LogParser] Tool run with debug turned ON.')

  if not options.filename:
    logging.error('[LogParser] Not correctly run (missing file?)')
    sys.exit(1)

  try:
    handle = SmartOpenFile(options.filename)
  except OpenFileError as err:
    logging.error('[LogParser] Unable to open file %s: %s',
                  options.filename, err)
    sys.exit(2)

  try:
    time_zone = pytz.timezone(options.tzone)
  except pytz.UnknownTimeZoneError:
    logging.error(('[LogParser] Time zone was not properly verified,'
                   ' exiting. Please use a valid timezone (%s not'
                   ' valid). Use "-z list" to get a list of all'
                   'available options.'), options.tzone)
    sys.exit(1)
  logging.debug('[LogParser] Time ZONE used (verified) [%s]', time_zone)

  logging.debug(('[LogParser] File (%s) exists and has been '
                 'opened for parsing.'), options.filename)
  ExtractTimestamps(handle, time_zone, output_formatter, out_handle)
  handle.close()
