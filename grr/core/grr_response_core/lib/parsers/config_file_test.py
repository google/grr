#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Unit test for config files."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io


from future.utils import iterkeys

from grr_response_core.lib import flags
from grr_response_core.lib.parsers import config_file
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import config_file as rdf_config_file
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr.test_lib import test_lib

CFG = b"""
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
    results = list(parser.Parse(None, io.BytesIO(CFG), None))
    self.assertLen(results, 1)
    return results[0]

  def testParseConfig(self):
    """Ensure we can extract sshd settings."""
    result = self.GetConfig()
    self.assertIsInstance(result, rdf_config_file.SshdConfig)
    self.assertCountEqual([2], result.config.protocol)
    expect = ["aes128-ctr", "aes256-ctr", "aes128-cbc", "aes256-cbc"]
    self.assertCountEqual(expect, result.config.ciphers)

  def testFindNumericValues(self):
    """Keywords with numeric settings are converted to integers."""
    result = self.GetConfig()
    self.assertEqual(768, result.config.serverkeybits)
    self.assertCountEqual([22, 2222, 10222], result.config.port)

  def testParseMatchGroups(self):
    """Match groups are added to separate sections."""
    result = self.GetConfig()
    # Multiple Match groups found.
    self.assertLen(result.matches, 2)
    # Config options set per Match group.
    block_1, block_2 = result.matches
    self.assertEqual("user root", block_1.criterion)
    self.assertEqual("address 192.168.3.12", block_2.criterion)
    self.assertEqual("yes", block_1.config.permitrootlogin)
    self.assertEqual("no", block_2.config.permitrootlogin)
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
                [
                    "this", "should", "be", "another", "entry",
                    "with this quoted text as one field"
                ], ["an entrywith only two", "fields"]]
    cfg = config_file.FieldParser(
        sep=["[ \t\f\v]+", ":", ";"], comments=["#", ";;"])
    results = cfg.ParseEntries(test_data)
    for i, expect in enumerate(expected):
      self.assertCountEqual(expect, results[i])

  def testNoFinalTerminator(self):
    test_data = "you forgot a newline"
    expected = [["you", "forgot", "a", "newline"]]
    cfg = config_file.FieldParser()
    results = cfg.ParseEntries(test_data)
    for i, expect in enumerate(expected):
      self.assertCountEqual(expect, results[i])

  def testWhitespaceDoesntNukeNewline(self):
    test_data = "trailing spaces     \nno trailing spaces\n"
    expected = [["trailing", "spaces"], ["no", "trailing", "spaces"]]
    results = config_file.FieldParser().ParseEntries(test_data)
    for i, expect in enumerate(expected):
      self.assertCountEqual(expect, results[i])
    expected = [["trailing", "spaces", "no", "trailing", "spaces"]]
    results = config_file.FieldParser(sep=r"\s+").ParseEntries(test_data)
    for i, expect in enumerate(expected):
      self.assertCountEqual(expect, results[i])


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
    expected = [{
        "key1": ["a", "list", "of", "fields"]
    }, {
        "key 2": ["another", "entry"]
    }, {
        "a keywith no value field": []
    }]
    cfg = config_file.KeyValueParser(kv_sep=["=", ":"], comments=["#", ";;"])
    results = cfg.ParseEntries(test_data)
    for i, expect in enumerate(expected):
      self.assertDictEqual(expect, results[i])


class NfsExportParserTests(test_lib.GRRBaseTest):
  """Test the NFS exports parser."""

  def testParseNfsExportFile(self):
    test_data = br"""
    /path/to/foo -rw,sync host1(ro) host2
    /path/to/bar *.example.org(all_squash,ro) \
        192.168.1.0/24 (rw) # Mistake here - space makes this default.
    """
    exports = io.BytesIO(test_data)
    parser = config_file.NfsExportsParser()
    results = list(parser.Parse(None, exports, None))
    self.assertEqual("/path/to/foo", results[0].share)
    self.assertCountEqual(["rw", "sync"], results[0].defaults)
    self.assertEqual("host1", results[0].clients[0].host)
    self.assertCountEqual(["ro"], results[0].clients[0].options)
    self.assertEqual("host2", results[0].clients[1].host)
    self.assertCountEqual([], results[0].clients[1].options)
    self.assertEqual("/path/to/bar", results[1].share)
    self.assertCountEqual(["rw"], results[1].defaults)
    self.assertEqual("*.example.org", results[1].clients[0].host)
    self.assertCountEqual(["all_squash", "ro"], results[1].clients[0].options)
    self.assertEqual("192.168.1.0/24", results[1].clients[1].host)
    self.assertCountEqual([], results[1].clients[1].options)


class MtabParserTests(test_lib.GRRBaseTest):
  """Test the mtab and proc/mounts parser."""

  def testParseMountData(self):
    test_data = br"""
    rootfs / rootfs rw 0 0
    arnie@host.example.org:/users/arnie /home/arnie/remote fuse.sshfs rw,nosuid,nodev,max_read=65536 0 0
    /dev/sr0 /media/USB\040Drive vfat ro,nosuid,nodev
    """
    exports = io.BytesIO(test_data)
    parser = config_file.MtabParser()
    results = list(parser.Parse(None, exports, None))
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

    self.assertEqual("/dev/sr0", results[2].device)
    self.assertEqual("/media/USB Drive", results[2].mount_point)
    self.assertEqual("vfat", results[2].type)
    self.assertTrue(results[2].options.ro)
    self.assertTrue(results[2].options.nosuid)
    self.assertTrue(results[2].options.nodev)


class MountCmdTests(test_lib.GRRBaseTest):
  """Test the mount command parser."""

  def testParseMountData(self):
    test_data = r"""
    rootfs on / type rootfs (rw)
    arnie@host.example.org:/users/arnie on /home/arnie/remote type fuse.sshfs (rw,nosuid,nodev,max_read=65536)
    /dev/sr0 on /media/USB Drive type vfat (ro,nosuid,nodev)
    """
    parser = config_file.MountCmdParser()
    results = list(parser.Parse("/bin/mount", [], test_data, "", 0, 5, None))
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

    self.assertEqual("/dev/sr0", results[2].device)
    self.assertEqual("/media/USB Drive", results[2].mount_point)
    self.assertEqual("vfat", results[2].type)
    self.assertTrue(results[2].options.ro)
    self.assertTrue(results[2].options.nosuid)
    self.assertTrue(results[2].options.nodev)


class RsyslogParserTests(test_lib.GRRBaseTest):
  """Test the rsyslog parser."""

  def testParseRsyslog(self):
    test_data = br"""
    $SomeDirective
    daemon.* @@tcp.example.com.:514;RSYSLOG_ForwardFormat
    syslog.debug,info @udp.example.com.:514;RSYSLOG_ForwardFormat
    kern.* |/var/log/pipe
    news,uucp.* ~
    user.* ^/usr/bin/log2cowsay
    *.* /var/log/messages
    *.emerg    *
    mail.*  -/var/log/maillog
    """
    log_conf = io.BytesIO(test_data)
    parser = config_file.RsyslogParser()
    results = list(parser.ParseMultiple([None], [log_conf], None))
    self.assertLen(results, 1)
    tcp, udp, pipe, null, script, fs, wall, async_fs = [
        target for target in results[0].targets
    ]

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
    self.assertEqual("NONE", null.transport)
    self.assertFalse(null.destination)

    self.assertEqual("user", script.facility)
    self.assertEqual("*", script.priority)
    self.assertEqual("SCRIPT", script.transport)
    self.assertEqual("/usr/bin/log2cowsay", script.destination)

    self.assertEqual("*", fs.facility)
    self.assertEqual("*", fs.priority)
    self.assertEqual("FILE", fs.transport)
    self.assertEqual("/var/log/messages", fs.destination)

    self.assertEqual("*", wall.facility)
    self.assertEqual("emerg", wall.priority)
    self.assertEqual("WALL", wall.transport)
    self.assertEqual("*", wall.destination)

    self.assertEqual("mail", async_fs.facility)
    self.assertEqual("*", async_fs.priority)
    self.assertEqual("FILE", async_fs.transport)
    self.assertEqual("/var/log/maillog", async_fs.destination)


class APTPackageSourceParserTests(test_lib.GRRBaseTest):
  """Test the APT package source lists parser."""

  def testPackageSourceData(self):
    test_data = br"""
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
    file_obj = io.BytesIO(test_data)
    pathspec = rdf_paths.PathSpec(path="/etc/apt/sources.list")
    stat = rdf_client_fs.StatEntry(pathspec=pathspec)
    parser = config_file.APTPackageSourceParser()
    results = list(parser.Parse(stat, file_obj, None))

    result = [
        d for d in results if isinstance(d, rdf_protodict.AttributedDict)
    ][0]

    self.assertEqual("/etc/apt/sources.list", result.filename)
    self.assertLen(result.uris, 5)

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
    test_data = (b"# comment 1\n"
                 b"# deb http://security.debian.org/ wheezy/updates main\n"
                 b"URI :\n"
                 b"URI:\n"
                 b"# Trailing whitespace on purpose\n"
                 b"URI:          \n"
                 b"\n"
                 b"URIs :\n"
                 b"URIs:\n"
                 b"# Trailing whitespace on purpose\n"
                 b"URIs:        \n"
                 b"# comment 2\n")

    file_obj = io.BytesIO(test_data)
    pathspec = rdf_paths.PathSpec(path="/etc/apt/sources.list.d/test.list")
    stat = rdf_client_fs.StatEntry(pathspec=pathspec)
    parser = config_file.APTPackageSourceParser()
    results = list(parser.Parse(stat, file_obj, None))

    result = [
        d for d in results if isinstance(d, rdf_protodict.AttributedDict)
    ][0]

    self.assertEqual("/etc/apt/sources.list.d/test.list", result.filename)
    self.assertEmpty(result.uris)

  def testRFC822StyleSourceDataParser(self):
    """Test source list formated as per rfc822 style."""

    test_data = br"""
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
    URI
    URI :  ssh://5.example.com/debian5
    Suites: stable testing
    Sections: component1 component2
    Description: short
     long long long
    [option1]: [option1-value]

    deb-src [arch=amd64,trusted=yes] ftp://security.debian.org/ wheezy/updates main contrib non-free

    # comment comment comment
    Types: deb
    URI:ftp://another.example.com/debian2
    Suites: experimental
    Sections: component1 component2
    Enabled: no
    Description: http://debian.org
     This URL shouldn't be picked up by the parser
    [option1]: [option1-value]

    """
    file_obj = io.BytesIO(test_data)
    pathspec = rdf_paths.PathSpec(path="/etc/apt/sources.list.d/rfc822.list")
    stat = rdf_client_fs.StatEntry(pathspec=pathspec)
    parser = config_file.APTPackageSourceParser()
    results = list(parser.Parse(stat, file_obj, None))

    result = [
        d for d in results if isinstance(d, rdf_protodict.AttributedDict)
    ][0]

    self.assertEqual("/etc/apt/sources.list.d/rfc822.list", result.filename)
    self.assertLen(result.uris, 11)

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


