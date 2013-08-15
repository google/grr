#!/usr/bin/env python
"""Simple parsers for Linux files."""


from grr.lib import parsers
from grr.lib import rdfvalue


class PasswdParser(parsers.CommandParser):
  """Parser for passwd files. Yields User semantic values."""

  output_types = ["User"]
  supported_artifacts = ["LinuxPasswd"]

  def Parse(self, stat, file_object, knowledge_base):
    """Parse the passwd file."""
    _, _ = stat, knowledge_base
    fields = "username,password,uid,gid,fullname,homedir,shell".split(",")
    lines = [l.strip() for l in file_object.read(100000).splitlines()]
    for index, line in enumerate(lines):
      try:
        if not line: continue
        dat = dict(zip(fields, line.split(":")))
        user = rdfvalue.KnowledgeBaseUser(
            username=dat["username"], uid=int(dat["uid"]),
            homedir=dat["homedir"], shell=dat["shell"], gid=int(dat["gid"])
            )
        yield user

      except (IndexError, KeyError):
        raise parsers.ParseError("Invalid passwd file at line %d. %s" %
                                 ((index + 1), line))
