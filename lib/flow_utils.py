#!/usr/bin/env python
"""Utils for flow related tasks."""

import logging


def GetUserInfo(client, user):
  """Get a User protobuf for a specific user.

  Args:
    client: A VFSGRRClient object.
    user: Username as string. May contain domain like DOMAIN\\user.
  Returns:
    A User rdfvalue or None
  """
  if "\\" in user:
    domain, user = user.split("\\", 1)
    users = [u for u in client.Get(client.Schema.USER, []) if u.username == user
             and u.domain == domain]
  else:
    users = [u for u in client.Get(client.Schema.USER, [])
             if u.username == user]

  if not users:
    return
  else:
    return users[0]


# TODO(user): Deprecate this function once Browser History is Artifacted.
def InterpolatePath(path, client, users=None, path_args=None, depth=0):
  """Take a string as a path on a client and interpolate with client data.

  Args:
    path: A single string/unicode to be interpolated.
    client: A VFSGRRClient object.
    users: A list of string usernames, or None.
    path_args: A dict of additional args to use in interpolation. These take
        precedence over any system provided variables.
    depth: A counter for recursion depth.

  Returns:
    A single string if users is None, otherwise a list of strings.
  """

  sys_formatters = {
      # TODO(user): Collect this during discovery from the registry.
      # HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\
      # Value: SystemRoot
      "systemroot": "c:\\Windows"
      }

  # Override any system formatters with path_args.
  if path_args:
    sys_formatters.update(path_args)

  if users:
    results = []
    for user in users:
      # Extract and interpolate user specific formatters.
      user = GetUserInfo(client, user)
      if user:
        formatters = dict((x.name, y) for x, y in user.ListFields())
        special_folders = dict(
            (x.name, y) for x, y in user.special_folders.ListFields())

        formatters.update(special_folders)
        formatters.update(sys_formatters)
        try:
          results.append(path.format(**formatters))
        except KeyError:
          pass   # We may be missing values for some users.
    return results
  else:
    try:
      path = path.format(**sys_formatters)
    except KeyError:
      logging.warn("Failed path interpolation on %s", path)
      return ""
    if "{" in path and depth < 10:
      path = InterpolatePath(path, client=client, users=users,
                             path_args=path_args, depth=depth+1)
    return path
