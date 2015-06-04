#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Unit test for config files."""
import StringIO


from grr.lib import flags
from grr.lib import test_lib
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import config_file as rdf_config_file
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.parsers import config_file


CFG = """
# A comment.
Protocol 2  # Another comment.
Ciphers aes128-ctr,aes256-ctr,aes128-cbc,aes256-cbc
ServerKeyBits 768
Port 22
Port 2222,10222

# Make life easy for root. It's hard running a server.
Match User root
  PermitRootLogin yes

# Oh yeah, this is an excellent way to protect that root account.
Match Address 192.168.3.12
  PermitRootLogin no
  Protocol 1  # Not a valid match group entry.
"""


class SshdConfigTest(test_lib.GRRBaseTest):
  """Test parsing of an sshd configuration."""

  def GetConfig(self):
    """Read in the test configuration file."""
    parser = config_file.SshdConfigParser()
    results = list(parser.Parse(None, StringIO.StringIO(CFG), None))
    self.assertEqual(1, len(results))
    return results[0]

  def testParseConfig(self):
    """Ensure we can extract sshd settings."""
    result = self.GetConfig()
    self.assertTrue(isinstance(result, rdf_config_file.SshdConfig))
    self.assertItemsEqual([2], result.config.protocol)
    expect = ["aes128-ctr", "aes256-ctr", "aes128-cbc", "aes256-cbc"]
    self.assertItemsEqual(expect, result.config.ciphers)

  def testFindNumericValues(self):
    """Keywords with numeric settings are converted to integers."""
    result = self.GetConfig()
    self.assertEqual(768, result.config.serverkeybits)
    self.assertItemsEqual([22, 2222, 10222], result.config.port)

  def testParseMatchGroups(self):
    """Match groups are added to separate sections."""
    result = self.GetConfig()
    # Multiple Match groups found.
    self.assertEqual(2, len(result.matches))
    # Config options set per Match group.
    block_1, block_2 = result.matches
    self.assertEqual("user root", block_1.criterion)
    self.assertEqual("address 192.168.3.12", block_2.criterion)
    self.assertEqual(True, block_1.config.permitrootlogin)
    self.assertEqual(False, block_2.config.permitrootlogin)
    self.assertFalse(block_1.config.protocol)


class FieldParserTests(test_lib.GRRBaseTest):
  """Test the field parser."""

  def testParser(self):
    test_data = r"""
    each of these words:should;be \
        fields # but not these ones \n, or \ these.
    this  should be     another entry "with this quoted text as one field"
    'an entry'with" only two" fields ;; and not this comment.
    """
    expected = [["each", "of", "these", "words", "should", "be", "fields"],
                ["this", "should", "be", "another", "entry",
                 "with this quoted text as one field"],
                ["an entrywith only two", "fields"]]
    cfg = config_file.FieldParser(sep=["[ \t\f\v]+", ":", ";"],
                                  comments=["#", ";;"])
    results = cfg.ParseEntries(test_data)
    for i, expect in enumerate(expected):
      self.assertItemsEqual(expect, results[i])

  def testNoFinalTerminator(self):
    test_data = "you forgot a newline"
    expected = [["you", "forgot", "a", "newline"]]
    cfg = config_file.FieldParser()
    results = cfg.ParseEntries(test_data)
    for i, expect in enumerate(expected):
      self.assertItemsEqual(expect, results[i])

  def testWhitespaceDoesntNukeNewline(self):
    test_data = "trailing spaces     \nno trailing spaces\n"
    expected = [["trailing", "spaces"], ["no", "trailing", "spaces"]]
    results = config_file.FieldParser().ParseEntries(test_data)
    for i, expect in enumerate(expected):
      self.assertItemsEqual(expect, results[i])
    expected = [["trailing", "spaces", "no", "trailing", "spaces"]]
    results = config_file.FieldParser(sep=r"\s+").ParseEntries(test_data)
    for i, expect in enumerate(expected):
      self.assertItemsEqual(expect, results[i])


