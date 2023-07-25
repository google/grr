#!/usr/bin/env python
"""GRR development environment."""

import shutil
import subprocess
import sys
import traceback

from . import cli
from . import commands
from . import util


def main() -> None:
  if len(sys.argv) < 2:
    sys.argv.append("-h")

  term_cols, _ = shutil.get_terminal_size(fallback=(80, 1))
  args = cli.parse_args()
  try:
    args.func(args)
  except subprocess.CalledProcessError as exc:
    fail_lines: list[str] = [
        "subprocess error",
        util.str_mid_pad(" COMMAND ", term_cols, "="),
        str(exc.cmd),
    ]
    if exc.stderr:
      fail_lines.extend([
          util.str_mid_pad(" STDERR ", term_cols, "="),
          exc.stderr.decode("utf-8"),
      ])
    util.say_fail("\n".join(fail_lines))
    if exc.stdout:
      sys.stderr.write(util.str_mid_pad(" STDOUT ", term_cols, "=") + "\n")
      sys.stderr.write(exc.stdout.decode("utf-8"))
    sys.stderr.write(util.str_mid_pad(" TRACEBACK ", term_cols, "=") + "\n")
    traceback.print_tb(exc.__traceback__, file=sys.stderr)
  except Exception as exc:  # pylint: disable=broad-exception-caught
    util.say_fail(f"{exc}")
    sys.stderr.write(util.str_mid_pad(" TRACEBACK ", term_cols, "=") + "\n")
    traceback.print_tb(exc.__traceback__, file=sys.stderr)
    sys.exit(1)
