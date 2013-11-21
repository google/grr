#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.

"""Flows for collecting Sophos related information.

Collects Logs and Infected files.
"""

## DISABLED for now until it gets converted to artifacts.



from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.proto import flows_pb2


class SophosCollectorArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.SophosCollectorArgs


class SophosCollector(flow.GRRFlow):
  """Collect all files related to Sophos."""

  category = "/Collectors/"
  behaviours = flow.GRRFlow.behaviours + "BASIC"
  args_type = SophosCollectorArgs
  collector_flow = "FileCollector"

  @flow.StateHandler(next_state="Done")
  def Start(self):
    fd = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.system = fd.Get(fd.Schema.SYSTEM)
    self.version = fd.Get(fd.Schema.OS_VERSION)

    # Set our findspecs.
    self.findspecs = list(self.GetFindSpecs())

    self.CallFlow(self.collector_flow, output=self.args.output,
                  findspecs=self.findspecs, next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    """Notify the user if we were successful."""
    response = responses.First()
    if response:
      fd = aff4.FACTORY.Open(response, mode="r", token=self.token)
      collection_list = list(fd)
      if collection_list:
        self.Notify("ViewObject", response,
                    "Retrieved %s sophos files." % len(collection_list))
        return

    raise flow.FlowError("No Sophos related files were downloaded.")

  @flow.StateHandler()
  def End(self, responses):
    pass

  def GetSophosAVInfectedPath(self):
    """Determines the platform specific Sophos AV infected path.

    Returns:
      A Unicode string containing the client specific Sophos AV infected path.

    Raises:
      OSError: If the client operating system is not supported.
    """
    if self.system == "Darwin":
      return u"/Users/Shared/Infected"

    elif self.system == "Windows":
      if self.version < "6.0.0000":
        return (u"C:\\Documents and Settings\\All Users\\Application Data"
                "\\Sophos\\Sophos Anti-Virus\\INFECTED")
      else:
        return u"C:\\ProgramData\\Sophos\\Sophos Anti-Virus\\INFECTED"

    else:
      raise OSError("Unsupported operating system: {0}".format(
          self.system))

  def GetSophosAVLogsPath(self):
    """Determines the platform specific Sophos AV logs path.

    Returns:
      A Unicode string containing the client specific Sophos AV logs path.

    Raises:
      OSError: If the client operating system is not supported.
    """
    if self.system == "Darwin":
      return u"/Library/Logs/"

    elif self.system == "Windows":
      if self.version < "6.0.0000":
        return (u"C:\\Documents and Settings\\All Users\\Application Data"
                "\\Sophos\\Sophos Anti-Virus\\Logs")
      else:
        return u"C:\\ProgramData\\Sophos\\Sophos Anti-Virus\\Logs"

    else:
      raise OSError("Unsupported operating system: {0}".format(
          self.system))

  def GetSophosAVLogsPathRegex(self):
    """Determines the platform specific Sophos AV logs path regex.

    Returns:
      A Unicode string containing the client specific Sophos AV logs path regex.

    Raises:
      OSError: If the client operating system is not supported.
    """
    if self.system == "Darwin":
      return u".*\\.log$"

    elif self.system == "Windows":
      return u".*\\.txt$"

    else:
      raise OSError("Unsupported operating system: {0}".format(
          self.system))

  def GetFindSpecs(self):
    """Determine the Find specifications.

    Yields:
      A path specification to search

    Raises:
      OSError: If the client operating system is not supported.
    """
    path_spec = rdfvalue.PathSpec(
        path=self.GetSophosAVInfectedPath(),
        pathtype=self.args.pathtype)

    yield rdfvalue.FindSpec(
        pathspec=path_spec,
        path_regex=".*",
        max_depth=1)

    path_spec = rdfvalue.PathSpec(
        path=self.GetSophosAVLogsPath(),
        pathtype=self.args.pathtype)

    yield rdfvalue.FindSpec(
        pathspec=path_spec,
        path_regex=self.GetSophosAVLogsPathRegex(),
        max_depth=1)
