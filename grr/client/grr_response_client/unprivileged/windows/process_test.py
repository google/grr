#!/usr/bin/env python
import os
import sys
import unittest

from absl.testing import absltest
try:
  # pylint: disable=g-import-not-at-top
  import msvcrt
  from grr_response_client.unprivileged.windows import process
  # pylint: enable=g-import-not-at-top
except ImportError:
  raise unittest.SkipTest("This is a Windows only test.")


class ProcessTest(absltest.TestCase):

  def testProcess(self):
    input_r_fd, input_w_fd = os.pipe()
    output_r_fd, output_w_fd = os.pipe()

    input_r_handle = msvcrt.get_osfhandle(input_r_fd)
    output_w_handle = msvcrt.get_osfhandle(output_w_fd)

    with os.fdopen(input_w_fd, "wb", buffering=0) as input_w:
      with os.fdopen(output_r_fd, "rb", buffering=0) as output_r:
        args = [
            sys.executable,
            "-m",
            "grr_response_client.unprivileged.windows.echo",
            "--pipe_input",
            str(input_r_handle),
            "--pipe_output",
            str(output_w_handle),
        ]

        p = process.Process(args, [input_r_handle, output_w_handle])
        input_w.write(b"foo")
        result = output_r.read(6)
        self.assertEqual(result, b"foo123")
        p.Stop()


if __name__ == "__main__":
  absltest.main()
