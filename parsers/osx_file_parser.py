#!/usr/bin/env python
"""Simple parsers for OS X files."""

import cStringIO

import os
import stat

from grr.lib import parsers
from grr.lib import rdfvalue
from grr.parsers import binplist


class OSXUsersParser(parsers.ArtifactFilesParser):
  """Parser for Glob of /Users/*."""

  output_types = ["KnowledgeBaseUser"]
  supported_artifacts = ["OSXUsers"]
  blacklist = ["Shared"]

  def Parse(self, stat_entries, knowledge_base, path_type):
    """Parse the StatEntry objects."""
    _, _ = knowledge_base, path_type

    for stat_entry in stat_entries:
      if stat.S_ISDIR(stat_entry.st_mode):
        homedir = stat_entry.pathspec.path
        username = os.path.basename(homedir)
        if username not in self.blacklist:
          yield rdfvalue.KnowledgeBaseUser(username=username,
                                           homedir=homedir)


class OSXSPHardwareDataTypeParser(parsers.CommandParser):
  """Parser for the Hardware Data from System Profiler."""
  output_types = ["HardwareInfo"]
  supported_artifacts = ["OSXSPHardwareDataType"]

  def Parse(self, cmd, args, stdout, stderr, return_val, time_taken,
            knowledge_base):
    """Parse the system profiler output. We get it in the form of a plist."""
    _ = stderr, time_taken, args, knowledge_base  # Unused
    self.CheckReturn(cmd, return_val)

    serial_number = []
    hardware_list = []
    plist = binplist.readPlist(cStringIO.StringIO(stdout))

    if len(plist) > 1:
      raise parsers.ParseError("SPHardwareDataType plist has too many items.")

    hardware_list = plist[0]["_items"][0]
    serial_number = hardware_list["serial_number"]

    yield rdfvalue.HardwareInfo(serial_number=serial_number)


class OSXLaunchdPlistParser(parsers.FileParser):
  """Parse Launchd plist files into LaunchdPlist objects."""

  output_types = ["LaunchdPlist"]
  supported_artifacts = ["OSXLaunchAgents", "OSXLaunchDaemons"]

  def Parse(self, statentry, file_object, knowledge_base):
    """Parse the Plist file."""
    _ = knowledge_base
    kwargs = {}
    kwargs["aff4path"] = statentry.aff4path

    direct_copy_items = ["Label", "Disabled", "UserName", "GroupName",
                         "Program", "StandardInPath", "StandardOutPath",
                         "StandardErrorPath", "LimitLoadToSessionType",
                         "EnableGlobbing", "EnableTransactions", "OnDemand",
                         "RunAtLoad", "RootDirectory", "WorkingDirectory",
                         "Umask", "TimeOut", "ExitTimeOut", "ThrottleInterval",
                         "InitGroups", "StartOnMount", "StartInterval",
                         "Debug", "WaitForDebugger", "Nice", "ProcessType",
                         "AbandonProcessGroup", "LowPriorityIO",
                         "LaunchOnlyOnce"]

    string_array_items = ["LimitLoadToHosts", "LimitLoadFromHosts",
                          "LimitLoadToSessionType", "ProgramArguments",
                          "WatchPaths", "QueueDirectories"]

    flag_only_items = ["SoftResourceLimits", "HardResourceLimits", "Sockets"]

    plist = {}

    try:
      plist = binplist.readPlist(file_object)
    except (binplist.FormatError, ValueError):
      plist["Label"] = "Could not parse plist."

    # These are items that can be directly copied
    for key in direct_copy_items:
      kwargs[key] = plist.get(key)

    # These could be a string, they could be an array, we don't know and neither
    # does Apple so we check.
    for key in string_array_items:
      elements = plist.get(key)
      if isinstance(elements, basestring):
        kwargs[key] = [elements]
      else:
        kwargs[key] = elements

    # These are complex items that can appear in multiple data structures
    # so we only flag on their existence
    for key in flag_only_items:
      if plist.get(key):
        kwargs[key] = True

    if plist.get("inetdCompatability") is not None:
      kwargs["inetdCompatabilityWait"] = plist.get(
          "inetdCompatability").get("Wait")

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
              rdfvalue.PlistBoolDictEntry(name=pathstate,
                                          value=pathstates[pathstate]))

      otherjobs = keepalive.get("OtherJobEnabled")
      if otherjobs is not None:
        keepalivedict["OtherJobEnabled"] = []
        for otherjob in otherjobs:
          keepalivedict["OtherJobEnabled"].append(
              rdfvalue.PlistBoolDictEntry(name=otherjob,
                                          value=otherjobs[otherjob]))
      kwargs["KeepAliveDict"] = rdfvalue.LaunchdKeepAlive(**keepalivedict)

    envvars = plist.get("EnvironmentVariables")
    if envvars is not None:
      kwargs["EnvironmentVariables"] = []
      for envvar in envvars:
        kwargs["EnvironmentVariables"].append(
            rdfvalue.PlistStringDictEntry(name=envvar,
                                          value=envvars[envvar]))

    startcalendarinterval = plist.get("StartCalendarInterval")
    if startcalendarinterval is not None:
      if isinstance(startcalendarinterval, dict):
        kwargs["StartCalendarInterval"] = [
            rdfvalue.LaunchdStartCalendarIntervalEntry(
                Minute=startcalendarinterval.get("Minute"),
                Hour=startcalendarinterval.get("Hour"),
                Day=startcalendarinterval.get("Day"),
                Weekday=startcalendarinterval.get("Weekday"),
                Month=startcalendarinterval.get("Month"))]
      else:
        kwargs["StartCalendarInterval"] = []
        for entry in startcalendarinterval:
          kwargs["StartCalendarInterval"].append(
              rdfvalue.LaunchdStartCalendarIntervalEntry(
                  Minute=entry.get("Minute"),
                  Hour=entry.get("Hour"),
                  Day=entry.get("Day"),
                  Weekday=entry.get("Weekday"),
                  Month=entry.get("Month")))

    yield rdfvalue.LaunchdPlist(**kwargs)
