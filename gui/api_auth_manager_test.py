#!/usr/bin/env python
"""Tests for the SimpleAPIAuthManager."""

import __builtin__

import mock

from grr.gui import api_auth_manager
from grr.gui import api_call_handler_base
from grr.gui import api_call_handlers
from grr.lib import access_control
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.rdfvalues import test_base


class DummyAuthManagerTestApiHandler(api_call_handler_base.ApiCallHandler):
  pass


class APIAuthorizationManagerTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(APIAuthorizationManagerTest, self).setUp()
    self.mock_handler = DummyAuthManagerTestApiHandler()
    self.mock_handler.enabled_by_default = True

    # API ACLs are off by default, we need to set this to something so the tests
    # exercise the functionality. Each test will supply its own ACL data.
    self.aclfile_overrider = test_lib.ConfigOverrider({
        "API.HandlerACLFile": "dummy"})
    self.aclfile_overrider.Start()

  def tearDown(self):
    super(APIAuthorizationManagerTest, self).tearDown()
    self.aclfile_overrider.Stop()

  def testAPIAuthorizationManager(self):
    acls = """
handler: "DummyAuthManagerTestApiHandler"
users:
- "u1"
- "u2"
"""
    with mock.patch.object(__builtin__, "open", mock.mock_open(read_data=acls)):
      auth_mgr = api_auth_manager.APIAuthorizationManager()

    auth_mgr.CheckAccess(self.mock_handler, "u1")
    auth_mgr.CheckAccess(self.mock_handler, "u2")
    with self.assertRaises(access_control.UnauthorizedAccess):
      auth_mgr.CheckAccess(self.mock_handler, "u4")

  def testDenyAll(self):
    acls = """
handler: "DummyAuthManagerTestApiHandler"
"""
    with mock.patch.object(__builtin__, "open", mock.mock_open(read_data=acls)):
      auth_mgr = api_auth_manager.APIAuthorizationManager()

    with self.assertRaises(access_control.UnauthorizedAccess):
      auth_mgr.CheckAccess(self.mock_handler, "u1")

  def testNoACLs(self):
    """All checking is skipped if no API.HandlerACLFile is defined."""
    with test_lib.ConfigOverrider({"API.HandlerACLFile": ""}):
      auth_mgr = api_auth_manager.APIAuthorizationManager()
      auth_mgr.CheckAccess(self.mock_handler, "u1")
      bad_handler = mock.MagicMock()
      bad_handler.enabled_by_default = True
      bad_handler.__class__.__name__ = "BadHandler"
      auth_mgr.CheckAccess(bad_handler, "u2")

  def testRaiseIfGroupsDefined(self):
    """We have no way to expand groups, so raise if defined."""
    acls = """
handler: "DummyAuthManagerTestApiHandler"
groups: ["g1"]
"""
    with mock.patch.object(__builtin__, "open", mock.mock_open(read_data=acls)):
      with self.assertRaises(NotImplementedError):
        api_auth_manager.APIAuthorizationManager()

  def testHandleApiCallNotEnabled(self):
    """Raises if no matching ACL and enabled_by_default=False."""
    with test_lib.ConfigOverrider({"API.HandlerACLFile": ""}):
      auth_mgr = api_auth_manager.APIAuthorizationManager()
      self.mock_handler.enabled_by_default = False
      with mock.patch.object(api_call_handlers, "API_AUTH_MGR", auth_mgr):
        with self.assertRaises(access_control.UnauthorizedAccess):
          api_call_handlers.HandleApiCall(self.mock_handler, "",
                                          token=self.token)

  def testHandleApiCallNotEnabledWithACL(self):
    """Matching ACL and enabled_by_default=False is allowed."""
    acls = """
handler: "DummyAuthManagerTestApiHandler"
users:
- "test"
"""
    with mock.patch.object(__builtin__, "open", mock.mock_open(read_data=acls)):
      auth_mgr = api_auth_manager.APIAuthorizationManager()

    self.mock_handler.enabled_by_default = False

    with mock.patch.object(api_call_handlers, "API_AUTH_MGR", auth_mgr):
      with mock.patch.object(self.mock_handler, "Handle"):
        self.mock_handler.Handle.return_value = None

        api_call_handlers.HandleApiCall(self.mock_handler, None,
                                        token=self.token)

        self.mock_handler.Handle.assert_called_once_with(None, token=self.token)


class APIAuthorizationTest(test_base.RDFValueTestCase):
  rdfvalue_class = api_auth_manager.APIAuthorization

  def GenerateSample(self, number=0):
    return api_auth_manager.APIAuthorization(
        handler="DummyAuthManagerTestApiHandler",
        users=["user%s" % number])

  def testACLValidation(self):
    api_auth_manager.APIAuthorization(
        handler="DummyAuthManagerTestApiHandler",
        users=["u1", "u2"], groups=["g1", "g2"])

    api_auth_manager.APIAuthorization(
        handler="DummyAuthManagerTestApiHandler")

  def testACLValidationBadHandler(self):
    acls = """
handler: "Bad"
users:
- "u1"
- "u2"
"""
    with test_lib.ConfigOverrider({"API.HandlerACLFile": "somefile"}):
      with self.assertRaises(api_call_handlers.ApiCallHandlerNotFoundError):
        with mock.patch.object(__builtin__, "open",
                               mock.mock_open(read_data=acls)):
          api_call_handlers.APIACLInit().RunOnce()

  def testACLValidationBadUsers(self):
    with self.assertRaises(api_auth_manager.InvalidAPIAuthorization):
      api_auth_manager.APIAuthorization(
          handler="DummyAuthManagerTestApiHandler",
          users="u1", groups=["g1"])

  def testACLValidationBadGroups(self):
    with self.assertRaises(api_auth_manager.InvalidAPIAuthorization):
      api_auth_manager.APIAuthorization(
          handler="DummyAuthManagerTestApiHandler",
          users=["u1"], groups="g1")


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
