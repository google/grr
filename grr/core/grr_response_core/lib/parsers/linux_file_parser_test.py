#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Unit test for the linux file parser."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import operator
import os


from builtins import zip  # pylint: disable=redefined-builtin
from future.utils import iteritems

from grr_response_core.lib import flags
from grr_response_core.lib import parser as lib_parser
from grr_response_core.lib.parsers import linux_file_parser
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr.test_lib import test_lib


class LinuxFileParserTest(test_lib.GRRBaseTest):
  """Test parsing of linux files."""

  def testPCIDevicesInfoParser(self):
    """Ensure we can extract PCI devices info."""

    # Test when there's data for one PCI device only.
    test_data1 = {
        "/sys/bus/pci/devices/0000:00:01.0/vendor": b"0x0e00\n",
        "/sys/bus/pci/devices/0000:00:01.0/class": b"0x060400\n",
        "/sys/bus/pci/devices/0000:00:01.0/device": b"0x0e02\n",
        "/sys/bus/pci/devices/0000:00:01.0/config": b"0200"
    }
    device_1 = rdf_client.PCIDevice(
        domain=0,
        bus=0,
        device=1,
        function=0,
        class_id="0x060400",
        vendor="0x0e00",
        vendor_device_id="0x0e02",
        config=b"0200")
    parsed_results = self._ParsePCIDeviceTestData(test_data1)
    self._MatchPCIDeviceResultToExpected(parsed_results, [device_1])

    test_data2 = {
        "/sys/bus/pci/devices/0000:00:00.0/vendor":
            b"0x8086\n",
        "/sys/bus/pci/devices/0000:00:00.0/class":
            b"0x060000\n",
        "/sys/bus/pci/devices/0000:00:00.0/device":
            b"0x0e00\n",
        "/sys/bus/pci/devices/0000:00:00.0/config": (b"\xea\xe8\xe7\xbc\x7a\x84"
                                                     b"\x91"),
    }
    device_2 = rdf_client.PCIDevice(
        domain=0,
        bus=0,
        device=0,
        function=0,
        class_id="0x060000",
        vendor="0x8086",
        vendor_device_id="0x0e00",
        config=b"\xea\xe8\xe7\xbcz\x84\x91")
    parsed_results = self._ParsePCIDeviceTestData(test_data2)
    self._MatchPCIDeviceResultToExpected(parsed_results, [device_2])

    # Test for when there's missing data.
    test_data3 = {
        "/sys/bus/pci/devices/0000:00:03.0/vendor": b"0x0e00\n",
        "/sys/bus/pci/devices/0000:00:03.0/config": b"0030"
    }
    device_3 = rdf_client.PCIDevice(
        domain=0, bus=0, device=3, function=0, vendor="0x0e00", config=b"0030")
    parsed_results = self._ParsePCIDeviceTestData(test_data3)
    self._MatchPCIDeviceResultToExpected(parsed_results, [device_3])

    # Test when data contains non-valid B/D/F folders/files.
    test_data4 = {
        "/sys/bus/pci/devices/0000:00:05.0/vendor": b"0x0e00\n",
        "/sys/bus/pci/devices/0000:00:05.0/class": b"0x060400\n",
        "/sys/bus/pci/devices/0000:00:05.0/device": b"0x0e02\n",
        "/sys/bus/pci/devices/0000:00:05.0/config": b"0200",
        "/sys/bus/pci/devices/crazyrandomfile/test1": b"test1",
        "/sys/bus/pci/devices/::./test2": b"test2",
        "/sys/bus/pci/devices/00:5.0/test3": b"test3"
    }
    device_4 = rdf_client.PCIDevice(
        domain=0,
        bus=0,
        device=5,
        function=0,
        class_id="0x060400",
        vendor="0x0e00",
        vendor_device_id="0x0e02",
        config=b"0200")
    parsed_results = self._ParsePCIDeviceTestData(test_data4)
    self._MatchPCIDeviceResultToExpected(parsed_results, [device_4])

    # Test when there's multiple PCI devices in the test_data.
    combined_data = test_data1.copy()
    combined_data.update(test_data3)
    combined_data.update(test_data4)
    combined_data.update(test_data2)
    parsed_results = self._ParsePCIDeviceTestData(combined_data)
    self._MatchPCIDeviceResultToExpected(
        parsed_results, [device_1, device_4, device_2, device_3])

  def _ParsePCIDeviceTestData(self, test_data):
    """Given test_data dictionary, parse it using PCIDevicesInfoParser."""
    parser = linux_file_parser.PCIDevicesInfoParser()
    stats = []
    file_objs = []
    kb_objs = []

    # Populate stats, file_ojbs, kb_ojbs lists needed by the parser.
    for filename, data in iteritems(test_data):
      pathspec = rdf_paths.PathSpec(path=filename, pathtype="OS")
      stat = rdf_client_fs.StatEntry(pathspec=pathspec)
      file_obj = io.BytesIO(data)
      stats.append(stat)
      file_objs.append(file_obj)
      kb_objs.append(None)

    return list(parser.ParseMultiple(stats, file_objs, kb_objs))

  def _MatchPCIDeviceResultToExpected(self, parsed_results, expected_output):
    """Make sure the parsed_results match expected_output."""

    # Check the size matches.
    self.assertLen(parsed_results, len(expected_output))

    # Sort parsed_results and expected_outputs so we're comparing properly.
    results = sorted(parsed_results, key=operator.attrgetter("device"))
    outputs = sorted(expected_output, key=operator.attrgetter("device"))

    # Check all the content matches.
    for result, output in zip(results, outputs):
      self.assertEqual(result.domain, output.domain)
      self.assertEqual(result.bus, output.bus)
      self.assertEqual(result.device, output.device)
      self.assertEqual(result.function, output.function)
      self.assertEqual(result.class_id, output.class_id)
      self.assertEqual(result.vendor, output.vendor)
      self.assertEqual(result.vendor_device_id, output.vendor_device_id)
      self.assertEqual(result.config, output.config)

  def testPasswdParser(self):
    """Ensure we can extract users from a passwd file."""
    parser = linux_file_parser.PasswdParser()
    dat = b"""
user1:x:1000:1000:User1 Name,,,:/home/user1:/bin/bash
user2:x:1001:1001:User2 Name,,,:/home/user2:/bin/bash
"""
    out = list(parser.Parse(None, io.BytesIO(dat), None))
    self.assertLen(out, 2)
    self.assertIsInstance(out[1], rdf_client.User)
    self.assertIsInstance(out[1], rdf_client.User)
    self.assertEqual(out[0].username, "user1")
    self.assertEqual(out[0].full_name, "User1 Name,,,")
    dat = b"""
user1:x:1000:1000:User1 Name,,,:/home/user1:/bin/bash
user2:x:1001:1001:User2 Name,,,:/home/user
"""
    parser = linux_file_parser.PasswdParser()
    self.assertRaises(lib_parser.ParseError, list,
                      parser.Parse(None, io.BytesIO(dat), None))

  def testPasswdBufferParser(self):
    """Ensure we can extract users from a passwd file."""
    parser = linux_file_parser.PasswdBufferParser()
    buf1 = rdf_client.BufferReference(
        data=b"user1:x:1000:1000:User1 Name,,,:/home/user1:/bin/bash\n")
    buf2 = rdf_client.BufferReference(
        data=b"user2:x:1000:1000:User2 Name,,,:/home/user2:/bin/bash\n")

    ff_result = rdf_file_finder.FileFinderResult(matches=[buf1, buf2])
    out = list(parser.Parse(ff_result, None))
    self.assertLen(out, 2)
    self.assertIsInstance(out[1], rdf_client.User)
    self.assertIsInstance(out[1], rdf_client.User)
    self.assertEqual(out[0].username, "user1")
    self.assertEqual(out[0].full_name, "User1 Name,,,")

  def testNetgroupParser(self):
    """Ensure we can extract users from a netgroup file."""
    parser = linux_file_parser.NetgroupParser()
    dat = """group1 (-,user1,) (-,user2,) (-,user3,)
#group1 comment
group2 (-,user4,) (-,user2,)

super_group (-,user5,) (-,user6,) (-,文德文,) group1 group2
super_group2 (-,user7,) super_group
super_group3 (-,user5,) (-,user6,) group1 group2
"""
    dat_fd = io.BytesIO(dat.encode("utf-8"))

    with test_lib.ConfigOverrider(
        {"Artifacts.netgroup_user_blacklist": ["user2", "user3"]}):
      out = list(parser.Parse(None, dat_fd, None))
      users = []
      for result in out:
        if isinstance(result, rdf_anomaly.Anomaly):
          self.assertIn("文德文", result.symptom)
        else:
          users.append(result)

      self.assertCountEqual([x.username for x in users],
                            [u"user1", u"user4", u"user5", u"user6", u"user7"])

      dat_fd.seek(0)

    with test_lib.ConfigOverrider(
        {"Artifacts.netgroup_filter_regexes": [r"^super_group3$"]}):
      out = list(parser.Parse(None, dat_fd, None))
      self.assertCountEqual([x.username for x in out], [u"user5", u"user6"])

  def testNetgroupBufferParser(self):
    """Ensure we can extract users from a netgroup file."""
    parser = linux_file_parser.NetgroupBufferParser()
    buf1 = rdf_client.BufferReference(
        data=b"group1 (-,user1,) (-,user2,) (-,user3,)\n")
    buf2 = rdf_client.BufferReference(
        data=b"super_group3 (-,user5,) (-,user6,) group1 group2\n")

    ff_result = rdf_file_finder.FileFinderResult(matches=[buf1, buf2])
    with test_lib.ConfigOverrider(
        {"Artifacts.netgroup_user_blacklist": ["user2", "user3"]}):
      out = list(parser.Parse(ff_result, None))
      self.assertCountEqual([x.username for x in out],
                            [u"user1", u"user5", u"user6"])

  def testNetgroupParserBadInput(self):
    parser = linux_file_parser.NetgroupParser()
    dat = b"""group1 (-,user1,) (-,user2,) (-,user3,)
#group1 comment
group2 user4 (-user2,)
super_group (-,,user5,) (-user6,) group1 group2
super_group2 (-,user7,) super_group
"""
    self.assertRaises(lib_parser.ParseError, list,
                      parser.Parse(None, io.BytesIO(dat), None))

  def testWtmpParser(self):
    """Test parsing of wtmp file."""
    parser = linux_file_parser.LinuxWtmpParser()
    path = os.path.join(self.base_path, "VFSFixture/var/log/wtmp")
    with open(path, "rb") as wtmp_fd:
      out = list(parser.Parse(None, wtmp_fd, None))

    self.assertLen(out, 3)
    self.assertCountEqual(["%s:%d" % (x.username, x.last_logon) for x in out], [
        "user1:1296552099000000", "user2:1296552102000000",
        "user3:1296569997000000"
    ])


