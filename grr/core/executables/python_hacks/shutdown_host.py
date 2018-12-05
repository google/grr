#!/usr/bin/env python
"""Shut down windows hosts."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import platform

tested_versions = ['xp', 'vista', '2008', '2003']
cmd = 'cmd'
args = ['/c', '%SystemRoot%\\System32\\shutdown.exe', '/s', '/f']
os_version = platform.platform().lower()

# pylint: disable=undefined-variable
if 'time_in_seconds' in py_args:
  args.extend(['/t', py_args['time_in_seconds']])
else:
  args.extend(['/t', '20'])

if 'reason' in py_args:
  args.extend(['/c', py_args['reason']])

for version in tested_versions:
  if os_version.find(version) != -1:
    stdout, stderr, exit_status, time_taken = client_utils_common.Execute(
        cmd, args, time_limit=-1, bypass_whitelist=True)
    magic_return_str = '%s, %s, %s, %s' % (stdout.encode('base64'),
                                           stderr.encode('base64'), exit_status,
                                           time_taken)
    break
