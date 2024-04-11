#!/usr/bin/env python
"""Simple parsers for the output of linux commands."""

import re

from grr_response_core.lib import parser
from grr_response_core.lib import parsers
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import client as rdf_client


class RpmCmdParser(parser.CommandParser):
  """Parser for rpm qa output. Yields SoftwarePackage rdfvalues."""

  output_types = [rdf_client.SoftwarePackages]
  supported_artifacts = ["RedhatPackagesList"]

  def Parse(self, cmd, args, stdout, stderr, return_val, knowledge_base):
    """Parse the rpm -qa output."""
    _ = args, knowledge_base  # Unused.
    rpm_re = re.compile(r"^(\w[-\w\+]+?)-(\d.*)$")
    self.CheckReturn(cmd, return_val)
    packages = []
    for line in stdout.decode("utf-8").splitlines():
      pkg_match = rpm_re.match(line.strip())
      if pkg_match:
        name, version = pkg_match.groups()
        packages.append(
            rdf_client.SoftwarePackage.Installed(name=name, version=version)
        )
    if packages:
      yield rdf_client.SoftwarePackages(packages=packages)

    for line in stderr.decode("utf-8").splitlines():
      if "error: rpmdbNextIterator: skipping h#" in line:
        yield rdf_anomaly.Anomaly(
            type="PARSER_ANOMALY", symptom="Broken rpm database."
        )
        break


class DpkgCmdParser(parser.CommandParser):
  """Parser for dpkg output. Yields SoftwarePackage rdfvalues."""

  output_types = [rdf_client.SoftwarePackages]
  supported_artifacts = ["DebianPackagesList"]

  def Parse(self, cmd, args, stdout, stderr, return_val, knowledge_base):
    """Parse the dpkg output."""
    _ = stderr, args, knowledge_base  # Unused.
    self.CheckReturn(cmd, return_val)
    lines = stdout.decode("utf-8").splitlines()
    num_columns = 0
    i = 0
    packages = []

    for i, line in enumerate(lines):
      if line.startswith("+++-"):
        # This is a special header line that determines column size.
        columns = line.split("-")
        num_columns = len(columns)
        for col in columns[1:]:
          if not re.match("=*", col):
            raise parsers.ParseError(
                "Invalid header parsing for %s at line %s" % (cmd, i)
            )
        break

    if num_columns == 0:
      return
    elif num_columns not in [4, 5]:
      raise ValueError(
          "Bad number of columns ({}) in dpkg --list output:\n{}\n...".format(
              num_columns, "\n".join(lines[:10])
          )
      )

    for line in lines[i + 1 :]:
      # Split the line at whitespace into at most `num_columns` columns.
      columns = line.split(None, num_columns - 1)

      # If the last column (description) is empty, pad it with None.
      if len(columns) == num_columns - 1:
        columns.append(None)

      if num_columns == 5:
        # Installed, Name, Version, Architecture, Description
        status, name, version, arch, desc = columns
      else:  # num_columns is 4
        # Older versions of dpkg don't print Architecture
        status, name, version, desc = columns
        arch = None

      # Status is potentially 3 columns, but always at least two, desired and
      # actual state. We only care about actual state.
      if status[1] == "i":
        status = rdf_client.SoftwarePackage.InstallState.INSTALLED
      else:
        status = rdf_client.SoftwarePackage.InstallState.UNKNOWN

      packages.append(
          rdf_client.SoftwarePackage(
              name=name,
              description=desc,
              version=version,
              architecture=arch,
              install_state=status,
          )
      )

    if packages:
      yield rdf_client.SoftwarePackages(packages=packages)


class DmidecodeCmdParser(parser.CommandParser):
  """Parser for dmidecode output. Yields HardwareInfo rdfvalues."""

  output_types = [rdf_client.HardwareInfo]
  supported_artifacts = ["LinuxHardwareInfo"]

  def _re_compile(self, search_str):
    return re.compile(r"\s*%s: ([0-9a-zA-Z-\s./#_=]*)" % (search_str))

  def Parse(self, cmd, args, stdout, stderr, return_val, knowledge_base):
    """Parse the dmidecode output. All data is parsed into a dictionary."""
    _ = stderr, args, knowledge_base  # Unused.
    self.CheckReturn(cmd, return_val)
    output = iter(stdout.decode("utf-8").splitlines())

    # Compile all regexes in advance.
    sys_info_re = re.compile(r"\s*System Information")
    sys_regexes = {
        "system_manufacturer": self._re_compile("Manufacturer"),
        "serial_number": self._re_compile("Serial Number"),
        "system_product_name": self._re_compile("Product Name"),
        "system_uuid": self._re_compile("UUID"),
        "system_sku_number": self._re_compile("SKU Number"),
        "system_family": self._re_compile("Family"),
        "system_assettag": self._re_compile("Asset Tag"),
    }

    bios_info_re = re.compile(r"\s*BIOS Information")
    bios_regexes = {
        "bios_vendor": self._re_compile("Vendor"),
        "bios_version": self._re_compile("Version"),
        "bios_release_date": self._re_compile("Release Date"),
        "bios_rom_size": self._re_compile("ROM Size"),
        "bios_revision": self._re_compile("BIOS Revision"),
    }

    # Initialize RDF.
    dmi_info = rdf_client.HardwareInfo()

    for line in output:
      if sys_info_re.match(line):
        # Collect all System Information until we hit a blank line.
        while line:
          for attr, regex in sys_regexes.items():
            match = regex.match(line)
            if match:
              setattr(dmi_info, attr, match.group(1).strip())
              break
          line = next(output)

      elif bios_info_re.match(line):
        # Collect all BIOS Information until we hit a blank line.
        while line:
          for attr, regex in bios_regexes.items():
            match = regex.match(line)
            if match:
              setattr(dmi_info, attr, match.group(1).strip())
              break
          line = next(output)

    yield dmi_info
