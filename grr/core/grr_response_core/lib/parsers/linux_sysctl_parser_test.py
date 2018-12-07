#!/usr/bin/env python
"""Unit test for the linux sysctl parser."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io


from grr_response_core.lib import flags
from grr_response_core.lib import utils
from grr_response_core.lib.parsers import linux_sysctl_parser
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr.test_lib import test_lib


class ProcSysParserTest(test_lib.GRRBaseTest):
  """Test parsing of linux /proc/sys data."""

  def _GenTestData(self, paths, data):
    stats = []
    files = []
    for path in paths:
      p = rdf_paths.PathSpec(path=path)
      stats.append(rdf_client_fs.StatEntry(pathspec=p))
    for val in data:
      files.append(io.BytesIO(utils.SmartStr(val)))
    return stats, files

  def testParseSysctl(self):
    """Sysctl entries return an underscore separated key and 0+ values."""
    parser = linux_sysctl_parser.ProcSysParser()
    paths = ["/proc/sys/net/ipv4/ip_forward", "/proc/sys/kernel/printk"]
    vals = ["0", "3 4 1 3"]
    stats, files = self._GenTestData(paths, vals)
    results = parser.ParseMultiple(stats, files, None)
    self.assertLen(results, 1)
    self.assertIsInstance(results[0], rdf_protodict.AttributedDict)
    self.assertEqual("0", results[0].net_ipv4_ip_forward)
    self.assertEqual(["3", "4", "1", "3"], results[0].kernel_printk)


class SysctlCmdParserTest(test_lib.GRRBaseTest):
  """Test parsing of linux sysctl -a command output."""

  def testParseSysctl(self):
    """Sysctl entries return an underscore separated key and 0+ values."""
    content = """
      kernel.printk = 3       4       1       3
      net.ipv4.ip_forward = 0
    """
    parser = linux_sysctl_parser.SysctlCmdParser()
    results = parser.Parse("/sbin/sysctl", ["-a"], content, "", 0, 5, None)
    self.assertLen(results, 1)
    self.assertIsInstance(results[0], rdf_protodict.AttributedDict)
    self.assertEqual("0", results[0].net_ipv4_ip_forward)
    self.assertEqual(["3", "4", "1", "3"], results[0].kernel_printk)


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
