#!/usr/bin/env python
"""Shut down windows hosts."""


import platform

def main():
  global py_args  # Predefined in the environment. See google/grr#937
  tested_versions = ['xp', 'vista', '2008', '2003']
  cmd = 'cmd'
  args = ['/c', '%SystemRoot%\\System32\\shutdown.exe', '/s', '/f']
  os_version = platform.platform().lower()

  if 'time_in_seconds' in py_args:
    args.extend(['/t', py_args['time_in_seconds']])
  else:
    args.extend(['/t', '20'])

  if 'reason' in py_args:
    args.extend(['/c', py_args['reason']])

  for version in tested_versions:
    if os_version.find(version) != -1:
      stdout, stderr, exit_status, time_taken = client_utils_common.Execute(
          cmd, args, time_limit=-1, bypass_allowlist=True)
      magic_return_str = '%s, %s, %s, %s' % (stdout.encode('base64'),
                                             stderr.encode('base64'), exit_status,
                                             time_taken)
      break


if __name__ == '__main__':
  main()
