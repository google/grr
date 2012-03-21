#!/usr/bin/env python
# Copyright 2010 Google Inc.
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


"""These are process related flows."""

import os
import pipes

from grr.lib import aff4
from grr.lib import flow
from grr.lib import time_utils
from grr.lib import utils
from grr.proto import jobs_pb2
from grr.proto import sysinfo_pb2


class ListProcesses(flow.GRRFlow):
  """List running processes on a system."""

  category = "/Processes/"

  @flow.StateHandler(next_state=["Done"])
  def Start(self):
    """Start processing."""
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.system = client.Get(client.Schema.SYSTEM)
    if self.system == "Windows":
      self.CallFlow("ListWindowsProcesses", next_state="Done")
    elif self.system == "Linux":
      self.CallFlow("ListLinuxProcesses", next_state="Done")
    else:
      raise RuntimeError("Unsupported platform for ListProcesses")

  @flow.StateHandler()
  def Done(self):
    self.Status("Listed Processed for %s", self.system)


class ListWindowsProcesses(flow.GRRFlow):
  """List running processes on a Windows system."""

  @flow.StateHandler(next_state=["StoreWmi"])
  def Start(self):
    """Issue a request to list the processes via WMI."""
    wmi_query = "Select * from Win32_Process"
    self.CallClient("WmiQuery", query=wmi_query, next_state="StoreWmi")

  @flow.StateHandler()
  def StoreWmi(self, responses):
    """Collect the process listing and store in the datastore.

    Args:
      responses: A list of Dict protobufs.

    Note that Windows WMI doesn't get process owner by default, it requires a
    separate WMI object invocation.
    """
    process_fd = aff4.FACTORY.Create(aff4.ROOT_URN.Add(
        self.client_id).Add("processes"), "ProcessListing", token=self.token)

    plist = process_fd.Schema.PROCESSES()

    for response in responses:
      try:
        pdict = utils.ProtoDict(response)
        # Collect all the responses into a single protobuf
        proc = sysinfo_pb2.Process(pid=int(pdict["ProcessId"]),
                                   ppid=int(pdict["ParentProcessId"]),
                                   cmdline=pdict["CommandLine"],
                                   exe=pdict["ExecutablePath"],
                                   ctime=time_utils.WmiTimeToEpoch(
                                       pdict["CreationDate"]))
        plist.Append(proc)

      except (KeyError, ValueError), err:
        self.Log("Missing process data %s for %s", err, pdict.ToDict())
        continue

    process_fd.AddAttribute(process_fd.Schema.PROCESSES, plist)
    process_fd.Close()


