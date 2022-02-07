#!/usr/bin/env python
import collections
import io
import os
import platform
from typing import List
import unittest
from unittest import mock
import sys
from absl.testing import absltest
import psutil

from grr_response_client.unprivileged import communication
from grr_response_client.unprivileged import sandbox


def _MakeArgs(channel: communication.Channel) -> List[str]:
  return [
      sys.executable, "-m",
      "grr_response_client.unprivileged.echo_server",
      str(channel.pipe_input.Serialize()),
      str(channel.pipe_output.Serialize()),
  ]


class CommunicationTest(absltest.TestCase):

  def testCommunication(self):

    server = communication.SubprocessServer(_MakeArgs)
    server.Start()
    connection = server.Connect()

    connection.Send(communication.Message(b"foo", b"bar"))
    result = connection.Recv()
    self.assertEqual(result.data, b"foox")
    self.assertEqual(result.attachment, b"barx")

    connection.Send(communication.Message(b"FOO", b"BAR"))
    result = connection.Recv()
    self.assertEqual(result.data, b"FOOx")
    self.assertEqual(result.attachment, b"BARx")

    connection.Send(communication.Message(b"", b""))
    result = connection.Recv()
    self.assertEqual(result.data, b"x")
    self.assertEqual(result.attachment, b"x")

    server.Stop()

  @unittest.skipIf(platform.system() == "Windows",
                   "psutil is not used on Windows.")
  def testTotalServerCpuSysTime_usesPsutilProcess(self):
    _FakeCpuTimes = collections.namedtuple("FakeCpuTimes", ["user", "system"])

    class _FakeProcess:

      def __init__(self, pid):
        pass

      def cpu_times(self):  # pylint: disable=invalid-name
        return _FakeCpuTimes(42.0, 43.0)

    with mock.patch.object(psutil, "Process", _FakeProcess):
      init_cpu_time = communication.TotalServerCpuTime()
      init_sys_time = communication.TotalServerSysTime()

      with communication.SubprocessServer(_MakeArgs):
        pass

      self.assertAlmostEqual(communication.TotalServerCpuTime() - init_cpu_time,
                             42.0)
      self.assertAlmostEqual(communication.TotalServerSysTime() - init_sys_time,
                             43.0)

  @unittest.skipIf(platform.system() != "Windows", "Windows only test.")
  def testTotalServerCpuSysTime_usesWin32Process(self):

    def _MockGetProcessTimes(handle):
      del handle  # Unused.
      return {
          "UserTime": 42 * 10 * 1000 * 1000,
          "KernelTime": 43 * 10 * 1000 * 1000
      }

    # pytype: disable=import-error
    import win32process  # pylint: disable=g-import-not-at-top
    # pytype: enable=import-error
    with mock.patch.object(win32process, "GetProcessTimes",
                           _MockGetProcessTimes):
      init_cpu_time = communication.TotalServerCpuTime()
      init_sys_time = communication.TotalServerSysTime()

      with communication.SubprocessServer(_MakeArgs):
        pass

      self.assertAlmostEqual(communication.TotalServerCpuTime() - init_cpu_time,
                             42.0)
      self.assertAlmostEqual(communication.TotalServerSysTime() - init_sys_time,
                             43.0)

  def testCpuSysTime_addsUpMultipleProcesses(self):

    class _SubprocessSeverWithFakeCpuTime(communication.SubprocessServer):

      def __init__(self, *args):
        super().__init__(*args)
        self.fake_cpu_time = 0.0
        self.fake_sys_time = 0.0

      @property
      def cpu_time(self):
        return self.fake_cpu_time

      @property
      def sys_time(self):
        return self.fake_sys_time

    init_cpu_time = communication.TotalServerCpuTime()
    init_sys_time = communication.TotalServerSysTime()

    server1 = _SubprocessSeverWithFakeCpuTime(_MakeArgs)
    server1.Start()

    server2 = _SubprocessSeverWithFakeCpuTime(_MakeArgs)
    server2.Start()

    server1.fake_cpu_time = 1.0
    server2.fake_cpu_time = 2.0

    server1.fake_sys_time = 3.0
    server2.fake_sys_time = 4.0

    self.assertAlmostEqual(communication.TotalServerCpuTime() - init_cpu_time,
                           1.0 + 2.0)
    self.assertAlmostEqual(communication.TotalServerSysTime() - init_sys_time,
                           3.0 + 4.0)

    server1.fake_cpu_time = 5.0
    server2.fake_cpu_time = 6.0

    server1.fake_sys_time = 7.0
    server2.fake_sys_time = 8.0

    self.assertAlmostEqual(communication.TotalServerCpuTime() - init_cpu_time,
                           5.0 + 6.0)
    self.assertAlmostEqual(communication.TotalServerSysTime() - init_sys_time,
                           7.0 + 8.0)

    server1.Stop()
    server2.Stop()

    # These updates shouldn't be taken into account.

    server1.fake_cpu_time = 9.0
    server2.fake_cpu_time = 9.0

    server1.fake_sys_time = 9.0
    server2.fake_sys_time = 9.0

    self.assertAlmostEqual(communication.TotalServerCpuTime() - init_cpu_time,
                           5.0 + 6.0)
    self.assertAlmostEqual(communication.TotalServerSysTime() - init_sys_time,
                           7.0 + 8.0)

  @unittest.skipIf(platform.system() != "Linux" and
                   platform.system() != "Darwin", "Unix only test.")
  def testMain_entersSandbox(self):
    with mock.patch.object(sandbox, "EnterSandbox") as mock_enter_sandbox:
      input_fd = os.open("/dev/null", os.O_RDONLY)
      output_file = os.open("/dev/null", os.O_WRONLY)
      channel = communication.Channel(
          communication.FileDescriptor.FromFileDescriptor(input_fd),
          communication.FileDescriptor.FromFileDescriptor(output_file))
      communication.Main(channel, lambda connection: None, "fooUser",
                         "barGroup")
      mock_enter_sandbox.assert_called_with("fooUser", "barGroup")


class PipeTransportTest(absltest.TestCase):

  def testRead_AllReadsAreShort(self):

    class ShortReadIO(io.BytesIO):

      def read(self, size: int) -> bytes:
        del size  # unused
        return super().read(2)

    short_read_io = ShortReadIO(b"foo bar baz")
    transport = communication.PipeTransport(short_read_io, short_read_io)
    self.assertEqual(transport.RecvBytes(len(b"foo bar baz")), b"foo bar baz")

  def testRead_FirstReadIsShort(self):

    class ShortReadIO(io.BytesIO):
      _first_read = True

      def read(self, size: int) -> bytes:
        if self._first_read:
          self._first_read = False
          return super().read(2)
        else:
          return super().read(size)

    short_read_io = ShortReadIO(b"foo bar baz EXTRA TRAILING DATA")
    transport = communication.PipeTransport(short_read_io, short_read_io)
    self.assertEqual(transport.RecvBytes(len(b"foo bar baz")), b"foo bar baz")

  def testWrite(self):

    class ShortWriteIO(io.BytesIO):

      def write(self, data: bytes) -> int:
        return super().write(data[:2])

    short_write_io = ShortWriteIO()
    transport = communication.PipeTransport(short_write_io, short_write_io)
    transport.SendBytes(b"foo bar baz")
    self.assertEqual(short_write_io.getvalue(), b"foo bar baz")


if __name__ == "__main__":
  absltest.main()
