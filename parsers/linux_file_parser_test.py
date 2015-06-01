#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Unit test for the linux file parser."""

import os
import StringIO


from grr.lib import config_lib
from grr.lib import flags
from grr.lib import parsers
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.flows.general import file_finder
from grr.lib.rdfvalues import anomaly as rdf_anomaly
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.parsers import linux_file_parser


class LinuxFileParserTest(test_lib.GRRBaseTest):
  """Test parsing of linux files."""

  def testPasswdParser(self):
    """Ensure we can extract users from a passwd file."""
    parser = linux_file_parser.PasswdParser()
    dat = """
user1:x:1000:1000:User1 Name,,,:/home/user1:/bin/bash
user2:x:1001:1001:User2 Name,,,:/home/user2:/bin/bash
"""
    out = list(parser.Parse(None, StringIO.StringIO(dat), None))
    self.assertEqual(len(out), 2)
    self.assertTrue(isinstance(out[1], rdf_client.KnowledgeBaseUser))
    self.assertTrue(isinstance(out[1], rdf_client.KnowledgeBaseUser))
    self.assertEqual(out[0].username, "user1")
    self.assertEqual(out[0].full_name, "User1 Name,,,")
    dat = """
user1:x:1000:1000:User1 Name,,,:/home/user1:/bin/bash
user2:x:1001:1001:User2 Name,,,:/home/user
"""
    parser = linux_file_parser.PasswdParser()
    self.assertRaises(parsers.ParseError,
                      list, parser.Parse(None, StringIO.StringIO(dat), None))

  def testPasswdBufferParser(self):
    """Ensure we can extract users from a passwd file."""
    parser = linux_file_parser.PasswdBufferParser()
    buf1 = rdf_client.BufferReference(data="user1:x:1000:1000:User1"
                                      " Name,,,:/home/user1:/bin/bash\n")

    buf2 = rdf_client.BufferReference(data="user2:x:1000:1000:User2"
                                      " Name,,,:/home/user2:/bin/bash\n")

    ff_result = file_finder.FileFinderResult(matches=[buf1, buf2])
    out = list(parser.Parse(ff_result, None))
    self.assertEqual(len(out), 2)
    self.assertTrue(isinstance(out[1], rdf_client.KnowledgeBaseUser))
    self.assertTrue(isinstance(out[1], rdf_client.KnowledgeBaseUser))
    self.assertEqual(out[0].username, "user1")
    self.assertEqual(out[0].full_name, "User1 Name,,,")

  def testNetgroupParser(self):
    """Ensure we can extract users from a netgroup file."""
    parser = linux_file_parser.NetgroupParser()
    dat = u"""group1 (-,user1,) (-,user2,) (-,user3,)
#group1 comment
group2 (-,user4,) (-,user2,)

super_group (-,user5,) (-,user6,) (-,文德文,) group1 group2
super_group2 (-,user7,) super_group
super_group3 (-,user5,) (-,user6,) group1 group2
"""
    dat_fd = StringIO.StringIO(dat)

    config_lib.CONFIG.Set("Artifacts.netgroup_user_blacklist", ["user2",
                                                                "user3"])
    out = list(parser.Parse(None, dat_fd, None))
    users = []
    for result in out:
      if isinstance(result, rdf_anomaly.Anomaly):
        self.assertTrue(utils.SmartUnicode(u"文德文") in result.symptom)
      else:
        users.append(result)

    self.assertItemsEqual([x.username for x in users],
                          [u"user1", u"user4", u"user5", u"user6", u"user7"])

    dat_fd.seek(0)
    config_lib.CONFIG.Set("Artifacts.netgroup_filter_regexes",
                          [r"^super_group3$"])
    out = list(parser.Parse(None, dat_fd, None))
    self.assertItemsEqual([x.username for x in out],
                          [u"user5", u"user6"])

  def testNetgroupBufferParser(self):
    """Ensure we can extract users from a netgroup file."""
    parser = linux_file_parser.NetgroupBufferParser()
    buf1 = rdf_client.BufferReference(data="group1 (-,user1,) (-,user2,) "
                                      "(-,user3,)\n")
    buf2 = rdf_client.BufferReference(data="super_group3 (-,user5,) (-,user6,)"
                                      " group1 group2\n")

    ff_result = file_finder.FileFinderResult(matches=[buf1, buf2])
    config_lib.CONFIG.Set("Artifacts.netgroup_user_blacklist", ["user2",
                                                                "user3"])
    out = list(parser.Parse(ff_result, None))
    self.assertItemsEqual([x.username for x in out],
                          [u"user1", u"user5", u"user6"])

  def testNetgroupParserBadInput(self):
    parser = linux_file_parser.NetgroupParser()
    dat = """group1 (-,user1,) (-,user2,) (-,user3,)
#group1 comment
group2 user4 (-user2,)
super_group (-,,user5,) (-user6,) group1 group2
super_group2 (-,user7,) super_group
"""
    self.assertRaises(parsers.ParseError,
                      list, parser.Parse(None, StringIO.StringIO(dat), None))

  def testWtmpParser(self):
    """Test parsing of wtmp file."""
    parser = linux_file_parser.LinuxWtmpParser()
    path = os.path.join(self.base_path, "wtmp")
    with open(path, "rb") as wtmp_fd:
      out = list(parser.Parse(None, wtmp_fd, None))

    self.assertEqual(len(out), 3)
    self.assertItemsEqual(["%s:%d" % (x.username, x.last_logon) for x in out],
                          ["user1:1296552099000000",
                           "user2:1296552102000000",
                           "user3:1296569997000000"])


