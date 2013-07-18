#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.

"""Utils for flow related tasks."""

import re

# Note that these function cannot be in utils
# because some of them rely on AFF4 which would
# create a cyclic dependency

import logging

from grr.lib import aff4
from grr.lib import utils


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


# TODO(user): Deprecate this in favor of client side interpolation.
class ClientPathHelper(object):
  """A class to assist in creating client specific paths.

  This class is used to cache certain client information.
  """

  MAJOR_VERSION_WINDOWS_VISTA = 6

  def __init__(self, client_id, token=None):
    """Constructor.

    Args:
      client_id: The Client ID as a string (e.g. "C.2f34cb70a2ae4c35").
      token: An ACL token.
    """
    self.client = None
    self.client_id = client_id
    self.token = token

  def ReadClientInfo(self):
    """Reads the client information.

    Raises:
      OSError: If the client operating system is not supported.
    """
    if not self.client:
      client_urn = aff4.ROOT_URN.Add(self.client_id)
      self.client = aff4.FACTORY.Open(client_urn, mode="r", token=self.token)
      self.system = self.client.Get(self.client.Schema.SYSTEM)
      os_version = self.client.Get(self.client.Schema.OS_VERSION)
      self.version = utils.SmartUnicode(os_version)

      # The OS version schema for Darwin should be similar to:
      # Darwin Kernel Version 10.8.0: Tue Jun 7 16:33:36 PDT 2011;
      # root:xnu-1504. 15.3~1/RELEASE_I386
      #
      # The OS version schema for Windows should be similar to:
      # 6.1.7600
      if self.system == "Darwin" or self.system == "Windows":
        if self.version:
          self.version = re.sub("^[^0-9]*([0-9]+[.][0-9]+[.][0-9]+).*$",
                                "\\1",
                                self.version)

      # The OS version schema for Linux should be similar to:
      # #77-Ubuntu SMP Tue 13 19:39:17 UTC 2011
      # but OR release contains
      # 2.6.32-35-generic
      # 2.6.38.8-gg621
      elif self.system == "Linux":
        self.version = utils.SmartUnicode(self.client.Get(
            self.client.Schema.OS_RELEASE))

        if self.version:
          self.version = re.sub("^[^0-9]*([0-9]+[.][0-9]+[.][0-9]+).*$",
                                "\\1",
                                self.version)

      else:
        raise OSError("Unsupported operating system: {0}".format(self.system))

      if self.version:
        self.major_version = re.sub("^([0-9]+).*$",
                                    "\\1",
                                    self.version)

  def GetPathSeparator(self):
    """Determine the client specific path separator.

    Returns:
      A Unicode string containing the client specific path separator.

    Raises:
      OSError: If the client operating system is not supported.
    """
    self.ReadClientInfo()

    if self.system == "Darwin" or self.system == "Linux":
      return u"/"

    elif self.system == "Windows":
      return u"\\"

    else:
      raise OSError("Unsupported operating system: {0}".format(self.system))

  def GetDefaultUsersPath(self):
    """Determine the client specific default users path.

    Returns:
      A Unicode string containing the client specific users path.

    Raises:
      OSError: If the client operating system is not supported.
    """
    self.ReadClientInfo()

    if self.system == "Darwin":
      return u"/Users"

    elif self.system == "Linux":
      return u"/home"

    elif self.system == "Windows":
      if self.major_version < self.MAJOR_VERSION_WINDOWS_VISTA:
        return u"C:\\Documents and Settings"
      else:
        return u"C:\\Users"

    else:
      raise OSError("Unsupported operating system: {0}".format(self.system))

  def GetHomeDirectory(self, username, domain=None):
    """Retrieve the client specific home directory of a specific user.

    The home directories are collected on Interrogate.

    Args:
      username: A string containing the username.
      domain: An optional string containing the domain name.
        This is currently only useful for Windows.

    Returns:
      A string containing the path to the user's home directory
      or None if no corresponding home directory could be found.

    Raises:
      OSError: If the client operating system is not supported.
    """
    self.ReadClientInfo()

    for user in self.client.Get(self.client.Schema.USER, []):
      if (user.username == username and
          (not domain or user.domain == domain)):
        return user.homedir

    return None
