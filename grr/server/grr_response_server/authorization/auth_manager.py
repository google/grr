#!/usr/bin/env python
"""GRR authorization manager."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import logging


from future.utils import iterkeys
from future.utils import itervalues
import yaml

from grr_response_server.authorization import groups


class Error(Exception):
  """Base class for auth manager exception."""


class InvalidAuthorization(Error):
  """Used when an invalid authorization is defined."""


class InvalidSubject(Error):
  """Used when the subject wasn't registered before."""


class AuthorizationReader(object):
  """Helper class for reading authorization objects from YAML sources."""

  def __init__(self):
    super(AuthorizationReader, self).__init__()
    self.auth_objects = collections.OrderedDict()

  def CreateAuthorizations(self, yaml_data, auth_class):
    try:
      raw_list = list(yaml.safe_load_all(yaml_data))
    except (ValueError, yaml.YAMLError) as e:
      raise InvalidAuthorization("Invalid YAML: %s" % e)

    logging.debug("Adding %s authorizations", len(raw_list))
    for auth in raw_list:
      auth_object = auth_class(**auth)
      if auth_object.key in self.auth_objects:
        raise InvalidAuthorization(
            "Duplicate authorizations for %s" % auth_object.key)
      self.auth_objects[auth_object.key] = auth_object

  def GetAuthorizationForSubject(self, subject):
    if subject not in self.auth_objects:
      return None
    return self.auth_objects[subject]

  def GetAllAuthorizationObjects(self):
    return itervalues(self.auth_objects)

  # TODO(hanuszczak): This appears to be used only in tests. Maybe it should be
  # removed.
  def GetAuthSubjects(self):
    return iterkeys(self.auth_objects)


class AuthorizationManager(object):
  """Abstract class for authorization managers.

  This class provides standard ways to authorize users and groups for various
  types of access. Subclasses should implement Initialize to call AuthorizeUser
  and AuthorizeGroup as appropriate. To use group authorization you will need to
  implement groups.GroupAccess check group membership by querying the canonical
  source for group membership in your environment (AD, LDAP etc.).
  """

  def __init__(self, group_access_manager=None):
    self.authorized_users = collections.OrderedDict()
    self.group_access_manager = (group_access_manager or
                                 groups.CreateGroupAccessManager())
    self.Initialize()

  def Initialize(self):
    """Load authorizations.

    Subclasses may load their authorizations using this method.
    """

  def AuthorizeUser(self, user, subject):
    """Allow given user access to a given subject."""

    user_set = self.authorized_users.setdefault(subject, set())
    user_set.add(user)

  def AuthorizeGroup(self, group, subject):
    """Allow given group access to a given subject."""

    # Add the subject to the dict if is isn't present, so it will get checked in
    # CheckPermissions
    self.authorized_users.setdefault(subject, set())
    self.group_access_manager.AuthorizeGroup(group, subject)

  def DenyAll(self, subject):
    """Deny everybody access to a given subject."""

    self.authorized_users[subject] = set()

  def CheckPermissions(self, username, subject):
    """Checks if a given user has access to a given subject."""

    if subject in self.authorized_users:
      return ((username in self.authorized_users[subject]) or
              self.group_access_manager.MemberOfAuthorizedGroup(
                  username, subject))

    # In case the subject is not found, the safest thing to do is to raise.
    # It's up to the users of this class to handle this exception and
    # grant/not grant permissions to the user in question.
    raise InvalidSubject("Subject %s was not found." % subject)

  # TODO(hanuszczak): This appears to be used only in tests. Maybe it should be
  # removed.
  def GetAuthSubjects(self):
    return iterkeys(self.authorized_users)

  def HasAuthSubject(self, subject):
    return subject in self.authorized_users