class LinuxShadowParserTest(test_lib.GRRBaseTest):
  """Test parsing of linux shadow files."""

  crypt = {"DES": "A.root/ootr.o",
           "MD5": "$1$rootrootrootrootrootro",
           "SHA256": "$5$saltsaltsalt${0}".format("r" * 43),
           "SHA512": "$6$saltsalt${0}".format("r" * 86),
           "UNSET": "*",
           "DISABLED": "!$1$rootrootroootroooooootroooooooo",
           "EMPTY": ""}

  def _GenFiles(self, passwd, shadow, group, gshadow):
    stats = []
    files = []
    for path in ["/etc/passwd", "/etc/shadow", "/etc/group", "/etc/gshadow"]:
      p = rdf_paths.PathSpec(path=path)
      stats.append(rdf_client.StatEntry(pathspec=p))
    for data in passwd, shadow, group, gshadow:
      if data is None:
        data = []
      lines = "\n".join(data).format(**self.crypt)
      files.append(StringIO.StringIO(lines))
    return stats, files

  def testNoAnomaliesWhenEverythingIsFine(self):
    passwd = ["ok_1:x:1000:1000::/home/ok_1:/bin/bash",
              "ok_2:x:1001:1001::/home/ok_2:/bin/bash"]
    shadow = ["ok_1:{SHA256}:16000:0:99999:7:::",
              "ok_2:{SHA512}:16000:0:99999:7:::"]
    group = ["ok_1:x:1000:ok_1", "ok_2:x:1001:ok_2"]
    gshadow = ["ok_1:::ok_1", "ok_2:::ok_2"]
    stats, files = self._GenFiles(passwd, shadow, group, gshadow)
    parser = linux_file_parser.LinuxSystemPasswdParser()
    rdfs = parser.ParseMultiple(stats, files, None)
    results = [r for r in rdfs if isinstance(r, rdf_anomaly.Anomaly)]
    self.assertFalse(results)

  def testSystemGroupParserAnomaly(self):
    """Detect anomalies in group/gshadow files."""
    group = ["root:x:0:root,usr1", "adm:x:1:syslog,usr1",
             "users:x:1000:usr1,usr2,usr3,usr4"]
    gshadow = ["root::usr4:root", "users:{DES}:usr1:usr2,usr3,usr4"]
    stats, files = self._GenFiles(None, None, group, gshadow)

    # Set up expected anomalies.
    member = {"symptom": "Group/gshadow members differ in group: root",
              "finding": ["Present in group, missing in gshadow: usr1",
                          "Present in gshadow, missing in group: usr4"],
              "type": "PARSER_ANOMALY"}
    group = {"symptom": "Mismatched group and gshadow files.",
             "finding": ["Present in group, missing in gshadow: adm"],
             "type": "PARSER_ANOMALY"}
    expected = [rdf_anomaly.Anomaly(**member), rdf_anomaly.Anomaly(**group)]

    parser = linux_file_parser.LinuxSystemGroupParser()
    rdfs = parser.ParseMultiple(stats, files, None)
    results = [r for r in rdfs if isinstance(r, rdf_anomaly.Anomaly)]

    self.assertEqual(len(expected), len(results))
    for expect, result in zip(expected, results):
      self.assertRDFValueEqual(expect, result)

  def testSystemAccountAnomaly(self):
    passwd = ["root:x:0:0::/root:/bin/sash",
              "miss:x:1000:100:Missing:/home/miss:/bin/bash",
              "bad1:x:0:1001:Bad 1:/home/bad1:/bin/bash",
              "bad2:x:1002:0:Bad 2:/home/bad2:/bin/bash"]
    shadow = ["root:{UNSET}:16000:0:99999:7:::",
              "ok:{SHA512}:16000:0:99999:7:::",
              "bad1::16333:0:99999:7:::", "bad2:{DES}:16333:0:99999:7:::"]
    group = ["root:x:0:root", "miss:x:1000:miss", "bad1:x:1001:bad1",
             "bad2:x:1002:bad2"]
    gshadow = ["root:::root", "miss:::miss", "bad1:::bad1", "bad2:::bad2"]
    stats, files = self._GenFiles(passwd, shadow, group, gshadow)

    no_grp = {"symptom": "Accounts with invalid gid.",
              "finding": ["gid 100 assigned without /etc/groups entry: miss"],
              "type": "PARSER_ANOMALY"}
    uid = {"symptom": "Accounts with shared uid.",
           "finding": ["uid 0 assigned to multiple accounts: bad1,root"],
           "type": "PARSER_ANOMALY"}
    gid = {"symptom": "Privileged group with unusual members.",
           "finding": ["Accounts in 'root' group: bad2"],
           "type": "PARSER_ANOMALY"}
    no_match = {"symptom": "Mismatched passwd and shadow files.",
                "finding": ["Present in passwd, missing in shadow: miss",
                            "Present in shadow, missing in passwd: ok"],
                "type": "PARSER_ANOMALY"}
    expected = [rdf_anomaly.Anomaly(**no_grp), rdf_anomaly.Anomaly(**uid),
                rdf_anomaly.Anomaly(**gid), rdf_anomaly.Anomaly(**no_match)]

    parser = linux_file_parser.LinuxSystemPasswdParser()
    rdfs = parser.ParseMultiple(stats, files, None)
    results = [r for r in rdfs if isinstance(r, rdf_anomaly.Anomaly)]

    self.assertEqual(len(expected), len(results))
    for expect, result in zip(expected, results):
      self.assertEqual(expect.symptom, result.symptom)
      # Expand out repeated field helper.
      self.assertItemsEqual(list(expect.finding), list(result.finding))
      self.assertEqual(expect.type, result.type)

  def GetExpectedUser(self, algo, user_store, group_store):
    user = rdf_client.KnowledgeBaseUser(username="user", full_name="User",
                                        uid="1001", gid="1001",
                                        homedir="/home/user", shell="/bin/bash")
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
    self.assertItemsEqual(expect.gids, result.gids)

  def CheckExpectedGroup(self, algo, expect, result):
    self.assertEqual(expect.name, result.name)
    self.assertEqual(expect.gid, result.gid)
    self.assertEqual(expect.pw_entry.store, result.pw_entry.store)
    self.assertEqual(expect.pw_entry.hash_type, result.pw_entry.hash_type)

  def CheckCryptResults(self, passwd, shadow, group, gshadow, algo, usr, grp):
    stats, files = self._GenFiles(passwd, shadow, group, gshadow)
    parser = linux_file_parser.LinuxSystemPasswdParser()
    results = list(parser.ParseMultiple(stats, files, None))
    usrs = [r for r in results if isinstance(r, rdf_client.KnowledgeBaseUser)]
    grps = [r for r in results if isinstance(r, rdf_client.Group)]
    self.assertEqual(1, len(usrs), "Different number of usr %s results" % algo)
    self.assertEqual(1, len(grps), "Different number of grp %s results" % algo)
    self.CheckExpectedUser(algo, usr, usrs[0])
    self.CheckExpectedGroup(algo, grp, grps[0])

  def testSetShadowedEntries(self):
    passwd = ["user:x:1001:1001:User:/home/user:/bin/bash"]
    group = ["user:x:1001:user"]
    for algo, crypted in self.crypt.iteritems():
      # Flush the parser for each iteration.
      shadow = ["user:%s:16000:0:99999:7:::" % crypted]
      gshadow = ["user:%s::user" % crypted]
      usr, grp = self.GetExpectedUser(algo, "SHADOW", "GSHADOW")
      self.CheckCryptResults(passwd, shadow, group, gshadow, algo, usr, grp)

  def testSetNonShadowedEntries(self):
    shadow = ["user::16000:0:99999:7:::"]
    gshadow = ["user:::user"]
    for algo, crypted in self.crypt.iteritems():
      # Flush the parser for each iteration.
      passwd = ["user:%s:1001:1001:User:/home/user:/bin/bash" % crypted]
      group = ["user:%s:1001:user" % crypted]
      usr, grp = self.GetExpectedUser(algo, "PASSWD", "GROUP")
      self.CheckCryptResults(passwd, shadow, group, gshadow, algo, usr, grp)


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
