#!/usr/bin/env python
"""Simple parsers for Linux files."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import logging
import os
import re

from builtins import zip  # pylint: disable=redefined-builtin
from future.utils import iteritems
from future.utils import itervalues

from grr_response_core import config
from grr_response_core.lib import parser
from grr_response_core.lib import utils
from grr_response_core.lib.parsers import config_file
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict


class PCIDevicesInfoParser(parser.FileMultiParser):
  """Parser for PCI devices' info files located in /sys/bus/pci/devices/*/*."""

  output_types = ["PCIDevice"]
  supported_artifacts = ["PCIDevicesInfoFiles"]

  def ParseMultiple(self, stats, file_objects, unused_knowledge_base):

    # Each file gives us only partial information for a particular PCI device.
    # Iterate through all the files first to create a dictionary encapsulating
    # complete information for each of the PCI device on the system. We need
    # all information for a PCI device before a proto for it can be created.
    # We will store data in a dictionary of dictionaries that looks like this:
    # data = { '0000:7f:0d.0': { 'class': '0x088000',
    #                            'vendor': '0x8086',
    #                            'device': '0x0ee1' } }
    # The key is location of PCI device on system in extended B/D/F notation
    # and value is a dictionary containing filename:data pairs for each file
    # returned by artifact collection for that PCI device.

    # Extended B/D/F is of form "domain:bus:device.function". Compile a regex
    # so we can use it to skip parsing files that don't match it.
    hc = r"[0-9A-Fa-f]"
    bdf_regex = re.compile(r"^%s+:%s+:%s+\.%s+" % (hc, hc, hc, hc))

    # This will make sure that when a non-existing 'key' (PCI location)
    # is accessed for the first time a new 'key':{} pair is auto-created
    data = collections.defaultdict(dict)

    for stat, file_obj in zip(stats, file_objects):
      filename = stat.pathspec.Basename()
      # Location of PCI device is the name of parent directory of returned file.
      bdf = stat.pathspec.Dirname().Basename()

      # Make sure we only parse files that are under a valid B/D/F folder
      if bdf_regex.match(bdf):
        # Remove newlines from all files except config. Config contains raw data
        # so we don't want to touch it even if it has a newline character.
        file_data = file_obj.read()
        if filename != "config":
          file_data = file_data.rstrip(b"\n")
        data[bdf][filename] = file_data

    # Now that we've captured all information for each PCI device. Let's convert
    # the dictionary into a list of PCIDevice protos.
    for bdf, bdf_filedata in iteritems(data):
      pci_device = rdf_client.PCIDevice()
      bdf_split = bdf.split(":")
      df_split = bdf_split[2].split(".")

      # We'll convert the hex into decimal to store in the protobuf.
      pci_device.domain = int(bdf_split[0], 16)
      pci_device.bus = int(bdf_split[1], 16)
      pci_device.device = int(df_split[0], 16)
      pci_device.function = int(df_split[1], 16)

      pci_device.class_id = bdf_filedata.get("class")
      pci_device.vendor = bdf_filedata.get("vendor")
      pci_device.vendor_device_id = bdf_filedata.get("device")
      pci_device.config = bdf_filedata.get("config")

      yield pci_device


class PasswdParser(parser.FileParser):
  """Parser for passwd files. Yields User semantic values."""

  output_types = ["User"]
  supported_artifacts = ["UnixPasswd"]

  @classmethod
  def ParseLine(cls, index, line):
    fields = "username,password,uid,gid,fullname,homedir,shell".split(",")
    try:
      if not line:
        return
      dat = dict(zip(fields, line.split(":")))
      user = rdf_client.User(
          username=dat["username"],
          uid=int(dat["uid"]),
          homedir=dat["homedir"],
          shell=dat["shell"],
          gid=int(dat["gid"]),
          full_name=dat["fullname"])
      return user

    except (IndexError, KeyError):
      raise parser.ParseError(
          "Invalid passwd file at line %d. %s" % ((index + 1), line))

  def Parse(self, stat, file_object, knowledge_base):
    """Parse the passwd file."""
    _, _ = stat, knowledge_base
    lines = [
        l.strip()
        for l in utils.ReadFileBytesAsUnicode(file_object).splitlines()
    ]
    for index, line in enumerate(lines):
      line = self.ParseLine(index, line)
      if line:
        yield line


