#!/usr/bin/env python
# Lint as: python3
"""Simple parsers for Linux files."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re
from typing import IO
from typing import Iterator

from grr_response_core.lib import parsers
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import paths as rdf_paths


class DebianPackagesStatusParser(
    parsers.SingleFileParser[rdf_client.SoftwarePackages]):
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

  def ParseFile(
      self,
      knowledge_base: rdf_client.KnowledgeBase,
      pathspec: rdf_paths.PathSpec,
      filedesc: IO[bytes],
  ) -> Iterator[rdf_client.SoftwarePackages]:
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