class ListLinuxProcesses(flow.GRRFlow):
  """List running processes on a Linux system."""

  # Field taken from linux/fs/proc/array.c
  _LIN_STAT_FIELDS = ["pid", "comm", "state", "ppid", "pgrp", "session",
                      "tty_nr", "tpgid", "flags", "minflt", "cminflt", "majflt",
                      "cmajflt", "utime", "stime", "cutime", "cstime",
                      "priority", "nice", "numthreads", "itrealvalue",
                      "starttime", "vsize", "rss", "rlim", "startcode",
                      "endcode", "startstack", "kstkesp", "kstkeip", "signal",
                      "blocked", "sigignore", "sigcatch", "wchan", "nswap",
                      "cnswap", "exit_signal", "processor"]

  @flow.StateHandler(next_state=["GetBootTime"])
  def Start(self):
    """Issue a request to list the processes via the proc filesystem."""
    self._procs = {}   # Temporary storage for processes as we collect them.

    self._boot_time = 0    # Epoch time in seconds for when machine booted.
    self._jiffie_size = 0  # Size of jiffies defined for the system.

    self.proc_pathspec = utils.Pathspec(jobs_pb2.Path(path="/proc",
                                                      pathtype=jobs_pb2.Path.OS))
    stat_pathspec = self.proc_pathspec.Copy().Append(
        pathtype=jobs_pb2.Path.OS, path="stat")

    # Read /proc/stat for boot time
    self.CallClient("ReadBuffer", offset=0, length=8192,
                    pathspec=stat_pathspec.ToProto(),
                    next_state="GetBootTime")

  @flow.StateHandler(next_state="GetProcList")
  def GetBootTime(self, responses):
    """Read the btime variable from /proc/stat and the uptime."""
    data = responses.First()
    if data:
      for line in responses.First().data.splitlines():
        if line.startswith("btime"):
          self._boot_time = int(line.split()[1])
          break

    if not self._boot_time:
      self.Log("Error getting boot time.")
      self.Terminate()
      return

    # If we know the boot time, continue processing. List the /proc/ directory.
    self.CallClient("ListDirectory", pathspec=self.proc_pathspec.ToProto(),
                    next_state="GetProcList")

  @flow.StateHandler(next_state=["GetPidDirListing", "GetCmdLine", "GetStat"])
  def GetProcList(self, responses):
    """Take a list of files/dirs in proc and retrieve info about processes."""
    for stat in responses:
      pid = os.path.basename(stat.pathspec.path)
      if pid.isnumeric():
        self._procs[pid] = {}
        self._procs[pid]["pid"] = int(pid)
        self._procs[pid]["user"] = str(stat.st_uid)
        process_path = self.proc_pathspec.Copy()
        process_path.Append(path=str(pid), pathtype=jobs_pb2.Path.OS)

        self.CallClient("ListDirectory", pathspec=process_path.ToProto(),
                        next_state="GetPidDirListing", request_data=dict(
                            pid=pid))

        # Get process command line
        bufpath = process_path.Copy().Append(pathtype=jobs_pb2.Path.OS,
                                             path="cmdline")
        self.CallClient("ReadBuffer", pathspec=bufpath.ToProto(),
                        offset=0, length=4096,
                        next_state="GetCmdLine", request_data=dict(
                            pid=pid))

        # Get process stats
        bufpath = process_path.Copy().Append(pathtype=jobs_pb2.Path.OS,
                                             path="stat")
        self.CallClient("ReadBuffer", pathspec=bufpath.ToProto(),
                        offset=0, length=4096,
                        next_state="GetStat", request_data=dict(
                            pid=pid))

  @flow.StateHandler(jobs_pb2.StatResponse)
  def GetPidDirListing(self, responses):
    """Take directory listing of a pid and populate self._procs."""
    pid = responses.request_data["pid"]
    if responses.status.status == jobs_pb2.GrrStatus.OK:
      for stat in responses:
        fname = utils.Pathspec(stat.pathspec).Basename()
        if fname == "exe":
          try:
            self._procs.setdefault(pid, {})["exe"] = stat.symlink
          except KeyError:
            pass

  def _EncodeCmdLine(self, argv):
    """Encode argv correctly into a cmdline."""
    return " ".join([pipes.quote(x) for x in argv])

  @flow.StateHandler()
  def GetCmdLine(self, responses):
    """Parse the command line."""
    cmdline = responses.First()
    if responses.success and cmdline:
      pid = responses.request_data["pid"]
      self._procs[pid]["cmdline"] = self._EncodeCmdLine(
          cmdline.data.split("\x00"))

  @flow.StateHandler()
  def GetStat(self, responses):
    data = responses.First()
    if data:
      pid = responses.request_data["pid"]
      proc_stat = self._ParseStat(data.data)
      self._procs[pid]["ppid"] = int(proc_stat.get("ppid", 0))
      ctime = long(proc_stat.get("starttime", 0))
      ctime /= self._CalcJiffies(ctime)
      self._procs[pid]["ctime"] = self._boot_time + ctime

  def _ParseStat(self, stat_data):
    """Parse a string of /proc/<pid>/stat file into a dict."""
    return dict(zip(self._LIN_STAT_FIELDS, stat_data.split()))

  def _CalcJiffies(self, unused_proc_jiffies):
    """Calculate a reasonable jiffy value."""
    if self._jiffie_size:
      return self._jiffie_size
    else:
      # TODO(user): Come up with a way of calculating this accurately
      # preferably os.sysconf(os.sysconf_names['SC_CLK_TCK'])
      self._jiffie_size = 100  # Yes... you saw that right
      return self._jiffie_size

  def End(self):
    """Finalize the processes and write to the datastore."""
    urn = aff4.ROOT_URN.Add(self.client_id).Add("processes")
    process_fd = aff4.FACTORY.Create(urn, "ProcessListing", token=self.token)
    plist = process_fd.Schema.PROCESSES()
    for _, p_dict in self._procs.iteritems():
      proc = sysinfo_pb2.Process()
      for k, v in p_dict.iteritems():
        setattr(proc, k, v)

      plist.Append(proc)

    # Flush the data to the store.
    process_fd.AddAttribute(plist)
    process_fd.Close()

    self.Log("Successfully wrote %d processes", len(self._procs))
    self.Notify("ViewObject", urn, "Listed Processes")
