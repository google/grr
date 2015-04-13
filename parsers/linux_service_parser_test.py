#!/usr/bin/env python
"""Unit test for the linux sysctl parser."""

import StringIO


from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.parsers import linux_service_parser


def GenTestData(paths, data):
  stats = []
  files = []
  for path in paths:
    p = rdfvalue.PathSpec(path=path)
    stats.append(rdfvalue.StatEntry(pathspec=p))
  for val in data:
    files.append(StringIO.StringIO(val))
  return stats, files


class LinuxLSBInitParserTest(test_lib.GRRBaseTest):
  """Test parsing of linux /etc/init.d files with LSB headers."""

  def testParseLSBInit(self):
    """Init entries return accurate LinuxServiceInformation values."""
    sshd_init = r"""
      ### BEGIN INIT INFO
      # Provides:             sshd
      # Required-Start:       $remote_fs $syslog
      # Required-Stop:        $syslog
      # Default-Start:        2 3 4 5
      # Default-Stop:         1
      # Short-Description:    OpenBSD Secure Shell server
      ### END INIT INFO"""
    insserv_conf = r"""
      $local_fs   +umountfs
      $network    +networking
      $remote_fs  $local_fs +umountnfs +sendsigs
      $syslog     +rsyslog +sysklogd +syslog-ng +dsyslog +inetutils-syslogd"""
    paths = ["/etc/init.d/sshd", "/etc/insserv.conf"]
    vals = [sshd_init, insserv_conf]
    stats, files = GenTestData(paths, vals)

    parser = linux_service_parser.LinuxLSBInitParser()
    results = list(parser.ParseMultiple(stats, files, None))
    self.assertIsInstance(results[0], rdfvalue.LinuxServiceInformation)
    result = results[0]
    self.assertEqual("sshd", result.name)
    self.assertEqual("OpenBSD Secure Shell server", result.description)
    self.assertEqual("INIT", result.start_mode)
    self.assertItemsEqual([2, 3, 4, 5], result.start_on)
    self.assertItemsEqual([1], result.stop_on)
    self.assertItemsEqual(["umountfs", "umountnfs", "sendsigs", "rsyslog",
                           "sysklogd", "syslog-ng", "dsyslog",
                           "inetutils-syslogd"], result.start_after)
    self.assertItemsEqual(["rsyslog", "sysklogd", "syslog-ng", "dsyslog",
                           "inetutils-syslogd"], result.stop_after)

  def testSkipBadLSBInit(self):
    """Bad Init entries fail gracefully."""
    empty = ""
    snippet = r"""# Provides:             sshd"""
    unfinished = """
      ### BEGIN INIT INFO
      what are you thinking?
    """
    paths = ["/tmp/empty", "/tmp/snippet", "/tmp/unfinished"]
    vals = [empty, snippet, unfinished]
    stats, files = GenTestData(paths, vals)
    parser = linux_service_parser.LinuxLSBInitParser()
    results = list(parser.ParseMultiple(stats, files, None))
    self.assertFalse(results)


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
