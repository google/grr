#!/usr/bin/env python
"""Utils for flow related tasks."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging


def GetUserInfo(knowledge_base, user):
  # TODO: This docstring cannot be a raw literal because there are
  # issues with raw unicode literals on Python 2. Once support for Python 2 is
  # dropped, it can be made raw again.
  # pylint: disable=g-docstring-has-escape
  """Get a User protobuf for a specific user.

  Args:
    knowledge_base: An rdf_client.KnowledgeBase object.
    user: Username as string. May contain domain like DOMAIN\\user.

  Returns:
    A User rdfvalue or None
  """
  # pylint: enable=g-docstring-has-escape
  if "\\" in user:
    domain, user = user.split("\\", 1)
    users = [
        u for u in knowledge_base.users
        if u.username == user and u.userdomain == domain
    ]
  else:
    users = [u for u in knowledge_base.users if u.username == user]

  if not users:
    return
  else:
    return users[0]


# TODO(user): Deprecate this function once there is an alternative for
# CacheGrep.
def InterpolatePath(path, knowledge_base, users=None, path_args=None, depth=0):
  """Take a string as a path on a client and interpolate with client data.

  Args:
    path: A single string/unicode to be interpolated.
    knowledge_base: An rdf_client.KnowledgeBase object.
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
      user = GetUserInfo(knowledge_base, user)
      if user:
        formatters = dict((x.name, y) for x, y in user.ListSetFields())
        formatters.update(sys_formatters)
        try:
          results.append(path.format(**formatters))
        except KeyError:
          pass  # We may be missing values for some users.
    return results
  else:
    try:
      path = path.format(**sys_formatters)
    except KeyError:
      logging.warning("Failed path interpolation on %s", path)
      return ""
    if "{" in path and depth < 10:
      path = InterpolatePath(
          path,
          knowledge_base=knowledge_base,
          users=users,
          path_args=path_args,
          depth=depth + 1)
    return path
