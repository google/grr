#!/usr/bin/env python
"""Misc utils (aka #include <misc.h>)."""

import collections
import os
import signal
import sys
import time

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


def kill_process(pid: int) -> None:
  """Kill a process and make sure it's dead."""

  try:
    os.kill(pid, signal.SIGTERM)
  except OSError:
    # pid already dead
    return
  dead: bool = False
  for _ in range(10):
    try:
      os.kill(pid, 0)
    except OSError:
      dead = True
      break
    time.sleep(1)
  if not dead:
    os.kill(pid, signal.SIGKILL)


class RollingLineBuffer:
  """A (very naive) rolling text line buffer.

  The buffer only keeps track of the last N lines of text.
  """

  def __init__(self, capacity: int) -> None:
    self._lines: collections.deque[str] = collections.deque()
    self._capacity: int = capacity

  def add(self, buf: str) -> None:
    """Add text to the buffer."""

    if self._lines:
      buf = self._lines.pop() + buf
    for line in buf.split("\n"):
      self._lines.append(line)
      if len(self._lines) > self._capacity:
        self._lines.popleft()

  def get(self) -> str:
    """Get the full buffer contents as text."""

    return "\n".join(list(self._lines))