class LinuxShadowParserTest(test_lib.GRRBaseTest):
  """Test parsing of linux shadow files."""

  crypt = {
      "DES": "A.root/o0tr.o",
      "MD5": "$1$roo/root/o07r.0tROOTro",
      "SHA256": "$5$sal/s.lt5a17${0}".format("r" * 43),
      "SHA512": "$6$sa./sa1T${0}".format("r" * 86),
      "UNSET": "*",
      "DISABLED": "!$1$roo/rootroootROOO0oooTroooooooo",
      "EMPTY": ""
  }

  def _GenFiles(self, passwd, shadow, group, gshadow):
    stats = []
    files = []
    for path in ["/etc/passwd", "/etc/shadow", "/etc/group", "/etc/gshadow"]:
      p = rdf_paths.PathSpec(path=path)
      stats.append(rdf_client_fs.StatEntry(pathspec=p))
    for data in passwd, shadow, group, gshadow:
      if data is None:
        data = []
      lines = "\n".join(data).format(**self.crypt).encode("utf-8")
      files.append(io.BytesIO(lines))
    return stats, files

  def testNoAnomaliesWhenEverythingIsFine(self):
    passwd = [
        "ok_1:x:1000:1000::/home/ok_1:/bin/bash",
        "ok_2:x:1001:1001::/home/ok_2:/bin/bash"
    ]
    shadow = [
        "ok_1:{SHA256}:16000:0:99999:7:::", "ok_2:{SHA512}:16000:0:99999:7:::"
    ]
    group = ["ok_1:x:1000:ok_1", "ok_2:x:1001:ok_2"]
    gshadow = ["ok_1:::ok_1", "ok_2:::ok_2"]
    stats, files = self._GenFiles(passwd, shadow, group, gshadow)
    parser = linux_file_parser.LinuxSystemPasswdParser()
    rdfs = parser.ParseMultiple(stats, files, None)
    results = [r for r in rdfs if isinstance(r, rdf_anomaly.Anomaly)]
    self.assertFalse(results)

  def testSystemGroupParserAnomaly(self):
    """Detect anomalies in group/gshadow files."""
    group = [
        "root:x:0:root,usr1", "adm:x:1:syslog,usr1",
        "users:x:1000:usr1,usr2,usr3,usr4"
    ]
    gshadow = ["root::usr4:root", "users:{DES}:usr1:usr2,usr3,usr4"]
    stats, files = self._GenFiles(None, None, group, gshadow)

    # Set up expected anomalies.
    member = {
        "symptom":
            "Group/gshadow members differ in group: root",
        "finding": [
            "Present in group, missing in gshadow: usr1",
            "Present in gshadow, missing in group: usr4"
        ],
        "type":
            "PARSER_ANOMALY"
    }
    group = {
        "symptom": "Mismatched group and gshadow files.",
        "finding": ["Present in group, missing in gshadow: adm"],
        "type": "PARSER_ANOMALY"
    }
    expected = [rdf_anomaly.Anomaly(**member), rdf_anomaly.Anomaly(**group)]

    parser = linux_file_parser.LinuxSystemGroupParser()
    rdfs = parser.ParseMultiple(stats, files, None)
    results = [r for r in rdfs if isinstance(r, rdf_anomaly.Anomaly)]

    self.assertLen(expected, len(results))
    for expect, result in zip(expected, results):
      self.assertRDFValuesEqual(expect, result)

  def testSystemAccountAnomaly(self):
    passwd = [
        "root:x:0:0::/root:/bin/sash",
        "miss:x:1000:100:Missing:/home/miss:/bin/bash",
        "bad1:x:0:1001:Bad 1:/home/bad1:/bin/bash",
        "bad2:x:1002:0:Bad 2:/home/bad2:/bin/bash"
    ]
    shadow = [
        "root:{UNSET}:16000:0:99999:7:::", "ok:{SHA512}:16000:0:99999:7:::",
        "bad1::16333:0:99999:7:::", "bad2:{DES}:16333:0:99999:7:::"
    ]
    group = [
        "root:x:0:root", "miss:x:1000:miss", "bad1:x:1001:bad1",
        "bad2:x:1002:bad2"
    ]
    gshadow = ["root:::root", "miss:::miss", "bad1:::bad1", "bad2:::bad2"]
    stats, files = self._GenFiles(passwd, shadow, group, gshadow)

    no_grp = {
        "symptom": "Accounts with invalid gid.",
        "finding": ["gid 100 assigned without /etc/groups entry: miss"],
        "type": "PARSER_ANOMALY"
    }
    uid = {
        "symptom": "Accounts with shared uid.",
        "finding": ["uid 0 assigned to multiple accounts: bad1,root"],
        "type": "PARSER_ANOMALY"
    }
    gid = {
        "symptom": "Privileged group with unusual members.",
        "finding": ["Accounts in 'root' group: bad2"],
        "type": "PARSER_ANOMALY"
    }
    no_match = {
        "symptom":
            "Mismatched passwd and shadow files.",
        "finding": [
            "Present in passwd, missing in shadow: miss",
            "Present in shadow, missing in passwd: ok"
        ],
        "type":
            "PARSER_ANOMALY"
    }
    expected = [
        rdf_anomaly.Anomaly(**no_grp),
        rdf_anomaly.Anomaly(**uid),
        rdf_anomaly.Anomaly(**gid),
        rdf_anomaly.Anomaly(**no_match)
    ]

    parser = linux_file_parser.LinuxSystemPasswdParser()
    rdfs = parser.ParseMultiple(stats, files, None)
    results = [r for r in rdfs if isinstance(r, rdf_anomaly.Anomaly)]

    self.assertLen(expected, len(results))
    for expect, result in zip(expected, results):
      self.assertEqual(expect.symptom, result.symptom)
      # Expand out repeated field helper.
      self.assertCountEqual(list(expect.finding), list(result.finding))
      self.assertEqual(expect.type, result.type)

  def GetExpectedUser(self, algo, user_store, group_store):
    user = rdf_client.User(
        username="user",
        full_name="User",
        uid="1001",
        gid="1001",
        homedir="/home/user",
        shell="/bin/bash")
    user.pw_entry = rdf_client.PwEntry(store=user_store, hash_type=algo)
    user.gids = [1001]
    grp = rdf_client.Group(gid=1001, members=["user"], name="user")
    grp.pw_entry = rdf_client.PwEntry(store=group_store, hash_type=algo)
    return user, grp

  def CheckExpectedUser(self, algo, expect, result):
    self.assertEqual(expect.username, result.username)
    self.assertEqual(expect.gid, result.gid)
    self.assertEqual(expect.pw_entry.store, result.pw_entry.store)
    self.assertEqual(expect.pw_entry.hash_type, result.pw_entry.hash_type)
    self.assertCountEqual(expect.gids, result.gids)

  def CheckExpectedGroup(self, algo, expect, result):
    self.assertEqual(expect.name, result.name)
    self.assertEqual(expect.gid, result.gid)
    self.assertEqual(expect.pw_entry.store, result.pw_entry.store)
    self.assertEqual(expect.pw_entry.hash_type, result.pw_entry.hash_type)

  def CheckCryptResults(self, passwd, shadow, group, gshadow, algo, usr, grp):
    stats, files = self._GenFiles(passwd, shadow, group, gshadow)
    parser = linux_file_parser.LinuxSystemPasswdParser()
    results = list(parser.ParseMultiple(stats, files, None))
    usrs = [r for r in results if isinstance(r, rdf_client.User)]
    grps = [r for r in results if isinstance(r, rdf_client.Group)]
    self.assertLen(usrs, 1, "Different number of usr %s results" % algo)
    self.assertLen(grps, 1, "Different number of grp %s results" % algo)
    self.CheckExpectedUser(algo, usr, usrs[0])
    self.CheckExpectedGroup(algo, grp, grps[0])

  def testSetShadowedEntries(self):
    passwd = ["user:x:1001:1001:User:/home/user:/bin/bash"]
    group = ["user:x:1001:user"]
    for algo, crypted in iteritems(self.crypt):
      # Flush the parser for each iteration.
      shadow = ["user:%s:16000:0:99999:7:::" % crypted]
      gshadow = ["user:%s::user" % crypted]
      usr, grp = self.GetExpectedUser(algo, "SHADOW", "GSHADOW")
      self.CheckCryptResults(passwd, shadow, group, gshadow, algo, usr, grp)

  def testSetNonShadowedEntries(self):
    shadow = ["user::16000:0:99999:7:::"]
    gshadow = ["user:::user"]
    for algo, crypted in iteritems(self.crypt):
      # Flush the parser for each iteration.
      passwd = ["user:%s:1001:1001:User:/home/user:/bin/bash" % crypted]
      group = ["user:%s:1001:user" % crypted]
      usr, grp = self.GetExpectedUser(algo, "PASSWD", "GROUP")
      self.CheckCryptResults(passwd, shadow, group, gshadow, algo, usr, grp)


