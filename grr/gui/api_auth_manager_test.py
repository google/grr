#!/usr/bin/env python
"""Tests for the SimpleAPIAuthManager."""

import __builtin__

import mock

from grr.gui import api_auth_manager
from grr.gui import api_call_router
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.rdfvalues import test_base


class DummyAuthManagerTestApiRouter(api_call_router.ApiCallRouter):
  pass


class APIAuthorizationManagerTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(APIAuthorizationManagerTest, self).setUp()

    # API ACLs are off by default, we need to set this to something so the tests
    # exercise the functionality. Each test will supply its own ACL data. We
    # also have to set up a default API router that will be used when none of
    # the rules matches.
    self.config_overrider = test_lib.ConfigOverrider({
        "API.RouterACLConfigFile": "dummy",
        "API.DefaultRouter": api_call_router.DisabledApiCallRouter.__name__})
    self.config_overrider.Start()

  def tearDown(self):
    super(APIAuthorizationManagerTest, self).tearDown()
    self.config_overrider.Stop()

  def testAPIAuthorizationManager(self):
    acls = """
router: "DummyAuthManagerTestApiRouter"
users:
- "u1"
- "u2"
"""
    with mock.patch.object(__builtin__, "open", mock.mock_open(read_data=acls)):
      auth_mgr = api_auth_manager.APIAuthorizationManager().Initialize()

    router = auth_mgr.GetRouterForUser("u1")
    self.assertTrue(router.__class__ == DummyAuthManagerTestApiRouter)

    router = auth_mgr.GetRouterForUser("u2")
    self.assertTrue(router.__class__ == DummyAuthManagerTestApiRouter)

    router = auth_mgr.GetRouterForUser("u4")
    self.assertTrue(router.__class__ == api_call_router.DisabledApiCallRouter)

  def testDenyAll(self):
    acls = """
router: "DummyAuthManagerTestApiRouter"
"""
    with mock.patch.object(__builtin__, "open", mock.mock_open(read_data=acls)):
      auth_mgr = api_auth_manager.APIAuthorizationManager().Initialize()

    router = auth_mgr.GetRouterForUser("u1")
    self.assertTrue(router.__class__ == api_call_router.DisabledApiCallRouter)

  def testDefaultRouterIsReturnedIfNoConfigFileDefined(self):
    """The default router is returned if no API.RouterACLConfigFile defined."""
    with test_lib.ConfigOverrider({"API.RouterACLConfigFile": ""}):
      auth_mgr = api_auth_manager.APIAuthorizationManager().Initialize()
      router = auth_mgr.GetRouterForUser("u1")
      self.assertTrue(router.__class__ == api_call_router.DisabledApiCallRouter)

  def testRaiseIfGroupsDefined(self):
    """We have no way to expand groups, so raise if defined."""
    acls = """
router: "DummyAuthManagerTestApiRouter"
groups: ["g1"]
"""
    with mock.patch.object(__builtin__, "open", mock.mock_open(read_data=acls)):
      with self.assertRaises(NotImplementedError):
        api_auth_manager.APIAuthorizationManager().Initialize()


class APIAuthorizationTest(test_base.RDFValueTestCase):
  rdfvalue_class = api_auth_manager.APIAuthorization

  def GenerateSample(self, number=0):
    return api_auth_manager.APIAuthorization(
        router="DummyAuthManagerTestApiRouter",
        users=["user%s" % number])

  def testACLValidation(self):
    api_auth_manager.APIAuthorization(
        router="DummyAuthManagerTestApiRouter",
        users=["u1", "u2"], groups=["g1", "g2"])

    api_auth_manager.APIAuthorization(
        router="DummyAuthManagerTestApiRouter")

  def testACLValidationBadRouter(self):
    acls = """
router: "Bad"
users:
- "u1"
- "u2"
"""
    with test_lib.ConfigOverrider({"API.RouterACLConfigFile": "somefile"}):
      with self.assertRaises(api_auth_manager.ApiCallRouterNotFoundError):
        with mock.patch.object(__builtin__, "open",
                               mock.mock_open(read_data=acls)):
          api_auth_manager.APIACLInit.InitApiAuthManager()

  def testACLValidationBadUsers(self):
    with self.assertRaises(api_auth_manager.InvalidAPIAuthorization):
      api_auth_manager.APIAuthorization(
          router="DummyAuthManagerTestApiRouter",
          users="u1", groups=["g1"])

  def testACLValidationBadGroups(self):
    with self.assertRaises(api_auth_manager.InvalidAPIAuthorization):
      api_auth_manager.APIAuthorization(
          router="DummyAuthManagerTestApiHandler",
          users=["u1"], groups="g1")


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
