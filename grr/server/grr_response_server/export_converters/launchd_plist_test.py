#!/usr/bin/env python
from absl import app
from absl.testing import absltest

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_proto import export_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_server.export_converters import launchd_plist
from grr.test_lib import test_lib


class LaunchdPlistConverterProtoTest(absltest.TestCase):
  """Tests for LaunchdPlistConverterProto."""

  def setUp(self):
    super().setUp()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testLaunchdPlistConverter(self):
    keep_alive_dict = sysinfo_pb2.LaunchdKeepAlive(
        SuccessfulExit=True,
        NetworkState=True,
        PathState=[
            sysinfo_pb2.PlistBoolDictEntry(name="test_path1", value=True),
            sysinfo_pb2.PlistBoolDictEntry(name="test_path2", value=False),
        ],
        OtherJobEnabled=[
            sysinfo_pb2.PlistBoolDictEntry(name="test_job1", value=True),
            sysinfo_pb2.PlistBoolDictEntry(name="test_job2", value=False),
        ],
    )
    sample = sysinfo_pb2.LaunchdPlist(
        path="test_path",
        Label="test_label",
        Disabled=True,
        UserName="test_user",
        GroupName="test_group",
        Program="test_program",
        ProgramArguments=["arg1", "arg2"],
        RootDirectory="test_root_directory",
        WorkingDirectory="test_working_directory",
        OnDemand=True,
        RunAtLoad=True,
        StartCalendarInterval=[
            sysinfo_pb2.LaunchdStartCalendarIntervalEntry(
                Month=1, Weekday=2, Day=3, Hour=4, Minute=5
            ),
            sysinfo_pb2.LaunchdStartCalendarIntervalEntry(
                Month=6, Weekday=7, Day=8, Hour=9, Minute=10
            ),
        ],
        EnvironmentVariables=[
            sysinfo_pb2.PlistStringDictEntry(name="test_env1", value="val1"),
            sysinfo_pb2.PlistStringDictEntry(name="test_env2", value="val2"),
        ],
        StandardInPath="test_standard_in_path",
        StandardOutPath="test_standard_out_path",
        StandardErrorPath="test_standard_error_path",
        LimitLoadToHosts=["host1", "host2"],
        LimitLoadFromHosts=["host3", "host4"],
        LimitLoadToSessionType=["session1", "session2"],
        EnableGlobbing=True,
        EnableTransactions=True,
        Umask=123,
        TimeOut=456,
        ExitTimeOut=789,
        ThrottleInterval=1011,
        InitGroups=True,
        WatchPaths=["path1", "path2"],
        QueueDirectories=["dir1", "dir2"],
        StartOnMount=True,
        StartInterval=1213,
        Debug=True,
        WaitForDebugger=True,
        Nice=1415,
        ProcessType="test_process_type",
        AbandonProcessGroup=True,
        LowPriorityIO=True,
        LaunchOnlyOnce=True,
        inetdCompatibilityWait=True,
        SoftResourceLimits=True,
        HardResourceLimits=True,
        Sockets=True,
        KeepAlive=True,
        KeepAliveDict=keep_alive_dict,
    )

    converter = launchd_plist.LaunchdPlistConverterProto()
    results = list(converter.Convert(self.metadata_proto, sample))

    self.assertLen(results, 1)

    self.assertEqual(results[0].launchd_file_path, "test_path")
    self.assertEqual(results[0].label, "test_label")
    self.assertTrue(results[0].disabled)
    self.assertEqual(results[0].user_name, "test_user")
    self.assertEqual(results[0].group_name, "test_group")
    self.assertEqual(results[0].program, "test_program")
    self.assertEqual(results[0].program_arguments, "arg1 arg2")
    self.assertEqual(results[0].root_directory, "test_root_directory")
    self.assertEqual(results[0].working_directory, "test_working_directory")
    self.assertTrue(results[0].on_demand)
    self.assertTrue(results[0].run_at_load)
    self.assertEqual(results[0].start_calendar_interval, "1-2-3-4-5 6-7-8-9-10")
    self.assertEqual(
        results[0].environment_variables, "test_env1=val1 test_env2=val2"
    )
    self.assertEqual(results[0].standard_in_path, "test_standard_in_path")
    self.assertEqual(results[0].standard_out_path, "test_standard_out_path")
    self.assertEqual(results[0].standard_error_path, "test_standard_error_path")
    self.assertEqual(results[0].limit_load_to_hosts, "host1 host2")
    self.assertEqual(results[0].limit_load_from_hosts, "host3 host4")
    self.assertEqual(results[0].limit_load_to_session_type, "session1 session2")
    self.assertTrue(results[0].enable_globbing)
    self.assertTrue(results[0].enable_transactions)
    self.assertEqual(results[0].umask, 123)
    self.assertEqual(results[0].time_out, 456)
    self.assertEqual(results[0].exit_time_out, 789)
    self.assertEqual(results[0].throttle_interval, 1011)
    self.assertTrue(results[0].init_groups)
    self.assertEqual(results[0].watch_paths, "path1 path2")
    self.assertEqual(results[0].queue_directories, "dir1 dir2")
    self.assertTrue(results[0].start_on_mount)
    self.assertEqual(results[0].start_interval, 1213)
    self.assertTrue(results[0].debug)
    self.assertTrue(results[0].wait_for_debugger)
    self.assertEqual(results[0].nice, 1415)
    self.assertEqual(results[0].process_type, "test_process_type")
    self.assertTrue(results[0].abandon_process_group)
    self.assertTrue(results[0].low_priority_io)
    self.assertTrue(results[0].launch_only_once)
    self.assertTrue(results[0].inetd_compatibility_wait)
    self.assertTrue(results[0].soft_resource_limits)
    self.assertTrue(results[0].hard_resource_limits)
    self.assertTrue(results[0].sockets)
    self.assertTrue(results[0].keep_alive)
    self.assertTrue(results[0].keep_alive_successful_exit)
    self.assertTrue(results[0].keep_alive_network_state)
    self.assertEqual(
        results[0].keep_alive_path_state, "test_path1=True test_path2=False"
    )
    self.assertEqual(
        results[0].keep_alive_other_job_enabled,
        "test_job1=True test_job2=False",
    )


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
