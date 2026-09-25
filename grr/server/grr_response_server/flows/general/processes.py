#!/usr/bin/env python
"""These are process related flows."""
import itertools
import re

from google.protobuf import any_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import rrg_path
from grr_response_server import rrg_stubs
from grr_response_server import rrg_wmi
from grr_response_server import server_stubs
from grr_response_server.flows.general import file_finder
from grr_response_proto.rrg import fs_pb2 as rrg_fs_pb2
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2
from grr_response_proto.rrg.action import get_file_contents_pb2 as rrg_get_file_contents_pb2
from grr_response_proto.rrg.action import get_file_metadata_pb2 as rrg_get_file_metadata_pb2
from grr_response_proto.rrg.action import list_processes_pb2 as rrg_list_processes_pb2
from grr_response_proto.rrg.action import query_wmi_pb2 as rrg_query_wmi_pb2


class ListProcesses(
    flow_base.FlowBase[
        flows_pb2.ListProcessesArgs,
        flows_pb2.ListProcessesStore,
        flows_pb2.DefaultFlowProgress,
    ]
):
  """List running processes on a system."""

  category = "/Processes/"
  behaviours = flow_base.BEHAVIOUR_BASIC

  proto_args_type = flows_pb2.ListProcessesArgs
  proto_store_type = flows_pb2.ListProcessesStore
  proto_result_types = (sysinfo_pb2.Process, jobs_pb2.StatEntry)

  def Start(self):
    """Start processing."""
    if (
        # `get_file_contents` inline transfer mode was introduced in v0.0.9.
        self.rrg_version >= (0, 0, 9)
        and self.rrg_os_type == rrg_os_pb2.LINUX
        # TODO - Add support for fetching binaries.
        and not self.proto_args.fetch_binaries
    ):
      # On Linux we use procfs [1]: to get all available PIDs, we list all
      # folders under `/proc`.
      #
      # [1]: https://en.wikipedia.org/wiki/procfs
      get_file_metadata = rrg_stubs.GetFileMetadata()
      get_file_metadata.args.paths.add().raw_bytes = b"/proc"
      get_file_metadata.args.max_depth = 2

      # `/proc` also contains information about some other stuff, so we filter
      # the results to only those that are numbers (PIDs).
      if self.proto_args.pids:
        pid_pattern = "(" + "|".join(map(str, self.proto_args.pids)) + ")"
      else:
        pid_pattern = "[0-9]+"

      get_file_metadata.args.path_pruning_regex = (
          f"^/proc(/{pid_pattern}(/(exe|cwd)?)?)?$"
      )

      get_file_metadata.Call(self._ProcessProcfsGetFileMetadata)  # pyrefly: ignore[bad-argument-type]
    elif (
        self.rrg_support
        and self.rrg_os_type == rrg_os_pb2.WINDOWS
        # TODO - Add support for fetching binaries.
        and not self.proto_args.fetch_binaries
    ):
      query_wmi = rrg_stubs.QueryWmi()
      query_wmi.args.query = """
      SELECT
        ProcessId,
        ParentProcessId,
        Name,
        ExecutablePath,
        CommandLine,
        Priority,
        UserModeTime,
        KernelModeTime,
        PageFileUsage,
        WorkingSetSize,
        ThreadCount
      FROM
        Win32_Process
      """
      if self.proto_args.pids:
        query_wmi.args.query += " WHERE " + " OR ".join(
            f"ProcessId = {pid}" for pid in self.proto_args.pids
        )

      query_wmi.args.namespace = "root\\cimv2"
      query_wmi.Call(self._ProcessQueryWMI)  # pyrefly: ignore[bad-argument-type]
    elif (
        self.rrg_version >= (0, 0, 10)
        and self.rrg_os_type == rrg_os_pb2.MACOS
        # TODO - Add support for fetching binaries.
        and not self.proto_args.fetch_binaries
    ):
      list_processes = rrg_stubs.ListProcesses()

      if self.proto_args.process_name_regex:
        cond_name = list_processes.AddFilter().conditions.add()
        cond_name.field.extend([
            rrg_list_processes_pb2.Result.NAME_FIELD_NUMBER,
        ])
        cond_name.string_match = self.proto_args.process_name_regex

      if self.proto_args.filename_regex:
        cond_exe = list_processes.AddFilter().conditions.add()
        cond_exe.field.extend([
            rrg_list_processes_pb2.Result.EXE_FIELD_NUMBER,
            rrg_fs_pb2.Path.RAW_BYTES_FIELD_NUMBER,
        ])
        cond_exe.bytes_match = self.proto_args.filename_regex

      list_processes.Call(self._ProcessListProcesses)  # pyrefly: ignore[bad-argument-type]
    else:
      self.CallClientProto(
          server_stubs.ListProcesses,
          next_state=self.IterateProcesses.__name__,
      )

  @flow_base.UseProto2AnyResponses  # pyrefly: ignore[bad-argument-type]
  def _ProcessProcfsGetFileMetadata(
      self,
      responses_any: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses_any.success:
      raise flow_base.FlowError(
          f"Failed to list `/proc`: {responses_any.status}",
      )

    for response_any in responses_any:
      response = rrg_get_file_metadata_pb2.Result()
      response.ParseFromString(response_any.value)

      path = rrg_path.PurePosixPath(response.path)

      assert path.components[0] == "proc"

      # We will get an entry for `/proc` folder itself, so we just skip it.
      if len(path.components) == 1:
        continue

      pid = int(path.components[1])
      process = self.GetStoreProcess(pid)

      # We will get entries for `/proc/$PID` folders. We skip it but note that
      # we still created a process entry for them above even if no executable or
      # working directory was collected (as they may have none).
      if len(path.components) == 2:
        continue

      # At this point we should only be dealing with `/proc/$PID/exe` or with
      # `/proc/$PID/cwd` paths.
      assert len(path.components) == 3

      if response.metadata.type != rrg_fs_pb2.FileMetadata.SYMLINK:
        raise flow_base.FlowError(
            f"{path} is not a symlink: {response.metadata.type}",
        )
      symlink = response.symlink.raw_bytes.decode("utf-8", "backslashreplace")

      if path.components[2] == "cwd":
        process.cwd = symlink
      elif path.components[2] == "exe":
        process.exe = symlink
      else:
        raise flow_base.FlowError(
            f"Unexpected `/proc` path: {path}",
        )

    processes = list(self.store.processes)
    # TODO - Replace with `clear()` once upgraded.
    del self.store.processes[:]
    self.store.processes.extend(
        process
        for process in processes
        if re.search(self.proto_args.filename_regex, process.exe)
    )

    # Early return to avoid unnecessary roundtrip to the endpoint in case no
    # processes were listed (which should generally not happen but who knows).
    if not self.store.processes:
      return

    get_file_contents = rrg_stubs.GetFileContents()
    get_file_contents.args.mode = rrg_get_file_contents_pb2.Mode.INLINE

    for process in self.store.processes:
      pid = process.pid

      get_file_contents.args.paths.add(
          raw_bytes=f"/proc/{pid}/cmdline".encode("ascii"),
      )
      get_file_contents.args.paths.add(
          raw_bytes=f"/proc/{pid}/stat".encode("ascii"),
      )
      get_file_contents.args.paths.add(
          raw_bytes=f"/proc/{pid}/status".encode("ascii"),
      )

    get_file_contents.Call(self._ProcessProcfsGetFileContents)  # pyrefly: ignore[bad-argument-type]

  @flow_base.UseProto2AnyResponses  # pyrefly: ignore[bad-argument-type]
  def _ProcessProcfsGetFileContents(
      self,
      responses_any: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses_any.success:
      raise flow_base.FlowError(
          f"Failed to read `/proc` contents: {responses_any.status}",
      )

    responses_by_path: dict[
        rrg_path.PurePosixPath,
        list[rrg_get_file_contents_pb2.Result],
    ] = dict()

    for response_any in responses_any:
      response = rrg_get_file_contents_pb2.Result()
      response.ParseFromString(response_any.value)

      path = rrg_path.PurePosixPath(response.path)
      responses_by_path.setdefault(path, []).append(response)

    blobs_by_pid_cmdline = dict()
    blobs_by_pid_stat = dict()
    blobs_by_pid_status = dict()

    for path, responses in responses_by_path.items():
      errors = [response.error for response in responses if response.error]
      if errors:
        self.Log("Failed to read %s: %s", path, errors)
        continue

      responses = sorted(responses, key=lambda response: response.offset)
      for response_curr, response_next in itertools.pairwise(responses):
        if response_curr.offset + response_curr.length != response_next.offset:
          raise flow_base.FlowError(
              f"Missing response for '{path}': {responses}",
          )

      assert len(path.components) == 3
      pid = int(path.components[1])

      for response in responses:
        if path.components[2] == "cmdline":
          blobs = blobs_by_pid_cmdline.setdefault(pid, [])
        elif path.components[2] == "stat":
          blobs = blobs_by_pid_stat.setdefault(pid, [])
        elif path.components[2] == "status":
          blobs = blobs_by_pid_status.setdefault(pid, [])
        else:
          raise flow_base.FlowError(
              f"Unexpected procfs path: {path}",
          )

        blobs.append(response.blob_contents)

    for process in self.store.processes:
      pid = process.pid
      result = self.GetStoreProcess(pid)

      # Contents could be empty (e.g. `/proc/2/cmdline`) or we just hit a race
      # condition (the process disappeared since it was listed) and so no blobs
      # will be available. We do `.get(pid, [])` to account for this.

      if contents_cmdline := b"".join(blobs_by_pid_cmdline.get(pid, [])):
        cmdline_str = contents_cmdline.decode("utf-8", "backslashreplace")
        # `cmdline` is not only 0-separated but also ends with an extra 0-byte,
        # so there will be an extra empty string at the end that we slice-out.
        result.cmdline.extend(cmdline_str.split("\x00")[:-1])

      if contents_stat := b"".join(blobs_by_pid_stat.get(pid, [])):
        _ParseProcfsStat(pid, contents_stat, result)

      if contents_status := b"".join(blobs_by_pid_status.get(pid, [])):
        _ParseProcfsStatus(pid, contents_status, result)

      # TODO - Figure out how to get the username.
      # TODO - Add support for listing network connections.

      if not re.search(self.proto_args.process_name_regex, result.name):
        continue
      if not re.search(self.proto_args.cmdline_regex, " ".join(result.cmdline)):
        continue

      self.SendReplyProto(result)

  @flow_base.UseProto2AnyResponses  # pyrefly: ignore[bad-argument-type]
  def _ProcessQueryWMI(
      self,
      responses_any: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses_any.success:
      raise flow_base.FlowError(
          f"Failed to query WMI: {responses_any.status}",
      )

    for response_any in responses_any:
      response = rrg_query_wmi_pb2.Result()
      response.ParseFromString(response_any.value)

      result = self.store.processes.add()
      result.pid = rrg_wmi.UInt32(response.row["ProcessId"])
      result.ppid = rrg_wmi.UInt32(response.row["ParentProcessId"])
      result.name = response.row["Name"].string
      result.exe = response.row["ExecutablePath"].string
      # TODO - `.split()` will not work well in case the arguments
      # contain a space (in which case they are quoted). We need to do some
      # parsing or use `shlex` accounting for some potential incompatibilities.
      result.cmdline.extend(response.row["CommandLine"].string.split())
      result.nice = rrg_wmi.UInt32(response.row["Priority"])
      result.num_threads = rrg_wmi.UInt32(response.row["ThreadCount"])
      # `*ModeTime` columns are specified in nanoseconds [1, 2], `*_cpu_time`
      # fields are in floating point seconds.
      #
      # pylint: disable=line-too-long
      # [1]: https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-process#:~:text=UserModeTime
      # [2]: https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-process#:~:text=KernelModeTime
      # pylint: enable=line-too-long
      result.user_cpu_time = rrg_wmi.UInt64(response.row["UserModeTime"]) / 1e7
      result.system_cpu_time = (
          rrg_wmi.UInt64(response.row["KernelModeTime"]) / 1e7
      )
      # The `PageFileUsage` column is given in kilobytes [1].
      #
      # pylint: disable=line-too-long
      # [1]: https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-process#:~:text=PageFileUsage
      # pylint: enable=line-too-long
      result.VMS_size = rrg_wmi.UInt32(response.row["PageFileUsage"]) * 1024
      # The `WorkingSetSize` column is give in bytes [1].
      #
      # pylint: disable=line-too-long
      # [1]: https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-process#:~:text=WorkingSetSize
      # pylint: enable=line-too-long
      result.RSS_size = rrg_wmi.UInt64(response.row["WorkingSetSize"])

      if not re.search(self.proto_args.process_name_regex, result.name):
        continue
      if not re.search(self.proto_args.filename_regex, result.exe):
        continue
      if not re.search(self.proto_args.cmdline_regex, " ".join(result.cmdline)):
        continue

      self.SendReplyProto(result)

  @flow_base.UseProto2AnyResponses  # pyrefly: ignore[bad-argument-type]
  def _ProcessListProcesses(
      self,
      responses_any: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses_any.success:
      raise flow_base.FlowError(
          f"Failed to list processes: {responses_any.status}",
      )

    for response_any in responses_any:
      response = rrg_list_processes_pb2.Result()
      response.ParseFromString(response_any.value)

      result = sysinfo_pb2.Process()
      result.pid = response.pid
      result.ppid = response.ppid
      result.name = response.name
      result.exe = response.exe.raw_bytes.decode("utf-8", "backslashreplace")
      result.cmdline.extend(response.args)

      if self.proto_args.pids and result.pid not in self.proto_args.pids:
        continue
      if not re.search(self.proto_args.cmdline_regex, " ".join(result.cmdline)):
        continue

      self.SendReplyProto(result)

  def _FilenameMatch(self, process: sysinfo_pb2.Process) -> bool:
    if not self.proto_args.filename_regex:
      return True
    return bool(re.compile(self.proto_args.filename_regex).match(process.exe))

  @flow_base.UseProto2AnyResponses  # pyrefly: ignore[bad-argument-type]
  def IterateProcesses(
      self, responses_any: flow_responses.Responses[any_pb2.Any]
  ) -> None:
    """This stores the processes."""

    if not responses_any.success:
      # Check for error, but continue. Errors are common on client.
      raise flow_base.FlowError(
          "Error during process listing %s" % responses_any.status
      )

    responses = []
    for response_any in responses_any:
      response = sysinfo_pb2.Process()
      response_any.Unpack(response)
      responses.append(response)

    # TODO - consider implementing filtering on the client to avoid
    # transferring a lot of data to the server.

    if self.proto_args.pids:
      pids = set(self.proto_args.pids)
      responses = [p for p in responses if p.pid in pids]

    if self.proto_args.process_name_regex:
      process_name_regex = re.compile(self.proto_args.process_name_regex)
      responses = [p for p in responses if process_name_regex.match(p.name)]

    if self.proto_args.cmdline_regex:
      cmdline_regex = re.compile(self.proto_args.cmdline_regex)
      responses = [
          p for p in responses if cmdline_regex.match(" ".join(p.cmdline))
      ]

    if self.proto_args.fetch_binaries:
      # Filter out processes entries without "exe" attribute and
      # deduplicate the list.
      paths_to_fetch = set()
      for p in responses:
        if p.exe and self._FilenameMatch(p):
          paths_to_fetch.add(p.exe)
      paths_to_fetch = sorted(paths_to_fetch)

      self.Log(
          "Got %d processes, fetching binaries for %d...",
          len(responses),
          len(paths_to_fetch),
      )

      self.CallFlowProto(
          file_finder.ClientFileFinder.__name__,
          flow_args=flows_pb2.FileFinderArgs(
              paths=paths_to_fetch,
              action=flows_pb2.FileFinderAction(
                  action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD
              ),
          ),
          next_state=self.HandleDownloadedFiles.__name__,
      )

    else:
      # Only send the list of processes if we don't fetch the binaries
      skipped = 0
      for p in responses:
        # It's normal to have lots of sleeping processes with no executable path
        # associated.
        if self.proto_args.filename_regex and not p.exe:
          skipped += 1
          continue

        if self._FilenameMatch(p):
          self.SendReplyProto(p)

      if skipped:
        self.Log("Skipped %s entries, missing path for regex" % skipped)

  @flow_base.UseProto2AnyResponses  # pyrefly: ignore[bad-argument-type]
  def HandleDownloadedFiles(
      self, responses: flow_responses.Responses[any_pb2.Any]
  ) -> None:
    """Handle success/failure of the FileFinder flow."""
    if not responses.success:
      self.Log(
          "Download of file %s failed %s",
          responses.request_data["path"],  # pyrefly: ignore[unsupported-operation]
          responses.status,
      )

    for response_any in responses:
      response = flows_pb2.FileFinderResult()
      response_any.Unpack(response)

      self.Log("Downloaded %s", response.stat_entry.pathspec)
      self.SendReplyProto(response.stat_entry)

  def GetStoreProcess(self, pid: int) -> sysinfo_pb2.Process:
    """Returns a `Process` message from the flow store associated with the PID.

    If a message with the given PID does not exist in the store, it is added and
    the added message is added to the store first.

    Args:
      pid: A process identifier to return the `Process` message for.

    Returns:
      A `Process` message associated with the given PID.
    """
    for process in self.store.processes:
      if process.pid == pid:
        return process

    process = self.store.processes.add()
    process.pid = pid
    return process


def _ParseProcfsStat(
    pid: int,
    content: bytes,
    result: sysinfo_pb2.Process,
) -> None:
  """Parses contents of the `/proc/{pid}/stat` file."""
  fields = content.decode("utf-8", "backslashreplace").split()

  # This is done just as a sanity check.
  if int(fields[1 - 1]) != pid:
    raise ValueError(f"Invalid PID in /`proc/{pid}/stat`: {int(fields[1 - 1])}")

  # https://man7.org/linux/man-pages/man5/proc_pid_stat.5.html
  tty_nr = int(fields[7 - 1])
  if tty_nr != 0:
    # * Major is defined on bits 15 to 8.
    # * Minor is defined on bits 31 to 20 and 7 to 0.
    dev_major = (tty_nr & 0b11111111_00000000) >> 8
    dev_minor = ((tty_nr >> 20) << 8) | (tty_nr & 0b11111111)

    # https://www.kernel.org/doc/Documentation/admin-guide/devices.txt
    if dev_major == 4:
      if dev_minor < 64:
        result.terminal = f"/dev/tty{dev_minor}"
      else:
        result.terminal = f"/dev/ttyS{dev_minor - 64}"
    elif dev_major >= 136 and dev_major <= 143:
      result.terminal = f"/dev/pts/{dev_minor}"

  # https://man7.org/linux/man-pages/man5/proc_pid_stat.5.html
  result.nice = int(fields[19 - 1])

  # https://man7.org/linux/man-pages/man5/proc_pid_stat.5.html
  result.user_cpu_time = int(fields[14 - 1]) / 100.0
  result.system_cpu_time = int(fields[15 - 1]) / 100.0
  result.RSS_size = int(fields[24 - 1]) * 4096
  result.VMS_size = int(fields[23 - 1])


def _ParseProcfsStatus(
    pid: int,
    contents: bytes,
    result: sysinfo_pb2.Process,
) -> None:
  """Parses contents of the `/proc/{pid}/status` file."""
  contents_str = contents.decode("utf-8", "backlashreplace")

  if match := re.search(
      r"^Pid:\s*(?P<pid>\d+)$",
      contents_str,
      re.MULTILINE,
  ):
    # This is done just as a sanity check.
    if pid != int(match["pid"]):
      raise ValueError(f"Unexpected PID in `/proc/{pid}/status: {match['pid']}")
  else:
    raise ValueError(f"No PID in `/proc/{pid}/status`")

  if match := re.search(
      r"^PPid:\s*(?P<ppid>\d+)$",
      contents_str,
      re.MULTILINE,
  ):
    result.ppid = int(match["ppid"])
  else:
    raise ValueError(f"No PPID in `/proc/{pid}/status`")

  if match := re.search(
      r"^Name:\s*(?P<name>.*)$",
      contents_str,
      re.MULTILINE,
  ):
    result.name = match["name"]
  else:
    raise ValueError(f"No name in `/proc/{pid}/status")

  if match := re.search(
      r"^Uid:\s*(?P<uid_r>\d+)\s*(?P<uid_e>\d+)\s*(?P<uid_s>\d+)\s*(?P<uid_f>\d+)$",
      contents_str,
      re.MULTILINE,
  ):
    result.real_uid = int(match["uid_r"])
    result.effective_uid = int(match["uid_e"])
    result.saved_uid = int(match["uid_s"])
  else:
    raise ValueError("No UID in `/proc/{pid}/status")

  if match := re.search(
      r"^Gid:\s*(?P<gid_r>\d+)\s*(?P<gid_e>\d+)\s*(?P<gid_s>\d+)\s*(?P<gid_f>\d+)$",
      contents_str,
      re.MULTILINE,
  ):
    result.real_gid = int(match["gid_r"])
    result.effective_gid = int(match["gid_e"])
    result.saved_gid = int(match["gid_s"])
  else:
    raise ValueError("No GID in `/proc/{pid}/status")

  if match := re.search(
      r"^State:\s*(?P<state>.*)$",
      contents_str,
      re.MULTILINE,
  ):
    result.status = match["state"]
  else:
    raise ValueError(f"No state in `/proc/{pid}/status`")

  if match := re.search(
      r"^Threads:\s*(?P<threads>\d+)$",
      contents_str,
      re.MULTILINE,
  ):
    result.num_threads = int(match["threads"])
  else:
    raise ValueError(f"No thread number in `/proc/{pid}/status`")
