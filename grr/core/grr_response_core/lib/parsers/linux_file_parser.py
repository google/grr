#!/usr/bin/env python
"""Simple parsers for Linux files."""

from typing import IO, Iterator, Optional

from grr_response_core.lib import parsers
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import precondition


class PasswdParser(parsers.SingleFileParser[rdf_client.User]):
  """Parser for passwd files. Yields User semantic values."""

  output_types = [rdf_client.User]
  supported_artifacts = ["UnixPasswdFile"]

  @classmethod
  def ParseLine(cls, index, line) -> Optional[rdf_client.User]:
    precondition.AssertType(line, str)

    fields = "username,password,uid,gid,fullname,homedir,shell".split(",")
    try:
      if not line:
        return None
      dat = dict(zip(fields, line.split(":")))
      user = rdf_client.User(
          username=dat["username"],
          uid=int(dat["uid"]),
          homedir=dat["homedir"],
          shell=dat["shell"],
          gid=int(dat["gid"]),
          full_name=dat["fullname"],
      )
      return user

    except (IndexError, KeyError) as e:
      raise parsers.ParseError(
          "Invalid passwd file at line %d. %s" % ((index + 1), line)
      ) from e

  def ParseFile(
      self,
      knowledge_base: rdf_client.KnowledgeBase,
      pathspec: rdf_paths.PathSpec,
      filedesc: IO[bytes],
  ) -> Iterator[rdf_client.User]:
    del knowledge_base  # Unused.
    del pathspec  # Unused.

    lines = [
        l.strip() for l in utils.ReadFileBytesAsUnicode(filedesc).splitlines()
    ]
    for index, line in enumerate(lines):
      user = self.ParseLine(index, line)
      if user is not None:
        yield user


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
