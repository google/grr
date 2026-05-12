#!/usr/bin/env python
"""Classes for exporting LaunchdPlist."""

from collections.abc import Iterator

from grr_response_proto import export_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_server.export_converters import base


class LaunchdPlistConverterProto(
    base.ExportConverterProto[sysinfo_pb2.LaunchdPlist]
):
  """Export converter for LaunchdPlist."""

  input_proto_type = sysinfo_pb2.LaunchdPlist
  output_proto_types = (export_pb2.ExportedLaunchdPlist,)

  def Convert(
      self, metadata: export_pb2.ExportedMetadata, l: sysinfo_pb2.LaunchdPlist
  ) -> Iterator[export_pb2.ExportedLaunchdPlist]:
    yield export_pb2.ExportedLaunchdPlist(
        metadata=metadata,
        launchd_file_path=l.path,
        label=l.Label,
        disabled=l.Disabled,
        user_name=l.UserName,
        group_name=l.GroupName,
        program=l.Program,
        program_arguments=" ".join(l.ProgramArguments),
        root_directory=l.RootDirectory,
        working_directory=l.WorkingDirectory,
        on_demand=l.OnDemand,
        run_at_load=l.RunAtLoad,
        start_calendar_interval=" ".join(
            f"{i.Month}-{i.Weekday}-{i.Day}-{i.Hour}-{i.Minute}"
            for i in l.StartCalendarInterval
        ),
        environment_variables=" ".join(
            f"{e.name}={e.value}" for e in l.EnvironmentVariables
        ),
        standard_in_path=l.StandardInPath,
        standard_out_path=l.StandardOutPath,
        standard_error_path=l.StandardErrorPath,
        limit_load_to_hosts=" ".join(i for i in l.LimitLoadToHosts),
        limit_load_from_hosts=" ".join(i for i in l.LimitLoadFromHosts),
        limit_load_to_session_type=" ".join(
            i for i in l.LimitLoadToSessionType
        ),
        enable_globbing=l.EnableGlobbing,
        enable_transactions=l.EnableTransactions,
        umask=l.Umask,
        time_out=l.TimeOut,
        exit_time_out=l.ExitTimeOut,
        throttle_interval=l.ThrottleInterval,
        init_groups=l.InitGroups,
        watch_paths=" ".join(i for i in l.WatchPaths),
        queue_directories=" ".join(i for i in l.QueueDirectories),
        start_on_mount=l.StartOnMount,
        start_interval=l.StartInterval,
        debug=l.Debug,
        wait_for_debugger=l.WaitForDebugger,
        nice=l.Nice,
        process_type=l.ProcessType,
        abandon_process_group=l.AbandonProcessGroup,
        low_priority_io=l.LowPriorityIO,
        launch_only_once=l.LaunchOnlyOnce,
        inetd_compatibility_wait=l.inetdCompatibilityWait,
        soft_resource_limits=l.SoftResourceLimits,
        hard_resource_limits=l.HardResourceLimits,
        sockets=l.Sockets,
        keep_alive=l.KeepAlive,
        keep_alive_successful_exit=l.KeepAliveDict.SuccessfulExit,
        keep_alive_network_state=l.KeepAliveDict.NetworkState,
        keep_alive_path_state=" ".join(
            f"{e.name}={e.value}" for e in l.KeepAliveDict.PathState
        ),
        keep_alive_other_job_enabled=" ".join(
            f"{e.name}={e.value}" for e in l.KeepAliveDict.OtherJobEnabled
        ),
    )
