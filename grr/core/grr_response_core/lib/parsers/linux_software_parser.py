#!/usr/bin/env python
"""Simple parsers for Linux files."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re
from grr_response_core.lib import parsers
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import client as rdf_client


class DebianPackagesStatusParser(parsers.SingleFileParser):
  """Parser for /var/lib/dpkg/status. Yields SoftwarePackage semantic values."""

  output_types = [rdf_client.SoftwarePackages]
  supported_artifacts = ["DebianPackagesStatus"]

  installed_re = re.compile(r"^\w+ \w+ installed$")

  def __init__(self, deb822):
    """Initializes the parser.

    Args:
      deb822: An accessor for RFC822-like data formats.
    """
    self._deb822 = deb822

  def ParseFile(self, knowledge_base, pathspec, filedesc):
    del knowledge_base  # Unused.
    del pathspec  # Unused.

    packages = []
    sw_data = utils.ReadFileBytesAsUnicode(filedesc)
    try:
      for pkg in self._deb822.Packages.iter_paragraphs(sw_data.splitlines()):
        if self.installed_re.match(pkg["Status"]):
          packages.append(
              rdf_client.SoftwarePackage(
                  name=pkg["Package"],
                  description=pkg["Description"],
                  version=pkg["Version"],
                  architecture=pkg["Architecture"],
                  publisher=pkg["Maintainer"],
                  install_state="INSTALLED"))
    except SystemError:
      yield rdf_anomaly.Anomaly(
          type="PARSER_ANOMALY", symptom="Invalid dpkg status file")
    finally:
      if packages:
        yield rdf_client.SoftwarePackages(packages=packages)