class KeyValueParserTests(test_lib.GRRBaseTest):
  """Test the field parser."""

  def testParser(self):
    test_data = r"""
    key1 = a list of \
      fields # but not \n this, or \ this.

    # Nothing here.
    key 2:another entry
    = # Bad line
    'a key'with" no" value field ;; and not this comment.
    """
    expected = [{"key1": ["a", "list", "of", "fields"]},
                {"key 2": ["another", "entry"]},
                {"a keywith no value field": []}]
    cfg = config_file.KeyValueParser(kv_sep=["=", ":"], comments=["#", ";;"])
    results = cfg.ParseEntries(test_data)
    for i, expect in enumerate(expected):
      self.assertDictEqual(expect, results[i])


class NfsExportParserTests(test_lib.GRRBaseTest):
  """Test the NFS exports parser."""

  def testParseNfsExportFile(self):
    test_data = r"""
    /path/to/foo -rw,sync host1(ro) host2
    /path/to/bar *.example.org(all_squash,ro) \
        192.168.1.0/24 (rw) # Mistake here - space makes this default.
    """
    exports = StringIO.StringIO(test_data)
    config = config_file.NfsExportsParser()
    results = list(config.Parse(None, exports, None))
    self.assertEqual("/path/to/foo", results[0].share)
    self.assertItemsEqual(["rw", "sync"], results[0].defaults)
    self.assertEqual("host1", results[0].clients[0].host)
    self.assertItemsEqual(["ro"], results[0].clients[0].options)
    self.assertEqual("host2", results[0].clients[1].host)
    self.assertItemsEqual([], results[0].clients[1].options)
    self.assertEqual("/path/to/bar", results[1].share)
    self.assertItemsEqual(["rw"], results[1].defaults)
    self.assertEqual("*.example.org", results[1].clients[0].host)
    self.assertItemsEqual(["all_squash", "ro"], results[1].clients[0].options)
    self.assertEqual("192.168.1.0/24", results[1].clients[1].host)
    self.assertItemsEqual([], results[1].clients[1].options)


class MtabParserTests(test_lib.GRRBaseTest):
  """Test the mtab and proc/mounts parser."""

  def testParseMountData(self):
    test_data = r"""
    rootfs / rootfs rw 0 0
    arnie@host.example.org:/users/arnie /home/arnie/remote fuse.sshfs rw,nosuid,nodev,max_read=65536 0 0
    """
    exports = StringIO.StringIO(test_data)
    config = config_file.MtabParser()
    results = list(config.Parse(None, exports, None))
    self.assertEqual("rootfs", results[0].device)
    self.assertEqual("/", results[0].mount_point)
    self.assertEqual("rootfs", results[0].type)
    self.assertTrue(results[0].options.rw)
    self.assertFalse(results[0].options.ro)

    self.assertEqual("arnie@host.example.org:/users/arnie", results[1].device)
    self.assertEqual("/home/arnie/remote", results[1].mount_point)
    self.assertEqual("fuse.sshfs", results[1].type)
    self.assertTrue(results[1].options.rw)
    self.assertTrue(results[1].options.nosuid)
    self.assertTrue(results[1].options.nodev)
    self.assertEqual(["65536"], results[1].options.max_read)


