#!/usr/bin/env python
"""Simple parsers for Linux Release files."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import itertools
import re

from grr_response_core.lib import parser
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict

ParsedRelease = collections.namedtuple('ParsedRelease', 'release, major, minor')
WeightedReleaseFile = collections.namedtuple('WeightedReleaseFile',
                                             'weight, path, processor')


class ReleaseParseHandler(object):
  """Base class for distribution data file parse handlers."""

  def __init__(self, contents):
    """Initialise the parser, presenting file contents to parse.

    Args:
      contents: file contents that are to be parsed.
    """
    self.contents = contents

  def Parse(self):
    """Parse the contents of the release file and return results.

    Return:
      A tuple with two items. The first is a Boolean value that determines
      whether or not a complete result is given ; that is, whether or not the
      parse is conclusive. The second is a ParsedRelease object that defines
      the distribution information.
    """
    raise NotImplementedError('parse() missing')


class LsbReleaseParseHandler(ReleaseParseHandler):
  """Parse /etc/lsb-release file."""

  # Keys for name/release in the lsb-release file.
  LSB_NAME_KEY = 'DISTRIB_ID'
  LSB_RELEASE_KEY = 'DISTRIB_RELEASE'

  # Distributions for which a fallback is not needed to be more specific.
  NO_FALLBACK_NEEDED = ['ubuntu', 'linuxmint']

  def Parse(self):
    name = None
    release = None
    major = 0
    minor = 0
    complete = False

    # Hacky key=value parser.
    for line in self.contents.splitlines():
      line = line.strip()
      if '=' not in line:
        continue

      key, value = line.split('=', 1)
      key = key.strip()
      value = value.strip()

      if key == self.LSB_NAME_KEY:
        name = value
      elif key == self.LSB_RELEASE_KEY:
        release = value

    # If the LSB file was not malformed and contained all we need, we are almost
    # done...
    complete = all([name, release])

    # ... however, check for systems for which lsb-release is NOT enough data.
    if complete:
      complete = name.lower() in self.NO_FALLBACK_NEEDED

    # Check that we have a valid release number.
    if complete:
      if '.' not in release:
        complete = False
      else:
        release_parts = release.split('.', 1)
        major, minor = [int(x.strip()) for x in release_parts]

    return complete, ParsedRelease(name, major, minor)


class ReleaseFileParseHandler(ReleaseParseHandler):
  """Parse 'release' files (eg, oracle-release, redhat-release)."""

  RH_RE = re.compile(r'release (\d[\d]*)\.(\d[\d]*)')

  def __init__(self, name):
    super(ReleaseFileParseHandler, self).__init__(None)

    self.name = name

  def __call__(self, contents):
    """Small hack to let instances act as if they are bare classes."""
    self.contents = contents
    return self

  def Parse(self):
    major = 0
    minor = 0
    complete = False
    data = self.contents.strip()

    if self.name in ['RedHat', 'OracleLinux', 'OEL']:
      check = self.RH_RE.search(data)
      if check is not None:
        major = int(check.group(1))
        minor = int(check.group(2))
        complete = True
      else:
        complete = False

    return complete, ParsedRelease(self.name, major, minor)


class LinuxReleaseParser(parser.FileMultiParser):
  """Parser for Linux distribution information."""

  output_types = ['Dict']
  supported_artifacts = ['LinuxRelease']

  # Multiple files exist to define a Linux distribution, some of which are more
  # accurate than others under certain circumstances. We assign a weight and
  # allow handling to fall through to the next file to get the most-specific
  # distribution.
  WEIGHTS = (
      # Top priority: systems with lsb-release.
      WeightedReleaseFile(0, '/etc/lsb-release', LsbReleaseParseHandler),
      # Oracle Linux (formerly OEL).
      WeightedReleaseFile(10, '/etc/oracle-release',
                          ReleaseFileParseHandler('OracleLinux')),
      # OEL.
      WeightedReleaseFile(11, '/etc/enterprise-release',
                          ReleaseFileParseHandler('OEL')),
      # RHEL-based.
      WeightedReleaseFile(20, '/etc/redhat-release',
                          ReleaseFileParseHandler('RedHat')),
      # Debian-based.
      WeightedReleaseFile(20, '/etc/debian_version',
                          ReleaseFileParseHandler('Debian')),
  )

  def _Combine(self, stats, file_objects):
    result = {}
    for stat, file_object in itertools.izip(stats, file_objects):
      path = stat.pathspec.path
      file_object.seek(0)
      contents = utils.ReadFileBytesAsUnicode(file_object)
      result[path] = contents
    return result

  def ParseMultiple(self, stats, file_objects, knowledge_base):
    """Parse the found release files."""
    _ = knowledge_base

    # Collate files into path: contents dictionary.
    found_files = self._Combine(stats, file_objects)

    # Determine collected files and apply weighting.
    weights = [w for w in self.WEIGHTS if w.path in found_files]
    weights = sorted(weights, key=lambda x: x.weight)

    for _, path, handler in weights:
      contents = found_files[path]
      obj = handler(contents)

      complete, result = obj.Parse()
      if result is None:
        continue
      elif complete:
        yield rdf_protodict.Dict({
            'os_release': result.release,
            'os_major_version': result.major,
            'os_minor_version': result.minor
        })
        break
    else:
      # No successful parse.
      yield rdf_anomaly.Anomaly(
          type='PARSER_ANOMALY', symptom='Unable to determine distribution.')
