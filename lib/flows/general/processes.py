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

from grr.lib import aff4
from grr.lib import flow
from grr.lib import time_utils
from grr.lib import utils
from grr.proto import jobs_pb2
from grr.proto import sysinfo_pb2


class ListProcesses(flow.GRRFlow):
  """List running processes on a system."""

  category = "/Processes/"

  def Start(self):
    """Start processing."""
    client = aff4.FACTORY.Open(self.client_id)
    system = client.Get(client.Schema.SYSTEM)
    if system == "Windows":
      flow.FACTORY.StartFlow(self.client_id, "ListWindowsProcesses")
    elif system == "Linux":
      flow.FACTORY.StartFlow(self.client_id, "ListLinuxProcesses")
    else:
      self.Log("Unsupported platform for ListProcesses")


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
    client_fd = aff4.FACTORY.Open(self.client_id)

    plist = client_fd.Schema.PROCESSES()

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

    client_fd.AddAttribute(client_fd.Schema.PROCESSES, plist)
    client_fd.Close()


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

    self._boot_time = None    # Epoch time in seconds for when machine booted.
    self._jiffie_size = None  # Size of jiffies defined for the system.

    self.CallClient("ReadBuffer", path="/proc/stat", offset=0, length=8192,
                    next_state="GetBootTime")

  @flow.StateHandler(jobs_pb2.BufferReadMessage, next_state="GetProcList")
  def GetBootTime(self, responses):
    """Read the btime variable from /proc/stat and the uptime."""
    try:
      for line in responses.First().data.splitlines():
        if line.startswith("btime"):
          btime = int(line.split()[1])
      self._boot_time = btime
    except (AttributeError, UnboundLocalError):
      self.Log("Error getting boot time.")
      self.Terminate()
      return

    # If we know the boot time, continue processing.
    self.CallClient("ListDirectory", path="/proc", next_state="GetProcList")

  @flow.StateHandler(jobs_pb2.StatResponse, next_state=["GetPidDirListing",
                                                        "ReadProcBuffer"])
  def GetProcList(self, responses):
    """Take a list of files/dirs in proc and retrieve info about processes."""
    for stat in responses:
      dir_name = os.path.basename(stat.path)
      if dir_name.isnumeric():
        pid = int(dir_name)
        self._procs[pid] = {}
        self._procs[pid]["pid"] = pid
        self._procs[pid]["user"] = str(stat.st_uid)
        process_path = "/proc/%s" % dir_name

        self.CallClient("ListDirectory", path=process_path,
                        next_state="GetPidDirListing", request_data=dict(
                            pid=dir_name))
        bufpath = os.path.join(process_path, "cmdline")

        self.CallClient("ReadBuffer", path=bufpath, offset=0, length=4096,
                        next_state="ReadProcBuffer", request_data=dict(
                            path=bufpath))
        bufpath = os.path.join(process_path, "stat")
        self.CallClient("ReadBuffer", path=bufpath, offset=0, length=4096,
                        next_state="ReadProcBuffer", request_data=dict(
                            path=bufpath))

  @flow.StateHandler(jobs_pb2.StatResponse)
  def GetPidDirListing(self, responses):
    """Take directory listing of a pid and populate self._procs."""
    pid = responses.request_data["pid"]
    if responses.status.status == jobs_pb2.GrrStatus.OK:
      for stat in responses:
        fname = os.path.basename(stat.path)
        if fname == "exe":
          try:
            self._procs[pid]["exe"] = stat.symlink
          except KeyError: pass

  @flow.StateHandler(jobs_pb2.BufferReadMessage)
  def ReadProcBuffer(self, responses):
    """Read buffers sent back and store resulting data in self._procs."""
    if responses.status.status != jobs_pb2.GrrStatus.OK:
      self.Log("Error running ReadProcBuffer: %s", responses.status)
      return
    response = responses.First()
    if not response:
      self.Log("Missing response to ReadProcBuffer: %s", responses.status)
      return
    fname = os.path.basename(responses.request_data["path"])
    pid = int(os.path.basename(os.path.dirname(responses.request_data["path"])))
    if fname == "cmdline":
      cmdline = response.data.replace("\0", " ")  # replace nulls with spaces
      self._procs[pid]["cmdline"] = cmdline
    elif fname == "stat":
      proc_stat = self._ParseStat(response.data)
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
    client_fd = aff4.FACTORY.Open(self.client_id)
    plist = client_fd.Schema.PROCESSES()
    for _, p_dict in self._procs.iteritems():
      proc = sysinfo_pb2.Process()
      for k, v in p_dict.iteritems():
        setattr(proc, k, v)

      plist.Append(proc)

    # Flush the data to the store.
    client_fd.AddAttribute(client_fd.Schema.PROCESSES, plist)
    client_fd.Close()

    self.Log("Successfully wrote %d processes", len(self._procs))


class NetstatFlow(flow.GRRFlow):
  """Run a netstat flow on the client."""

  category = "/Network/"

  @flow.StateHandler(next_state=["Process", "EnumeratePids"])
  def Start(self):
    """Enumerate pids and list network connections."""
    # First enumerate all the pids
    self.CallClient("WmiQuery", query="Select * from Win32_Process",
                    next_state="EnumeratePids")

    self.CallClient("Netstat", next_state="Process")

  @flow.StateHandler(jobs_pb2.Dict)
  def EnumeratePids(self, responses):
    self.pid_map = {}
    for response in responses:
      pdict = utils.ProtoDict(response)
      pid = int(pdict.Get("ProcessId", 0))
      self.pid_map[pid] = pdict.Get("CommandLine", "")

  @flow.StateHandler(sysinfo_pb2.Connection, next_state="Done")
  def Process(self, responses):
    for response in responses:
      # TODO(user): Implement proper AFF4 objects here.
      print response
      print self.pid_map.get(response.pid)