class PasswdBufferParser(parser.GrepParser):
  """Parser for lines grepped from passwd files."""

  output_types = ["User"]
  supported_artifacts = ["LinuxPasswdHomedirs", "NssCacheLinuxPasswdHomedirs"]

  def Parse(self, filefinderresult, knowledge_base):
    _ = knowledge_base
    for index, line in enumerate([x.data for x in filefinderresult.matches]):
      line = PasswdParser.ParseLine(index, line.strip())
      if line:
        yield line


class UtmpStruct(utils.Struct):
  """Parse wtmp file from utmp.h."""
  _fields = [
      ("h", "ut_type"),
      ("i", "pid"),
      ("32s", "line"),
      ("4s", "id"),
      ("32s", "user"),
      ("256s", "host"),
      ("i", "exit"),
      ("i", "session"),
      ("i", "sec"),
      ("i", "usec"),
      ("i", "ip_1"),
      ("i", "ip_2"),
      ("i", "ip_3"),
      ("i", "ip_4"),
      ("20s", "nothing"),
  ]


class LinuxWtmpParser(parser.FileParser):
  """Simplified parser for linux wtmp files.

  Yields User semantic values for USER_PROCESS events.
  """

  output_types = ["User"]
  supported_artifacts = ["LinuxWtmp"]

  def Parse(self, stat, file_object, knowledge_base):
    """Parse the wtmp file."""
    _, _ = stat, knowledge_base
    users = {}
    wtmp = file_object.read()
    while wtmp:
      try:
        record = UtmpStruct(wtmp)
      except utils.ParsingError:
        break

      wtmp = wtmp[record.size:]
      # Users only appear for USER_PROCESS events, others are system.
      if record.ut_type != 7:
        continue

      # Lose the null termination
      record.user = record.user.split("\x00", 1)[0]

      # Store the latest login time.
      # TODO(user): remove the 0 here once RDFDatetime can support times
      # pre-epoch properly.
      try:
        users[record.user] = max(users[record.user], record.sec, 0)
      except KeyError:
        users[record.user] = record.sec

    for user, last_login in iteritems(users):
      yield rdf_client.User(
          username=utils.SmartUnicode(user), last_logon=last_login * 1000000)


class NetgroupParser(parser.FileParser):
  """Parser that extracts users from a netgroup file."""

  output_types = ["User"]
  supported_artifacts = ["NetgroupConfiguration"]
  # From useradd man page
  USERNAME_REGEX = r"^[a-z_][a-z0-9_-]{0,30}[$]?$"

  @classmethod
  def ParseLines(cls, lines):
    users = set()
    filter_regexes = [
        re.compile(x)
        for x in config.CONFIG["Artifacts.netgroup_filter_regexes"]
    ]
    username_regex = re.compile(cls.USERNAME_REGEX)
    blacklist = config.CONFIG["Artifacts.netgroup_user_blacklist"]
    for index, line in enumerate(lines):
      if line.startswith("#"):
        continue

      splitline = line.split(" ")
      group_name = splitline[0]

      if filter_regexes:
        filter_match = False
        for regex in filter_regexes:
          if regex.search(group_name):
            filter_match = True
            break
        if not filter_match:
          continue

      for member in splitline[1:]:
        if member.startswith("("):
          try:
            _, user, _ = member.split(",")
            if user not in users and user not in blacklist:
              if not username_regex.match(user):
                yield rdf_anomaly.Anomaly(
                    type="PARSER_ANOMALY",
                    symptom="Invalid username: %s" % user)
              else:
                users.add(user)
                yield rdf_client.User(username=utils.SmartUnicode(user))
          except ValueError:
            raise parser.ParseError(
                "Invalid netgroup file at line %d: %s" % (index + 1, line))

  def Parse(self, stat, file_object, knowledge_base):
    """Parse the netgroup file and return User objects.

    Lines are of the form:
      group1 (-,user1,) (-,user2,) (-,user3,)

    Groups are ignored, we return users in lines that match the filter regexes,
    or all users in the file if no filters are specified.

    We assume usernames are in the default regex format specified in the adduser
    man page.  Notably no non-ASCII characters.

    Args:
      stat: unused statentry
      file_object: netgroup VFSFile
      knowledge_base: unused

    Returns:
      rdf_client.User
    """
    _, _ = stat, knowledge_base
    lines = [
        l.strip()
        for l in utils.ReadFileBytesAsUnicode(file_object).splitlines()
    ]
    return self.ParseLines(lines)


