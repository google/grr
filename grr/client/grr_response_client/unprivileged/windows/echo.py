#!/usr/bin/env python
"""Simple echo program for testing the `process` module."""

from absl import app
from absl import flags
import win32file

flags.DEFINE_integer("pipe_input", -1, "Input pipe handle.")

flags.DEFINE_integer("pipe_output", -1, "Output pipe handle.")

flags.DEFINE_integer("extra_pipe_input", -1, "Additional input pipe handle.")


def main(args):
  del args
  pipe_input = flags.FLAGS.pipe_input
  pipe_output = flags.FLAGS.pipe_output
  extra_pipe_input = flags.FLAGS.extra_pipe_input
  data = win32file.ReadFile(pipe_input, 3, None)[1]
  extra_data = win32file.ReadFile(extra_pipe_input, 3, None)[1]
  win32file.WriteFile(pipe_output, data + extra_data + b"123")


if __name__ == "__main__":
  app.run(main)
