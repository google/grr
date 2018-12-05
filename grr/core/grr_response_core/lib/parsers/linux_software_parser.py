#!/usr/bin/env python
"""Simple parsers for Linux files."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from grr_response_core.lib import parser
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import client as rdf_client


class DebianPackagesStatusParser(parser.FileParser):
  """Parser for /var/lib/dpkg/status. Yields SoftwarePackage semantic values."""

  output_types = ["SoftwarePackage"]
  supported_artifacts = ["DebianPackagesStatus"]

  installed_re = re.compile(r"^\w+ \w+ installed$")

  def __init__(self, deb822):
    """Initializes the parser.

    Args:
      deb822: An accessor for RFC822-like data formats.
    """
    self._deb822 = deb822

  def Parse(self, stat, file_object, knowledge_base):
    """Parse the status file."""
    _, _ = stat, knowledge_base

    try:
      sw_data = utils.ReadFileBytesAsUnicode(file_object)
      for pkg in self._deb822.Packages.iter_paragraphs(sw_data.splitlines()):
        if self.installed_re.match(pkg["Status"]):
          soft = rdf_client.SoftwarePackage(
              name=pkg["Package"],
              description=pkg["Description"],
              version=pkg["Version"],
              architecture=pkg["Architecture"],
              publisher=pkg["Maintainer"],
              install_state="INSTALLED")
          yield soft
    except SystemError:
      yield rdf_anomaly.Anomaly(
          type="PARSER_ANOMALY", symptom="Invalid dpkg status file")