class NetgroupBufferParser(parser.GrepParser):
  """Parser for lines grepped from /etc/netgroup files."""

  output_types = ["User"]

  def Parse(self, filefinderresult, knowledge_base):
    _ = knowledge_base
    return NetgroupParser.ParseLines(
        [x.data.encode("utf-8").strip() for x in filefinderresult.matches])


class LinuxBaseShadowParser(parser.FileMultiParser):
  """Base parser to process user/groups with shadow files."""

  # A list of hash types and hash matching expressions.
  hashes = [("SHA512", re.compile(r"\$6\$[A-z\d\./]{0,16}\$[A-z\d\./]{86}$")),
            ("SHA256", re.compile(r"\$5\$[A-z\d\./]{0,16}\$[A-z\d\./]{43}$")),
            ("DISABLED", re.compile(r"!.*")), ("UNSET", re.compile(r"\*.*")),
            ("MD5", re.compile(r"\$1\$([A-z\d\./]{1,8}\$)?[A-z\d\./]{22}$")),
            ("DES", re.compile(r"[A-z\d\./]{2}.{11}$")),
            ("BLOWFISH", re.compile(r"\$2a?\$\d\d\$[A-z\d\.\/]{22}$")),
            ("NTHASH", re.compile(r"\$3\$")), ("UNUSED", re.compile(r"\$4\$"))]

  # Prevents this from automatically registering.
  __abstract = True  # pylint: disable=g-bad-name

  base_store = None
  shadow_store = None

  def __init__(self, *args, **kwargs):
    super(LinuxBaseShadowParser, self).__init__(*args, **kwargs)
    # Entries as defined by "getent", i.e. account databases used by nsswitch.
    self.entry = {}
    # Shadow files
    self.shadow = {}

  def GetPwStore(self, pw_attr):
    """Decide if the  passwd field is a passwd or a reference to shadow.

    Evaluates the contents of the password field to determine how the password
    is stored.
    - If blank either no password is required or no access is granted.
      This behavior is system and application dependent.
    - If 'x', the encrypted password is stored in /etc/shadow.
    - Otherwise, the password is any other string, it's treated as an encrypted
      password.

    Args:
      pw_attr: The password field as a string.

    Returns:
      An enum indicating the location of the password store.
    """
    # PwEntry.PwStore enum values.
    if pw_attr == "x":
      return self.shadow_store
    return self.base_store

  def GetHashType(self, hash_str):
    """Identify the type of hash in a hash string.

    Args:
      hash_str: A string value that may be a hash.

    Returns:
      A string description of the type of hash.
    """
    # Return the type of the first matching hash.
    for hash_type, hash_re in self.hashes:
      if hash_re.match(hash_str):
        return hash_type
    # No hash matched.
    return "EMPTY"

  def _ParseFile(self, file_obj, line_parser):
    """Process a file line by line.

    Args:
      file_obj: The file to parse.
      line_parser: The parser method used to process and store line content.

    Raises:
      parser.ParseError if the parser is unable to process the line.
    """
    lines = [
        l.strip() for l in utils.ReadFileBytesAsUnicode(file_obj).splitlines()
    ]
    try:
      for index, line in enumerate(lines):
        if line:
          line_parser(line)
    except (IndexError, KeyError) as e:
      raise parser.ParseError("Invalid file at line %d: %s" % (index + 1, e))

  def ReconcileShadow(self, store_type):
    """Verify that entries that claim to use shadow files have a shadow entry.

    If the entries of the non-shadowed file indicate that a shadow file is used,
    check that there is actually an entry for that file in shadow.

    Args:
      store_type: The type of password store that should be used (e.g.
        /etc/shadow or /etc/gshadow)
    """
    for k, v in iteritems(self.entry):
      if v.pw_entry.store == store_type:
        shadow_entry = self.shadow.get(k)
        if shadow_entry:
          v.pw_entry = shadow_entry
        else:
          v.pw_entry.store = "UNKNOWN"

  def _Anomaly(self, msg, found):
    return rdf_anomaly.Anomaly(
        type="PARSER_ANOMALY", symptom=msg, finding=found)

  @staticmethod
  def MemberDiff(data1, set1_name, data2, set2_name):
    """Helper method to perform bidirectional set differences."""
    set1 = set(data1)
    set2 = set(data2)
    diffs = []
    msg = "Present in %s, missing in %s: %s"
    if set1 != set2:
      in_set1 = set1 - set2
      in_set2 = set2 - set1
      if in_set1:
        diffs.append(msg % (set1_name, set2_name, ",".join(in_set1)))
      if in_set2:
        diffs.append(msg % (set2_name, set1_name, ",".join(in_set2)))
    return diffs

  def ParseMultiple(self, stats, file_objs, kb):
    """Process files together."""
    fileset = {stat.pathspec.path: obj for stat, obj in zip(stats, file_objs)}
    return self.ParseFileset(fileset)


