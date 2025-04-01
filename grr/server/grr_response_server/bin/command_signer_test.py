#!/usr/bin/env python
from absl import app
from grr_response_proto.api import signed_commands_pb2 as api_signed_commands_pb2
from grr_response_server.bin import command_signer
from grr.test_lib import test_lib
from grr_response_proto.rrg.action import execute_signed_command_pb2


class CommandSignerTest(test_lib.GRRBaseTest):

  def testConvertToRrgCommand(self):
    command = api_signed_commands_pb2.ApiCommand()
    command.path = "foo"
    command.args.extend(["bar", "baz"])
    command.env_vars.add(name="FOO", value="bar")
    command.env_vars.add(name="BAZ", value="qux")
    command.signed_stdin = b"quux"

    rrg_command = command_signer._ConvertToRrgCommand(command)

    expected = execute_signed_command_pb2.Command()
    expected.path.raw_bytes = b"foo"
    expected.args.extend(["bar", "baz"])
    expected.env["FOO"] = "bar"
    expected.env["BAZ"] = "qux"
    expected.signed_stdin = b"quux"

    self.assertEqual(expected, rrg_command)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
