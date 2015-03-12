#!/usr/bin/env python
"""Unit test for the linux sysctl parser."""

import StringIO


from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.parsers import linux_sysctl_parser


class ProcSysParserTest(test_lib.GRRBaseTest):
  """Test parsing of linux /proc/sys data."""

  def _GenTestData(self, paths, data):
    stats = []
    files = []
    for path in paths:
      p = rdfvalue.PathSpec(path=path)
      stats.append(rdfvalue.StatEntry(pathspec=p))
    for val in data:
      files.append(StringIO.StringIO(val))
    return stats, files

  def testParseSysctl(self):
    """Sysctl entries return an underscore separated key and 0+ values."""
    parser = linux_sysctl_parser.ProcSysParser()
    paths = ["/proc/sys/net/ipv4/ip_forward", "/proc/sys/kernel/printk"]
    vals = ["0", "3 4 1 3"]
    stats, files = self._GenTestData(paths, vals)
    results = parser.ParseMultiple(stats, files, None)
    self.assertEqual("0", results.net_ipv4_ip_forward)
    self.assertEqual(["3", "4", "1", "3"], results.kernel_printk)


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
