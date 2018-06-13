#!/usr/bin/env python
"""Simple parsers for the output of linux commands."""
import logging
import os
import re


from grr.lib import parser
from grr.lib.rdfvalues import anomaly as rdf_anomaly
from grr.lib.rdfvalues import client as rdf_client
from grr.server.grr_response_server import artifact_registry


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
          for attr, regex in repo_regexes.iteritems():
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
          for attr, regex in sys_regexes.iteritems():
            match = regex.match(line)
            if match:
              setattr(dmi_info, attr, match.group(1).strip())
              break
          line = output.next()

      elif bios_info_re.match(line):
        # Collect all BIOS Information until we hit a blank line.
        while line:
          for attr, regex in bios_regexes.iteritems():
            match = regex.match(line)
            if match:
              setattr(dmi_info, attr, match.group(1).strip())
              break
          line = output.next()

    return dmi_info


class PsCmdParser(parser.CommandParser):
  """Parser for '/bin/ps' output. Yields Process rdfvalues."""

  output_types = ["Process"]
  supported_artifacts = ["ListProcessesPsCommand"]

  @classmethod
  def Validate(cls):
    """Perform some extra sanity checks on the ps arguments."""
    super(PsCmdParser, cls).Validate()
    for artifact_name in cls.supported_artifacts:
      artifact = artifact_registry.REGISTRY.GetArtifact(artifact_name)
      for source in artifact.sources:
        if not cls._FindPsOutputFormat(source.attributes["cmd"],
                                       source.attributes["args"]):
          raise parser.ParserDefinitionError(
              "Artifact parser %s can't process artifact %s. 'ps' command has "
              "unacceptable arguments." % (cls.__name__, artifact_name))

  @classmethod
  def _FindPsOutputFormat(cls, cmd, args):
    """Return our best guess the formating of the "ps" output."""
    output_format = []
    for arg in args:
      # If the "ps" arg contains a comma, it's probably an output format defn.
      if "," in arg:
        output_format.extend(arg.split(","))
    if not output_format:
      # Assume a default format for the "-f" style formating.
      output_format = [
          "user", "pid", "ppid", "pcpu", "not_implemented", "tty",
          "not_implemented", "cmd"
      ]
    # Do some sanity checking for the cmd/cmdline if present.
    for option in ["cmd", "command", "args"]:
      if option in output_format:
        if output_format.count(option) > 1:
          logging.warn(
              "Multiple commandline outputs expected in '%s %s' "
              "output. Skipping parsing.", cmd, " ".join(args))
          return []
        if output_format[-1] != option:
          logging.warn(
              "'ps's output has the commandline not as the last "
              "column. We can't safely parse output of '%s %s'."
              "Skipping parsing.", cmd, " ".join(args))
          return []

    # If we made it here, we should be able to parse the output and we have a
    # good idea of it's format.
    return output_format

  def _SplitCmd(self, cmdline):
    """Split up the command line."""
    return cmdline.split()

  def _HasHeaders(self, args):
    """Look at the args and decided if we expect headers or not."""
    # The default is on.
    headers = True
    for arg in args:
      # Simple cases where it is turn off.
      if arg in ["--no-headers", "h", "--no-heading"]:
        headers = False
      # Simple case where it is turned on.
      elif arg in ["--headers"]:
        headers = True
      # if 'h' appears in a arg, that doesn't start with '-', and
      # doesn't look like a format defn. Then that's probably turning it off.
      elif "h" in arg and not arg.startswith("-") and "," not in arg:
        headers = False
    return headers

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

    if not stdout:
      # We have nothing to process so bug out. (Handles a input of None.)
      return

    rdf_convert_table = {
        "pid": ("pid", int),
        "tgid": ("pid", int),
        "ppid": ("ppid", int),
        "comm": ("name", str),
        "ucomm": ("name", str),
        "ruid": ("real_uid", int),
        "uid": ("effective_uid", int),
        "euid": ("effective_uid", int),
        "suid": ("saved_uid", int),
        "svuid": ("saved_uid", int),
        "user": ("username", str),
        "euser": ("username", str),
        "uname": ("username", str),
        "rgid": ("real_gid", int),
        "gid": ("effective_gid", int),
        "egid": ("effective_gid", int),
        "sgid": ("saved_gid", int),
        "svgid": ("saved_gid", int),
        "tty": ("terminal", str),
        "tt": ("terminal", str),
        "tname": ("terminal", str),
        "stat": ("status", str),
        "nice": ("nice", int),
        "ni": ("nice", int),
        "thcount": ("num_threads", int),
        "nlwp": ("num_threads", int),
        "pcpu": ("cpu_percent", float),
        "%cpu": ("cpu_percent", float),
        "c": ("cpu_percent", float),
        "rss": ("RSS_size", long),
        "rssize": ("RSS_size", long),
        "rsz": ("RSS_size", long),
        "vsz": ("VMS_size", long),
        "vsize": ("VMS_size", long),
        "pmem": ("memory_percent", float),
        "%mem": ("memory_percent", float),
        "args": ("cmdline", self._SplitCmd),
        "command": ("cmdline", self._SplitCmd),
        "cmd": ("cmdline", self._SplitCmd)
    }

    expected_fields = self._FindPsOutputFormat(cmd, args)

    # If we made it here, we expect we can now parse the output and we know
    # expected its format.

    lines = stdout.splitlines()
    if self._HasHeaders(args):
      # Ignore the headers.
      lines = lines[1:]

    for line in lines:
      try:
        # The "len() - 1" allows us to group any extra fields into
        # the last field. e.g. cmdline.
        entries = line.split(None, len(expected_fields) - 1)
        # Create an empty process for us to fill in as best we can.
        process = rdf_client.Process()
        for name, value in zip(expected_fields, entries):
          if name not in rdf_convert_table:
            # If the field is not something we can process, skip it.
            continue
          rdf_name, method = rdf_convert_table[name]
          setattr(process, rdf_name, method(value))
        # Approximate the 'comm' from the cmdline if it wasn't detailed.
        # i.e. the basename of the first arg of the commandline.
        if not process.name and process.cmdline:
          process.name = os.path.basename(process.cmdline[0])
        yield process
      except ValueError:
        logging.warn("Unparsable line found for %s %s:\n"
                     "  %s", cmd, args, line)
