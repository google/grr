#!/usr/bin/env python
"""Group authorization checking."""



import logging

from grr.lib import config_lib
from grr.lib import registry


class GroupAccessRegistry(object):
  __metaclass__ = registry.MetaclassRegistry


class NoGroupAccess(GroupAccessRegistry):
  """Placeholder class for enabling group ACLs.

  By default GRR doesn't have the concept of groups. To add it, override this
  class with a module in lib/local/groups.py that inherits from the same
  superclass. This class should be able to check group membership in whatever
  system you use: LDAP/AD/etc.
  """

  def AuthorizeGroup(self, group, subject):
    raise NotImplementedError("Replace this class to use group authorizations.")

  # pylint: disable=unused-argument
  def MemberOfAuthorizedGroup(self, username, subject):
    return False
  # pylint: enable=unused-argument


# Set in GroupAccessManagerInit
GROUP_ACCESS_MANAGER = None


class GroupAccessManagerInit(registry.InitHook):
  pre = ["StatsInit"]

  def RunOnce(self):
    global GROUP_ACCESS_MANAGER
    group_mgr_cls = config_lib.CONFIG["ACL.group_access_manager_class"]
    logging.debug("Using group access manager: %s", group_mgr_cls)
    GROUP_ACCESS_MANAGER = GroupAccessRegistry.classes[
        group_mgr_cls]()