class YumPackageSourceParserTests(test_lib.GRRBaseTest):
  """Test the Yum package source lists parser."""

  def testPackageSourceData(self):
    test_data = br"""
    # comment 1
    [centosdvdiso]
    name=CentOS DVD ISO
    baseurl=file:///mnt
    http://mirror1.centos.org/CentOS/6/os/i386/
    baseurl =ssh://mirror2.centos.org/CentOS/6/os/i386/
    enabled=1
    gpgcheck=1
    gpgkey=file:///mnt/RPM-GPG-KEY-CentOS-6

    # comment2
    [examplerepo]
    name=Example Repository
    baseurl = https://mirror3.centos.org/CentOS/6/os/i386/
    enabled=1
    gpgcheck=1
    gpgkey=http://mirror.centos.org/CentOS/6/os/i386/RPM-GPG-KEY-CentOS-6

    """
    file_obj = io.BytesIO(test_data)
    pathspec = rdf_paths.PathSpec(path="/etc/yum.repos.d/test1.repo")
    stat = rdf_client_fs.StatEntry(pathspec=pathspec)
    parser = config_file.YumPackageSourceParser()
    results = list(parser.Parse(stat, file_obj, None))

    result = [
        d for d in results if isinstance(d, rdf_protodict.AttributedDict)
    ][0]

    self.assertEqual("/etc/yum.repos.d/test1.repo", result.filename)
    self.assertLen(result.uris, 4)

    self.assertEqual("file", result.uris[0].transport)
    self.assertEqual("", result.uris[0].host)
    self.assertEqual("/mnt", result.uris[0].path)

    self.assertEqual("http", result.uris[1].transport)
    self.assertEqual("mirror1.centos.org", result.uris[1].host)
    self.assertEqual("/CentOS/6/os/i386/", result.uris[1].path)

    self.assertEqual("ssh", result.uris[2].transport)
    self.assertEqual("mirror2.centos.org", result.uris[2].host)
    self.assertEqual("/CentOS/6/os/i386/", result.uris[2].path)

    self.assertEqual("https", result.uris[3].transport)
    self.assertEqual("mirror3.centos.org", result.uris[3].host)
    self.assertEqual("/CentOS/6/os/i386/", result.uris[3].path)

  def testEmptySourceData(self):
    test_data = (b"# comment 1\n"
                 b"baseurl=\n"
                 b"# Trailing whitespace on purpose\n"
                 b"baseurl=      \n"
                 b"# Trailing whitespace on purpose\n"
                 b"baseurl =            \n"
                 b"baseurl\n"
                 b"# comment 2\n")

    file_obj = io.BytesIO(test_data)
    pathspec = rdf_paths.PathSpec(path="/etc/yum.repos.d/emptytest.repo")
    stat = rdf_client_fs.StatEntry(pathspec=pathspec)
    parser = config_file.YumPackageSourceParser()
    results = list(parser.Parse(stat, file_obj, None))

    result = [
        d for d in results if isinstance(d, rdf_protodict.AttributedDict)
    ][0]

    self.assertEqual("/etc/yum.repos.d/emptytest.repo", result.filename)
    self.assertEmpty(result.uris)


