#!/usr/bin/env python
"""This file contains utility functions used in ApiCallHandler classes."""

from __future__ import annotations

from collections.abc import Sequence
import re
import sys
from typing import TypeVar

from google.protobuf import message

_MessageT = TypeVar("_MessageT", bound=message.Message)


def FilterList(
    l: Sequence[_MessageT],
    offset: int,
    count: int = 0,
    filter_value: str | None = None,
) -> Sequence[_MessageT]:
  """Filters a list, getting count elements, starting at offset."""

  if offset < 0:
    raise ValueError("Offset needs to be greater than or equal to zero")

  if count < 0:
    raise ValueError("Count needs to be greater than or equal to zero")

  count = count or sys.maxsize
  if not filter_value:
    return l[offset : offset + count]

  index = 0
  items: list[_MessageT] = []
  for item in l:
    serialized_item = item.SerializeToString()
    regex = re.escape(filter_value).encode("utf-8")
    if re.search(regex, serialized_item, re.I):
      if index >= offset:
        items.append(item)
      index += 1

      if len(items) >= count:
        break

  return items