class RsyslogParserTests(test_lib.GRRBaseTest):
  """Test the rsyslog parser."""

  def testParseRsyslog(self):
    test_data = r"""
    $SomeDirective
    daemon.* @@tcp.example.com.:514;RSYSLOG_ForwardFormat
    syslog.debug,info @udp.example.com.:514;RSYSLOG_ForwardFormat
    kern.* |/var/log/pipe
    news,uucp.* ~
    user.* ^/usr/bin/log2cowsay
    *.* /var/log/messages
    """
    log_conf = StringIO.StringIO(test_data)
    config = config_file.RsyslogParser()
    results = list(config.ParseMultiple([None], [log_conf], None))[0]
    tcp, udp, pipe, null, script, fs = [target for target in results.targets]

    self.assertEqual("daemon", tcp.facility)
    self.assertEqual("*", tcp.priority)
    self.assertEqual("TCP", tcp.transport)
    self.assertEqual("tcp.example.com.:514", tcp.destination)

    self.assertEqual("syslog", udp.facility)
    self.assertEqual("debug,info", udp.priority)
    self.assertEqual("UDP", udp.transport)
    self.assertEqual("udp.example.com.:514", udp.destination)

    self.assertEqual("kern", pipe.facility)
    self.assertEqual("*", pipe.priority)
    self.assertEqual("PIPE", pipe.transport)
    self.assertEqual("/var/log/pipe", pipe.destination)

    self.assertEqual("news,uucp", null.facility)
    self.assertEqual("*", null.priority)
    self.assertEqual("NULL", null.transport)
    self.assertFalse(null.destination)

    self.assertEqual("user", script.facility)
    self.assertEqual("*", script.priority)
    self.assertEqual("SCRIPT", script.transport)
    self.assertEqual("/usr/bin/log2cowsay", script.destination)

    self.assertEqual("*", fs.facility)
    self.assertEqual("*", fs.priority)
    self.assertEqual("FILE", fs.transport)
    self.assertEqual("/var/log/messages", fs.destination)


