#!/usr/bin/env python
"""Simple parsers for OS X files."""


import datetime
import io
import os
import plistlib
import stat
from typing import IO
from typing import Iterable
from typing import Iterator


from grr_response_core.lib import parser
from grr_response_core.lib import parsers
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import plist as rdf_plist


class OSXUsersParser(parsers.MultiResponseParser[rdf_client.User]):
  """Parser for Glob of /Users/*."""

  output_types = [rdf_client.User]
  supported_artifacts = ["UsersDirectory"]

  _ignore_users = ["Shared"]

  def ParseResponses(
      self,
      knowledge_base: rdf_client.KnowledgeBase,
      responses: Iterable[rdfvalue.RDFValue],
  ) -> Iterator[rdf_client.User]:
    for response in responses:
      if not isinstance(response, rdf_client_fs.StatEntry):
        raise TypeError(f"Unexpected response type: `{type(response)}`")

      # TODO: `st_mode` has to be an `int`, not `StatMode`.
      if stat.S_ISDIR(int(response.st_mode)):
        homedir = response.pathspec.path
        username = os.path.basename(homedir)
        if username not in self._ignore_users:
          yield rdf_client.User(username=username, homedir=homedir)


# TODO(hanuszczak): Why is a command parser in a file called `osx_file_parsers`?
class OSXSPHardwareDataTypeParser(parser.CommandParser):
  """Parser for the Hardware Data from System Profiler."""
  output_types = [rdf_client.HardwareInfo]
  supported_artifacts = ["OSXSPHardwareDataType"]

  def Parse(self, cmd, args, stdout, stderr, return_val, knowledge_base):
    """Parse the system profiler output. We get it in the form of a plist."""
    _ = stderr, args, knowledge_base  # Unused
    self.CheckReturn(cmd, return_val)

    try:
      plist = plistlib.load(io.BytesIO(stdout))
    except plistlib.InvalidFileException as error:
      raise parsers.ParseError("Failed to parse a plist file", cause=error)

    if len(plist) > 1:
      raise parsers.ParseError("SPHardwareDataType plist has too many items.")

    hardware_list = plist[0]["_items"][0]
    serial_number = hardware_list.get("serial_number", None)
    system_product_name = hardware_list.get("machine_model", None)
    bios_version = hardware_list.get("boot_rom_version", None)

    yield rdf_client.HardwareInfo(
        serial_number=serial_number,
        bios_version=bios_version,
        system_product_name=system_product_name)


