#!/usr/bin/env python
"""Parsers for Linux PAM configuration files."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import re


from builtins import zip  # pylint: disable=redefined-builtin

from grr_response_core.lib import parser
from grr_response_core.lib import utils
from grr_response_core.lib.parsers import config_file
from grr_response_core.lib.rdfvalues import config_file as rdf_config_file


class PAMFieldParser(config_file.FieldParser):
  """Field parser for PAM configurations."""

  # The syntax is based on:
  #   http://linux.die.net/man/5/pam.d

  PAMDIR = "/etc/pam.d"
  OLD_PAMCONF_FILENAME = "/etc/pam.conf"
  PAMCONF_RE = re.compile(
      r"""
      (\S+)          # The "type".
      \s+            # separator
      (              # Now match the "control" argument.
        \[[^\]]*\]   # Complex form. e.g. [success=ok default=die] etc.
        | \w+        # Or a single word form.
      )              # End of the "control" argument.
      \s+            # separator
      (\S+)          # The "module-path".
      (?:\s+(.*))?   # And the optional "module-arguments" is anything else.
      """, re.VERBOSE)

  def _FixPath(self, path):
    # Anchor any relative paths in the PAMDIR
    if not os.path.isabs(path):
      return os.path.join(self.PAMDIR, path)
    else:
      return path

  def EnumerateAllConfigs(self, stats, file_objects):
    """Generate RDFs for the fully expanded configs.

    Args:
      stats: A list of RDF StatEntries corresponding to the file_objects.
      file_objects: A list of file handles.

    Returns:
      A tuple of a list of RDFValue PamConfigEntries found & a list of strings
      which are the external config references found.
    """
    # Convert the stats & file_objects into a cache of a
    # simple path keyed dict of file contents.
    cache = {}
    for stat_obj, file_obj in zip(stats, file_objects):
      cache[stat_obj.pathspec.path] = utils.ReadFileBytesAsUnicode(file_obj)

    result = []
    external = []
    # Check to see if we have the old pam config file laying around.
    if self.OLD_PAMCONF_FILENAME in cache:
      # The PAM documentation says if it contains config data, then
      # it takes precedence over the rest of the config.
      # If it doesn't, the rest of the PAMDIR config counts.
      result, external = self.EnumerateConfig(None, self.OLD_PAMCONF_FILENAME,
                                              cache)
      if result:
        return result, external

    # If we made it here, there isn't a old-style pam.conf file worth
    # speaking of, so process everything!
    for path in cache:
      # PAM uses the basename as the 'service' id.
      service = os.path.basename(path)
      r, e = self.EnumerateConfig(service, path, cache)
      result.extend(r)
      external.extend(e)
    return result, external

  def EnumerateConfig(self, service, path, cache, filter_type=None):
    """Return PamConfigEntries it finds as it recursively follows PAM configs.

    Args:
      service: A string containing the service name we are processing.
      path: A string containing the file path name we want.
      cache: A dictionary keyed on path, with the file contents (list of str).
      filter_type: A string containing type name of the results we want.

    Returns:
      A tuple of a list of RDFValue PamConfigEntries found & a list of strings
      which are the external config references found.
    """

    result = []
    external = []
    path = self._FixPath(path)

    # Make sure we only look at files under PAMDIR.
    # Check we have the file in our artifact/cache. If not, our artifact
    # didn't give it to us, and that's a problem.
    # Note: This should only ever happen if it was referenced
    # from /etc/pam.conf so we can assume that was the file.
    if path not in cache:
      external.append("%s -> %s", self.OLD_PAMCONF_FILENAME, path)
      return result, external

    for tokens in self.ParseEntries(cache[path]):
      if path == self.OLD_PAMCONF_FILENAME:
        # We are processing the old style PAM conf file. It's a special case.
        # It's format is "service type control module-path module-arguments"
        # i.e. the 'service' is the first arg, the rest is line
        # is like everything else except for that addition.
        try:
          service = tokens[0]  # Grab the service from the start line.
          tokens = tokens[1:]  # Make the rest of the line look like "normal".
        except IndexError:
          continue  # It's a blank line, skip it.

      # Process any inclusions in the line.
      new_path = None
      filter_request = None
      try:
        # If a line starts with @include, then include the entire referenced
        # file.
        # e.g. "@include common-auth"
        if tokens[0] == "@include":
          new_path = tokens[1]
        # If a line's second arg is an include/substack, then filter the
        # referenced file only including entries that match the 'type'
        # requested.
        # e.g. "auth include common-auth-screensaver"
        elif tokens[1] in ["include", "substack"]:
          new_path = tokens[2]
          filter_request = tokens[0]
      except IndexError:
        # It's not a valid include line, so keep processing as normal.
        pass

      # If we found an include file, enumerate that file now, and
      # included it where we are in this config file.
      if new_path:
        # Preemptively check to see if we have a problem where the config
        # is referencing a file outside of the expected/defined artifact.
        # Doing it here allows us to produce a better context for the
        # problem. Hence the slight duplication of code.

        new_path = self._FixPath(new_path)
        if new_path not in cache:
          external.append("%s -> %s" % (path, new_path))
          continue  # Skip to the next line of the file.
        r, e = self.EnumerateConfig(service, new_path, cache, filter_request)
        result.extend(r)
        external.extend(e)
      else:
        # If we have been asked to filter on types, skip over any types
        # we are not interested in.
        if filter_type and tokens[0] != filter_type:
          continue  # We can skip this line.

        # If we got here, then we want to include this line in this service's
        # config.

        # Reform the line and break into the correct fields as best we can.
        # Note: ParseEntries doesn't cope with what we need to do.
        match = self.PAMCONF_RE.match(" ".join(tokens))
        if match:
          p_type, control, module_path, module_args = match.group(1, 2, 3, 4)
          # Trim a leading "-" from the type field if present.
          if p_type.startswith("-"):
            p_type = p_type[1:]
          result.append(
              rdf_config_file.PamConfigEntry(
                  service=service,
                  type=p_type,
                  control=control,
                  module_path=module_path,
                  module_args=module_args))
    return result, external


class PAMParser(parser.FileMultiParser):
  """Artifact parser for PAM configurations."""

  output_types = ["PamConfig"]
  supported_artifacts = ["LinuxPamConfigs"]

  def __init__(self, *args, **kwargs):
    super(PAMParser, self).__init__(*args, **kwargs)
    self._field_parser = PAMFieldParser()

  def ParseMultiple(self, stats, file_objects, knowledge_base):
    _ = knowledge_base
    results, externals = self._field_parser.EnumerateAllConfigs(
        stats, file_objects)
    yield rdf_config_file.PamConfig(entries=results, external_config=externals)
