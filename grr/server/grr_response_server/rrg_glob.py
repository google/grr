#!/usr/bin/env python
"""Utilities for performing path globbing on RRG-supported endpoints."""

import pathlib
import re


class Glob:
  """Utility class for simulating globs using RRG capabilities.

  The RRG agent does not implement complex filesystem globbing logic that the
  Python agent does. However, it does support recursive walks across the file
  system. To guide the walk and avoid custom globbing mechanism it uses much
  simpler (and at the same time: more powerful!) regex-based pruning.

  Pruning is similar to filtering. We apply the given regex to a path we are
  currently visiting and discard the result if the path does not match the
  pattern. The difference between pruning and filtering is that the former does
  not continue the recursive walk in case of pattern mismatch—the entire subtree
  is pruned as opposed to filtering out a single result.
  """

  _root: pathlib.PurePath
  _root_level: int
  _regex: re.Pattern[str]
  _pruning_regex: re.Pattern[str]

  def __init__(self, path: pathlib.PurePath):
    if not path.is_absolute():
      raise ValueError(f"Non-absolute path: {path}")

    if isinstance(path, pathlib.PurePosixPath):
      sep = "/"
    elif isinstance(path, pathlib.PureWindowsPath):
      sep = "\\"
    else:
      raise TypeError(f"Unexpected path type: {type(path)}")
    sep_re = re.escape(sep)

    # Currently considered path prefix. We iterate over all of them, from the
    # longest to the shortest (`/foo/bar/baz`, `/foo/bar`, `/foo`) until we hit
    # the anchor (root on Unixes, drive letter on Windows).
    prefix = path
    prefix_level = 0  # The inverse of depth.

    # Currently found candidate for the root. As we move across the prefixes we
    # find more parts with glob expressions and the root candidate keeps getting
    # shorter.
    root = path
    root_level = 0  # The inverse of depth.

    # The regex patterns we have built so far. As we move across the prefixes
    # this gets longer and longer as each path component prepends its pattern.
    pattern = ""
    pruning_pattern = ""

    if path != path.__class__(path.anchor):
      part_sep_re = ""
    else:
      # Special case for anchor-only globs as otherwise we omit an empty pattern
      # (or naked drive letter on Windows) and we want them to match the anchor.
      part_sep_re = sep_re

    while str(prefix) != path.anchor:
      part = prefix.name
      part_pattern: str
      part_sep_re_next: str
      part_depth: int
      part_is_glob: bool

      if (match := re.fullmatch(r"\*\*(?P<depth>\d+)?", part)) is not None:
        if match["depth"]:
          part_depth = int(match["depth"])
        else:
          part_depth = _DEFAULT_RECURSIVE_GLOB_DEPTH

        part_pattern = f"({sep_re}[^{sep_re}]*){{0,{part_depth}}}"
        part_sep_re_next = ""
        part_is_glob = True
      elif re.search(r"[?*]|\[.*\]", part) is not None:
        # We want *almost* everything to be matched literally, so we escape the
        # whole component.
        part_pattern = re.escape(part)
        # Now that everything is escaped, we take care of `*` and `?` and chara-
        # cter sets. The escaping routine above has turned them into `\*`, `\?`
        # and `\[(...)\]` expressions. Thus we need to replace such sequences
        # with appropriate regex (so, "unescape" in a sense).
        #
        # Note that as the second parameter to `re.sub` we pass a lambda instead
        # of a string. This is because any escape sequences are processed [1]
        # and since the separator can be `\\` (for Windows), it would have been
        # unnecessary turned into `\`. The lambda version of `re.sub` does not
        # suffer from this issue.
        #
        # [1]: https://docs.python.org/3/library/re.html#re.sub
        part_pattern = re.sub(
            r"\\\[(?P<from>.)\\\-(?P<to>.)\\\]",
            lambda match: f"[{match['from']}-{match['to']}]",
            part_pattern,
        )
        part_pattern = re.sub(r"\\\[", lambda _: "[", part_pattern)
        part_pattern = re.sub(r"\\\]", lambda _: "]", part_pattern)
        part_pattern = re.sub(r"\\\*", lambda _: f"[^{sep_re}]*", part_pattern)
        part_pattern = re.sub(r"\\\?", lambda _: f"[^{sep_re}]", part_pattern)
        part_sep_re_next = sep_re
        part_depth = 1
        part_is_glob = True
      else:
        part_pattern = re.escape(part)
        part_sep_re_next = sep_re
        part_depth = 1
        part_is_glob = False

      if part_is_glob:
        # We found a glob expression within the current path part, it means that
        # the next candidate for the root is parent of the current prefix (which
        # might be discarded by the next loop iteration).
        root = prefix.parent
        root_level = prefix_level + part_depth

      if pruning_pattern:
        pattern = f"{part_pattern}{part_sep_re}{pattern}"
        pruning_pattern = f"{part_pattern}({part_sep_re}{pruning_pattern})?"
      else:
        pattern = part_pattern
        pruning_pattern = part_pattern

      prefix = prefix.parent
      prefix_level = prefix_level + part_depth

      part_sep_re = part_sep_re_next

    pattern = f"{part_sep_re}{pattern}"
    pruning_pattern = f"{part_sep_re}({pruning_pattern})?"

    # Special case for Windows paths: we stop building the pruning pattern once
    # the prefix is the anchor. But that means we did not include the drive, so
    # we patch it into the pattern.
    #
    # Windows paths are also case-insensitive so we need to enable the `(?i)`
    # modifier.
    if isinstance(path, pathlib.PureWindowsPath):
      pattern = f"(?i)^{re.escape(path.drive)}{pattern}$"
      pruning_pattern = f"(?i)^{re.escape(path.drive)}{pruning_pattern}$"
    else:
      pattern = f"^{pattern}$"
      pruning_pattern = f"^{pruning_pattern}$"

    self._root = root
    self._root_level = root_level

    self._regex = re.compile(pattern)
    self._pruning_regex = re.compile(pruning_pattern)

  @property
  def root(self) -> pathlib.PurePath:
    """Returns the longest path glob prefix without any glob expressions.

    For example, for `/foo/bar/*/quux/**/*.txt` it is `/foo/bar`.
    """
    return self._root

  @property
  def root_level(self) -> int:
    """Returns the maximum number of components permitted after root.

    For example, for `/foo/bar/*/quux/**5/*.txt` it is 8: `/foo/bar` is the root
    and it can be followed by 1 (`*`) + 1 (`quux`) + 5 (`**5`) + 1 (`*.txt`)
    components.
    """
    return self._root_level

  @property
  def regex(self) -> re.Pattern[str]:
    """Returns normal, non-pruning regex corresponding to this path glob.

    This is similar to the standard `fnmatch.translate` but that function does
    not work well with recursive globs (nor does it distinguish between them and
    normal ones) and ignores depth specification.
    """
    return self._regex

  @property
  def pruning_regex(self) -> re.Pattern[str]:
    """Returns pruning regex corresponding to this path glob.

    See the documentation for the `Glob` class itself for more information about
    pruning.
    """
    return self._pruning_regex


# GRR uses the default depth of 3 for recursive globs (`**` patterns) so we
# replicate behaviour.
_DEFAULT_RECURSIVE_GLOB_DEPTH = 3