class CronAtAllowDenyParserTests(test_lib.GRRBaseTest):
  """Test the cron/at allow/deny parser."""

  def testParseCronData(self):
    test_data = br"""root
    user

    user2 user3
    root
    hi hello
    user
    pparth"""
    file_obj = io.BytesIO(test_data)
    pathspec = rdf_paths.PathSpec(path="/etc/at.allow")
    stat = rdf_client_fs.StatEntry(pathspec=pathspec)
    parser = config_file.CronAtAllowDenyParser()
    results = list(parser.Parse(stat, file_obj, None))

    result = [
        d for d in results if isinstance(d, rdf_protodict.AttributedDict)
    ][0]
    filename = result.filename
    users = result.users
    self.assertEqual("/etc/at.allow", filename)
    self.assertEqual(sorted(["root", "user", "pparth"]), sorted(users))

    anomalies = [a for a in results if isinstance(a, rdf_anomaly.Anomaly)]
    self.assertLen(anomalies, 1)
    anom = anomalies[0]
    self.assertEqual("Dodgy entries in /etc/at.allow.", anom.symptom)
    self.assertEqual(sorted(["user2 user3", "hi hello"]), sorted(anom.finding))
    self.assertEqual(pathspec, anom.reference_pathspec)
    self.assertEqual("PARSER_ANOMALY", anom.type)


