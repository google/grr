#!/usr/bin/env python
# Copyright 2012 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Parser for OSX launchd jobs."""




import re


class OSXLaunchdJobDict(object):
  """Cleanup launchd jobs reported by the service management framework.

  Exclude some rubbish like logged requests that aren't real jobs (see
  launchctl man page).  Examples:

  Exclude 0x7f8759d30310.anonymous.launchd
  Exclude 0x7f8759d1d200.mach_init.crash_inspector
  Keep [0x0-0x21021].com.google.GoogleDrive

  We could probably just exclude anything starting with a memory address, but
  I'm being more specific here as a tradeoff between sensible results and places
  for malware to hide.
  """

  def __init__(self, launchdjobs):
    """Initialize.

    Args:
      launchdjobs: NSCFArray of NSCFDictionarys containing launchd job data from
                   the ServiceManagement framework.
    """
    self.launchdjobs = launchdjobs

    self.blacklist_regex = [
        re.compile('^0x[a-z0-9]+\.anonymous\..+$'),
        re.compile('^0x[a-z0-9]+\.mach_init\.(crash_inspector|Inspector)$'),
        ]

  def Parse(self):
    """Parse the list of jobs and yield the good ones."""
    for item in self.launchdjobs:
      if not self.FilterItem(item):
        yield item

  def FilterItem(self, launchditem):
    """Should this job be filtered.

    Args:
      launchditem: job NSCFDictionary
    Returns:
      True if the item should be filtered (dropped)
    """
    for regex in self.blacklist_regex:
      if regex.match(launchditem.get('Label', '')):
        return True
    return False