class LinuxSystemGroupParser(LinuxBaseShadowParser):
  """Parser for group files. Yields Group semantic values."""

  output_types = ["Group"]
  supported_artifacts = ["LoginPolicyConfiguration"]

  base_store = "GROUP"
  shadow_store = "GSHADOW"

  def __init__(self, *args, **kwargs):
    super(LinuxSystemGroupParser, self).__init__(*args, **kwargs)
    self.gshadow_members = {}

  def ParseGshadowEntry(self, line):
    """Extract the members of each group from /etc/gshadow.

    Identifies the groups in /etc/gshadow and several attributes of the group,
    including how the password is crypted (if set).

    gshadow files have the format group_name:passwd:admins:members
    admins are both group members and can manage passwords and memberships.

    Args:
      line: An entry in gshadow.
    """
    fields = ("name", "passwd", "administrators", "members")
    if line:
      rslt = dict(zip(fields, line.split(":")))
      # Add the shadow state to the internal store.
      name = rslt["name"]
      pw_entry = self.shadow.setdefault(name, rdf_client.PwEntry())
      pw_entry.store = self.shadow_store
      pw_entry.hash_type = self.GetHashType(rslt["passwd"])
      # Add the members to the internal store.
      members = self.gshadow_members.setdefault(name, set())
      for accts in rslt["administrators"], rslt["members"]:
        if accts:
          members.update(accts.split(","))

  def ParseGroupEntry(self, line):
    """Extract the members of a group from /etc/group."""
    fields = ("name", "passwd", "gid", "members")
    if line:
      rslt = dict(zip(fields, line.split(":")))
      name = rslt["name"]
      group = self.entry.setdefault(name, rdf_client.Group(name=name))
      group.pw_entry.store = self.GetPwStore(rslt["passwd"])
      if group.pw_entry.store == self.base_store:
        group.pw_entry.hash_type = self.GetHashType(rslt["passwd"])
      # If the group contains NIS entries, they may not have a gid.
      if rslt["gid"]:
        group.gid = int(rslt["gid"])
      group.members = set(rslt["members"].split(","))

  def MergeMembers(self):
    """Add shadow group members to the group if gshadow is used.

    Normally group and shadow should be in sync, but no guarantees. Merges the
    two stores as membership in either file may confer membership.
    """
    for group_name, members in iteritems(self.gshadow_members):
      group = self.entry.get(group_name)
      if group and group.pw_entry.store == self.shadow_store:
        group.members = members.union(group.members)

  def FindAnomalies(self):
    """Identify any anomalous group attributes or memberships."""
    for grp_name, group in iteritems(self.entry):
      shadow = self.shadow.get(grp_name)
      gshadows = self.gshadow_members.get(grp_name, [])
      if shadow:
        diff = self.MemberDiff(group.members, "group", gshadows, "gshadow")
        if diff:
          msg = "Group/gshadow members differ in group: %s" % grp_name
          yield self._Anomaly(msg, diff)

    diff = self.MemberDiff(self.entry, "group", self.gshadow_members, "gshadow")
    if diff:
      yield self._Anomaly("Mismatched group and gshadow files.", diff)

  def ParseFileset(self, fileset=None):
    """Process linux system group and gshadow files.

    Orchestrates collection of account entries from /etc/group and /etc/gshadow.
    The group and gshadow entries are reconciled and member users are added to
    the entry.

    Args:
      fileset: A dict of files mapped from path to an open file.

    Yields:
      - A series of Group entries, each of which is populated with group
        [memberships and indications of the shadow state of any group password.
      - A series of anomalies in cases where there are mismatches between group
        and gshadow states.
    """
    # Get relevant shadow attributes.
    gshadow = fileset.get("/etc/gshadow")
    if gshadow:
      self._ParseFile(gshadow, self.ParseGshadowEntry)
    else:
      logging.debug("No /etc/gshadow file.")
    group = fileset.get("/etc/group")
    if group:
      self._ParseFile(group, self.ParseGroupEntry)
    else:
      logging.debug("No /etc/group file.")
    self.ReconcileShadow(self.shadow_store)
    # Identify any anomalous group/shadow entries.
    # This needs to be done before memberships are merged: merged memberships
    # are the *effective* membership regardless of wierd configurations.
    for anom in self.FindAnomalies():
      yield anom
    # Then add shadow group members to the group membership.
    self.MergeMembers()
    for group in itervalues(self.entry):
      yield group