class LinuxDotFileParserTest(test_lib.GRRBaseTest):
  """Test parsing of user dotfiles."""

  def testFindPaths(self):
    # TODO(user): Deal with cases where multiple vars are exported.
    # export TERM PERLLIB=.:shouldntbeignored
    bashrc_data = io.BytesIO(b"""
      IGNORE='bad' PATH=${HOME}/bin:$PATH
     { PYTHONPATH=/path1:/path2 }
      export TERM=screen-256color
      export http_proxy="http://proxy.example.org:3128/"
      export HTTP_PROXY=$http_proxy
      if [[ "$some_condition" ]]; then
        export PATH=:$PATH; LD_LIBRARY_PATH=foo:bar:$LD_LIBRARY_PATH
        PYTHONPATH=$PATH:"${PYTHONPATH}"
        CLASSPATH=
      fi
      echo PATH=/should/be/ignored
      # Ignore PATH=foo:bar
      TERM=vt100 PS=" Foo" PERL5LIB=:shouldntbeignored
    """)
    cshrc_data = io.BytesIO(b"""
      setenv PATH ${HOME}/bin:$PATH
      setenv PYTHONPATH /path1:/path2
      set term = (screen-256color)
      setenv http_proxy "http://proxy.example.org:3128/"
      setenv HTTP_PROXY $http_proxy
      if ( -e "$some_condition" ) then
        set path =  (. $path); setenv LD_LIBRARY_PATH foo:bar:$LD_LIBRARY_PATH
        setenv PYTHONPATH $PATH:"${PYTHONPATH}"
        setenv CLASSPATH
      endif
      echo PATH=/should/be/ignored
      setenv PERL5LIB :shouldntbeignored
    """)
    parser = linux_file_parser.PathParser()
    bashrc_stat = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(path="/home/user1/.bashrc", pathtype="OS"))
    cshrc_stat = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(path="/home/user1/.cshrc", pathtype="OS"))
    bashrc = {
        r.name: r.vals for r in parser.Parse(bashrc_stat, bashrc_data, None)
    }
    cshrc = {r.name: r.vals for r in parser.Parse(cshrc_stat, cshrc_data, None)}
    expected = {
        "PATH": [".", "${HOME}/bin", "$PATH"],
        "PYTHONPATH": [".", "${HOME}/bin", "$PATH", "/path1", "/path2"],
        "LD_LIBRARY_PATH": ["foo", "bar", "$LD_LIBRARY_PATH"],
        "CLASSPATH": [],
        "PERL5LIB": [".", "shouldntbeignored"]
    }
    # Got the same environment variables for bash and cshrc files.
    self.assertCountEqual(expected, bashrc)
    self.assertCountEqual(expected, cshrc)
    # The path values are expanded correctly.
    for var_name in ("PATH", "PYTHONPATH", "LD_LIBRARY_PATH"):
      self.assertEqual(expected[var_name], bashrc[var_name])
      self.assertEqual(expected[var_name], cshrc[var_name])


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