class APTPackageSourceParserTests(test_lib.GRRBaseTest):
  """Test the APT package source lists parser."""

  def testPackageSourceData(self):
    test_data = r"""
    # Security updates
    deb  http://security.debian.org/ wheezy/updates main contrib non-free
    deb-src  [arch=amd64,trusted=yes]    ftp://security.debian.org/ wheezy/updates main contrib non-free

    ## Random comment

    # Different transport protocols below
    deb  ssh://ftp.debian.org/debian wheezy main contrib non-free
    deb-src    file:/mnt/deb-sources-files/ wheezy main contrib non-free

    # correct - referencing root file system
    deb-src file:/
    # incorrect
    deb-src http://

    # Bad lines below - these shouldn't get any URIs back
    deb
    deb-src   [arch=i386]
    deb-src abcdefghijklmnopqrstuvwxyz
    """
    file_obj = StringIO.StringIO(test_data)
    pathspec = rdf_paths.PathSpec(path="/etc/apt/sources.list")
    stat = rdf_client.StatEntry(pathspec=pathspec)
    parser = config_file.APTPackageSourceParser()
    results = list(parser.Parse(stat, file_obj, None))

    result = [d for d in results if isinstance(d,
                                               rdf_protodict.AttributedDict)][0]

    self.assertEqual("/etc/apt/sources.list", result.filename)
    self.assertEqual(5, len(result.uris))

    self.assertEqual("http", result.uris[0].transport)
    self.assertEqual("security.debian.org", result.uris[0].host)
    self.assertEqual("/", result.uris[0].path)

    self.assertEqual("ftp", result.uris[1].transport)
    self.assertEqual("security.debian.org", result.uris[1].host)
    self.assertEqual("/", result.uris[1].path)

    self.assertEqual("ssh", result.uris[2].transport)
    self.assertEqual("ftp.debian.org", result.uris[2].host)
    self.assertEqual("/debian", result.uris[2].path)

    self.assertEqual("file", result.uris[3].transport)
    self.assertEqual("", result.uris[3].host)
    self.assertEqual("/mnt/deb-sources-files/", result.uris[3].path)

    self.assertEqual("file", result.uris[4].transport)
    self.assertEqual("", result.uris[4].host)
    self.assertEqual("/", result.uris[4].path)

  def testEmptySourceData(self):
    test_data = r"""


    # comment 1
    # deb http://security.debian.org/ wheezy/updates main contrib non-free

    # comment 2

    """

    file_obj = StringIO.StringIO(test_data)
    pathspec = rdf_paths.PathSpec(path="/etc/apt/sources.list.d/test.list")
    stat = rdf_client.StatEntry(pathspec=pathspec)
    parser = config_file.APTPackageSourceParser()
    results = list(parser.Parse(stat, file_obj, None))

    result = [d for d in results if isinstance(d,
                                               rdf_protodict.AttributedDict)][0]

    self.assertEqual("/etc/apt/sources.list.d/test.list", result.filename)
    self.assertEqual(0, len(result.uris))

  def testRFC822StyleSourceDataParser(self):
    """Test source list formated as per rfc822 style."""

    test_data = r"""
    # comment comment comment
    Types: deb deb-src
    URIs:    http://example.com/debian
      http://1.example.com/debian1
      http://2.example.com/debian2

      http://willdetect.example.com/debian-strange
    URIs :  ftp://3.example.com/debian3
      http://4.example.com/debian4
      blahblahblahblahblahlbha
      http://willdetect2.example.com/debian-w2

      http://willdetect3.example.com/debian-w3
    URI :  ssh://5.example.com/debian5
    Suites: stable testing
    Sections: component1 component2
    Description: short
     long long long
    [option1]: [option1-value]

    deb-src [arch=amd64,trusted=yes] ftp://security.debian.org/ wheezy/updates main contrib non-free

    # comment comment comment
    Types: deb
    URI : ftp://another.example.com/debian2
    Suites: experimental
    Sections: component1 component2
    Enabled: no
    Description: http://debian.org
     This URL shouldn't be picked up by the parser
    [option1]: [option1-value]

    """
    file_obj = StringIO.StringIO(test_data)
    pathspec = rdf_paths.PathSpec(path="/etc/apt/sources.list.d/rfc822.list")
    stat = rdf_client.StatEntry(pathspec=pathspec)
    parser = config_file.APTPackageSourceParser()
    results = list(parser.Parse(stat, file_obj, None))

    result = [d for d in results if isinstance(d,
                                               rdf_protodict.AttributedDict)][0]

    self.assertEqual("/etc/apt/sources.list.d/rfc822.list", result.filename)
    self.assertEqual(11, len(result.uris))

    self.assertEqual("ftp", result.uris[0].transport)
    self.assertEqual("security.debian.org", result.uris[0].host)
    self.assertEqual("/", result.uris[0].path)

    self.assertEqual("http", result.uris[1].transport)
    self.assertEqual("example.com", result.uris[1].host)
    self.assertEqual("/debian", result.uris[1].path)

    self.assertEqual("http", result.uris[2].transport)
    self.assertEqual("1.example.com", result.uris[2].host)
    self.assertEqual("/debian1", result.uris[2].path)

    self.assertEqual("http", result.uris[3].transport)
    self.assertEqual("2.example.com", result.uris[3].host)
    self.assertEqual("/debian2", result.uris[3].path)

    self.assertEqual("http", result.uris[4].transport)
    self.assertEqual("willdetect.example.com", result.uris[4].host)
    self.assertEqual("/debian-strange", result.uris[4].path)

    self.assertEqual("ftp", result.uris[5].transport)
    self.assertEqual("3.example.com", result.uris[5].host)
    self.assertEqual("/debian3", result.uris[5].path)

    self.assertEqual("http", result.uris[6].transport)
    self.assertEqual("4.example.com", result.uris[6].host)
    self.assertEqual("/debian4", result.uris[6].path)

    self.assertEqual("http", result.uris[7].transport)
    self.assertEqual("willdetect2.example.com", result.uris[7].host)
    self.assertEqual("/debian-w2", result.uris[7].path)

    self.assertEqual("http", result.uris[8].transport)
    self.assertEqual("willdetect3.example.com", result.uris[8].host)
    self.assertEqual("/debian-w3", result.uris[8].path)

    self.assertEqual("ssh", result.uris[9].transport)
    self.assertEqual("5.example.com", result.uris[9].host)
    self.assertEqual("/debian5", result.uris[9].path)

    self.assertEqual("ftp", result.uris[10].transport)
    self.assertEqual("another.example.com", result.uris[10].host)
    self.assertEqual("/debian2", result.uris[10].path)


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
