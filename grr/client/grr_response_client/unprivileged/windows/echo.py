#!/usr/bin/env python
"""Simple echo program for testing the `process` module."""

import os
from absl import app
from absl import flags
import msvcrt

_PIPE_INPUT = flags.DEFINE_integer("pipe_input", -1, "Input pipe handle.")

_PIPE_OUTPUT = flags.DEFINE_integer("pipe_output", -1, "Output pipe handle.")


def main(args):
  del args
  pipe_input_fd = msvcrt.open_osfhandle(_PIPE_INPUT.value, os.O_RDONLY)
  pipe_output_fd = msvcrt.open_osfhandle(_PIPE_OUTPUT.value, os.O_APPEND)
  with os.fdopen(pipe_input_fd, "rb", buffering=0) as pipe_input:
    with os.fdopen(pipe_output_fd, "wb", buffering=0) as pipe_output:
      data = pipe_input.read(3)
      pipe_output.write(data + b"123")


if __name__ == "__main__":
  app.run(main)
