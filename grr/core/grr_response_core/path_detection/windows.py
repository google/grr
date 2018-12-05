#!/usr/bin/env python
"""Windows paths detection classes."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re


from future.utils import iteritems
from future.utils import string_types

from grr_response_core.path_detection import core


class RunDllExtractor(core.Extractor):
  """Extractor that extracts rundll paths."""

  def Extract(self, components):
    """Extracts interesting paths from a given path.

    Args:
      components: Source string represented as a list of components.

    Returns:
      A list of extracted paths (as strings).
    """

    rundll_index = -1
    for index, component in enumerate(components):
      if component.lower().endswith("rundll32.exe"):
        rundll_index = index

    if rundll_index == -1:
      return []

    components = components[(rundll_index + 1):]

    # We expect components after "rundll32.exe" to point at a DLL and a
    # function. For example:
    # rundll32.exe "C:\Windows\system32\advpack.dll",DelNodeRunDLL32
    last_component = components[-1].rsplit(",", 1)[0]

    extracted_path = " ".join(components[0:-1] + [last_component])
    return [extracted_path]


class ExecutableExtractor(core.Extractor):
  """Extractor for ordinary paths."""

  EXECUTABLE_EXTENSIONS = ("exe", "com", "bat", "dll", "msi", "sys", "scr",
                           "pif")

  def Extract(self, components):
    """Extracts interesting paths from a given path.

    Args:
      components: Source string represented as a list of components.

    Returns:
      A list of extracted paths (as strings).
    """

    for index, component in enumerate(components):
      if component.lower().endswith(self.EXECUTABLE_EXTENSIONS):
        extracted_path = " ".join(components[0:index + 1])
        return [extracted_path]

    return []


class EnvVarsPostProcessor(core.PostProcessor):
  """PostProcessor that replaces env variables with predefined values."""

  # Service keys have peculiar ways of specifying systemroot, these regexes
  # will be used to convert them to standard expansions.
  SYSTEMROOT_RE = re.compile(r"^\\SystemRoot", flags=re.IGNORECASE)
  SYSTEM32_RE = re.compile(r"^system32", flags=re.IGNORECASE)

  # Regex that matches Windows Registry environment variables.
  WIN_ENVIRON_REGEX = re.compile(r"%([^%]+?)%")

  def __init__(self, vars_map):
    """EnvVarsPostProcessor constructor.

    Args:
      vars_map: Dictionary of "string" -> "string|list", i.e. a mapping of
          environment variables names to their suggested values or to lists
          of their suggested values.
    """
    super(core.PostProcessor, self).__init__()

    self.vars_map = {}
    for var_name, value in iteritems(vars_map):
      var_regex = re.compile(
          re.escape("%" + var_name + "%"), flags=re.IGNORECASE)
      self.vars_map[var_name.lower()] = (var_regex, value)

  def Process(self, path):
    """Processes a given path.

    Args:
      path: Path (as a string) to post-process.

    Returns:
      A list of paths with environment variables replaced with their
      values. If the mapping had a list of values for a particular variable,
      instead of just one value, then all possible replacements will be
      returned.
    """
    path = re.sub(self.SYSTEMROOT_RE, r"%systemroot%", path, count=1)
    path = re.sub(self.SYSTEM32_RE, r"%systemroot%\\system32", path, count=1)

    matches_iter = self.WIN_ENVIRON_REGEX.finditer(path)
    var_names = set(m.group(1).lower() for m in matches_iter)

    results = [path]
    for var_name in var_names:
      try:
        var_regex, var_value = self.vars_map[var_name]
      except KeyError:
        continue

      if isinstance(var_value, string_types):
        replacements = [var_value]
      else:
        replacements = var_value

      processed_results = []
      for result in results:
        for repl in replacements:
          # Using lambda here, as otherwise Python interprets \\f as a
          # backreference (same applies to \\0 and \\1). When using a
          # function as a replacement argument, backreferences are ignored.
          # pylint: disable=cell-var-from-loop
          processed_results.append(var_regex.sub(lambda _: repl, result))
      results = processed_results

    return results


def CreateWindowsRegistryExecutablePathsDetector(vars_map=None):
  """Creates Windows paths detector.

  Commandline strings can be space separated and contain options.
  e.g. C:\\Program Files\\ACME Corporation\\wiz.exe /quiet /blah

  See here for microsoft doco on commandline parsing:
  http://msdn.microsoft.com/en-us/library/windows/desktop/ms682425(v=vs.85).aspx

  Args:
    vars_map: Environment variables mapping. Default is None.

  Returns:
    A detector (core.Detector instance).
  """
  return core.Detector(
      extractors=[RunDllExtractor(), ExecutableExtractor()],
      post_processors=[EnvVarsPostProcessor(vars_map or {})],)


def DetectExecutablePaths(source_values, vars_map=None):
  """Detects paths in a list of Windows Registry strings.

  Args:
    source_values: A list of strings to detect paths in.
    vars_map: Dictionary of "string" -> "string|list", i.e. a mapping of
          environment variables names to their suggested values or to lists
          of their suggested values.

  Yields:
    A list of detected paths (as strings).
  """
  detector = CreateWindowsRegistryExecutablePathsDetector(vars_map=vars_map)

  for source_value in source_values:
    for result in detector.Detect(source_value):
      yield result
