#!/usr/bin/env python
"""Misc utils (aka #include <misc.h>)."""

import sys

from .. import config
from . import term


_TAG = "[grr-devenv]"


def say(msg: str) -> None:
  tag: str = term.ok(_TAG)
  sys.stdout.write(f"{tag} {msg}\n")


def say_fail(msg: str) -> None:
  buf: str = term.fail(f"{_TAG} {msg}")
  sys.stderr.write(buf + "\n")


def say_warn(msg: str) -> None:
  buf: str = term.warn(f"{_TAG} {msg}")
  sys.stderr.write(buf + "\n")


# pylint: disable=invalid-name
def str_mid_pad(s: str, width: int, fill: str) -> str:
  pad = fill * int((width - len(s)) / (2 * len(fill)))
  return f"{pad}{s}{pad}"
