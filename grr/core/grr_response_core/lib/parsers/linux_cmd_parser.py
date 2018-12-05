#!/usr/bin/env python
"""Simple parsers for the output of linux commands."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import re


from future.utils import iteritems

from grr_response_core.lib import parser
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import client as rdf_client


# TODO(user): Extend this to resolve repo/publisher to its baseurl.
class YumListCmdParser(parser.CommandParser):
  """Parser for yum list output. Yields SoftwarePackage rdfvalues.

  We read the output of yum rather than rpm because it has publishers, and we
  don't use bdb because it's a world of hurt and appears to use different,
  incompatible versions across OS revisions.
  """

  output_types = ["SoftwarePackage"]
  supported_artifacts = ["RedhatYumPackagesList"]

  def Parse(self, cmd, args, stdout, stderr, return_val, time_taken,
            knowledge_base):
    """Parse the yum output."""
    _ = stderr, time_taken, args, knowledge_base  # Unused.
    self.CheckReturn(cmd, return_val)
    for line in stdout.splitlines()[1:]:  # Ignore first line
      cols = line.split()
      name_arch, version, source = cols
      name, arch = name_arch.split(".")

      status = rdf_client.SoftwarePackage.InstallState.INSTALLED
      yield rdf_client.SoftwarePackage(
          name=name,
          publisher=source,
          version=version,
          architecture=arch,
          install_state=status)


class YumRepolistCmdParser(parser.CommandParser):
  """Parser for yum repolist output. Yields PackageRepository.

  Parse all enabled repositories as output by yum repolist -q -v.
  """

  output_types = ["PackageRepository"]
  supported_artifacts = ["RedhatYumRepoList"]

  def _re_compile(self, search_str):
    return re.compile(r"%s\s*: ([0-9a-zA-Z-\s./#_=:\(\)]*)" % (search_str))

  def Parse(self, cmd, args, stdout, stderr, return_val, time_taken,
            knowledge_base):
    """Parse the yum repolist output."""
    _ = stderr, time_taken, args, knowledge_base  # Unused.
    self.CheckReturn(cmd, return_val)
    output = iter(stdout.splitlines())

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
          for attr, regex in iteritems(repo_regexes):
            match = regex.match(line)
            if match:
              setattr(repo_info, attr, match.group(1).strip())
              break
          line = output.next()
        yield repo_info


class RpmCmdParser(parser.CommandParser):
  """Parser for rpm qa output. Yields SoftwarePackage rdfvalues."""

  output_types = ["SoftwarePackage"]
  supported_artifacts = ["RedhatPackagesList"]

  def Parse(self, cmd, args, stdout, stderr, return_val, time_taken,
            knowledge_base):
    """Parse the rpm -qa output."""
    _ = time_taken, args, knowledge_base  # Unused.
    rpm_re = re.compile(r"^(\w[-\w\+]+?)-(\d.*)$")
    self.CheckReturn(cmd, return_val)
    for line in stdout.splitlines():
      pkg_match = rpm_re.match(line.strip())
      if pkg_match:
        name, version = pkg_match.groups()
        status = rdf_client.SoftwarePackage.InstallState.INSTALLED
        yield rdf_client.SoftwarePackage(
            name=name, version=version, install_state=status)
    for line in stderr.splitlines():
      if "error: rpmdbNextIterator: skipping h#" in line:
        yield rdf_anomaly.Anomaly(
            type="PARSER_ANOMALY", symptom="Broken rpm database.")
        break


class DpkgCmdParser(parser.CommandParser):
  """Parser for dpkg output. Yields SoftwarePackage rdfvalues."""

  output_types = ["SoftwarePackage"]
  supported_artifacts = ["DebianPackagesList"]

  def Parse(self, cmd, args, stdout, stderr, return_val, time_taken,
            knowledge_base):
    """Parse the dpkg output."""
    _ = stderr, time_taken, args, knowledge_base  # Unused.
    self.CheckReturn(cmd, return_val)
    column_lengths = []
    i = 0
    for i, line in enumerate(stdout.splitlines()):
      if line.startswith("+++-"):
        # This is a special header line that determines column size.
        for col in line.split("-")[1:]:
          if not re.match("=*", col):
            raise parser.ParseError("Invalid header parsing for %s at line "
                                    "%s" % (cmd, i))
          column_lengths.append(len(col))
        break

    if column_lengths:
      remaining_lines = stdout.splitlines()[i + 1:]
      for i, line in enumerate(remaining_lines):
        cols = line.split(None, len(column_lengths))

        # The status column is ignored in column_lengths.
        if len(column_lengths) == 4:
          # Installed, Name, Version, Architecture, Description
          status, name, version, arch, desc = cols
        elif len(column_lengths) == 3:
          # Older versions of dpkg don't print Architecture
          status, name, version, desc = cols
          arch = None
        else:
          raise ValueError("Bad number of columns in dpkg --list output: %s" %
                           len(column_lengths))

        # Status is potentially 3 columns, but always at least two, desired and
        # actual state. We only care about actual state.
        if status[1] == "i":
          status = rdf_client.SoftwarePackage.InstallState.INSTALLED
        else:
          status = rdf_client.SoftwarePackage.InstallState.UNKNOWN
        yield rdf_client.SoftwarePackage(
            name=name,
            description=desc,
            version=version,
            architecture=arch,
            install_state=status)


class DmidecodeCmdParser(parser.CommandParser):
  """Parser for dmidecode output. Yields HardwareInfo rdfvalues."""

  output_types = ["HardwareInfo"]
  supported_artifacts = ["LinuxHardwareInfo"]

  def _re_compile(self, search_str):
    return re.compile(r"\s*%s: ([0-9a-zA-Z-\s./#_=]*)" % (search_str))

  def Parse(self, cmd, args, stdout, stderr, return_val, time_taken,
            knowledge_base):
    """Parse the dmidecode output. All data is parsed into a dictionary."""
    _ = stderr, time_taken, args, knowledge_base  # Unused.
    self.CheckReturn(cmd, return_val)
    output = iter(stdout.splitlines())

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
          for attr, regex in iteritems(sys_regexes):
            match = regex.match(line)
            if match:
              setattr(dmi_info, attr, match.group(1).strip())
              break
          line = output.next()

      elif bios_info_re.match(line):
        # Collect all BIOS Information until we hit a blank line.
        while line:
          for attr, regex in iteritems(bios_regexes):
            match = regex.match(line)
            if match:
              setattr(dmi_info, attr, match.group(1).strip())
              break
          line = output.next()

    yield dmi_info


class PsCmdParser(parser.CommandParser):
  """Parser for '/bin/ps' output. Yields Process rdfvalues."""

  output_types = ["Process"]
  supported_artifacts = ["ListProcessesPsCommand"]

  def Parse(self, cmd, args, stdout, stderr, return_val, time_taken,
            knowledge_base):
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
      time_taken: The time taken to run the process. (Unused)
      knowledge_base: An RDF KnowledgeBase. (Unused)

    Yields:
      RDF Process objects.
    """

    _ = stderr, time_taken, knowledge_base  # Unused.
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