class NtpParserTests(test_lib.GRRBaseTest):
  """Test the ntp.conf parser."""

  def testParseNtpConfig(self):
    test_data = br"""
    # Time servers
    server 1.2.3.4 iburst
    server 4.5.6.7 iburst
    server 8.9.10.11 iburst
    server time.google.com iburst
    server 2001:1234:1234:2::f iburst

    # Drift file
    driftfile /var/lib/ntp/ntp.drift

    restrict default nomodify noquery nopeer

    # Guard against monlist NTP reflection attacks.
    disable monitor

    # Enable the creation of a peerstats file
    enable stats
    statsdir /var/log/ntpstats
    filegen peerstats file peerstats type day link enable

    # Test only.
    ttl 127 88
    broadcastdelay 0.01
"""
    conffile = io.BytesIO(test_data)
    parser = config_file.NtpdParser()
    results = list(parser.Parse(None, conffile, None))

    # We expect some results.
    self.assertTrue(results)
    # There should be only one result.
    self.assertLen(results, 1)
    # Now that we are sure, just use that single result for easy of reading.
    results = results[0]

    # Check all the expected "simple" config keywords are present.
    expected_config_keywords = set([
        "driftfile", "statsdir", "filegen", "ttl", "broadcastdelay"
    ]) | set(iterkeys(config_file.NtpdFieldParser.defaults))
    self.assertEqual(expected_config_keywords, set(iterkeys(results.config)))

    # Check all the expected "keyed" config keywords are present.
    self.assertTrue(results.server)
    self.assertTrue(results.restrict)
    # And check one that isn't in the config, isn't in out result.
    self.assertFalse(results.trap)

    # Check we got all the "servers".
    servers = [
        "1.2.3.4", "4.5.6.7", "8.9.10.11", "time.google.com",
        "2001:1234:1234:2::f"
    ]
    self.assertCountEqual(servers, [r.address for r in results.server])
    # In our test data, they all have "iburst" as an arg. Check that is found.
    for r in results.server:
      self.assertEqual("iburst", r.options)

    # Check a few values were parsed correctly.
    self.assertEqual("/var/lib/ntp/ntp.drift", results.config["driftfile"])
    self.assertEqual("/var/log/ntpstats", results.config["statsdir"])
    self.assertEqual("peerstats file peerstats type day link enable",
                     results.config["filegen"])
    self.assertLen(results.restrict, 1)
    self.assertEqual("default", results.restrict[0].address)
    self.assertEqual("nomodify noquery nopeer", results.restrict[0].options)
    # A option that can have a list of integers.
    self.assertEqual([127, 88], results.config["ttl"])
    # An option that should only have a single float.
    self.assertEqual([0.01], results.config["broadcastdelay"])

    # Check the modified defaults.
    self.assertFalse(results.config["monitor"])
    self.assertTrue(results.config["stats"])

    # Check an unlisted defaults are unmodified.
    self.assertFalse(results.config["kernel"])
    self.assertTrue(results.config["auth"])


