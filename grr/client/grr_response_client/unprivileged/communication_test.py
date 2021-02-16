#!/usr/bin/env python
from typing import List
import sys
from absl.testing import absltest

from grr_response_client.unprivileged import communication


class CommunicationTest(absltest.TestCase):

  def testCommunication(self):

    def MakeArgs(channel: communication.Channel) -> List[str]:
      return [
          sys.executable, "-m",
          "grr_response_client.unprivileged.echo_server",
          str(channel.pipe_input),
          str(channel.pipe_output),
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


if __name__ == "__main__":
  absltest.main()
