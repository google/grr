#!/usr/bin/env python
"""Tests for the SimpleAPIAuthManager."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from absl import app

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import compatibility
from grr_response_proto import tests_pb2
from grr_response_server.authorization import groups
from grr_response_server.gui import api_auth_manager
from grr_response_server.gui import api_call_router
from grr.test_lib import test_lib


class DummyAuthManagerTestApiRouter(api_call_router.ApiCallRouter):
  pass


class DummyAuthManagerTestApiRouter2(api_call_router.ApiCallRouter):
  pass


class DummyAuthManagerTestApiRouter3(api_call_router.ApiCallRouter):
  pass


class DefaultDummyAuthManagerTestApiRouter(api_call_router.ApiCallRouter):
  pass


class DummyAuthManagerTestConfigurableApiRouterParams(
    rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.DummyAuthManagerTestConfigurableApiRouterParams


class DummyAuthManagerTestConfigurableApiRouter(api_call_router.ApiCallRouter):
  params_type = DummyAuthManagerTestConfigurableApiRouterParams

  def __init__(self, params=None):
    super(DummyAuthManagerTestConfigurableApiRouter, self).__init__(
        params=params)
    self.params = params


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
    name = compatibility.GetName(DummyGroupAccessManager)
    config_overrider = test_lib.ConfigOverrider(
        {"ACL.group_access_manager_class": name})
    config_overrider.Start()
    self.addCleanup(config_overrider.Stop)

  def testMatchesIfOneOfUsersIsMatching(self):
    auth_mgr = api_auth_manager.APIAuthorizationManager.FromYaml(
        """
router: "DummyAuthManagerTestApiRouter"
users:
- "u1"
- "u2"
""", DefaultDummyAuthManagerTestApiRouter)

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.__class__, DummyAuthManagerTestApiRouter)

    router = auth_mgr.GetRouterForUser("u2")
    self.assertEqual(router.__class__, DummyAuthManagerTestApiRouter)

  def testReturnsDefaultOnNoMatchByUser(self):
    auth_mgr = api_auth_manager.APIAuthorizationManager.FromYaml(
        """
router: "DummyAuthManagerTestApiRouter"
users:
- "u1"
- "u2"
""", DefaultDummyAuthManagerTestApiRouter)

    router = auth_mgr.GetRouterForUser("u4")
    self.assertEqual(router.__class__, DefaultDummyAuthManagerTestApiRouter)

  def testMatchesFirstRouterIfMultipleRoutersMatchByUser(self):
    auth_mgr = api_auth_manager.APIAuthorizationManager.FromYaml(
        """
router: "DummyAuthManagerTestApiRouter"
users:
- "u1"
- "u3"
---
router: "DummyAuthManagerTestApiRouter2"
users:
- "u1"
- "u2"
""", DefaultDummyAuthManagerTestApiRouter)

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.__class__, DummyAuthManagerTestApiRouter)

  def testReturnsFirstRouterWhenMatchingByUser(self):
    auth_mgr = api_auth_manager.APIAuthorizationManager.FromYaml(
        """
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
""", DefaultDummyAuthManagerTestApiRouter)

    router = auth_mgr.GetRouterForUser("u2")
    self.assertEqual(router.__class__, DummyAuthManagerTestApiRouter2)

    router = auth_mgr.GetRouterForUser("u4")
    self.assertTrue(router.__class__, DummyAuthManagerTestApiRouter3)

  def testMatchingByGroupWorks(self):
    auth_mgr = api_auth_manager.APIAuthorizationManager.FromYaml(
        """
router: "DummyAuthManagerTestApiRouter2"
groups:
- "g1"
""", DefaultDummyAuthManagerTestApiRouter)

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.__class__, DummyAuthManagerTestApiRouter2)

  def testMatchingByUserHasPriorityOverMatchingByGroup(self):
    auth_mgr = api_auth_manager.APIAuthorizationManager.FromYaml(
        """
router: "DummyAuthManagerTestApiRouter"
users:
- "u1"
---
router: "DummyAuthManagerTestApiRouter2"
groups:
- "g1"
""", DefaultDummyAuthManagerTestApiRouter)

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.__class__, DummyAuthManagerTestApiRouter)

  def testReturnsFirstRouterWhenMultipleMatchByGroup(self):
    auth_mgr = api_auth_manager.APIAuthorizationManager.FromYaml(
        """
router: "DummyAuthManagerTestApiRouter"
groups:
- "g3"
---
router: "DummyAuthManagerTestApiRouter2"
groups:
- "g1"
""", DefaultDummyAuthManagerTestApiRouter)

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.__class__, DummyAuthManagerTestApiRouter)

  def testReturnsFirstMatchingRouterWhenItMatchesByGroupAndOtherByUser(self):
    auth_mgr = api_auth_manager.APIAuthorizationManager.FromYaml(
        """
router: "DummyAuthManagerTestApiRouter"
groups:
- "g3"
---
router: "DummyAuthManagerTestApiRouter2"
users:
- "u1"
""", DefaultDummyAuthManagerTestApiRouter)

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.__class__, DummyAuthManagerTestApiRouter)

  def testReturnsDefaultRouterWhenNothingMatchesByGroup(self):
    auth_mgr = api_auth_manager.APIAuthorizationManager.FromYaml(
        """
router: "DummyAuthManagerTestApiRouter"
groups:
- "g5"
---
router: "DummyAuthManagerTestApiRouter2"
groups:
- "g6"
""", DefaultDummyAuthManagerTestApiRouter)

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.__class__, DefaultDummyAuthManagerTestApiRouter)

  def testDefaultRouterIsReturnedIfNoAclsAreDefined(self):
    auth_mgr = api_auth_manager.APIAuthorizationManager(
        [], DefaultDummyAuthManagerTestApiRouter)

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.__class__, DefaultDummyAuthManagerTestApiRouter)

  def testRaisesWhenNonConfigurableRouterInitializedWithParams(self):
    exception = api_auth_manager.ApiCallRouterDoesNotExpectParameters
    with self.assertRaises(exception):
      api_auth_manager.APIAuthorizationManager.FromYaml(
          """
router: "DummyAuthManagerTestApiRouter"
router_params:
  foo: "Oh no!"
  bar: 42
users:
- "u1"
""", DefaultDummyAuthManagerTestApiRouter)

  def testConfigurableRouterIsInitializedWithoutParameters(self):
    auth_mgr = api_auth_manager.APIAuthorizationManager.FromYaml(
        """
router: "DummyAuthManagerTestConfigurableApiRouter"
users:
- "u1"
""", DefaultDummyAuthManagerTestApiRouter)

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.params.foo, "")
    self.assertEqual(router.params.bar, 0)

  def testConfigurableRouterIsInitializedWithParameters(self):
    auth_mgr = api_auth_manager.APIAuthorizationManager.FromYaml(
        """
router: "DummyAuthManagerTestConfigurableApiRouter"
router_params:
  foo: "Oh no!"
  bar: 42
users:
- "u1"
""", DefaultDummyAuthManagerTestApiRouter)

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.params.foo, "Oh no!")
    self.assertEqual(router.params.bar, 42)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