class OSXLaunchdPlistParser(parsers.SingleFileParser[rdf_plist.LaunchdPlist]):
  """Parse Launchd plist files into LaunchdPlist objects."""

  output_types = [rdf_plist.LaunchdPlist]
  supported_artifacts = [
      "MacOSLaunchAgentsPlistFile", "MacOSLaunchDaemonsPlistFile"
  ]

  def ParseFile(
      self,
      knowledge_base: rdf_client.KnowledgeBase,
      pathspec: rdf_paths.PathSpec,
      filedesc: IO[bytes],
  ) -> Iterator[rdf_plist.LaunchdPlist]:
    del knowledge_base  # Unused.

    kwargs = {"path": pathspec.last.path}

    direct_copy_items = [
        "Label", "Disabled", "UserName", "GroupName", "Program",
        "StandardInPath", "StandardOutPath", "StandardErrorPath",
        "LimitLoadToSessionType", "EnableGlobbing", "EnableTransactions",
        "OnDemand", "RunAtLoad", "RootDirectory", "WorkingDirectory", "Umask",
        "TimeOut", "ExitTimeOut", "ThrottleInterval", "InitGroups",
        "StartOnMount", "StartInterval", "Debug", "WaitForDebugger", "Nice",
        "ProcessType", "AbandonProcessGroup", "LowPriorityIO", "LaunchOnlyOnce"
    ]

    string_array_items = [
        "LimitLoadToHosts", "LimitLoadFromHosts", "LimitLoadToSessionType",
        "ProgramArguments", "WatchPaths", "QueueDirectories"
    ]

    flag_only_items = ["SoftResourceLimits", "HardResourceLimits", "Sockets"]

    plist = {}

    try:
      plist = plistlib.load(filedesc)
    except (plistlib.InvalidFileException, ValueError, IOError) as e:
      plist["Label"] = "Could not parse plist: %s" % e

    # These are items that can be directly copied
    for key in direct_copy_items:
      kwargs[key] = plist.get(key)

    # These could be a string, they could be an array, we don't know and neither
    # does Apple so we check.
    for key in string_array_items:
      elements = plist.get(key)
      if isinstance(elements, str):
        kwargs[key] = [elements]
      else:
        kwargs[key] = elements

    # These are complex items that can appear in multiple data structures
    # so we only flag on their existence
    for key in flag_only_items:
      if plist.get(key):
        kwargs[key] = True

    if plist.get("inetdCompatibility") is not None:
      kwargs["inetdCompatibilityWait"] = plist.get("inetdCompatibility").get(
          "Wait")

    keepalive = plist.get("KeepAlive")
    if isinstance(keepalive, bool) or keepalive is None:
      kwargs["KeepAlive"] = keepalive
    else:
      keepalivedict = {}
      keepalivedict["SuccessfulExit"] = keepalive.get("SuccessfulExit")
      keepalivedict["NetworkState"] = keepalive.get("NetworkState")

      pathstates = keepalive.get("PathState")
      if pathstates is not None:
        keepalivedict["PathState"] = []
        for pathstate in pathstates:
          keepalivedict["PathState"].append(
              rdf_plist.PlistBoolDictEntry(
                  name=pathstate, value=pathstates[pathstate]))

      otherjobs = keepalive.get("OtherJobEnabled")
      if otherjobs is not None:
        keepalivedict["OtherJobEnabled"] = []
        for otherjob in otherjobs:
          keepalivedict["OtherJobEnabled"].append(
              rdf_plist.PlistBoolDictEntry(
                  name=otherjob, value=otherjobs[otherjob]))
      kwargs["KeepAliveDict"] = rdf_plist.LaunchdKeepAlive(**keepalivedict)

    envvars = plist.get("EnvironmentVariables")
    if envvars is not None:
      kwargs["EnvironmentVariables"] = []
      for envvar in envvars:
        kwargs["EnvironmentVariables"].append(
            rdf_plist.PlistStringDictEntry(
                name=envvar, value=str(envvars[envvar])))

    startcalendarinterval = plist.get("StartCalendarInterval")
    if startcalendarinterval is not None:
      if isinstance(startcalendarinterval, dict):
        kwargs["StartCalendarInterval"] = [
            rdf_plist.LaunchdStartCalendarIntervalEntry(
                Minute=startcalendarinterval.get("Minute"),
                Hour=startcalendarinterval.get("Hour"),
                Day=startcalendarinterval.get("Day"),
                Weekday=startcalendarinterval.get("Weekday"),
                Month=startcalendarinterval.get("Month"))
        ]
      else:
        kwargs["StartCalendarInterval"] = []
        for entry in startcalendarinterval:
          kwargs["StartCalendarInterval"].append(
              rdf_plist.LaunchdStartCalendarIntervalEntry(
                  Minute=entry.get("Minute"),
                  Hour=entry.get("Hour"),
                  Day=entry.get("Day"),
                  Weekday=entry.get("Weekday"),
                  Month=entry.get("Month")))

    yield rdf_plist.LaunchdPlist(**kwargs)


class OSXInstallHistoryPlistParser(
    parsers.SingleFileParser[rdf_client.SoftwarePackages]):
  """Parse InstallHistory plist files into SoftwarePackage objects."""

  output_types = [rdf_client.SoftwarePackages]
  supported_artifacts = ["MacOSInstallationHistory"]

  def ParseFile(
      self,
      knowledge_base: rdf_client.KnowledgeBase,
      pathspec: rdf_paths.PathSpec,
      filedesc: IO[bytes],
  ) -> Iterator[rdf_client.SoftwarePackages]:
    del knowledge_base  # Unused.
    del pathspec  # Unused.

    try:
      plist = plistlib.load(filedesc)
    except plistlib.InvalidFileException as error:
      raise parsers.ParseError("Failed to parse a plist file", cause=error)

    if not isinstance(plist, list):
      raise parsers.ParseError(
          "InstallHistory plist is a '%s', expecting a list" % type(plist))

    packages = []
    for sw in plist:
      packages.append(
          rdf_client.SoftwarePackage.Installed(
              name=sw.get("displayName"),
              version=sw.get("displayVersion"),
              description=",".join(sw.get("packageIdentifiers", [])),
              # TODO(hanuszczak): make installed_on an RDFDatetime
              installed_on=_DateToEpoch(sw.get("date"))))

    if packages:
      yield rdf_client.SoftwarePackages(packages=packages)


def _DateToEpoch(date):
  """Converts python datetime to epoch microseconds."""
  tz_zero = datetime.datetime.utcfromtimestamp(0)
  diff_sec = int((date - tz_zero).total_seconds())
  return diff_sec * 1000000
