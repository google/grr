#!/usr/bin/env python
"""GRR authorization manager."""



import abc
import logging
import yaml
from grr.lib.authorization import groups


class Error(Exception):
  """Base class for auth manager exception."""


class InvalidAuthorization(Error):
  """Used when an invalid authorization is defined."""


class AuthorizationManager(object):
  """Abstract class for authorization managers.

  This class provides standard ways to authorize users and groups for various
  types of access. Subclasses should implement Initialize to call AuthorizeUser
  and AuthorizeGroup as appropriate. To use group authorization you will need to
  implement groups.GroupAccess check group membership by querying the canonical
  source for group membership in your environment (AD, LDAP etc.).
  """

  def __init__(self):
    self.authorized_users = {}
    self.auth_objects = {}
    self.Initialize()

  @abc.abstractmethod
  def Initialize(self):
    """Load authorizations.

    Subclasses should load their authorizations using this method.
    """

  def AuthorizeUser(self, user, subject):
    user_set = self.authorized_users.setdefault(subject, set())
    user_set.add(user)

  def AuthorizeGroup(self, group, subject):
    # Add the subject to the dict if is isn't present, so it will get checked in
    # CheckPermissions
    self.authorized_users.setdefault(subject, set())
    groups.GROUP_ACCESS_MANAGER.AuthorizeGroup(group, subject)

  def DenyAll(self, subject):
    self.authorized_users[subject] = set()

  def UserIsAuthorized(self, username, subject):
    return username in self.authorized_users[subject]

  def CheckPermissions(self, username, subject):
    if subject in self.authorized_users:
      return self.UserIsAuthorized(
          username, subject) or (
              groups.GROUP_ACCESS_MANAGER.MemberOfAuthorizedGroup(
                  username, subject))
    return True

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
    return self.auth_objects.values()

  def GetAuthSubjects(self):
    return self.authorized_users.keys()

