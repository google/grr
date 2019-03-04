#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Simple parsers for Linux Release files."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import re

from future.builtins import zip
from typing import Text

from grr_response_core.lib import parser
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.util import precondition

# Parameters identifying the Linux OS-type and version in /etc/os-release.
_SYSTEMD_OS_RELEASE_NAME = 'NAME'
_SYSTEMD_OS_RELEASE_VERSION = 'VERSION_ID'

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
    precondition.AssertOptionalType(contents, Text)
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

  # TODO(hanuszczak): But... why? ¯\_(ツ)_/¯
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
  supported_artifacts = ['LinuxReleaseInfo']

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
      # TODO(user): These weights are pointless - we can remove
      # them while preserving functionality. ReleaseFileParseHandler should
      # be deleted and replaced with a function.
  )

  def _Combine(self, stats, file_objects):
    result = {}
    for stat, file_object in zip(stats, file_objects):
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
        return

    # Amazon AMIs place release info in /etc/system-release.
    # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/amazon-linux-ami-basics.html
    system_release = found_files.get('/etc/system-release', None)
    if system_release and 'Amazon Linux' in system_release:
      match_object = ReleaseFileParseHandler.RH_RE.search(system_release)
      if match_object and match_object.lastindex > 1:
        yield rdf_protodict.Dict({
            'os_release': 'AmazonLinuxAMI',
            'os_major_version': int(match_object.group(1)),
            'os_minor_version': int(match_object.group(2))
        })
        return

    # Fall back to /etc/os-release.
    results_dict = self._ParseOSReleaseFile(found_files)
    if results_dict is not None:
      yield results_dict
      return

    # No successful parse.
    yield rdf_anomaly.Anomaly(
        type='PARSER_ANOMALY', symptom='Unable to determine distribution.')

  def _ParseOSReleaseFile(self, matches_dict):
    # The spec for the os-release file is given at
    # https://www.freedesktop.org/software/systemd/man/os-release.html.
    try:
      os_release_contents = matches_dict['/etc/os-release']
    except KeyError:
      return None
    os_release_name = None
    os_major_version = None
    os_minor_version = None
    for entry in os_release_contents.splitlines():
      entry_parts = entry.split('=', 1)
      if len(entry_parts) != 2:
        continue
      key = entry_parts[0].strip()
      # Remove whitespace and quotes from the value (leading and trailing).
      value = entry_parts[1].strip('\t \'"')
      if key == _SYSTEMD_OS_RELEASE_NAME:
        os_release_name = value
      elif key == _SYSTEMD_OS_RELEASE_VERSION:
        match_object = re.search(r'(?P<major>\d+)\.?(?P<minor>\d+)?', value)
        if match_object is not None:
          os_major_version = int(match_object.group('major'))
          minor_match = match_object.group('minor')
          # Some platforms (e.g. Google's Container-Optimized OS) do not have
          # multi-part version numbers so we use a default minor version of
          # zero.
          os_minor_version = 0 if minor_match is None else int(minor_match)
      if (os_release_name and os_major_version is not None and
          os_minor_version is not None):
        return rdf_protodict.Dict({
            'os_release': os_release_name,
            'os_major_version': os_major_version,
            'os_minor_version': os_minor_version,
        })
    return None
