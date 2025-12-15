#!/usr/bin/env python
"""Utilities for working with Windows Registry through RRG."""

import re
import stat

from grr_response_proto import jobs_pb2
from grr_response_proto.rrg import winreg_pb2 as rrg_winreg_pb2
from grr_response_proto.rrg.action import list_winreg_keys_pb2 as rrg_list_winreg_keys_pb2
from grr_response_proto.rrg.action import list_winreg_values_pb2 as rrg_list_winreg_values_pb2


class KeyGlob:
  """Representation of a Window registry glob expression."""

  def __init__(self, key_glob: str) -> None:
    """Initializes the key glob object.

    Args:
      key_glob: String representation of the key glob expression.
    """
    self._key_glob = key_glob

  @property
  def root(self) -> str:
    r"""Returns the longest key glob prefix without any glob expressions.

    For example, for a glob expression `SOFTWARE\Google\*\Config\**\*Path*` it
    is `SOFTWARE\Google`.
    """
    key_parts = self._key_glob.split("\\")
    key_parts_len_unglobbed = 0

    for key_part in key_parts:
      if "*" in key_part:
        break

      key_parts_len_unglobbed += 1

    return "\\".join(key_parts[:key_parts_len_unglobbed])

  @property
  def root_level(self) -> int:
    r"""Returns the maximum number of subkeys permitted after root.

    For example, for a glob expression `SOFTWARE\Google\*\Config\**5\*Path*` it
    is 8: root `SOFTWARE\Google` can be followed by 1 (`*`) + 1 (`Config`) + 5
    (`**5`) + 1 (`*Path*`) subkeys.
    """
    result = 0

    # Note that `key_glob_suffix` will either be empty or will begin in `\\`.
    # Thus, we always ignore the first element after doing split as it will
    # always be an empty string.
    key_glob_suffix = self._key_glob.removeprefix(self.root)
    for key_part in key_glob_suffix.split("\\")[1:]:
      if (match := re.fullmatch(r"\*\*(?P<depth>\d+)?", key_part)) is not None:
        result += int(match["depth"] or "3")
      else:
        result += 1

    return result

  @property
  def regex(self) -> re.Pattern[str]:
    """Returns regex representation of this key glob expression.

    This is similar to the standard `fnmatch.translate` but that function does
    not work well with recursive globs (norit distinguishes between them and
    normal ones) and ignores depth specification.

    Returns:
      A regex corresponding to the given registry key glob expression.
    """
    # We want *almost* everything to be matched literally, so we escape the
    # whole component and then deal with escaped glob patterns separately.
    key_pattern = re.escape(self._key_glob)

    # Now that everything is escaped, we take care of `**` and `*`. The escaping
    # routine above has turned them into `\*\*` and `\*`. Thus we need to
    # replace such sequences with appropriate regex ("unescape", in a sense).
    #
    # Note that as the second parameter to `re.sub` we pass a lambda instead of
    # a string. This is because any escape sequences are processed [1] and since
    # the separator is `\\`, it would have been unnecessary turned into `\`.
    # There is no such issue with the lambda version of `re.sub`.
    #
    # [1]: https://docs.python.org/3/library/re.html#re.sub

    # `**` at the beginning.
    key_pattern = re.sub(
        r"^\\\*\\\*(?P<depth>\d+)?",
        repl=lambda match: rf"[^\\]*(\\[^\\]*){{0,{int(match['depth'] or 3) - 1}}}",
        string=key_pattern,
    )
    # `**` after `\`.
    key_pattern = re.sub(
        r"\\\\\\\*\\\*(?P<depth>\d+)?",
        repl=lambda match: rf"(\\[^\\]*){{0,{match['depth'] or 3}}}",
        string=key_pattern,
    )
    # `*` (allowed to appear anywhere).
    key_pattern = re.sub(
        r"\\\*",
        repl=lambda _: r"[^\\]*",
        string=key_pattern,
    )

    return re.compile(f"^{key_pattern}$")


HKEY_STR: dict[rrg_winreg_pb2.PredefinedKey, str] = {
    rrg_winreg_pb2.CLASSES_ROOT: "HKEY_CLASSES_ROOT",
    rrg_winreg_pb2.CURRENT_CONFIG: "HKEY_CURRENT_CONFIG",
    rrg_winreg_pb2.CURRENT_USER: "HKEY_CURRENT_USER",
    rrg_winreg_pb2.LOCAL_MACHINE: "HKEY_LOCAL_MACHINE",
    rrg_winreg_pb2.PERFORMANCE_DATA: "HKEY_PERFORMANCE_DATA",
    rrg_winreg_pb2.PERFORMANCE_TEXT: "HKEY_PERFORMANCE_TEXT",
    rrg_winreg_pb2.USERS: "HKEY_USERS",
}

HKEY_ENUM: dict[str, rrg_winreg_pb2.PredefinedKey] = {
    key_str: key_enum for key_enum, key_str in HKEY_STR.items()
}


def StatEntryOfKeyResult(
    result: rrg_list_winreg_keys_pb2.Result,
) -> jobs_pb2.StatEntry:
  """Converts the given `list_winreg_keys` result to a stat entry object."""
  stat_entry = jobs_pb2.StatEntry()
  stat_entry.pathspec.pathtype = jobs_pb2.PathSpec.PathType.REGISTRY
  stat_entry.pathspec.path = f"{HKEY_STR[result.root]}\\{result.key}\\{result.subkey}"  # pylint: disable=line-too-long
  # We preserve Python agent semantics and since we are dealing with stat
  # entries for registry keys, we pretend to be a directory.
  stat_entry.st_mode = stat.S_IFDIR

  return stat_entry


def StatEntryOfValueResult(
    result: rrg_list_winreg_values_pb2.Result,
) -> jobs_pb2.StatEntry:
  """Converts the given `list_winreg_values` result to a stat entry object."""
  stat_entry = jobs_pb2.StatEntry()
  stat_entry.pathspec.pathtype = jobs_pb2.PathSpec.PathType.REGISTRY
  stat_entry.pathspec.path = f"{HKEY_STR[result.root]}\\{result.key}"
  if result.value.name:
    stat_entry.pathspec.path += f"\\{result.value.name}"

  if result.value.HasField("bytes"):
    stat_entry.registry_type = jobs_pb2.StatEntry.REG_BINARY
    stat_entry.registry_data.data = result.value.bytes
  elif result.value.HasField("string"):
    stat_entry.registry_type = jobs_pb2.StatEntry.REG_SZ
    stat_entry.registry_data.string = result.value.string
  elif result.value.HasField("expand_string"):
    stat_entry.registry_type = jobs_pb2.StatEntry.REG_EXPAND_SZ
    stat_entry.registry_data.string = result.value.expand_string
  elif result.value.multi_string.values:
    stat_entry.registry_type = jobs_pb2.StatEntry.REG_MULTI_SZ
    for response_string_value in result.value.multi_string.values:
      stat_entry_string = stat_entry.registry_data.list.content.add()
      stat_entry_string.string = response_string_value
  elif result.value.HasField("link"):
    stat_entry.registry_type = jobs_pb2.StatEntry.REG_LINK
    stat_entry.registry_data.string = result.value.link
  elif result.value.HasField("uint32"):
    stat_entry.registry_type = jobs_pb2.StatEntry.REG_DWORD
    stat_entry.registry_data.integer = result.value.uint32
  elif result.value.HasField("uint64"):
    stat_entry.registry_type = jobs_pb2.StatEntry.REG_QWORD
    stat_entry.registry_data.integer = result.value.uint64

  return stat_entry
