#!/usr/bin/env python
# Lint as: python3
"""Simple parsers for the output of linux commands."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import re


from grr_response_core.lib import parser
from grr_response_core.lib import parsers
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.util import collection


# TODO(user): Extend this to resolve repo/publisher to its baseurl.
class YumListCmdParser(parser.CommandParser):
  """Parser for yum list output.

  Yields SoftwarePackage rdfvalues.

  We read the output of yum rather than rpm because it has publishers, and we
  don't use bdb because it's a world of hurt and appears to use different,
  incompatible versions across OS revisions.
  """

  output_types = [rdf_client.SoftwarePackages]
  supported_artifacts = ["RedhatYumPackagesList"]

  def Parse(self, cmd, args, stdout, stderr, return_val, knowledge_base):
    """Parse the yum output."""
    _ = stderr, args, knowledge_base  # Unused.
    self.CheckReturn(cmd, return_val)

    # `yum list installed` output is divided into lines. First line should be
    # always equal to "Installed Packages". The following lines are triplets,
    # but if one of the triplet columns does not fit, the rest of the row is
    # carried over to the next line. Thus, instead of processing the output line
    # by line, we split it into individual items (they cannot contain any space)
    # and chunk them to triplets.

    items = stdout.decode("utf-8").split()
    if not (items[0] == "Installed" and items[1] == "Packages"):
      message = ("`yum list installed` output does not start with \"Installed "
                 "Packages\"")
      raise AssertionError(message)
    items = items[2:]

    packages = []
    for name_arch, version, source in collection.Batch(items, 3):
      # The package name can actually contain dots, e.g. java-1.8.0.
      name, arch = name_arch.rsplit(".", 1)

      packages.append(
          rdf_client.SoftwarePackage.Installed(
              name=name, publisher=source, version=version, architecture=arch))

    if packages:
      yield rdf_client.SoftwarePackages(packages=packages)


class YumRepolistCmdParser(parser.CommandParser):
  """Parser for yum repolist output.

  Yields PackageRepository.

  Parse all enabled repositories as output by yum repolist -q -v.
  """

  output_types = [rdf_client.PackageRepository]
  supported_artifacts = ["RedhatYumRepoList"]

  def _re_compile(self, search_str):
    return re.compile(r"%s\s*: ([0-9a-zA-Z-\s./#_=:\(\)]*)" % (search_str))

  def Parse(self, cmd, args, stdout, stderr, return_val, knowledge_base):
    """Parse the yum repolist output."""
    _ = stderr, args, knowledge_base  # Unused.
    self.CheckReturn(cmd, return_val)
    output = iter(stdout.decode("utf-8").splitlines())

    repo_regexes = {
        "name": self._re_compile("Repo-name"),
        "revision": self._re_compile("Repo-revision"),
        "last_update": self._re_compile("Repo-updated"),
        "num_packages": self._re_compile("Repo-pkgs"),
        "size": self._re_compile("Repo-size"),
        "baseurl": self._re_compile("Repo-baseurl"),
        "timeout": self._re_compile("Repo-expire")
    }

    repo_id_re = self._re_compile("Repo-id")

    for line in output:
      match = repo_id_re.match(line)
      if match:
        repo_info = rdf_client.PackageRepository()
        setattr(repo_info, "id", match.group(1).strip())
        while line:
          for attr, regex in repo_regexes.items():
            match = regex.match(line)
            if match:
              setattr(repo_info, attr, match.group(1).strip())
              break
          line = next(output)
        yield repo_info


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
    for line in stdout.splitlines():
      pkg_match = rpm_re.match(line.strip())
      if pkg_match:
        name, version = pkg_match.groups()
        packages.append(
            rdf_client.SoftwarePackage.Installed(name=name, version=version))
    if packages:
      yield rdf_client.SoftwarePackages(packages=packages)

    for line in stderr.splitlines():
      if "error: rpmdbNextIterator: skipping h#" in line:
        yield rdf_anomaly.Anomaly(
            type="PARSER_ANOMALY", symptom="Broken rpm database.")
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
            raise parsers.ParseError("Invalid header parsing for %s at line "
                                     "%s" % (cmd, i))
        break

    if num_columns == 0:
      return
    elif num_columns not in [4, 5]:
      raise ValueError(
          "Bad number of columns ({}) in dpkg --list output:\n{}\n...".format(
              num_columns, "\n".join(lines[:10])))

    for line in lines[i + 1:]:
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
              install_state=status))

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
        "system_assettag": self._re_compile("Asset Tag")
    }

    bios_info_re = re.compile(r"\s*BIOS Information")
    bios_regexes = {
        "bios_vendor": self._re_compile("Vendor"),
        "bios_version": self._re_compile("Version"),
        "bios_release_date": self._re_compile("Release Date"),
        "bios_rom_size": self._re_compile("ROM Size"),
        "bios_revision": self._re_compile("BIOS Revision")
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


class PsCmdParser(parser.CommandParser):
  """Parser for '/bin/ps' output. Yields Process rdfvalues."""

  output_types = [rdf_client.Process]
  supported_artifacts = ["ListProcessesPsCommand"]

  def Parse(self, cmd, args, stdout, stderr, return_val, knowledge_base):
    """Parse the ps output.

    Note that cmdline consumes every field up to the end of line
    and as it is string, we can't perfectly see what the arguments
    on the command line really were. We just assume a space is the arg
    seperator. It's imperfect, but it's better than nothing.
    Obviously, if cmd/cmdline is specified, it must be the last
    column of output.

    Args:
      cmd: A string containing the base command that was run.
      args: A list of strings containing the commandline args for the command.
      stdout: A string containing the stdout of the command run.
      stderr: A string containing the stderr of the command run. (Unused)
      return_val: The return code following command execution.
      knowledge_base: An RDF KnowledgeBase. (Unused)

    Yields:
      RDF Process objects.
    """

    _ = stderr, knowledge_base  # Unused.
    self.CheckReturn(cmd, return_val)

    lines = stdout.splitlines()[1:]  # First line is just a header.
    for line in lines:
      try:
        uid, pid, ppid, c, _, tty, _, cmd = line.split(None, 7)

        rdf_process = rdf_client.Process()
        rdf_process.username = uid
        rdf_process.pid = int(pid)
        rdf_process.ppid = int(ppid)
        rdf_process.cpu_percent = float(c)
        rdf_process.terminal = tty
        rdf_process.cmdline = cmd.split()
        yield rdf_process
      except ValueError as error:
        message = "Error while parsing `ps` output line '%s': %s"
        logging.warning(message, line, error)