class LinuxSystemPasswdParser(LinuxBaseShadowParser):
  """Parser for local accounts."""

  output_types = ["User"]
  supported_artifacts = ["LoginPolicyConfiguration"]

  base_store = "PASSWD"
  shadow_store = "SHADOW"

  def __init__(self, *args, **kwargs):
    super(LinuxSystemPasswdParser, self).__init__(*args, **kwargs)
    self.groups = {}  # Groups mapped by name.
    self.memberships = {}  # Group memberships per user.
    self.uids = {}  # Assigned uids
    self.gids = {}  # Assigned gids

  def ParseShadowEntry(self, line):
    """Extract the user accounts in /etc/shadow.

    Identifies the users in /etc/shadow and several attributes of their account,
    including how their password is crypted and password aging characteristics.

    Args:
      line: An entry of the shadow file.
    """
    fields = ("login", "passwd", "last_change", "min_age", "max_age",
              "warn_time", "inactivity", "expire", "reserved")
    if line:
      rslt = dict(zip(fields, line.split(":")))
      pw_entry = self.shadow.setdefault(rslt["login"], rdf_client.PwEntry())
      pw_entry.store = self.shadow_store
      pw_entry.hash_type = self.GetHashType(rslt["passwd"])
      # Tread carefully here in case these values aren't set.
      last_change = rslt.get("last_change")
      if last_change:
        pw_entry.age = int(last_change)
      max_age = rslt.get("max_age")
      if max_age:
        pw_entry.max_age = int(max_age)

  def ParsePasswdEntry(self, line):
    """Process the passwd entry fields and primary group memberships."""
    fields = ("uname", "passwd", "uid", "gid", "fullname", "homedir", "shell")
    if line:
      rslt = dict(zip(fields, line.split(":")))
      user = self.entry.setdefault(rslt["uname"], rdf_client.User())
      user.username = rslt["uname"]
      user.pw_entry.store = self.GetPwStore(rslt["passwd"])
      if user.pw_entry.store == self.base_store:
        user.pw_entry.hash_type = self.GetHashType(rslt["passwd"])
      # If the passwd file contains NIS entries they may not have uid/gid set.
      if rslt["uid"]:
        user.uid = int(rslt["uid"])
      if rslt["gid"]:
        user.gid = int(rslt["gid"])
      user.homedir = rslt["homedir"]
      user.shell = rslt["shell"]
      user.full_name = rslt["fullname"]
      # Map uid numbers to detect duplicates.
      uids = self.uids.setdefault(user.uid, set())
      uids.add(user.username)
      # Map primary group memberships to populate memberships.
      gid = self.gids.setdefault(user.gid, set())
      gid.add(user.username)

  def _Members(self, group):
    """Unify members of a group and accounts with the group as primary gid."""
    group.members = set(group.members).union(self.gids.get(group.gid, []))
    return group

  def AddGroupMemberships(self):
    """Adds aggregate group membership from group, gshadow and passwd."""
    self.groups = {g.name: self._Members(g) for g in itervalues(self.groups)}
    # Map the groups a user is a member of, irrespective of primary/extra gid.
    for g in itervalues(self.groups):
      for user in g.members:
        membership = self.memberships.setdefault(user, set())
        membership.add(g.gid)
    # Now add the completed membership to the user account.
    for user in itervalues(self.entry):
      user.gids = self.memberships.get(user.username)

  def FindAnomalies(self):
    """Identify anomalies in the password/shadow and group/gshadow data."""
    # Find anomalous group entries.
    findings = []
    group_entries = {g.gid for g in itervalues(self.groups)}
    for gid in set(self.gids) - group_entries:
      undefined = ",".join(self.gids.get(gid, []))
      findings.append(
          "gid %d assigned without /etc/groups entry: %s" % (gid, undefined))
    if findings:
      yield self._Anomaly("Accounts with invalid gid.", findings)

    # Find any shared user IDs.
    findings = []
    for uid, names in iteritems(self.uids):
      if len(names) > 1:
        findings.append("uid %d assigned to multiple accounts: %s" %
                        (uid, ",".join(sorted(names))))
    if findings:
      yield self._Anomaly("Accounts with shared uid.", findings)

    # Find privileged groups with unusual members.
    findings = []
    root_grp = self.groups.get("root")
    if root_grp:
      root_members = sorted([m for m in root_grp.members if m != "root"])
      if root_members:
        findings.append("Accounts in 'root' group: %s" % ",".join(root_members))
    if findings:
      yield self._Anomaly("Privileged group with unusual members.", findings)

    # Find accounts without passwd/shadow entries.
    diffs = self.MemberDiff(self.entry, "passwd", self.shadow, "shadow")
    if diffs:
      yield self._Anomaly("Mismatched passwd and shadow files.", diffs)

  def AddPassword(self, fileset):
    """Add the passwd entries to the shadow store."""
    passwd = fileset.get("/etc/passwd")
    if passwd:
      self._ParseFile(passwd, self.ParsePasswdEntry)
    else:
      logging.debug("No /etc/passwd file.")

  def AddShadow(self, fileset):
    """Add the shadow entries to the shadow store."""
    shadow = fileset.get("/etc/shadow")
    if shadow:
      self._ParseFile(shadow, self.ParseShadowEntry)
    else:
      logging.debug("No /etc/shadow file.")

  def ParseFileset(self, fileset=None):
    """Process linux system login files.

    Orchestrates collection of  account entries from /etc/passwd and
    /etc/shadow. The passwd and shadow entries are reconciled and group
    memberships are mapped to the account.

    Args:
      fileset: A dict of files mapped from path to an open file.

    Yields:
      - A series of User entries, each of which is populated with
         group memberships and indications of the shadow state of the account.
      - A series of anomalies in cases where there are mismatches between passwd
        and shadow state.
    """
    self.AddPassword(fileset)
    self.AddShadow(fileset)
    self.ReconcileShadow(self.shadow_store)
    # Get group memberships using the files that were already collected.
    # Separate out groups and anomalies.
    for rdf in LinuxSystemGroupParser().ParseFileset(fileset):
      if isinstance(rdf, rdf_client.Group):
        self.groups[rdf.name] = rdf
      else:
        yield rdf
    self.AddGroupMemberships()
    for user in itervalues(self.entry):
      yield user
    for grp in itervalues(self.groups):
      yield grp
    for anom in self.FindAnomalies():
      yield anom


