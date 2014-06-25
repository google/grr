#!/usr/bin/env python
"""Simple parsers for Linux files."""
import re
from debian_bundle import deb822

from grr.lib import parsers
from grr.lib import rdfvalue


class DebianPackagesStatusParser(parsers.FileParser):
  """Parser for /var/lib/dpkg/status. Yields SoftwarePackage semantic values."""

  output_types = ["SoftwarePackage"]
  supported_artifacts = ["DebianPackagesStatus"]

  installed_re = re.compile(r"^\w+ \w+ installed$")

  def Parse(self, stat, file_object, knowledge_base):
    """Parse the status file."""
    _, _ = stat, knowledge_base
    try:
      for pkg in deb822.Packages.iter_paragraphs(file_object):
        if self.installed_re.match(pkg["Status"]):
          soft = rdfvalue.SoftwarePackage(
              name=pkg["Package"],
              description=pkg["Description"],
              version=pkg["Version"],
              architecture=pkg["Architecture"],
              publisher=pkg["Maintainer"],
              install_state="INSTALLED")
          yield soft
    except SystemError:
      yield rdfvalue.Anomaly(type="PARSER_ANOMALY",
                             symptom="Invalid dpkg status file")
