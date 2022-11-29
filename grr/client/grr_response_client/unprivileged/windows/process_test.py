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
        # Commenting out the following checks that were previously here,
        # as they're not reliable and depend on the performance of
        # the machine that the tests run on:
        # self.assertGreater(p.GetCpuTimes().cpu_time, 0.0)
        # self.assertGreater(p.GetCpuTimes().sys_time, 0.0)
        #
        # Reason:
        # 'Windows time interval is 16ms by default. It uses this value for
        # its internal timers and thread time quantum, which
        # effectively means you won't see any changes until they have
        # added up to a min of 16ms.'
        # Link: https://groups.google.com/g/golang-nuts/c/idD2Z8wYeiE

        p.Stop()


if __name__ == "__main__":
  absltest.main()
