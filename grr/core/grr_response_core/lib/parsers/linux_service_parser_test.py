#!/usr/bin/env python
"""Unit test for the linux sysctl parser."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app

from grr_response_core.lib.parsers import linux_service_parser
from grr_response_core.lib.parsers import parsers_test_lib
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr.test_lib import artifact_test_lib
from grr.test_lib import test_lib


class LinuxLSBInitParserTest(test_lib.GRRBaseTest):
  """Test parsing of linux /etc/init.d files with LSB headers."""

  def testParseLSBInit(self):
    """Init entries return accurate LinuxServiceInformation values."""
    configs = parsers_test_lib.GenInit("sshd", "OpenBSD Secure Shell server")
    pathspecs, files = artifact_test_lib.GenPathspecFileData(configs)

    parser = linux_service_parser.LinuxLSBInitParser()
    results = list(parser.ParseFiles(None, pathspecs, files))
    self.assertIsInstance(results[0], rdf_client.LinuxServiceInformation)
    result = results[0]
    self.assertEqual("sshd", result.name)
    self.assertEqual("OpenBSD Secure Shell server", result.description)
    self.assertEqual("INIT", result.start_mode)
    self.assertCountEqual([2, 3, 4, 5], result.start_on)
    self.assertCountEqual([1], result.stop_on)
    self.assertCountEqual([
        "umountfs", "umountnfs", "sendsigs", "rsyslog", "sysklogd", "syslog-ng",
        "dsyslog", "inetutils-syslogd"
    ], result.start_after)
    self.assertCountEqual(
        ["rsyslog", "sysklogd", "syslog-ng", "dsyslog", "inetutils-syslogd"],
        result.stop_after)

  def testSkipBadLSBInit(self):
    """Bad Init entries fail gracefully."""
    empty = ""
    snippet = r"""# Provides:             sshd"""
    unfinished = """
      ### BEGIN INIT INFO
      what are you thinking?
    """
    data = {
        "/tmp/empty": empty.encode("utf-8"),
        "/tmp/snippet": snippet.encode("utf-8"),
        "/tmp/unfinished": unfinished.encode("utf-8"),
    }
    pathspecs, files = artifact_test_lib.GenPathspecFileData(data)
    parser = linux_service_parser.LinuxLSBInitParser()
    results = list(parser.ParseFiles(None, pathspecs, files))
    self.assertFalse(results)


class LinuxXinetdParserTest(test_lib.GRRBaseTest):
  """Test parsing of xinetd entries."""

  def testParseXinetd(self):
    """Xinetd entries return accurate LinuxServiceInformation values."""
    configs = parsers_test_lib.GenXinetd("telnet", "yes")
    configs.update(parsers_test_lib.GenXinetd("forwarder", "no"))
    pathspecs, files = artifact_test_lib.GenPathspecFileData(configs)

    parser = linux_service_parser.LinuxXinetdParser()
    results = list(parser.ParseFiles(None, pathspecs, files))
    self.assertLen(results, 2)
    self.assertCountEqual(["forwarder", "telnet"], [r.name for r in results])
    for rslt in results:
      self.assertFalse(rslt.start_on)
      self.assertFalse(rslt.stop_on)
      self.assertFalse(rslt.stop_after)
      if rslt.name == "telnet":
        self.assertFalse(rslt.start_mode)
        self.assertFalse(rslt.start_after)
        self.assertFalse(rslt.starts)
      else:
        self.assertEqual(rslt.start_mode,
                         rdf_client.LinuxServiceInformation.StartMode.XINETD)
        self.assertCountEqual(["xinetd"], list(rslt.start_after))
        self.assertTrue(rslt.starts)


class LinuxSysVInitParserTest(test_lib.GRRBaseTest):
  """Test parsing of sysv startup and shutdown links."""

  results = None

  def setUp(self, *args, **kwargs):
    super(LinuxSysVInitParserTest, self).setUp(*args, **kwargs)
    if self.results is None:
      # Create a fake filesystem.
      dirs = ["/etc", "/etc/rc1.d", "/etc/rc2.d", "/etc/rc6.d", "/etc/rcS.d"]
      d_stat, d_files = parsers_test_lib.GenTestData(
          dirs, [""] * len(dirs), st_mode=16877)
      files = ["/etc/rc.local", "/etc/ignoreme", "/etc/rc2.d/S20ssh"]
      f_stat, f_files = parsers_test_lib.GenTestData(files, [""] * len(files))
      links = [
          "/etc/rc1.d/S90single", "/etc/rc1.d/K20ssh", "/etc/rc1.d/ignore",
          "/etc/rc2.d/S20ntp", "/etc/rc2.d/S30ufw", "/etc/rc6.d/K20ssh",
          "/etc/rcS.d/S20firewall"
      ]
      l_stat, l_files = parsers_test_lib.GenTestData(
          links, [""] * len(links), st_mode=41471)
      stats = d_stat + f_stat + l_stat
      files = d_files + f_files + l_files

      parser = linux_service_parser.LinuxSysVInitParser()
      self.results = list(parser.ParseMultiple(stats, files, None))

  def testParseServices(self):
    """SysV init links return accurate LinuxServiceInformation values."""
    services = {
        s.name: s
        for s in self.results
        if isinstance(s, rdf_client.LinuxServiceInformation)
    }
    self.assertLen(services, 5)
    self.assertCountEqual(["single", "ssh", "ntp", "ufw", "firewall"], services)
    self.assertCountEqual([2], services["ssh"].start_on)
    self.assertCountEqual([1, 6], services["ssh"].stop_on)
    self.assertTrue(services["ssh"].starts)
    self.assertCountEqual([1], services["firewall"].start_on)
    self.assertTrue(services["firewall"].starts)

  def testDetectAnomalies(self):
    anomalies = [a for a in self.results if isinstance(a, rdf_anomaly.Anomaly)]
    self.assertLen(anomalies, 1)
    rslt = anomalies[0]
    self.assertEqual("Startup script is not a symlink.", rslt.explanation)
    self.assertEqual(["/etc/rc2.d/S20ssh"], rslt.finding)
    self.assertEqual("PARSER_ANOMALY", rslt.type)


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  app.run(main)
