#!/usr/bin/env python
"""Simple parsers for Linux files."""
import re


from grr.lib import config_lib
from grr.lib import parsers
from grr.lib import rdfvalue
from grr.lib import utils


class PasswdParser(parsers.FileParser):
  """Parser for passwd files. Yields KnowledgeBaseUser semantic values."""

  output_types = ["KnowledgeBaseUser"]
  supported_artifacts = ["LinuxPasswd"]

  @classmethod
  def ParseLine(cls, index, line):
    fields = "username,password,uid,gid,fullname,homedir,shell".split(",")
    try:
      if not line: return
      dat = dict(zip(fields, line.split(":")))
      user = rdfvalue.KnowledgeBaseUser(username=dat["username"],
                                        uid=int(dat["uid"]),
                                        homedir=dat["homedir"],
                                        shell=dat["shell"],
                                        gid=int(dat["gid"]),
                                        full_name=dat["fullname"])
      return user

    except (IndexError, KeyError):
      raise parsers.ParseError(
          "Invalid passwd file at line %d. %s" % ((index + 1), line))

  def Parse(self, stat, file_object, knowledge_base):
    """Parse the passwd file."""
    _, _ = stat, knowledge_base
    lines = [l.strip() for l in file_object.read(100000).splitlines()]
    for index, line in enumerate(lines):
      line = self.ParseLine(index, line)
      if line:
        yield line


class PasswdBufferParser(parsers.GrepParser):
  """Parser for lines grepped from passwd files."""

  output_types = ["KnowledgeBaseUser"]
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


class LinuxWtmpParser(parsers.FileParser):
  """Simplified parser for linux wtmp files.

  Yields KnowledgeBaseUser semantic values for USER_PROCESS events.
  """

  output_types = ["KnowledgeBaseUser"]
  supported_artifacts = ["LinuxWtmp"]

  def Parse(self, stat, file_object, knowledge_base):
    """Parse the wtmp file."""
    _, _ = stat, knowledge_base
    users = {}
    wtmp = file_object.read(10000000)
    while wtmp:
      try:
        record = UtmpStruct(wtmp)
      except RuntimeError:
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

    for user, last_login in users.iteritems():
      yield rdfvalue.KnowledgeBaseUser(username=utils.SmartUnicode(user),
                                       last_logon=last_login*1000000)


class NetgroupParser(parsers.FileParser):
  """Parser that extracts users from a netgroup file."""

  output_types = ["KnowledgeBaseUser"]
  supported_artifacts = ["NetgroupConfiguration"]
  # From useradd man page
  USERNAME_REGEX = r"^[a-z_][a-z0-9_-]{0,30}[$]?$"

  @classmethod
  def ParseLines(cls, lines):
    users = set()
    filter_regexes = [re.compile(x) for x in
                      config_lib.CONFIG["Artifacts.netgroup_filter_regexes"]]
    username_regex = re.compile(cls.USERNAME_REGEX)
    blacklist = config_lib.CONFIG["Artifacts.netgroup_user_blacklist"]
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
                yield rdfvalue.Anomaly(type="PARSER_ANOMALY",
                                       symptom="Invalid username: %s" % user)
              else:
                users.add(user)
                yield rdfvalue.KnowledgeBaseUser(
                    username=utils.SmartUnicode(user))
          except ValueError:
            raise parsers.ParseError("Invalid netgroup file at line %d: %s" %
                                     (index + 1, line))

  def Parse(self, stat, file_object, knowledge_base):
    """Parse the netgroup file and return KnowledgeBaseUser objects.

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
      rdfvalue.KnowledgeBaseUser
    """
    _, _ = stat, knowledge_base
    lines = [l.strip() for l in file_object.read(100000).splitlines()]
    return self.ParseLines(lines)


class NetgroupBufferParser(parsers.GrepParser):
  """Parser for lines grepped from /etc/netgroup files."""

  output_types = ["KnowledgeBaseUser"]

  def Parse(self, filefinderresult, knowledge_base):
    _ = knowledge_base
    return NetgroupParser.ParseLines(
        [x.data.strip() for x in filefinderresult.matches])

