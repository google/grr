#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""Unit test for the linux log parser."""



import cStringIO
import os
import pytz

from grr.lib import flags
from grr.lib import test_lib
from grr.parsers import linux_log_parser


# We are intentionally not implementing the class correctly.
# pylint: disable=abstract-method
class NewImplementation(linux_log_parser.LogParser):
  """Tries to implement LogParser but is insufficient.

  That is this implementation does not implement the Parse
  method, which should raise an error.
  """


class LinuxLogParserTest(test_lib.GRRBaseTest):
  """Test parsing of linux log files."""

  def ReturnLines(self, module, filename):
    """Return the lines of output from a parsed file.

    This method takes as an input a file and module and tries to parse
    the file using the module (which extends LogParser).

    It then builds up a list of output entries from the parsed file and
    returns it:
      ((timestamp, source_name, event_type, event_msg), (......))

    Args:
      module: The LogParser module that should be used to parse the file.
      filename: The filename, relative to the base path, to the file that
      should be parsed by the module supplied to the tool.

    Returns:
      A list of entries in the first line of output.
    """
    log_file = os.path.join(self.base_path, filename)
    filehandle = open(log_file, 'rb')

    log_module = module()

    returned_value = []

    for time, source, etype, emsg in log_module.Parse(filehandle, pytz.utc):
      returned_value.append((time, source, etype, emsg))

    return returned_value

  def CheckFirstLine(self, filename, parser, check_timestamp,
                     check_source, check_etype, check_msg):
    """Checks the first line of a log file to see if it is properly parsed.

    Parses a log file according to the parser provided and verifies that
    the output is consistent with what it should be.

    Args:
      filename: The relative path of the file to be tested.
      parser: The module (linux_log_parser) to be used to parse the file.
      check_timestamp: A string (YYYY-mm-dd HH:MM:SS) of the correctly
                       parsed timestamp.
      check_source: A string that should match the correct source.
      check_etype: A string that should match the correct type.
      check_msg: A string that should match to the correctly parsed message.
    """
    full_filename = os.path.join(self.base_path, filename)
    timestamp, source, etype, msg = self.ReturnLines(parser, full_filename)[0]

    if check_timestamp:
      self.assertEquals(timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        check_timestamp)
    self.assertEquals(source, check_source)
    self.assertEquals(etype, check_etype)
    self.assertEquals(msg, check_msg)

  def testL2tHeader(self):
    """Test to see if we get the proper header printed out for a l2t csv."""
    out = linux_log_parser.L2tCsvFormatter()

    self.assertEquals(out.CreateHeader(), ('date,time,timezone,MACB,source,'
                                           'sourcetype,type,user,host,short,'
                                           'desc,version,filename,inode,'
                                           'notes,format,extra\n'))

  def testPipeHeader(self):
    """Test to see if we get a proper header printed out for a pipe output."""
    out = linux_log_parser.PipeFormatter()

    self.assertEquals(out.CreateHeader(), 'time|epoch|source|type|message\n')

  def testL2tEntry(self):
    """Test a single formatter entry for l2t csv file."""
    out = linux_log_parser.L2tCsvFormatter()

    full_path = os.path.join(self.base_path, 'wtmp.1')
    event = self.ReturnLines(linux_log_parser.WtmpParser, full_path)[0]
    line = out.AddEvent(event)

    self.assertEquals(line, ('12/01/2011,17:36:38,UTC,MACB,LOG,UTMP,Logon,'
                             '-,-,User userA [host 10.10.122.1]. PID 20060.'
                             ' Event came from s/12 (id s/12),User userA '
                             '[host 10.10.122.1]. PID 20060. Event came '
                             'from s/12 (id s/12),2,-,0,-,linux_log_parser'
                             ',-\n'))

  def testL2tNoTimestamp(self):
    """Test adding an event to l2t formatter without a timestamp."""
    out = linux_log_parser.L2tCsvFormatter()

    event = (0, 'No Source', 'Entry Written', 'My Message')
    self.assertRaises(linux_log_parser.NoTimestampFound, out.AddEvent,
                      event)

  def testL2tNoEventType(self):
    """Test adding an event to l2t formatter without an event type."""
    out = linux_log_parser.L2tCsvFormatter()

    event = (2314512, 'No Source', None, 'My Message')
    self.assertRaises(linux_log_parser.NoTimestampFound, out.AddEvent,
                      event)

  def testPipeNoTimestamp(self):
    """Test adding an event to a pipe formatter without a timestamp."""
    out = linux_log_parser.PipeFormatter()

    event = (0, 'No Source', 'Entry Written', 'My Message')
    self.assertRaises(linux_log_parser.NoTimestampFound, out.AddEvent,
                      event)

  def testPipeNoEventType(self):
    """Test adding an event to a pipe formatter without an event type."""
    out = linux_log_parser.PipeFormatter()

    event = (2314512, 'No Source', None, 'My Message')
    self.assertRaises(linux_log_parser.NoTimestampFound, out.AddEvent,
                      event)

  def testNewIncompleteImplementation(self):
    """Test creating a new LogParser implementation that is not complete."""
    full_path = os.path.join(self.base_path, 'wtmp.1')
    filehandle = open(full_path, 'rb')
    implementation = NewImplementation()
    self.assertRaises(NotImplementedError, implementation.Parse,
                      filehandle)

  def testPipeEntry(self):
    """Test a single formatter entry for the pipe format."""
    out = linux_log_parser.PipeFormatter()

    full_path = os.path.join(self.base_path, 'wtmp.1')
    event = self.ReturnLines(linux_log_parser.WtmpParser, full_path)[0]
    line = out.AddEvent(event)

    self.assertEquals(line, ('2011-12-01T17:36:38Z|1322760998|UTMP|Logon|'
                             'User userA [host 10.10.122.1]. PID 20060. '
                             'Event came from s/12 (id s/12)\n'))

  def testSmartOpen(self):
    """Test the opening of files."""
    full_path = os.path.join(self.base_path, 'wtmp.1')
    fh = linux_log_parser.SmartOpenFile(full_path)

    self.assertIsInstance(fh, file)

  def testSmartOpenNoFile(self):
    """Test opening a file that does not exist."""
    full_path = os.path.join(self.base_path, 'nofilehere')
    self.assertRaises(linux_log_parser.OpenFileError,
                      linux_log_parser.SmartOpenFile, full_path)

  def testUtmpParsing(self):
    """Test to see if we can parse an utmp file."""
    self.CheckFirstLine('wtmp.1', linux_log_parser.WtmpParser,
                        '2011-12-01 17:36:38',
                        'UTMP',
                        'Logon',
                        ('User userA [host 10.10.122.1]. '
                         'PID 20060. Event came from s/12 (id s/12)'))

  def testSyslogParsing(self):
    """Test to see if we can parse a syslog file."""
    # All those hard coded years are a really ugly hack. We should deprecate
    # the log_parser in favor of Plaso and get rid of those tests asap...
    self.CheckFirstLine('syslog', linux_log_parser.SyslogParser,
                        '2013-01-22 07:52:33',
                        'Syslog',
                        'Entry Written',
                        ('[myhostname.myhost.com] Reporter '
                         '<client> PID: 30840 (INFO No new content.)'))
    full_filename = os.path.join(self.base_path, 'syslog')
    events = self.ReturnLines(linux_log_parser.SyslogParser, full_filename)

    timestamp_1, _, _, msg_1 = events[6]
    self.assertEquals(msg_1, 'No entry')
    self.assertEquals(timestamp_1, 0)

    timestamp_2, _, _, msg_2 = events[9]
    self.assertEquals(msg_2, 'No entry')
    self.assertEquals(timestamp_2, 0)

  def testAuthParsingSyslogFile(self):
    """Test to see if the Auth parser can parse a syslog file."""
    full_filename = os.path.join(self.base_path, 'syslog')
    self.assertRaises(TypeError, self.ReturnLines, linux_log_parser.AuthParser,
                      full_filename)

  def testAuthParsing(self):
    """Test to see if we can parse an auth file."""
    self.CheckFirstLine('auth.log', linux_log_parser.AuthParser,
                        '2013-01-26 19:35:30',
                        'Auth',
                        'Entry Written',
                        ('[myhost.log.mydomain.com] Reporter <sshd> '
                         'PID: 1059 Msg: Postponed keyboard-interactive/pam'
                         ' for dearjohn from 10.10.122.1 port 49567 ssh2 '
                         '[preauth]'))
    full_filename = os.path.join(self.base_path, 'auth.log')
    events = self.ReturnLines(linux_log_parser.AuthParser, full_filename)

    timestamp_1, _, _, msg_1 = events[3]

    self.assertEquals(timestamp_1, 0)
    self.assertEquals(msg_1, 'No entry')

    _, _, _, msg_2 = events[4]

    self.assertEquals(msg_2, 'No entry')

  def testApacheParsing(self):
    """Test to see if we can parse an Apache log file."""
    self.CheckFirstLine('apache_log', linux_log_parser.ApacheParser,
                        '2012-01-08 06:35:26',
                        'Apache',
                        'Entry Written',
                        ('[404] GET /pub/dists/karmic/InRelease HTTP/1.0 '
                         '<UA: Debian APT-HTTP/1.3 (0.8.15.9)>'))

    full_filename = os.path.join(self.base_path, 'apache_log')
    events = self.ReturnLines(linux_log_parser.ApacheParser, full_filename)

    timestamp_1, _, _, msg_1 = events[2]

    self.assertEquals(timestamp_1, 0)
    self.assertEquals(msg_1, ('[304] GET /pub/dists/karmic/Release HTTP/1.0 '
                              '(referer: My Referer) <UA: Debian APT-HTTP/1.3'
                              ' (0.7.25.3)>'))

    _, _, _, msg_2 = events[8]

    self.assertEquals(msg_2, 'No entry')

  def testDmesgParsing(self):
    """Test to see if we can parse a dmesg file."""
    self.CheckFirstLine('dmesg', linux_log_parser.DmesgParser,
                        None,
                        'DMESG',
                        'Entry Written',
                        'Initializing cgroup subsys cpuset')

    full_filename = os.path.join(self.base_path, 'dmesg')
    events = self.ReturnLines(linux_log_parser.DmesgParser, full_filename)

    timestamp, _, _, msg = events[7]

    self.assertEquals(timestamp, 0)
    self.assertEquals(msg, 'No entry')

  def testDpkgParsing(self):
    """Test to see if we can parse a DPKG file."""
    self.CheckFirstLine('dpkg.log', linux_log_parser.DpkgParser,
                        '2012-01-02 03:31:36',
                        'DPKG',
                        'Entry Written',
                        '[startup] packages configure')

  def testFalseDpkgParsing(self):
    """See if we get a correct error with a slightly false DPKG file."""
    full_filename = os.path.join(self.base_path, 'dpkg_false.log')
    self.assertRaises(TypeError, self.ReturnLines, linux_log_parser.DpkgParser,
                      full_filename)

  def RunGenerator(self, generator):
    """Simple method to call to run a generator, see if an error is raised."""
    for _ in generator:
      pass

  def testFalseSyslogParsing(self):
    """See if we get a correct error with a slightly false Syslog file."""
    full_filename = os.path.join(self.base_path, 'syslog_false.gz')
    filehandle = linux_log_parser.SmartOpenFile(full_filename)
    module = linux_log_parser.SyslogParser()

    event_generator = module.Parse(filehandle)
    self.assertRaises(TypeError, list, event_generator)

  def testSyslogParsingGzipYearTest(self):
    """See if we get the year calculation done correctly when compressed."""
    full_filename = os.path.join(self.base_path, 'syslog_compress.gz')
    filehandle = linux_log_parser.SmartOpenFile(full_filename)
    module = linux_log_parser.SyslogParser()

    event_generator = module.Parse(filehandle)
    self.RunGenerator(event_generator)

    self.assertEquals(module.year_use, 2013)

  def testFalseApacheParsing(self):
    """See if we get a correct error with a slightly false Apache file."""
    full_filename = os.path.join(self.base_path, 'apache_false_log')
    self.assertRaises(TypeError, self.ReturnLines,
                      linux_log_parser.ApacheParser, full_filename)

  def testNotCorrectStructureDpkg(self):
    apache_file = os.path.join(self.base_path, 'apache_log')
    self.assertRaises(TypeError, self.ReturnLines,
                      linux_log_parser.DpkgParser, apache_file)

  def testNotCorrectStructureWtmp(self):
    dpkg_file = os.path.join(self.base_path, 'dpkg.log')
    self.assertRaises(TypeError, self.ReturnLines,
                      linux_log_parser.WtmpParser, dpkg_file)

  def testNotCorrectStructureDmesg(self):
    dpkg_file = os.path.join(self.base_path, 'dpkg.log')
    self.assertRaises(TypeError, self.ReturnLines,
                      linux_log_parser.DmesgParser, dpkg_file)

  def testEmptyFile(self):
    empty_file = os.path.join(self.base_path, 'empty_file')
    self.assertRaises(TypeError, self.ReturnLines,
                      linux_log_parser.SyslogParser, empty_file)

  def testExtractTimestamps(self):
    full_filename = os.path.join(self.base_path, 'syslog_compress.gz')
    filehandle = linux_log_parser.SmartOpenFile(full_filename)
    out_format = linux_log_parser.L2tCsvFormatter()
    out_handle = cStringIO.StringIO()
    linux_log_parser.ExtractTimestamps(filehandle, pytz.utc, out_format,
                                       out_handle)

    self.assertEquals(out_handle.getvalue(), ("""\
date,time,timezone,MACB,source,sourcetype,type,user,host,short,desc,version,\
filename,inode,notes,format,extra
01/22/2013,07:52:33,UTC,MACB,LOG,Syslog,Entry Written,-,-,\
[myhostname.myhost.com] Reporter <client> PID: 30840 (INFO \
No new content.),[myhostname.myhost.com] Reporter <client> PID: \
30840 (INFO No new content.),2,-,0,-,linux_log_parser,-
01/22/2013,07:52:33,UTC,MACB,LOG,Syslog,Entry Written,-,-,\
[myhostname.myhost.com] Reporter <client> PID: 30840 (INFO No \
change in [/etc/netgroup]. Done),[myhostname.myhost.com] Reporter \
<client> PID: 30840 (INFO No change in [/etc/netgroup]. Done),2,-\
,0,-,linux_log_parser,-
"""))


def main(args):
  test_lib.main(args)

if __name__ == '__main__':
  flags.StartMain(main)