class SudoersParserTest(test_lib.GRRBaseTest):
  """Test the sudoers parser."""

  def testIncludes(self):
    test_data = br"""
    # general comment
    #include a  # end of line comment
    #includedir b
    #includeis now a comment
    """
    contents = io.BytesIO(test_data)
    config = config_file.SudoersParser()
    result = list(config.Parse(None, contents, None))

    self.assertListEqual(list(result[0].includes), ["a", "b"])
    self.assertListEqual(list(result[0].entries), [])

  def testParseAliases(self):
    test_data = br"""
    User_Alias basic = a , b, c
    User_Alias left = a, b, c :\
               right = d, e, f
    User_Alias complex = #1000, %group, %#1001, %:nonunix, %:#1002
    """
    contents = io.BytesIO(test_data)
    config = config_file.SudoersParser()
    result = list(config.Parse(None, contents, None))

    golden = {
        "aliases": [
            {
                "name": "basic",
                "type": "USER",
                "users": ["a", "b", "c"],
            },
            {
                "name": "left",
                "type": "USER",
                "users": ["a", "b", "c"],
            },
            {
                "name": "right",
                "type": "USER",
                "users": ["d", "e", "f"],
            },
            {
                "name": "complex",
                "type": "USER",
                "users": ["#1000", "%group", "%#1001", "%:nonunix", "%:#1002"],
            },
        ],
    }

    self.assertDictEqual(result[0].ToPrimitiveDict(), golden)

  def testDefaults(self):
    test_data = br"""
    Defaults               syslog=auth
    Defaults>root          !set_logname
    Defaults:FULLTIMERS    !lecture
    Defaults@SERVERS       log_year, logfile=/var/log/sudo.log
    """
    contents = io.BytesIO(test_data)
    config = config_file.SudoersParser()
    result = list(config.Parse(None, contents, None))

    golden = {
        "defaults": [
            {
                "name": "syslog",
                "value": "auth",
            },
            {
                "scope": "root",
                "name": "!set_logname",
                "value": "",
            },
            {
                "scope": "FULLTIMERS",
                "name": "!lecture",
                "value": "",
            },
            # 4th entry is split into two, for each option.
            {
                "scope": "SERVERS",
                "name": "log_year",
                "value": "",
            },
            {
                "scope": "SERVERS",
                "name": "logfile",
                "value": "/var/log/sudo.log",
            },
        ],
    }

    self.assertDictEqual(result[0].ToPrimitiveDict(), golden)

  def testSpecs(self):
    test_data = br"""
    # user specs
    root        ALL = (ALL) ALL
    %wheel      ALL = (ALL) ALL
    bob     SPARC = (OP) ALL : SGI = (OP) ALL
    fred        ALL = (DB) NOPASSWD: ALL
    """
    contents = io.BytesIO(test_data)
    config = config_file.SudoersParser()
    result = list(config.Parse(None, contents, None))

    golden = {
        "entries": [
            {
                "users": ["root"],
                "hosts": ["ALL"],
                "cmdspec": ["(ALL)", "ALL"],
            },
            {
                "users": ["%wheel"],
                "hosts": ["ALL"],
                "cmdspec": ["(ALL)", "ALL"],
            },
            {
                "users": ["bob"],
                "hosts": ["SPARC"],
                "cmdspec": ["(OP)", "ALL"],
            },
            {
                "users": ["bob"],
                "hosts": ["SGI"],
                "cmdspec": ["(OP)", "ALL"],
            },
            {
                "users": ["fred"],
                "hosts": ["ALL"],
                "cmdspec": ["(DB)", "NOPASSWD:", "ALL"],
            },
        ],
    }

    self.assertDictEqual(result[0].ToPrimitiveDict(), golden)


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
