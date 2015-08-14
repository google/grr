#!/usr/bin/env python
"""Tests for the SimpleAPIAuthManager."""

import __builtin__

import mock

from grr.gui import api_auth_manager
from grr.gui import api_call_renderers
from grr.lib import access_control
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.rdfvalues import test_base


class SimpleAPIAuthorizationManagerTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(SimpleAPIAuthorizationManagerTest, self).setUp()
    self.mock_renderer = mock.MagicMock()
    self.mock_renderer.enabled_by_default = True
    self.mock_renderer.__class__.__name__ = "ApiCallRenderer"
    # API ACLs are off by default, we need to set this to something so the tests
    # exercise the functionality. Each test will supply its own ACL data.
    self.aclfile_overrider = test_lib.ConfigOverrider({
        "API.RendererACLFile": "dummy"})
    self.aclfile_overrider.Start()

  def tearDown(self):
    super(SimpleAPIAuthorizationManagerTest, self).tearDown()
    self.aclfile_overrider.Stop()

  def testSimpleAPIAuthorizationManager(self):
    acls = """
renderer: "ApiCallRenderer"
users:
- "u1"
- "u2"
"""
    with mock.patch.object(__builtin__, "open", mock.mock_open(read_data=acls)):
      auth_mgr = api_auth_manager.SimpleAPIAuthorizationManager()

    auth_mgr.CheckAccess(self.mock_renderer, "u1")
    auth_mgr.CheckAccess(self.mock_renderer, "u2")
    with self.assertRaises(access_control.UnauthorizedAccess):
      auth_mgr.CheckAccess(self.mock_renderer, "u4")

  def testDenyAll(self):
    acls = """
renderer: "ApiCallRenderer"
"""
    with mock.patch.object(__builtin__, "open", mock.mock_open(read_data=acls)):
      auth_mgr = api_auth_manager.SimpleAPIAuthorizationManager()

    with self.assertRaises(access_control.UnauthorizedAccess):
      auth_mgr.CheckAccess(self.mock_renderer, "u1")

  def testNoACLs(self):
    """All checking is skipped if no API.RendererACLFile is defined."""
    with test_lib.ConfigOverrider({"API.RendererACLFile": ""}):
      auth_mgr = api_auth_manager.SimpleAPIAuthorizationManager()
      auth_mgr.CheckAccess(self.mock_renderer, "u1")
      bad_renderer = mock.MagicMock()
      bad_renderer.enabled_by_default = True
      bad_renderer.__class__.__name__ = "BadRenderer"
      auth_mgr.CheckAccess(bad_renderer, "u2")

  def testRaiseIfGroupsDefined(self):
    """We have no way to expand groups, so raise if defined."""
    acls = """
renderer: "ApiCallRenderer"
groups: ["g1"]
"""
    with mock.patch.object(__builtin__, "open", mock.mock_open(read_data=acls)):
      with self.assertRaises(NotImplementedError):
        api_auth_manager.SimpleAPIAuthorizationManager()

  def testHandleApiCallNotEnabled(self):
    """Raises if no matching ACL and enabled_by_default=False."""
    with test_lib.ConfigOverrider({"API.RendererACLFile": ""}):
      auth_mgr = api_auth_manager.SimpleAPIAuthorizationManager()
      self.mock_renderer.enabled_by_default = False
      with mock.patch.object(api_call_renderers, "API_AUTH_MGR", auth_mgr):
        with self.assertRaises(access_control.UnauthorizedAccess):
          api_call_renderers.HandleApiCall(self.mock_renderer, "",
                                           token=self.token)

  def testHandleApiCallNotEnabledWithACL(self):
    """Matching ACL and enabled_by_default=False is allowed."""
    acls = """
renderer: "ApiCallRenderer"
users:
- "test"
"""
    with mock.patch.object(__builtin__, "open", mock.mock_open(read_data=acls)):
      auth_mgr = api_auth_manager.SimpleAPIAuthorizationManager()

    self.mock_renderer.enabled_by_default = False
    with mock.patch.object(api_call_renderers, "API_AUTH_MGR", auth_mgr):
      api_call_renderers.HandleApiCall(self.mock_renderer, "", token=self.token)

    self.mock_renderer.Render.assert_called_once_with("", token=self.token)


class APIAuthorizationImporterTest(test_lib.GRRBaseTest):

  def testACLs(self):
    acls = """
renderer: "ApiCallRenderer"
users:
  - "u1"
  - "u2"
groups: ["g1"]
"""
    acl_mgr = api_auth_manager.APIAuthorizationImporter()
    acl_mgr.CreateACLs(acls)
    self.assertItemsEqual(acl_mgr.acl_dict["ApiCallRenderer"].users,
                          ["u1", "u2"])
    self.assertItemsEqual(acl_mgr.acl_dict["ApiCallRenderer"].groups, ["g1"])

  def testRaiseOnDuplicateACLs(self):
    acls = """
renderer: "ApiCallRenderer"
users:
  - "u1"
  - "u2"
groups: ["g1"]
---
renderer: "ApiCallRenderer"
users: ["u3"]
"""

    acl_mgr = api_auth_manager.APIAuthorizationImporter()
    with self.assertRaises(api_auth_manager.InvalidAPIAuthorization):
      acl_mgr.CreateACLs(acls)


class APIAuthorizationTest(test_base.RDFValueTestCase):
  rdfvalue_class = api_auth_manager.APIAuthorization

  def GenerateSample(self, number=0):
    return api_auth_manager.APIAuthorization(renderer="ApiCallRenderer",
                                             users=["user%s" % number])

  def testACLValidation(self):
    api_auth_manager.APIAuthorization(
        renderer="ApiCallRenderer",
        users=["u1", "u2"], groups=["g1", "g2"])

    api_auth_manager.APIAuthorization(
        renderer="ApiCallRenderer")

  def testACLValidationBadRenderer(self):
    acls = """
renderer: "Bad"
users:
- "u1"
- "u2"
"""
    with test_lib.ConfigOverrider({"API.RendererACLFile": "somefile"}):
      with self.assertRaises(api_call_renderers.ApiCallRendererNotFoundError):
        with mock.patch.object(__builtin__, "open",
                               mock.mock_open(read_data=acls)):
          api_call_renderers.APIACLInit().RunOnce()

  def testACLValidationBadUsers(self):
    with self.assertRaises(api_auth_manager.InvalidAPIAuthorization):
      api_auth_manager.APIAuthorization(
          renderer="ApiCallRenderer",
          users="u1", groups=["g1"])

  def testACLValidationBadGroups(self):
    with self.assertRaises(api_auth_manager.InvalidAPIAuthorization):
      api_auth_manager.APIAuthorization(
          renderer="ApiCallRenderer",
          users=["u1"], groups="g1")


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
