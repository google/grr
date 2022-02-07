#!/usr/bin/env python
from absl import app

from grr_response_core.lib.rdfvalues import plist as rdf_plist
from grr_response_server.export_converters import launchd_plist
from grr.test_lib import export_test_lib
from grr.test_lib import test_lib


class LaunchdPlistConverterTest(export_test_lib.ExportTestBase):
  """Tests for LaunchdPlist converter."""

  def testExportsValueCorrectly(self):
    sample = rdf_plist.LaunchdPlist(
        path="/etc/foo.plist",
        Label="label",
        Disabled=True,
        UserName="someuser",
        GroupName="somegroup",
        Program="foo",
        ProgramArguments=["-h", "-k"],
        RootDirectory="/foo",
        WorkingDirectory="/bar",
        OnDemand=True,
        RunAtLoad=True,
        StartCalendarInterval=[
            rdf_plist.LaunchdStartCalendarIntervalEntry(
                Minute=1, Hour=2, Day=3, Weekday=4, Month=5),
            rdf_plist.LaunchdStartCalendarIntervalEntry(
                Minute=2, Hour=3, Day=4, Weekday=5, Month=6),
        ],
        EnvironmentVariables=[
            rdf_plist.PlistStringDictEntry(name="foo", value="bar"),
            rdf_plist.PlistStringDictEntry(name="foo2", value="bar2"),
        ],
        KeepAlive=True,
        KeepAliveDict=rdf_plist.LaunchdKeepAlive(
            SuccessfulExit=True,
            NetworkState=True,
            PathState=[
                rdf_plist.PlistBoolDictEntry(name="foo", value=True),
                rdf_plist.PlistBoolDictEntry(name="bar", value=False),
            ],
            OtherJobEnabled=[
                rdf_plist.PlistBoolDictEntry(name="foo2", value=True),
                rdf_plist.PlistBoolDictEntry(name="bar2", value=False),
            ],
        ),
        StandardInPath="in_path",
        StandardOutPath="out_path",
        StandardErrorPath="error_path",
        LimitLoadToHosts=["host1", "host2"],
        LimitLoadFromHosts=["host3", "host4"],
        LimitLoadToSessionType=["type1", "type2"],
        EnableGlobbing=True,
        EnableTransactions=True,
        Umask=42,
        TimeOut=43,
        ExitTimeOut=44,
        ThrottleInterval=45,
        InitGroups=True,
        WatchPaths=["path1", "path2"],
        QueueDirectories=["dir1", "dir2"],
        StartOnMount=True,
        StartInterval=46,
        Debug=True,
        WaitForDebugger=True,
        Nice=47,
        ProcessType="sometype",
        AbandonProcessGroup=True,
        LowPriorityIO=True,
        LaunchOnlyOnce=True,
        inetdCompatibilityWait=True,
        SoftResourceLimits=True,
        HardResourceLimits=True,
        Sockets=True)

    converter = launchd_plist.LaunchdPlistConverter()
    converted = list(converter.Convert(self.metadata, sample))

    self.assertLen(converted, 1)
    c = converted[0]

    self.assertIsInstance(c, launchd_plist.ExportedLaunchdPlist)

    self.assertEqual(c.metadata, self.metadata)
    self.assertEqual(c.launchd_file_path, "/etc/foo.plist")

    self.assertEqual(c.label, "label")
    self.assertTrue(c.disabled)
    self.assertEqual(c.user_name, "someuser")
    self.assertEqual(c.group_name, "somegroup")
    self.assertEqual(c.program, "foo")
    self.assertEqual(c.program_arguments, "-h -k")
    self.assertEqual(c.root_directory, "/foo")
    self.assertEqual(c.working_directory, "/bar")
    self.assertTrue(c.on_demand)
    self.assertTrue(c.run_at_load)
    self.assertEqual(c.start_calendar_interval, "5-4-3-2-1 6-5-4-3-2")
    self.assertEqual(c.environment_variables, "foo=bar foo2=bar2")
    self.assertEqual(c.standard_in_path, "in_path")
    self.assertEqual(c.standard_out_path, "out_path")
    self.assertEqual(c.standard_error_path, "error_path")
    self.assertEqual(c.limit_load_to_hosts, "host1 host2")
    self.assertEqual(c.limit_load_from_hosts, "host3 host4")
    self.assertEqual(c.limit_load_to_session_type, "type1 type2")
    self.assertTrue(c.enable_globbing)
    self.assertTrue(c.enable_transactions)
    self.assertEqual(c.umask, 42)
    self.assertEqual(c.time_out, 43)
    self.assertEqual(c.exit_time_out, 44)
    self.assertEqual(c.throttle_interval, 45)
    self.assertTrue(c.init_groups)
    self.assertEqual(c.watch_paths, "path1 path2")
    self.assertEqual(c.queue_directories, "dir1 dir2")
    self.assertTrue(c.start_on_mount)
    self.assertEqual(c.start_interval, 46)
    self.assertTrue(c.debug)
    self.assertTrue(c.wait_for_debugger)
    self.assertEqual(c.nice, 47)
    self.assertEqual(c.process_type, "sometype")
    self.assertTrue(c.abandon_process_group)
    self.assertTrue(c.low_priority_io)
    self.assertTrue(c.launch_only_once)
    self.assertTrue(c.inetd_compatibility_wait)
    self.assertTrue(c.soft_resource_limits)
    self.assertTrue(c.hard_resource_limits)
    self.assertTrue(c.sockets)
    self.assertTrue(c.keep_alive)
    self.assertTrue(c.keep_alive_successful_exit)
    self.assertTrue(c.keep_alive_network_state)
    self.assertEqual(c.keep_alive_path_state, "foo=True bar=False")
    self.assertEqual(c.keep_alive_other_job_enabled, "foo2=True bar2=False")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
