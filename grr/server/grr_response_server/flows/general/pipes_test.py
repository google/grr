#!/usr/bin/env python
from collections.abc import Iterable, Iterator, Sequence

from absl.testing import absltest

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_proto import pipes_pb2
from grr_response_server.flows.general import pipes
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import testing_startup


class ListNamedPipesFlowTest(flow_test_lib.FlowTestsBaseclass):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    testing_startup.TestInit()

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0, system="Windows")

  def testPlatformNotSupported(self):
    self.client_id = self.SetupClient(0, system="Linux")

    args = pipes.ListNamedPipesFlowArgs()

    with self.assertRaisesRegex(RuntimeError, "Unsupported platform"):
      self._RunListNamedPipesFlow(args)

  def testNoPipes(self):
    args = pipes.ListNamedPipesFlowArgs()

    results = self._RunListNamedPipesFlow(args, pipe_results=[])
    self.assertEmpty(results)

  def testSinglePipe(self):
    args = pipes.ListNamedPipesFlowArgs()

    pipe = rdf_client.NamedPipe()
    pipe.name = "foo"
    pipe.server_pid = 1337

    results = self._RunListNamedPipesFlow(args, pipe_results=[pipe])
    self.assertLen(results, 1)
    self.assertEqual(results[0].pipe.name, "foo")
    self.assertEqual(results[0].pipe.server_pid, 1337)

  def testMultiplePipes(self):
    args = pipes.ListNamedPipesFlowArgs()

    pipe_foo = rdf_client.NamedPipe()
    pipe_foo.name = "foo"
    pipe_foo.server_pid = 0xF00

    pipe_baz = rdf_client.NamedPipe()
    pipe_baz.name = "baz"
    pipe_baz.server_pid = 0xB45

    results = self._RunListNamedPipesFlow(
        args,
        pipe_results=[pipe_foo, pipe_baz],
    )
    self.assertLen(results, 2)

    results_by_name = {result.pipe.name: result for result in results}
    self.assertEqual(results_by_name["foo"].pipe.server_pid, 0xF00)
    self.assertEqual(results_by_name["baz"].pipe.server_pid, 0xB45)

  def testPipeNameRegex(self):
    args = pipes.ListNamedPipesFlowArgs()
    args.pipe_name_regex = "ba."

    pipe_foo = rdf_client.NamedPipe()
    pipe_foo.name = "foo"

    pipe_bar = rdf_client.NamedPipe()
    pipe_bar.name = "bar"

    pipe_baz = rdf_client.NamedPipe()
    pipe_baz.name = "baz"

    results = self._RunListNamedPipesFlow(
        args,
        pipe_results=[pipe_foo, pipe_bar, pipe_baz],
    )
    self.assertLen(results, 2)

    result_names = {result.pipe.name for result in results}
    self.assertIn("bar", result_names)
    self.assertIn("baz", result_names)

  def testProcExeRegex(self):
    args = pipes.ListNamedPipesFlowArgs()
    args.proc_exe_regex = r"C:\\Windows\\ba.\.exe"

    pipe_foo = rdf_client.NamedPipe()
    pipe_foo.name = "foo"
    pipe_foo.server_pid = 123

    proc_foo = rdf_client.Process()
    proc_foo.pid = 123
    proc_foo.exe = r"C:\Windows\foo.exe"

    pipe_bar = rdf_client.NamedPipe()
    pipe_bar.name = "bar"
    pipe_bar.server_pid = 456

    proc_bar = rdf_client.Process()
    proc_bar.pid = 456
    proc_bar.exe = r"C:\Windows\bar.exe"

    pipe_baz = rdf_client.NamedPipe()
    pipe_baz.name = "baz"
    pipe_baz.server_pid = 789

    proc_baz = rdf_client.Process()
    proc_baz.pid = 789
    proc_baz.exe = r"C:\Windows\baz.exe"

    results = self._RunListNamedPipesFlow(
        args,
        pipe_results=[pipe_foo, pipe_bar, pipe_baz],
        proc_results=[proc_foo, proc_bar, proc_baz],
    )
    self.assertLen(results, 2)

    result_names = {result.pipe.name for result in results}
    self.assertIn("bar", result_names)
    self.assertIn("baz", result_names)

  def testPipeTypeFilterByteMatch(self):
    args = pipes.ListNamedPipesFlowArgs()
    args.pipe_type_filter = pipes_pb2.ListNamedPipesFlowArgs.BYTE_TYPE

    pipe = rdf_client.NamedPipe()
    pipe.name = "foo"
    pipe.flags = pipes.PIPE_TYPE_BYTE | pipes.PIPE_CLIENT_END

    results = self._RunListNamedPipesFlow(args, pipe_results=[pipe])
    self.assertLen(results, 1)
    self.assertEqual(results[0].pipe.name, "foo")

  def testPipeTypeFilterByteNoMatch(self):
    args = pipes.ListNamedPipesFlowArgs()
    args.pipe_type_filter = pipes_pb2.ListNamedPipesFlowArgs.BYTE_TYPE

    pipe = rdf_client.NamedPipe()
    pipe.name = "foo"
    pipe.flags = pipes.PIPE_TYPE_MESSAGE | pipes.PIPE_CLIENT_END

    results = self._RunListNamedPipesFlow(args, pipe_results=[pipe])
    self.assertEmpty(results)

  def testPipeTypeFilterMessageMatch(self):
    args = pipes.ListNamedPipesFlowArgs()
    args.pipe_type_filter = pipes_pb2.ListNamedPipesFlowArgs.MESSAGE_TYPE

    pipe = rdf_client.NamedPipe()
    pipe.name = "foo"
    pipe.flags = pipes.PIPE_TYPE_MESSAGE | pipes.PIPE_CLIENT_END

    results = self._RunListNamedPipesFlow(args, pipe_results=[pipe])
    self.assertLen(results, 1)
    self.assertEqual(results[0].pipe.name, "foo")

  def testPipeTypeFilterMessageNoMatch(self):
    args = pipes.ListNamedPipesFlowArgs()
    args.pipe_type_filter = pipes_pb2.ListNamedPipesFlowArgs.MESSAGE_TYPE

    pipe = rdf_client.NamedPipe()
    pipe.name = "foo"
    pipe.flags = pipes.PIPE_TYPE_BYTE | pipes.PIPE_CLIENT_END

    results = self._RunListNamedPipesFlow(args, pipe_results=[pipe])
    self.assertEmpty(results)

  def testPipeEndFilterClientMatch(self):
    args = pipes.ListNamedPipesFlowArgs()
    args.pipe_end_filter = pipes_pb2.ListNamedPipesFlowArgs.CLIENT_END

    pipe = rdf_client.NamedPipe()
    pipe.name = "foo"
    pipe.flags = pipes.PIPE_TYPE_MESSAGE | pipes.PIPE_CLIENT_END

    results = self._RunListNamedPipesFlow(args, pipe_results=[pipe])
    self.assertLen(results, 1)
    self.assertEqual(results[0].pipe.name, "foo")

  def testPipeEndFilterClientNoMatch(self):
    args = pipes.ListNamedPipesFlowArgs()
    args.pipe_end_filter = pipes_pb2.ListNamedPipesFlowArgs.CLIENT_END

    pipe = rdf_client.NamedPipe()
    pipe.name = "foo"
    pipe.flags = pipes.PIPE_TYPE_MESSAGE | pipes.PIPE_SERVER_END

    results = self._RunListNamedPipesFlow(args, pipe_results=[pipe])
    self.assertEmpty(results)

  def testPipeEndFilterServerMatch(self):
    args = pipes.ListNamedPipesFlowArgs()
    args.pipe_end_filter = pipes_pb2.ListNamedPipesFlowArgs.SERVER_END

    pipe = rdf_client.NamedPipe()
    pipe.name = "foo"
    pipe.flags = pipes.PIPE_TYPE_MESSAGE | pipes.PIPE_SERVER_END

    results = self._RunListNamedPipesFlow(args, pipe_results=[pipe])
    self.assertLen(results, 1)
    self.assertEqual(results[0].pipe.name, "foo")

  def testPipeEndFilterServerNoMatch(self):
    args = pipes.ListNamedPipesFlowArgs()
    args.pipe_end_filter = pipes_pb2.ListNamedPipesFlowArgs.SERVER_END

    pipe = rdf_client.NamedPipe()
    pipe.name = "foo"
    pipe.flags = pipes.PIPE_TYPE_MESSAGE | pipes.PIPE_CLIENT_END

    results = self._RunListNamedPipesFlow(args, pipe_results=[pipe])
    self.assertEmpty(results)

  def testSinglePipeWithServerPid(self):
    args = pipes.ListNamedPipesFlowArgs()

    pipe = rdf_client.NamedPipe()
    pipe.name = "foo"
    pipe.server_pid = 42

    proc = rdf_client.Process()
    proc.pid = 42
    proc.exe = r"C:\Windows\foo.exe"

    results = self._RunListNamedPipesFlow(
        args,
        pipe_results=[pipe],
        proc_results=[proc],
    )

    self.assertLen(results, 1)
    self.assertEqual(results[0].pipe.name, "foo")
    self.assertEqual(results[0].proc.exe, r"C:\Windows\foo.exe")

  def testSinglePipeWithClientPid(self):
    args = pipes.ListNamedPipesFlowArgs()

    pipe = rdf_client.NamedPipe()
    pipe.name = "foo"
    pipe.client_pid = 1337

    proc = rdf_client.Process()
    proc.pid = 1337
    proc.exe = r"C:\Windows\foo.exe"

    results = self._RunListNamedPipesFlow(
        args,
        pipe_results=[pipe],
        proc_results=[proc],
    )

    self.assertLen(results, 1)
    self.assertEqual(results[0].pipe.name, "foo")
    self.assertEqual(results[0].proc.exe, r"C:\Windows\foo.exe")

  def testSinglePipeWithNoMatchingPid(self):
    args = pipes.ListNamedPipesFlowArgs()

    pipe = rdf_client.NamedPipe()
    pipe.name = "foo"
    pipe.server_pid = 1

    proc_bar = rdf_client.Process()
    proc_bar.pid = 2
    proc_bar.exe = r"C:\Windows\bar.exe"

    proc_baz = rdf_client.Process()
    proc_baz.pid = 3
    proc_baz.exe = r"C:\Windows\baz.exe"

    results = self._RunListNamedPipesFlow(
        args,
        pipe_results=[pipe],
        proc_results=[proc_bar, proc_baz],
    )

    self.assertLen(results, 1)
    self.assertEqual(results[0].pipe.name, "foo")
    self.assertEmpty(results[0].proc.exe)

  def testMultiplePipesWithPids(self):
    args = pipes.ListNamedPipesFlowArgs()

    pipe_foo = rdf_client.NamedPipe()
    pipe_foo.name = "foo-pipe"
    pipe_foo.client_pid = 42

    pipe_bar = rdf_client.NamedPipe()
    pipe_bar.name = "bar-pipe"
    pipe_bar.server_pid = 1337

    pipe_baz = rdf_client.NamedPipe()
    pipe_baz.name = "baz-pipe"
    pipe_baz.server_pid = 108

    proc_foo = rdf_client.Process()
    proc_foo.exe = r"C:\Temp\foo.exe"
    proc_foo.pid = 42

    proc_baz = rdf_client.Process()
    proc_baz.exe = r"C:\Temp\baz.exe"
    proc_baz.pid = 108

    results = self._RunListNamedPipesFlow(
        args,
        pipe_results=[pipe_foo, pipe_bar, pipe_baz],
        proc_results=[proc_foo, proc_baz],
    )
    self.assertLen(results, 3)

    results_by_name = {result.pipe.name: result for result in results}
    self.assertEqual(results_by_name["foo-pipe"].proc.exe, r"C:\Temp\foo.exe")
    self.assertEqual(results_by_name["baz-pipe"].proc.exe, r"C:\Temp\baz.exe")
    self.assertEmpty(results_by_name["bar-pipe"].proc.exe)

  def testMultiplePipesWithPid0(self):
    args = pipes.ListNamedPipesFlowArgs()

    pipe_foo = rdf_client.NamedPipe()
    pipe_foo.name = "foo-pipe"
    pipe_foo.client_pid = 0

    pipe_bar = rdf_client.NamedPipe()
    pipe_bar.name = "bar-pipe"
    pipe_bar.server_pid = 0

    proc = rdf_client.Process()
    proc.pid = 0
    proc.exe = r"C:\Windows\system32\notepad.exe"

    results = self._RunListNamedPipesFlow(
        args,
        pipe_results=[pipe_foo, pipe_bar],
        proc_results=[proc],
    )

    self.assertLen(results, 2)
    self.assertEqual(results[0].proc.exe, r"C:\Windows\system32\notepad.exe")
    self.assertEqual(results[1].proc.exe, r"C:\Windows\system32\notepad.exe")

  def _RunListNamedPipesFlow(
      self,
      args: pipes.ListNamedPipesFlowArgs,
      pipe_results: Iterable[rdf_client.NamedPipe] = (),
      proc_results: Iterable[rdf_client.Process] = (),
  ) -> Sequence[pipes.ListNamedPipesFlowResult]:
    """Runs the flow listing named pipes with the given fake action results."""

    class ActionMock(action_mocks.ActionMock):

      def ListNamedPipes(
          self,
          args: None,
      ) -> Iterator[rdf_client.NamedPipe]:
        del args  # Unused.

        for pipe in pipe_results:
          yield pipe

      def ListProcesses(
          self,
          args: None,
      ) -> Iterator[rdf_client.Process]:
        del args  # Unused.

        for proc in proc_results:
          yield proc

    flow_id = flow_test_lib.StartAndRunFlow(
        pipes.ListNamedPipesFlow,
        client_mock=ActionMock(),
        client_id=self.client_id,
        flow_args=args,
    )

    flow_test_lib.FinishAllFlowsOnClient(self.client_id)
    return flow_test_lib.GetFlowResults(self.client_id, flow_id)


if __name__ == "__main__":
  absltest.main()
