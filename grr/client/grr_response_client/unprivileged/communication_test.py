#!/usr/bin/env python
import os
import platform
from typing import List
import unittest
from unittest import mock
import sys
from absl.testing import absltest

from grr_response_client.unprivileged import communication


class CommunicationTest(absltest.TestCase):

  def testCommunication(self):

    def MakeArgs(channel: communication.Channel) -> List[str]:
      return [
          sys.executable, "-m",
          "grr_response_client.unprivileged.echo_server",
          str(channel.pipe_input.Serialize()),
          str(channel.pipe_output.Serialize()),
      ]

    server = communication.SubprocessServer(MakeArgs)
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

  @unittest.skipIf(platform.system() != "Linux" and
                   platform.system() != "Darwin", "Unix only test.")
  def testMain_entersSandbox(self):
    # pylint: disable=g-import-not-at-top
    from grr_response_client.unprivileged.unix import sandbox
    # pylint: enable=g-import-not-at-top
    with mock.patch.object(sandbox, "EnterSandbox") as mock_enter_sandbox:
      input_fd = os.open("/dev/null", os.O_RDONLY)
      output_file = os.open("/dev/null", os.O_WRONLY)
      channel = communication.Channel(
          communication.FileDescriptor.FromFileDescriptor(input_fd),
          communication.FileDescriptor.FromFileDescriptor(output_file))
      communication.Main(channel, lambda connection: None, "fooUser",
                         "barGroup")
      mock_enter_sandbox.assert_called_with("fooUser", "barGroup")


if __name__ == "__main__":
  absltest.main()
