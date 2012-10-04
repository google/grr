#!/usr/bin/env python
# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Flows for collecting Sophos related information.

Collects Logs and Infected files.
"""



from grr.lib import aff4
from grr.lib import flow
from grr.lib import type_info
from grr.proto import jobs_pb2


class SophosCollector(flow.GRRFlow):
  """Collect all files related to Sophos."""

  category = "/Collectors/"
  flow_typeinfo = {"pathtype": type_info.ProtoEnum(jobs_pb2.Path, "PathType")}

  def __init__(self, pathtype=jobs_pb2.Path.TSK,
               output="analysis/sophos/{u}-{t}", **kwargs):
    """Constructor.

    Args:
      pathtype: Identifies requested path type. Enum from Path protobuf.
      output: If set, a URN to an AFF4Collection to add each result to.
          This will create the collection if it does not exist.
    """
    super(SophosCollector, self).__init__(**kwargs)

    self.pathtype = pathtype

    fd = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.system = fd.Get(fd.Schema.SYSTEM)
    self.version = fd.Get(fd.Schema.OS_VERSION)

    # Set our findspecs.
    self.findspecs = list(self.GetFindSpecs())
    self.output = output

  @flow.StateHandler(next_state="End")
  def Start(self):
    self.CallFlow("FileCollector", output=self.output,
                  findspecs=self.findspecs, next_state="End")

  @flow.StateHandler()
  def End(self, responses):
    """Notify the user if we were successful."""
    response = responses.First()
    if response:
      fd = aff4.FACTORY.Open(response.aff4path, mode="r", token=self.token)
      collection_list = fd.Get(fd.Schema.COLLECTION)
      if collection_list:
        self.Notify("ViewObject", response.aff4path,
                    "Retrieved %s sophos files." % len(collection_list))
        return

    raise flow.FlowError("No Sophos related files were downloaded.")

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
    path_spec = jobs_pb2.Path(path=self.GetSophosAVInfectedPath(),
                              pathtype=int(self.pathtype))

    yield jobs_pb2.Find(
        pathspec=path_spec,
        path_regex=".*",
        max_depth=1)

    path_spec = jobs_pb2.Path(path=self.GetSophosAVLogsPath(),
                              pathtype=int(self.pathtype))

    yield jobs_pb2.Find(
        pathspec=path_spec,
        path_regex=self.GetSophosAVLogsPathRegex(),
        max_depth=1)
