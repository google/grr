#!/usr/bin/env python
"""Terminal pretty stuffs."""

import re
import sys
from typing import Callable


_ESC = "\x1b"
_RESET = f"{_ESC}[0m"
_RED_FG = f"{_ESC}[1;31m"
_GREEN_FG = f"{_ESC}[1;32m"
_YELLOW_FG = f"{_ESC}[1;33m"
_GRAY_FG = f"{_ESC}[38;5;240m"
_WHITE_FG = f"{_ESC}[1;37m"


def _colorize(buf: str, color_code: str) -> str:
  if not sys.stdout.isatty():
    return buf
  return f"{color_code}{buf}{_RESET}"


fail: Callable[[str], str] = lambda buf: _colorize(buf, _RED_FG)
warn: Callable[[str], str] = lambda buf: _colorize(buf, _YELLOW_FG)
ok: Callable[[str], str] = lambda buf: _colorize(buf, _GREEN_FG)
meh: Callable[[str], str] = lambda buf: _colorize(buf, _GRAY_FG)
attn: Callable[[str], str] = lambda buf: _colorize(buf, _WHITE_FG)


def strip_control_chars(buf: str) -> str:
  """Strips terminal control characters from a given string."""
  return re.sub(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", buf)
