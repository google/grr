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


class LinuxXinetdParserTest(test_lib.GRRBaseTest):
  """Test parsing of xinetd entries."""

  def testParseXinetd(self):
    """Xinetd entries return accurate LinuxServiceInformation values."""
    defaults = """
      defaults
      {
         instances      = 60
         log_type       = SYSLOG     authpriv
         log_on_success = HOST PID
         log_on_failure = HOST
         cps            = 25 30
      }
      includedir /etc/xinetd.d"""
    telnet = """
      service telnet
      {
         flags           = REUSE
         socket_type     = stream
         wait            = no
         user            = root
         server          = /sbin/telnetd
         log_on_failure  += USERID
         disable         = yes
      }

      service forwarder
      {
         disable        = no
         type           = UNLISTED
         socket_type    = stream
         protocol       = tcp
         wait           = no
         redirect       = 192.168.1.1 22
         bind           = 8.8.8.8
         port           = 443
         user           = nobody
      }"""
    paths = ["/etc/xinetd.conf", "/etc/xinetd.d/telnet"]
    vals = [defaults, telnet]
    stats, files = GenTestData(paths, vals)

    parser = linux_service_parser.LinuxXinetdParser()
    results = list(parser.ParseMultiple(stats, files, None))
    self.assertEqual(2, len(results))
    self.assertItemsEqual(["forwarder", "telnet"], [r.name for r in results])
    for rslt in results:
      self.assertFalse(rslt.start_on)
      self.assertFalse(rslt.stop_on)
      self.assertFalse(rslt.stop_after)
      if rslt.name == "telnet":
        self.assertFalse(rslt.start_mode)
        self.assertFalse(rslt.start_after)
      else:
        self.assertEqual("XINETD", str(rslt.start_mode))
        self.assertItemsEqual(["xinetd"], list(rslt.start_after))


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
