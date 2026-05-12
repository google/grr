#!/usr/bin/env python
"""Test the process list module."""

import os

from absl import app

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_server import data_store
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.flows.general import processes as flow_processes
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import rrg_test_lib
from grr.test_lib import test_lib
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2


class ListProcessesTest(flow_test_lib.FlowTestsBaseclass):
  """Test the process listing flow."""

  def testProcessListingOnly(self):
    """Test that the ListProcesses flow works."""
    client_id = self.SetupClient(0)

    client_mock = action_mocks.ListProcessesMock([
        rdf_client.Process(
            pid=2,
            ppid=1,
            cmdline=["cmd.exe"],
            exe="c:\\windows\\cmd.exe",
            ctime=1333718907167083,
        )
    ])

    session_id = flow_test_lib.StartAndRunFlow(
        flow_processes.ListProcesses,
        client_mock,
        client_id=client_id,
        creator=self.test_username,
    )

    processes = flow_test_lib.GetUnpackedFlowResults(
        client_id=client_id,
        flow_id=session_id,
        result_type=sysinfo_pb2.Process,
    )

    self.assertLen(processes, 1)
    self.assertEqual(processes[0].ctime, 1333718907167083)
    self.assertEqual(processes[0].cmdline, ["cmd.exe"])

  def testProcessListingWithFilter(self):
    """Test that the ListProcesses flow works with filter."""
    client_id = self.SetupClient(0)

    client_mock = action_mocks.ListProcessesMock([
        rdf_client.Process(
            pid=2,
            ppid=1,
            cmdline=["cmd.exe"],
            exe="c:\\windows\\cmd.exe",
            ctime=1333718907167083,
        ),
        rdf_client.Process(
            pid=3,
            ppid=1,
            cmdline=["cmd2.exe"],
            exe="c:\\windows\\cmd2.exe",
            ctime=1333718907167083,
        ),
        rdf_client.Process(
            pid=4, ppid=1, cmdline=["missing_exe.exe"], ctime=1333718907167083
        ),
        rdf_client.Process(
            pid=5, ppid=1, cmdline=["missing2_exe.exe"], ctime=1333718907167083
        ),
    ])

    session_id = flow_test_lib.StartAndRunFlow(
        flow_processes.ListProcesses,
        client_mock,
        client_id=client_id,
        creator=self.test_username,
        flow_args=flows_pb2.ListProcessesArgs(
            filename_regex=r".*cmd2.exe",
        ),
    )

    # Expect one result that matches regex
    processes = flow_test_lib.GetUnpackedFlowResults(
        client_id=client_id,
        flow_id=session_id,
        result_type=sysinfo_pb2.Process,
    )

    self.assertLen(processes, 1)
    self.assertEqual(processes[0].ctime, 1333718907167083)
    self.assertEqual(processes[0].cmdline, ["cmd2.exe"])

    # Expect two skipped results
    logs = data_store.REL_DB.ReadFlowLogEntries(client_id, session_id, 0, 100)
    for log in logs:
      if "Skipped 2" in log.message:
        return
    raise RuntimeError("Skipped process not mentioned in logs")

  def testFetchesAndStoresBinary(self):
    client_id = self.SetupClient(0)

    process = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["test_img.dd"],
        exe=os.path.join(self.base_path, "test_img.dd"),
        ctime=1333718907167083,
    )

    client_mock = action_mocks.ListProcessesMock([process])

    session_id = flow_test_lib.StartAndRunFlow(
        flow_processes.ListProcesses,
        client_mock,
        client_id=client_id,
        creator=self.test_username,
        flow_args=flows_pb2.ListProcessesArgs(
            fetch_binaries=True,
        ),
    )

    binaries = flow_test_lib.GetUnpackedFlowResults(
        client_id=client_id,
        flow_id=session_id,
        result_type=jobs_pb2.StatEntry,
    )
    self.assertLen(binaries, 1)
    self.assertEqual(binaries[0].pathspec.path, process.exe)
    self.assertEqual(binaries[0].st_size, os.stat(process.exe).st_size)

  def testDoesNotFetchDuplicates(self):
    client_id = self.SetupClient(0)
    process1 = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["test_img.dd"],
        exe=os.path.join(self.base_path, "test_img.dd"),
        ctime=1333718907167083,
    )

    process2 = rdf_client.Process(
        pid=3,
        ppid=1,
        cmdline=["test_img.dd", "--arg"],
        exe=os.path.join(self.base_path, "test_img.dd"),
        ctime=1333718907167083,
    )

    client_mock = action_mocks.ListProcessesMock([process1, process2])

    session_id = flow_test_lib.StartAndRunFlow(
        flow_processes.ListProcesses,
        client_mock,
        client_id=client_id,
        creator=self.test_username,
        flow_args=flows_pb2.ListProcessesArgs(
            fetch_binaries=True,
        ),
    )

    processes = flow_test_lib.GetUnpackedFlowResults(
        client_id=client_id,
        flow_id=session_id,
        result_type=jobs_pb2.StatEntry,
    )
    self.assertLen(processes, 1)

  def testWhenFetchingIgnoresMissingFiles(self):
    client_id = self.SetupClient(0)
    process1 = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["test_img.dd"],
        exe=os.path.join(self.base_path, "test_img.dd"),
        ctime=1333718907167083,
    )

    process2 = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["file_that_does_not_exist"],
        exe=os.path.join(self.base_path, "file_that_does_not_exist"),
        ctime=1333718907167083,
    )

    client_mock = action_mocks.ListProcessesMock([process1, process2])

    session_id = flow_test_lib.StartAndRunFlow(
        flow_processes.ListProcesses,
        client_mock,
        client_id=client_id,
        creator=self.test_username,
        check_flow_errors=False,
        flow_args=flows_pb2.ListProcessesArgs(
            fetch_binaries=True,
        ),
    )

    binaries = flow_test_lib.GetUnpackedFlowResults(
        client_id=client_id,
        flow_id=session_id,
        result_type=jobs_pb2.StatEntry,
    )
    self.assertLen(binaries, 1)
    self.assertEqual(binaries[0].pathspec.path, process1.exe)

  def testPidFiltering(self):
    client_id = self.SetupClient(0)

    proc_foo = rdf_client.Process()
    proc_foo.pid = 42
    proc_foo.exe = "/usr/bin/foo"

    proc_bar = rdf_client.Process()
    proc_bar.pid = 108
    proc_bar.exe = "/usr/bin/bar"

    proc_baz = rdf_client.Process()
    proc_baz.pid = 1337
    proc_baz.exe = "/usr/bin/baz"

    args = flows_pb2.ListProcessesArgs()
    args.pids.extend([42, 1337])

    client_mock = action_mocks.ListProcessesMock([proc_foo, proc_bar, proc_baz])
    flow_id = flow_test_lib.StartAndRunFlow(
        flow_processes.ListProcesses,
        client_mock=client_mock,
        client_id=client_id,
        flow_args=args,
    )

    results = flow_test_lib.GetUnpackedFlowResults(
        client_id=client_id,
        flow_id=flow_id,
        result_type=sysinfo_pb2.Process,
    )
    self.assertLen(results, 2)

    result_exes = {result.exe for result in results}
    self.assertIn("/usr/bin/foo", result_exes)
    self.assertIn("/usr/bin/baz", result_exes)
    self.assertNotIn("/usr/bin/bar", result_exes)

  def testCmdlineFiltering(self):
    client_id = self.SetupClient(0)

    proc_foo = rdf_client.Process()
    proc_foo.pid = 42
    proc_foo.exe = "/usr/bin/foo"
    proc_foo.cmdline = ["/usr/bin/foo", "--bar"]

    proc_bar = rdf_client.Process()
    proc_bar.pid = 108
    proc_bar.exe = "/usr/bin/bar"
    proc_bar.cmdline = ["/usr/bin/bar", "--baz"]

    proc_baz = rdf_client.Process()
    proc_baz.pid = 1337
    proc_baz.exe = "/usr/bin/baz"
    proc_baz.cmdline = ["/usr/bin/baz", "--bar"]

    args = flows_pb2.ListProcessesArgs()
    args.cmdline_regex = r"/usr/bin/.* --bar"

    client_mock = action_mocks.ListProcessesMock([proc_foo, proc_bar, proc_baz])
    flow_id = flow_test_lib.StartAndRunFlow(
        flow_processes.ListProcesses,
        client_mock=client_mock,
        client_id=client_id,
        flow_args=args,
    )

    results = flow_test_lib.GetUnpackedFlowResults(
        client_id=client_id,
        flow_id=flow_id,
        result_type=sysinfo_pb2.Process,
    )
    self.assertLen(results, 2)

    result_exes = {result.exe for result in results}
    self.assertIn("/usr/bin/foo", result_exes)
    self.assertNotIn("/usr/bin/bar", result_exes)
    self.assertIn("/usr/bin/baz", result_exes)

  def testProcNameFiltering(self):
    client_id = self.SetupClient(0)

    proc_foo = rdf_client.Process()
    proc_foo.pid = 42
    proc_foo.exe = "/usr/bin/foo"
    proc_foo.name = "foo"
    proc_foo.cmdline = ["/usr/bin/foo", "--bar"]

    proc_bar = rdf_client.Process()
    proc_bar.pid = 108
    proc_bar.exe = "/usr/bin/bar"
    proc_bar.name = "bar"
    proc_bar.cmdline = ["/usr/bin/bar", "--baz"]

    proc_baz = rdf_client.Process()
    proc_baz.pid = 1337
    proc_baz.exe = "/usr/bin/baz"
    proc_baz.name = "baz"
    proc_baz.cmdline = ["/usr/bin/baz", "--bar"]

    args = flows_pb2.ListProcessesArgs()
    args.process_name_regex = r"ba."

    client_mock = action_mocks.ListProcessesMock([proc_foo, proc_bar, proc_baz])
    flow_id = flow_test_lib.StartAndRunFlow(
        flow_processes.ListProcesses,
        client_mock=client_mock,
        client_id=client_id,
        flow_args=args,
    )

    results = flow_test_lib.GetUnpackedFlowResults(
        client_id=client_id,
        flow_id=flow_id,
        result_type=sysinfo_pb2.Process,
    )
    self.assertLen(results, 2)

    result_exes = {result.exe for result in results}
    self.assertNotIn("/usr/bin/foo", result_exes)
    self.assertIn("/usr/bin/baz", result_exes)
    self.assertIn("/usr/bin/bar", result_exes)

  @db_test_lib.WithDatabase
  def testRRG_Linux_Single(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.ListProcessesArgs()
    # By default `filename_regex` is `'.'` so we clear it.
    args.filename_regex = ""

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=flow_processes.ListProcesses,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({
            # pylint: disable=line-too-long
            # pyformat: disable
            "/proc/512532/exe": "/usr/bin/python3.13",
            "/proc/512532/cwd": "/home/foobar",
            "/proc/512532/cmdline": b"python3\x00",
            "/proc/512532/stat": b"512532 (python3) S 512449 512532 512449 34817 512532 4194304 3041 0 0 0 28 16 0 0 20 0 1 0 18339043 24719360 4473 18446744073709551615 4325376 7709849 140734741595264 0 0 0 0 16781312 134348802 1 0 0 17 0 0 0 0 0 0 11042232 11634816 538783744 140734741603281 140734741603289 140734741603289 140734741606375 0\n",
            "/proc/512532/status": b"""\
Name:	python3
Umask:	0022
State:	S (sleeping)
Tgid:	512532
Ngid:	0
Pid:	512532
PPid:	512449
TracerPid:	0
Uid:	451511	451511	451511	451511
Gid:	89979	89979	89979	89979
FDSize:	256
VmPeak:	   24300 kB
VmSize:	   24140 kB
VmHWM:	   17996 kB
VmRSS:	   17996 kB
RssAnon:	    8168 kB
RssFile:	    9828 kB
RssShmem:	       0 kB
Threads:	1
voluntary_ctxt_switches:	4279
nonvoluntary_ctxt_switches:	1497
x86_Thread_features:
x86_Thread_features_locked:
""",
            # pylint: enable=line-too-long
            # pyformat: enable
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    results = flow_test_lib.GetUnpackedFlowResults(
        client_id=client_id,
        flow_id=flow_id,
        result_type=sysinfo_pb2.Process,
    )
    self.assertLen(results, 1)

    result = results[0]
    self.assertEqual(result.pid, 512532)
    self.assertEqual(result.ppid, 512449)
    self.assertEqual(result.exe, "/usr/bin/python3.13")
    self.assertEqual(result.cmdline, ["python3"])
    self.assertEqual(result.real_uid, 451511)
    self.assertEqual(result.effective_uid, 451511)
    self.assertEqual(result.saved_uid, 451511)
    self.assertEqual(result.real_gid, 89979)
    self.assertEqual(result.effective_gid, 89979)
    self.assertEqual(result.saved_gid, 89979)
    self.assertEqual(result.terminal, "/dev/pts/1")
    self.assertEqual(result.status, "S (sleeping)")
    self.assertEqual(result.nice, 0)
    self.assertEqual(result.cwd, "/home/foobar")
    self.assertEqual(result.num_threads, 1)
    self.assertGreater(result.user_cpu_time, 0)
    self.assertGreater(result.system_cpu_time, 0)
    self.assertGreater(result.RSS_size, 0)
    self.assertGreater(result.VMS_size, 0)

  @db_test_lib.WithDatabase
  def testRRG_Linux_Multiple(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.ListProcessesArgs()
    # By default `filename_regex` is `'.'` so we clear it.
    args.filename_regex = ""

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=flow_processes.ListProcesses,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({
            # pylint: disable=line-too-long
            # pyformat: disable
            "/proc/1769/exe": "/usr/sbin/fleetspeakd",
            "/proc/1769/cwd": "/",
            "/proc/1769/cmdline": b"/usr/sbin/fleetspeakd\x00--flagfile=/etc/fleetspeakd/fleetspeakd.flags\x00",
            "/proc/1769/stat": b"1769 (fleetspeakd) S 1 1769 1769 0 -1 4194560 164002 43460 0 0 8867 7270 7794 5272 30 10 15 0 1926 2523992064 17384 18446744073709551615 1 1 0 0 0 0 0 0 2143420159 0 0 0 17 1 0 0 0 0 0 0 0 0 0 0 0 0 0\n",
            "/proc/1769/status": b"""\
Name:   fleetspeakd
Umask:  0022
State:  S (sleeping)
Tgid:   1769
Ngid:   0
Pid:    1769
PPid:   1
TracerPid:      0
Uid:    0       0       0       0
Gid:    0       0       0       0
Groups:
VmPeak:  2464868 kB
VmSize:  2464836 kB
VmHWM:    179268 kB
VmRSS:     69132 kB
RssAnon:           37656 kB
RssFile:           31476 kB
RssShmem:              0 kB
VmData:   332232 kB
VmStk:       132 kB
untag_mask:     0xffffffffffffffff
Threads:        15
""",
            "/proc/213619/exe": "/usr/sbin/rrg",
            "/proc/213619/cwd": "/",
            "/proc/213619/cmdline": b"/usr/sbin/rrg\x00--verbosity\x00WARN\x00--log-to-file\x00/var/log/rrg.log\x00--ping-rate\x0030m\x00--filestore-dir\x00/var/lib/rrg/filestore\x00--filestore-ttl\x0021d\x00",
            "/proc/213619/stat": b"213619 (rrg) S 1769 1769 1769 0 -1 4194304 688 0 0 0 19 22 0 0 30 10 3 0 9394980 3262967808 4457 18446744073709551615 1 1 0 0 0 0 0 4096 1088 0 0 0 17 2 0 0 0 0 0 0 0 0 0 0 0 0 0\n",
            "/proc/213619/status": b"""\
Name:   rrg
Umask:  0022
State:  S (sleeping)
Tgid:   213619
Ngid:   0
Pid:    213619
PPid:   1769
TracerPid:      0
Uid:    0       0       0       0
Gid:    0       0       0       0
Groups:
VmPeak:  3186492 kB
VmSize:  3186492 kB
VmHWM:     18980 kB
VmRSS:     17780 kB
RssAnon:           10524 kB
RssFile:            7256 kB
RssShmem:              0 kB
VmData:    24352 kB
VmStk:       132 kB
untag_mask:     0xffffffffffffffff
Threads:        3
""",
            # pylint: enable=line-too-long
            # pyformat: enable
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    results = flow_test_lib.GetUnpackedFlowResults(
        client_id=client_id,
        flow_id=flow_id,
        result_type=sysinfo_pb2.Process,
    )
    results_by_name = {result.name: result for result in results}

    result_fleetspeak = results_by_name["fleetspeakd"]
    result_rrg = results_by_name["rrg"]

    self.assertEqual(result_fleetspeak.pid, 1769)
    self.assertEqual(result_fleetspeak.ppid, 1)
    self.assertEqual(result_fleetspeak.exe, "/usr/sbin/fleetspeakd")
    self.assertEqual(result_fleetspeak.cmdline[0], "/usr/sbin/fleetspeakd")
    self.assertEqual(result_fleetspeak.real_uid, 0)
    self.assertEqual(result_fleetspeak.effective_uid, 0)
    self.assertEqual(result_fleetspeak.saved_uid, 0)
    self.assertEqual(result_fleetspeak.real_gid, 0)
    self.assertEqual(result_fleetspeak.effective_gid, 0)
    self.assertEqual(result_fleetspeak.saved_gid, 0)
    self.assertEqual(result_fleetspeak.terminal, "")
    self.assertEqual(result_fleetspeak.status, "S (sleeping)")
    self.assertEqual(result_fleetspeak.nice, 10)
    self.assertEqual(result_fleetspeak.cwd, "/")
    self.assertEqual(result_fleetspeak.num_threads, 15)
    self.assertGreater(result_fleetspeak.user_cpu_time, 0)
    self.assertGreater(result_fleetspeak.system_cpu_time, 0)
    self.assertGreater(result_fleetspeak.RSS_size, 0)
    self.assertGreater(result_fleetspeak.VMS_size, 0)

    self.assertEqual(result_rrg.pid, 213619)
    self.assertEqual(result_rrg.ppid, result_fleetspeak.pid)
    self.assertEqual(result_rrg.exe, "/usr/sbin/rrg")
    self.assertEqual(result_rrg.cmdline[0], "/usr/sbin/rrg")
    self.assertEqual(result_rrg.cmdline[1], "--verbosity")
    self.assertEqual(result_rrg.real_uid, 0)
    self.assertEqual(result_rrg.effective_uid, 0)
    self.assertEqual(result_rrg.saved_uid, 0)
    self.assertEqual(result_rrg.real_gid, 0)
    self.assertEqual(result_rrg.effective_gid, 0)
    self.assertEqual(result_rrg.saved_gid, 0)
    self.assertEqual(result_rrg.terminal, "")
    self.assertEqual(result_rrg.status, "S (sleeping)")
    self.assertEqual(result_rrg.nice, 10)
    self.assertEqual(result_rrg.cwd, "/")
    self.assertEqual(result_rrg.num_threads, 3)
    self.assertGreater(result_rrg.user_cpu_time, 0)
    self.assertGreater(result_rrg.system_cpu_time, 0)
    self.assertGreater(result_rrg.RSS_size, 0)
    self.assertGreater(result_rrg.VMS_size, 0)

  @db_test_lib.WithDatabase
  def testRRG_Linux_Filter_PID(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.ListProcessesArgs()
    # By default `filename_regex` is `'.'` so we clear it.
    args.filename_regex = ""
    args.pids.append(1769)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=flow_processes.ListProcesses,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({
            # pylint: disable=line-too-long
            # pyformat: disable
            "/proc/1769/exe": "/usr/sbin/fleetspeakd",
            "/proc/1769/cwd": "/",
            "/proc/1769/cmdline": b"/usr/sbin/fleetspeakd\x00--flagfile=/etc/fleetspeakd/fleetspeakd.flags\x00",
            "/proc/1769/stat": b"1769 (fleetspeakd) S 1 1769 1769 0 -1 4194560 164002 43460 0 0 8867 7270 7794 5272 30 10 15 0 1926 2523992064 17384 18446744073709551615 1 1 0 0 0 0 0 0 2143420159 0 0 0 17 1 0 0 0 0 0 0 0 0 0 0 0 0 0\n",
            "/proc/1769/status": b"""\
Name:   fleetspeakd
Umask:  0022
State:  S (sleeping)
Pid:    1769
PPid:   1
Uid:    0       0       0       0
Gid:    0       0       0       0
Threads:        15
""",
            "/proc/213619/exe": "/usr/sbin/rrg",
            "/proc/213619/cwd": "/",
            "/proc/213619/cmdline": b"/usr/sbin/rrg\x00--verbosity\x00WARN\x00--log-to-file\x00/var/log/rrg.log\x00--ping-rate\x0030m\x00--filestore-dir\x00/var/lib/rrg/filestore\x00--filestore-ttl\x0021d\x00",
            "/proc/213619/stat": b"213619 (rrg) S 1769 1769 1769 0 -1 4194304 688 0 0 0 19 22 0 0 30 10 3 0 9394980 3262967808 4457 18446744073709551615 1 1 0 0 0 0 0 4096 1088 0 0 0 17 2 0 0 0 0 0 0 0 0 0 0 0 0 0\n",
            "/proc/213619/status": b"""\
Name:   rrg
Umask:  0022
State:  S (sleeping)
Pid:    213619
PPid:   1769
Uid:    0       0       0       0
Gid:    0       0       0       0
Threads:        3
""",
            # pylint: enable=line-too-long
            # pyformat: enable
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    results = flow_test_lib.GetUnpackedFlowResults(
        client_id=client_id,
        flow_id=flow_id,
        result_type=sysinfo_pb2.Process,
    )
    results_by_pid = {result.pid: result for result in results}
    self.assertIn(1769, results_by_pid)
    self.assertNotIn(213619, results_by_pid)

  @db_test_lib.WithDatabase
  def testRRG_Linux_Filter_Filename(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.ListProcessesArgs()
    args.filename_regex = "/usr/sbin/.*speak"

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=flow_processes.ListProcesses,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({
            # pylint: disable=line-too-long
            # pyformat: disable
            "/proc/1769/exe": "/usr/sbin/fleetspeakd",
            "/proc/1769/cwd": "/",
            "/proc/1769/cmdline": b"/usr/sbin/fleetspeakd\x00--flagfile=/etc/fleetspeakd/fleetspeakd.flags\x00",
            "/proc/1769/stat": b"1769 (fleetspeakd) S 1 1769 1769 0 -1 4194560 164002 43460 0 0 8867 7270 7794 5272 30 10 15 0 1926 2523992064 17384 18446744073709551615 1 1 0 0 0 0 0 0 2143420159 0 0 0 17 1 0 0 0 0 0 0 0 0 0 0 0 0 0\n",
            "/proc/1769/status": b"""\
Name:   fleetspeakd
Umask:  0022
State:  S (sleeping)
Pid:    1769
PPid:   1
Uid:    0       0       0       0
Gid:    0       0       0       0
Threads:        15
""",
            "/proc/213619/exe": "/usr/sbin/rrg",
            "/proc/213619/cwd": "/",
            "/proc/213619/cmdline": b"/usr/sbin/rrg\x00--verbosity\x00WARN\x00--log-to-file\x00/var/log/rrg.log\x00--ping-rate\x0030m\x00--filestore-dir\x00/var/lib/rrg/filestore\x00--filestore-ttl\x0021d\x00",
            "/proc/213619/stat": b"213619 (rrg) S 1769 1769 1769 0 -1 4194304 688 0 0 0 19 22 0 0 30 10 3 0 9394980 3262967808 4457 18446744073709551615 1 1 0 0 0 0 0 4096 1088 0 0 0 17 2 0 0 0 0 0 0 0 0 0 0 0 0 0\n",
            "/proc/213619/status": b"""\
Name:   rrg
Umask:  0022
State:  S (sleeping)
Pid:    213619
PPid:   1769
Uid:    0       0       0       0
Gid:    0       0       0       0
Threads:        3
""",
            # pylint: enable=line-too-long
            # pyformat: enable
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    results = flow_test_lib.GetUnpackedFlowResults(
        client_id=client_id,
        flow_id=flow_id,
        result_type=sysinfo_pb2.Process,
    )
    results_by_name = {result.name: result for result in results}
    self.assertIn("fleetspeakd", results_by_name)
    self.assertNotIn("rrg", results_by_name)

  @db_test_lib.WithDatabase
  def testRRG_Linux_Filter_ProcessName(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.ListProcessesArgs()
    args.process_name_regex = "fleetspeakd"

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=flow_processes.ListProcesses,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({
            # pylint: disable=line-too-long
            # pyformat: disable
            "/proc/1769/exe": "/usr/sbin/fleetspeakd",
            "/proc/1769/cwd": "/",
            "/proc/1769/cmdline": b"/usr/sbin/fleetspeakd\x00--flagfile=/etc/fleetspeakd/fleetspeakd.flags\x00",
            "/proc/1769/stat": b"1769 (fleetspeakd) S 1 1769 1769 0 -1 4194560 164002 43460 0 0 8867 7270 7794 5272 30 10 15 0 1926 2523992064 17384 18446744073709551615 1 1 0 0 0 0 0 0 2143420159 0 0 0 17 1 0 0 0 0 0 0 0 0 0 0 0 0 0\n",
            "/proc/1769/status": b"""\
Name:   fleetspeakd
Umask:  0022
State:  S (sleeping)
Pid:    1769
PPid:   1
Uid:    0       0       0       0
Gid:    0       0       0       0
Threads:        15
""",
            "/proc/213619/exe": "/usr/sbin/rrg",
            "/proc/213619/cwd": "/",
            "/proc/213619/cmdline": b"/usr/sbin/rrg\x00--verbosity\x00WARN\x00--log-to-file\x00/var/log/rrg.log\x00--ping-rate\x0030m\x00--filestore-dir\x00/var/lib/rrg/filestore\x00--filestore-ttl\x0021d\x00",
            "/proc/213619/stat": b"213619 (rrg) S 1769 1769 1769 0 -1 4194304 688 0 0 0 19 22 0 0 30 10 3 0 9394980 3262967808 4457 18446744073709551615 1 1 0 0 0 0 0 4096 1088 0 0 0 17 2 0 0 0 0 0 0 0 0 0 0 0 0 0\n",
            "/proc/213619/status": b"""\
Name:   rrg
Umask:  0022
State:  S (sleeping)
Pid:    213619
PPid:   1769
Uid:    0       0       0       0
Gid:    0       0       0       0
Threads:        3
""",
            # pylint: enable=line-too-long
            # pyformat: enable
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    results = flow_test_lib.GetUnpackedFlowResults(
        client_id=client_id,
        flow_id=flow_id,
        result_type=sysinfo_pb2.Process,
    )
    results_by_name = {result.name: result for result in results}
    self.assertIn("fleetspeakd", results_by_name)
    self.assertNotIn("rrg", results_by_name)

  @db_test_lib.WithDatabase
  def testRRG_Linux_Filter_Cmdline(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.ListProcessesArgs()
    args.cmdline_regex = "/etc/fleetspeakd/fleetspeakd\\.flags"

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=flow_processes.ListProcesses,
        flow_args=args,
        handlers=rrg_test_lib.FakePosixFileHandlers({
            # pylint: disable=line-too-long
            # pyformat: disable
            "/proc/1769/exe": "/usr/sbin/fleetspeakd",
            "/proc/1769/cwd": "/",
            "/proc/1769/cmdline": b"/usr/sbin/fleetspeakd\x00--flagfile=/etc/fleetspeakd/fleetspeakd.flags\x00",
            "/proc/1769/stat": b"1769 (fleetspeakd) S 1 1769 1769 0 -1 4194560 164002 43460 0 0 8867 7270 7794 5272 30 10 15 0 1926 2523992064 17384 18446744073709551615 1 1 0 0 0 0 0 0 2143420159 0 0 0 17 1 0 0 0 0 0 0 0 0 0 0 0 0 0\n",
            "/proc/1769/status": b"""\
Name:   fleetspeakd
Umask:  0022
State:  S (sleeping)
Pid:    1769
PPid:   1
Uid:    0       0       0       0
Gid:    0       0       0       0
Threads:        15
""",
            "/proc/213619/exe": "/usr/sbin/rrg",
            "/proc/213619/cwd": "/",
            "/proc/213619/cmdline": b"/usr/sbin/rrg\x00--verbosity\x00WARN\x00--log-to-file\x00/var/log/rrg.log\x00--ping-rate\x0030m\x00--filestore-dir\x00/var/lib/rrg/filestore\x00--filestore-ttl\x0021d\x00",
            "/proc/213619/stat": b"213619 (rrg) S 1769 1769 1769 0 -1 4194304 688 0 0 0 19 22 0 0 30 10 3 0 9394980 3262967808 4457 18446744073709551615 1 1 0 0 0 0 0 4096 1088 0 0 0 17 2 0 0 0 0 0 0 0 0 0 0 0 0 0\n",
            "/proc/213619/status": b"""\
Name:   rrg
Umask:  0022
State:  S (sleeping)
Pid:    213619
PPid:   1769
Uid:    0       0       0       0
Gid:    0       0       0       0
Threads:        3
""",
            # pylint: enable=line-too-long
            # pyformat: enable
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    results = flow_test_lib.GetUnpackedFlowResults(
        client_id=client_id,
        flow_id=flow_id,
        result_type=sysinfo_pb2.Process,
    )
    results_by_name = {result.name: result for result in results}
    self.assertIn("fleetspeakd", results_by_name)
    self.assertNotIn("rrg", results_by_name)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
