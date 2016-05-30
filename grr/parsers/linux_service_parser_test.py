#!/usr/bin/env python
"""Unit test for the linux sysctl parser."""

import StringIO


from grr.lib import flags
from grr.lib import test_lib
from grr.lib.rdfvalues import anomaly as rdf_anomaly
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.parsers import linux_service_parser


def GenTestData(paths, data, st_mode=33188):
  stats = []
  files = []
  for path in paths:
    p = rdf_paths.PathSpec(path=path, pathtype="OS")
    stats.append(rdf_client.StatEntry(pathspec=p, st_mode=st_mode))
  for val in data:
    files.append(StringIO.StringIO(val))
  return stats, files


def GenInit(svc, desc, start=("2", "3", "4", "5"), stop=("1")):
  insserv = r"""
    $local_fs   +umountfs
    $network    +networking
    $remote_fs  $local_fs +umountnfs +sendsigs
    $syslog     +rsyslog +sysklogd +syslog-ng +dsyslog +inetutils-syslogd
    """
  tmpl = r"""
    ### BEGIN INIT INFO
    # Provides:             %s
    # Required-Start:       $remote_fs $syslog
    # Required-Stop:        $syslog
    # Default-Start:        %s
    # Default-Stop:         %s
    # Short-Description:    %s
    ### END INIT INFO
    """ % (svc, " ".join(start), " ".join(stop), desc)
  return {"/etc/insserv.conf": insserv, "/etc/init.d/%s" % svc: tmpl}


def GenXinetd(svc="test", disable="no"):
  defaults = r"""
    defaults
    {
       instances      = 60
       log_type       = SYSLOG     authpriv
       log_on_success = HOST PID
       log_on_failure = HOST
       cps            = 25 30
    }
    includedir /etc/xinetd.d
    """
  tmpl = """
    service %s
    {
       disable         = %s
    }
    """ % (svc, disable)
  return {"/etc/xinetd.conf": defaults, "/etc/xinetd.d/%s" % svc: tmpl}


class LinuxLSBInitParserTest(test_lib.GRRBaseTest):
  """Test parsing of linux /etc/init.d files with LSB headers."""

  def testParseLSBInit(self):
    """Init entries return accurate LinuxServiceInformation values."""
    configs = GenInit("sshd", "OpenBSD Secure Shell server")
    stats, files = GenTestData(configs, configs.values())

    parser = linux_service_parser.LinuxLSBInitParser()
    results = list(parser.ParseMultiple(stats, files, None))
    self.assertIsInstance(results[0], rdf_client.LinuxServiceInformation)
    result = results[0]
    self.assertEqual("sshd", result.name)
    self.assertEqual("OpenBSD Secure Shell server", result.description)
    self.assertEqual("INIT", result.start_mode)
    self.assertItemsEqual([2, 3, 4, 5], result.start_on)
    self.assertItemsEqual([1], result.stop_on)
    self.assertItemsEqual(
        ["umountfs", "umountnfs", "sendsigs", "rsyslog", "sysklogd",
         "syslog-ng", "dsyslog", "inetutils-syslogd"], result.start_after)
    self.assertItemsEqual(
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
    configs = GenXinetd("telnet", "yes")
    configs.update(GenXinetd("forwarder", "no"))
    stats, files = GenTestData(configs, configs.values())

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
        self.assertFalse(rslt.starts)
      else:
        self.assertEqual("XINETD", str(rslt.start_mode))
        self.assertItemsEqual(["xinetd"], list(rslt.start_after))
        self.assertTrue(rslt.starts)


class LinuxSysVInitParserTest(test_lib.GRRBaseTest):
  """Test parsing of sysv startup and shutdown links."""

  results = None

  def setUp(self, *args, **kwargs):
    super(LinuxSysVInitParserTest, self).setUp(*args, **kwargs)
    if self.results is None:
      # Create a fake filesystem.
      dirs = ["/etc", "/etc/rc1.d", "/etc/rc2.d", "/etc/rc6.d", "/etc/rcS.d"]
      d_stat, d_files = GenTestData(dirs, [""] * len(dirs), st_mode=16877)
      files = ["/etc/rc.local", "/etc/ignoreme", "/etc/rc2.d/S20ssh"]
      f_stat, f_files = GenTestData(files, [""] * len(files))
      links = ["/etc/rc1.d/S90single", "/etc/rc1.d/K20ssh", "/etc/rc1.d/ignore",
               "/etc/rc2.d/S20ntp", "/etc/rc2.d/S30ufw", "/etc/rc6.d/K20ssh",
               "/etc/rcS.d/S20firewall"]
      l_stat, l_files = GenTestData(links, [""] * len(links), st_mode=41471)
      stats = d_stat + f_stat + l_stat
      files = d_files + f_files + l_files

      parser = linux_service_parser.LinuxSysVInitParser()
      self.results = list(parser.ParseMultiple(stats, files, None))

  def testParseServices(self):
    """SysV init links return accurate LinuxServiceInformation values."""
    services = {s.name: s
                for s in self.results
                if isinstance(s, rdf_client.LinuxServiceInformation)}
    self.assertEqual(5, len(services))
    self.assertItemsEqual(["single", "ssh", "ntp", "ufw", "firewall"], services)
    self.assertItemsEqual([2], services["ssh"].start_on)
    self.assertItemsEqual([1, 6], services["ssh"].stop_on)
    self.assertTrue(services["ssh"].starts)
    self.assertItemsEqual([1], services["firewall"].start_on)
    self.assertTrue(services["firewall"].starts)

  def testDetectAnomalies(self):
    anomalies = [a for a in self.results if isinstance(a, rdf_anomaly.Anomaly)]
    self.assertEqual(1, len(anomalies))
    rslt = anomalies[0]
    self.assertEqual("Startup script is not a symlink.", rslt.explanation)
    self.assertEqual(["/etc/rc2.d/S20ssh"], rslt.finding)
    self.assertEqual("PARSER_ANOMALY", rslt.type)


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
