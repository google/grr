#!/usr/bin/env python
import sys
import unittest

from absl.testing import absltest
try:
  # pylint: disable=g-import-not-at-top
  import win32file
  from grr_response_client.unprivileged.windows import process
  # pylint: enable=g-import-not-at-top
except ImportError:
  raise unittest.SkipTest("This is a Windows only test.")


class ProcessTest(absltest.TestCase):

  def testProcess(self):
    extra_pipe_r, extra_pipe_w = process.CreatePipeWrapper()

    def MakeCommandLine(pipe_input: int, pipe_output: int) -> str:
      return " ".join([
          sys.executable,
          "-m",
          "grr_response_client.unprivileged.windows.echo",
          "--pipe_input",
          str(pipe_input),
          "--pipe_output",
          str(pipe_output),
          "--extra_pipe_input",
          str(extra_pipe_r.value),
      ])

    p = process.Process(MakeCommandLine, [extra_pipe_r.value])
    win32file.WriteFile(p.input, b"foo")
    win32file.WriteFile(extra_pipe_w.value, b"bar")
    result = win32file.ReadFile(p.output, 9)[1]
    self.assertEqual(result, b"foobar123")
    p.Stop()


if __name__ == "__main__":
  absltest.main()
