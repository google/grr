#!/usr/bin/env python
"""Tests for the SimpleAPIAuthManager."""

import __builtin__

import mock

from grr.gui import api_auth_manager
from grr.gui import api_call_router
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.authorization import groups


class DummyAuthManagerTestApiRouter(api_call_router.ApiCallRouter):
  pass


class DummyAuthManagerTestApiRouter2(api_call_router.ApiCallRouter):
  pass


class DummyAuthManagerTestApiRouter3(api_call_router.ApiCallRouter):
  pass


class DefaultDummyAuthManagerTestApiRouter(api_call_router.ApiCallRouter):
  pass


class DummyGroupAccessManager(groups.GroupAccessManager):

  def __init__(self):
    self.authorized_groups = {}
    self.positive_matches = {"u1": ["g1", "g3"]}

  def AuthorizeGroup(self, group, subject):
    self.authorized_groups.setdefault(subject, []).append(group)

  def MemberOfAuthorizedGroup(self, username, subject):
    try:
      group_names = self.positive_matches[username]
    except KeyError:
      return False

    for group_name in group_names:
      if group_name in self.authorized_groups[subject]:
        return True

    return False


class APIAuthorizationManagerTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(APIAuthorizationManagerTest, self).setUp()

    # API ACLs are off by default, we need to set this to something so the tests
    # exercise the functionality. Each test will supply its own ACL data. We
    # also have to set up a default API router that will be used when none of
    # the rules matches.
    self.config_overrider = test_lib.ConfigOverrider({
        "API.RouterACLConfigFile": "dummy",
        "API.DefaultRouter": DefaultDummyAuthManagerTestApiRouter.__name__,
        "ACL.group_access_manager_class": DummyGroupAccessManager.__name__
    })
    self.config_overrider.Start()

  def tearDown(self):
    super(APIAuthorizationManagerTest, self).tearDown()
    self.config_overrider.Stop()

  def testMatchesIfOneOfUsersIsMatching(self):
    acls = """
router: "DummyAuthManagerTestApiRouter"
users:
- "u1"
- "u2"
"""
    with mock.patch.object(__builtin__, "open", mock.mock_open(read_data=acls)):
      auth_mgr = api_auth_manager.APIAuthorizationManager()

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.__class__, DummyAuthManagerTestApiRouter)

    router = auth_mgr.GetRouterForUser("u2")
    self.assertEqual(router.__class__, DummyAuthManagerTestApiRouter)

  def testReturnsDefaultOnNoMatchByUser(self):
    acls = """
router: "DummyAuthManagerTestApiRouter"
users:
- "u1"
- "u2"
"""
    with mock.patch.object(__builtin__, "open", mock.mock_open(read_data=acls)):
      auth_mgr = api_auth_manager.APIAuthorizationManager()

    router = auth_mgr.GetRouterForUser("u4")
    self.assertEqual(router.__class__, DefaultDummyAuthManagerTestApiRouter)

  def testMatchesFirstRouterIfMultipleRoutersMatchByUser(self):
    acls = """
router: "DummyAuthManagerTestApiRouter"
users:
- "u1"
- "u3"
---
router: "DummyAuthManagerTestApiRouter2"
users:
- "u1"
- "u2"

"""
    with mock.patch.object(__builtin__, "open", mock.mock_open(read_data=acls)):
      auth_mgr = api_auth_manager.APIAuthorizationManager()

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.__class__, DummyAuthManagerTestApiRouter)

  def testReturnsFirstRouterWhenMatchingByUser(self):
    acls = """
router: "DummyAuthManagerTestApiRouter"
users:
- "u1"
- "u3"
---
router: "DummyAuthManagerTestApiRouter2"
users:
- "u1"
- "u2"
---
router: "DummyAuthManagerTestApiRouter3"
users:
- "u2"
- "u4"
"""
    with mock.patch.object(__builtin__, "open", mock.mock_open(read_data=acls)):
      auth_mgr = api_auth_manager.APIAuthorizationManager()

    router = auth_mgr.GetRouterForUser("u2")
    self.assertEqual(router.__class__, DummyAuthManagerTestApiRouter2)

    router = auth_mgr.GetRouterForUser("u4")
    self.assertTrue(router.__class__, DummyAuthManagerTestApiRouter3)

  def testMatchingByGroupWorks(self):
    acls = """
router: "DummyAuthManagerTestApiRouter2"
groups:
- "g1"
"""

    with mock.patch.object(__builtin__, "open", mock.mock_open(read_data=acls)):
      auth_mgr = api_auth_manager.APIAuthorizationManager()

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.__class__, DummyAuthManagerTestApiRouter2)

  def testMatchingByUserHasPriorityOverMatchingByGroup(self):
    acls = """
router: "DummyAuthManagerTestApiRouter"
users:
- "u1"
---
router: "DummyAuthManagerTestApiRouter2"
groups:
- "g1"
"""

    with mock.patch.object(__builtin__, "open", mock.mock_open(read_data=acls)):
      auth_mgr = api_auth_manager.APIAuthorizationManager()

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.__class__, DummyAuthManagerTestApiRouter)

  def testReturnsFirstRouterWhenMultipleMatchByGroup(self):
    acls = """
router: "DummyAuthManagerTestApiRouter"
groups:
- "g3"
---
router: "DummyAuthManagerTestApiRouter2"
groups:
- "g1"
"""

    with mock.patch.object(__builtin__, "open", mock.mock_open(read_data=acls)):
      auth_mgr = api_auth_manager.APIAuthorizationManager()

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.__class__, DummyAuthManagerTestApiRouter)

  def testReturnsFirstMatchingRouterWhenItMatchesByGroupAndOtherByUser(self):
    acls = """
router: "DummyAuthManagerTestApiRouter"
groups:
- "g3"
---
router: "DummyAuthManagerTestApiRouter2"
users:
- "u1"
"""

    with mock.patch.object(__builtin__, "open", mock.mock_open(read_data=acls)):
      auth_mgr = api_auth_manager.APIAuthorizationManager()

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.__class__, DummyAuthManagerTestApiRouter)

  def testReturnsDefaultRouterWhenNothingMatchesByGroup(self):
    acls = """
router: "DummyAuthManagerTestApiRouter"
groups:
- "g5"
---
router: "DummyAuthManagerTestApiRouter2"
groups:
- "g6"
"""
    with mock.patch.object(__builtin__, "open", mock.mock_open(read_data=acls)):
      auth_mgr = api_auth_manager.APIAuthorizationManager()

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.__class__, DefaultDummyAuthManagerTestApiRouter)

  def testDefaultRouterIsReturnedIfNoConfigFileDefined(self):
    """The default router is returned if no API.RouterACLConfigFile defined."""
    with test_lib.ConfigOverrider({"API.RouterACLConfigFile": ""}):
      auth_mgr = api_auth_manager.APIAuthorizationManager()
      router = auth_mgr.GetRouterForUser("u1")
      self.assertEqual(router.__class__, DefaultDummyAuthManagerTestApiRouter)


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