class PathParser(parser.FileParser):
  """Parser for dotfile entries.

  Extracts path attributes from dotfiles to infer effective paths for users.
  This parser doesn't attempt or expect to determine path state for all cases,
  rather, it is a best effort attempt to detect common misconfigurations. It is
  not intended to detect maliciously obfuscated path modifications.
  """
  output_types = ["AttributedDict"]
  # TODO(user): Modify once a decision is made on contextual selection of
  # parsed results for artifact data.
  supported_artifacts = [
      "GlobalShellConfigs", "RootUserShellConfigs", "UsersShellConfigs"
  ]

  # https://cwe.mitre.org/data/definitions/426.html
  _TARGETS = ("CLASSPATH", "LD_AOUT_LIBRARY_PATH", "LD_AOUT_PRELOAD",
              "LD_LIBRARY_PATH", "LD_PRELOAD", "MODULE_PATH", "PATH",
              "PERL5LIB", "PERLLIB", "PYTHONPATH", "RUBYLIB")
  _SH_CONTINUATION = ("{", "}", "||", "&&", "export")

  _CSH_FILES = (".login", ".cshrc", ".tcsh", "csh.cshrc", "csh.login",
                "csh.logout")
  # This matches "set a = (b . ../../.. )", "set a=(. b c)" etc.
  _CSH_SET_RE = re.compile(r"(\w+)\s*=\s*\((.*)\)$")

  # This matches $PATH, ${PATH}, "$PATH" and "${   PATH }" etc.
  # Omits more fancy parameter expansion e.g. ${unset_val:=../..}
  _SHELLVAR_RE = re.compile(r'"?\$\{?\s*(\w+)\s*\}?"?')

  def __init__(self, *args, **kwargs):
    super(PathParser, self).__init__(*args, **kwargs)
    # Terminate entries on ";" to capture multiple values on one line.
    self.parser = config_file.FieldParser(term=r"[\r\n;]")

  def _ExpandPath(self, target, vals, paths):
    """Extract path information, interpolating current path values as needed."""
    if target not in self._TARGETS:
      return
    expanded = []
    for val in vals:
      # Null entries specify the current directory, so :a::b:c: is equivalent
      # to .:a:.:b:c:.
      shellvar = self._SHELLVAR_RE.match(val)
      if not val:
        expanded.append(".")
      elif shellvar:
        # The value may actually be in braces as well. Always convert to upper
        # case so we deal with stuff like lowercase csh path.
        existing = paths.get(shellvar.group(1).upper())
        if existing:
          expanded.extend(existing)
        else:
          expanded.append(val)
      else:
        expanded.append(val)
    paths[target] = expanded

  def _ParseShVariables(self, lines):
    """Extract env_var and path values from sh derivative shells.

    Iterates over each line, word by word searching for statements that set the
    path. These are either variables, or conditions that would allow a variable
    to be set later in the line (e.g. export).

    Args:
      lines: A list of lines, each of which is a list of space separated words.

    Returns:
      a dictionary of path names and values.
    """
    paths = {}
    for line in lines:
      for entry in line:
        if "=" in entry:
          # Pad out the list so that it's always 2 elements, even if the split
          # failed.
          target, vals = (entry.split("=", 1) + [""])[:2]
          if vals:
            path_vals = vals.split(":")
          else:
            path_vals = []
          self._ExpandPath(target, path_vals, paths)
        elif entry not in self._SH_CONTINUATION:
          # Stop processing the line unless the entry might allow paths to still
          # be set, e.g.
          #   reserved words: "export"
          #   conditions: { PATH=VAL } && PATH=:$PATH || PATH=.
          break
    return paths

  def _ParseCshVariables(self, lines):
    """Extract env_var and path values from csh derivative shells.

    Path attributes can be set several ways:
    - setenv takes the form "setenv PATH_NAME COLON:SEPARATED:LIST"
    - set takes the form "set path_name=(space separated list)" and is
      automatically exported for several types of files.

    The first entry in each stanza is used to decide what context to use.
    Other entries are used to identify the path name and any assigned values.

    Args:
      lines: A list of lines, each of which is a list of space separated words.

    Returns:
      a dictionary of path names and values.
    """
    paths = {}
    for line in lines:
      if len(line) < 2:
        continue
      action = line[0]
      if action == "setenv":
        target = line[1]
        path_vals = []
        if line[2:]:
          path_vals = line[2].split(":")
        self._ExpandPath(target, path_vals, paths)
      elif action == "set":
        set_vals = self._CSH_SET_RE.search(" ".join(line[1:]))
        if set_vals:
          target, vals = set_vals.groups()
          # Automatically exported to ENV vars.
          if target in ("path", "term", "user"):
            target = target.upper()
          path_vals = vals.split()
          self._ExpandPath(target, path_vals, paths)
    return paths

  def Parse(self, stat, file_obj, knowledge_base):
    """Identifies the paths set within a file.

    Expands paths within the context of the file, but does not infer fully
    expanded paths from external states. There are plenty of cases where path
    attributes are unresolved, e.g. sourcing other files.

    Lines are not handled literally. A field parser is used to:
    - Break lines with multiple distinct statements into separate lines (e.g.
      lines with a ';' separating stanzas.
    - Strip out comments.
    - Handle line continuations to capture multi-line configurations into one
      statement.

    Args:
      stat: statentry
      file_obj: VFSFile
      knowledge_base: unused

    Yields:
      An attributed dict for each env vars. 'name' contains the path name, and
      'vals' contains its vals.
    """
    _ = knowledge_base
    lines = self.parser.ParseEntries(utils.ReadFileBytesAsUnicode(file_obj))
    if os.path.basename(stat.pathspec.path) in self._CSH_FILES:
      paths = self._ParseCshVariables(lines)
    else:
      paths = self._ParseShVariables(lines)
    for path_name, path_vals in iteritems(paths):
      yield rdf_protodict.AttributedDict(
          config=stat.pathspec.path, name=path_name, vals=path_vals)
