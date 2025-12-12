#!/usr/bin/env python
"""Tests for the SimpleAPIAuthManager."""

from absl import app
from absl.testing import absltest
import yaml

from google.protobuf import json_format
from grr_response_proto import tests_pb2
from grr_response_server.authorization import groups
from grr_response_server.gui import api_auth_manager
from grr_response_server.gui import api_call_router
from grr_response_server.gui import api_test_lib
from grr.test_lib import test_lib


class DummyAuthManagerTestApiRouter(api_call_router.ApiCallRouter):
  pass


class DummyAuthManagerTestApiRouter2(api_call_router.ApiCallRouter):
  pass


class DummyAuthManagerTestApiRouter3(api_call_router.ApiCallRouter):
  pass


class DefaultDummyAuthManagerTestApiRouter(api_call_router.ApiCallRouter):
  pass


class DummyAuthManagerTestConfigurableApiRouterProto(
    api_call_router.ApiCallRouter
):
  proto_params_type = tests_pb2.DummyAuthManagerTestConfigurableApiRouterParams

  def __init__(self, params=None):
    super().__init__(params=params)
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
    super().setUp()

    # API ACLs are off by default, we need to set this to something so the tests
    # exercise the functionality. Each test will supply its own ACL data. We
    # also have to set up a default API router that will be used when none of
    # the rules matches.
    name = DummyGroupAccessManager.__name__
    config_overrider = test_lib.ConfigOverrider(
        {"ACL.group_access_manager_class": name}
    )
    config_overrider.Start()
    self.addCleanup(config_overrider.Stop)

  @api_test_lib.WithApiCallRouter(
      "DummyAuthManagerTestApiRouter", DummyAuthManagerTestApiRouter
  )
  def testMatchesIfOneOfUsersIsMatching(self):
    auth_mgr = api_auth_manager.APIAuthorizationManager.FromYaml(
        """
router: "DummyAuthManagerTestApiRouter"
users:
- "u1"
- "u2"
""",
        DefaultDummyAuthManagerTestApiRouter,
    )

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.__class__, DummyAuthManagerTestApiRouter)

    router = auth_mgr.GetRouterForUser("u2")
    self.assertEqual(router.__class__, DummyAuthManagerTestApiRouter)

  @api_test_lib.WithApiCallRouter(
      "DummyAuthManagerTestApiRouter", DummyAuthManagerTestApiRouter
  )
  def testReturnsDefaultOnNoMatchByUser(self):
    auth_mgr = api_auth_manager.APIAuthorizationManager.FromYaml(
        """
router: "DummyAuthManagerTestApiRouter"
users:
- "u1"
- "u2"
""",
        DefaultDummyAuthManagerTestApiRouter,
    )

    router = auth_mgr.GetRouterForUser("u4")
    self.assertEqual(router.__class__, DefaultDummyAuthManagerTestApiRouter)

  @api_test_lib.WithApiCallRouter(
      "DummyAuthManagerTestApiRouter", DummyAuthManagerTestApiRouter
  )
  @api_test_lib.WithApiCallRouter(
      "DummyAuthManagerTestApiRouter2", DummyAuthManagerTestApiRouter2
  )
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
""",
        DefaultDummyAuthManagerTestApiRouter,
    )

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.__class__, DummyAuthManagerTestApiRouter)

  @api_test_lib.WithApiCallRouter(
      "DummyAuthManagerTestApiRouter", DummyAuthManagerTestApiRouter
  )
  @api_test_lib.WithApiCallRouter(
      "DummyAuthManagerTestApiRouter2", DummyAuthManagerTestApiRouter2
  )
  @api_test_lib.WithApiCallRouter(
      "DummyAuthManagerTestApiRouter3", DummyAuthManagerTestApiRouter3
  )
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
""",
        DefaultDummyAuthManagerTestApiRouter,
    )

    router = auth_mgr.GetRouterForUser("u2")
    self.assertEqual(router.__class__, DummyAuthManagerTestApiRouter2)

    router = auth_mgr.GetRouterForUser("u4")
    self.assertEqual(router.__class__, DummyAuthManagerTestApiRouter3)

  @api_test_lib.WithApiCallRouter(
      "DummyAuthManagerTestApiRouter2", DummyAuthManagerTestApiRouter2
  )
  def testMatchingByGroupWorks(self):
    auth_mgr = api_auth_manager.APIAuthorizationManager.FromYaml(
        """
router: "DummyAuthManagerTestApiRouter2"
groups:
- "g1"
""",
        DefaultDummyAuthManagerTestApiRouter,
    )

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.__class__, DummyAuthManagerTestApiRouter2)

  @api_test_lib.WithApiCallRouter(
      "DummyAuthManagerTestApiRouter", DummyAuthManagerTestApiRouter
  )
  @api_test_lib.WithApiCallRouter(
      "DummyAuthManagerTestApiRouter2", DummyAuthManagerTestApiRouter2
  )
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
""",
        DefaultDummyAuthManagerTestApiRouter,
    )

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.__class__, DummyAuthManagerTestApiRouter)

  @api_test_lib.WithApiCallRouter(
      "DummyAuthManagerTestApiRouter", DummyAuthManagerTestApiRouter
  )
  @api_test_lib.WithApiCallRouter(
      "DummyAuthManagerTestApiRouter2", DummyAuthManagerTestApiRouter2
  )
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
""",
        DefaultDummyAuthManagerTestApiRouter,
    )

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.__class__, DummyAuthManagerTestApiRouter)

  @api_test_lib.WithApiCallRouter(
      "DummyAuthManagerTestApiRouter", DummyAuthManagerTestApiRouter
  )
  @api_test_lib.WithApiCallRouter(
      "DummyAuthManagerTestApiRouter2", DummyAuthManagerTestApiRouter2
  )
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
""",
        DefaultDummyAuthManagerTestApiRouter,
    )

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.__class__, DummyAuthManagerTestApiRouter)

  @api_test_lib.WithApiCallRouter(
      "DummyAuthManagerTestApiRouter", DummyAuthManagerTestApiRouter
  )
  @api_test_lib.WithApiCallRouter(
      "DummyAuthManagerTestApiRouter2", DummyAuthManagerTestApiRouter2
  )
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
""",
        DefaultDummyAuthManagerTestApiRouter,
    )

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.__class__, DefaultDummyAuthManagerTestApiRouter)

  def testDefaultRouterIsReturnedIfNoAclsAreDefined(self):
    auth_mgr = api_auth_manager.APIAuthorizationManager(
        [], DefaultDummyAuthManagerTestApiRouter
    )

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.__class__, DefaultDummyAuthManagerTestApiRouter)

  @api_test_lib.WithApiCallRouter(
      "DummyAuthManagerTestApiRouter", DummyAuthManagerTestApiRouter
  )
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
""",
          DefaultDummyAuthManagerTestApiRouter,
      )

  @api_test_lib.WithApiCallRouter(
      "DummyAuthManagerTestConfigurableApiRouterProto",
      DummyAuthManagerTestConfigurableApiRouterProto,
  )
  def testConfigurableRouterIsInitializedWithoutParameters(self):
    auth_mgr = api_auth_manager.APIAuthorizationManager.FromYaml(
        """
router: "DummyAuthManagerTestConfigurableApiRouterProto"
users:
- "u1"
""",
        DefaultDummyAuthManagerTestApiRouter,
    )

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.params.foo, "")
    self.assertEqual(router.params.bar, 0)

  @api_test_lib.WithApiCallRouter(
      "DummyAuthManagerTestConfigurableApiRouterProto",
      DummyAuthManagerTestConfigurableApiRouterProto,
  )
  def testConfigurableRouterIsInitializedWithParametersProtoAndTag(self):
    auth_mgr = api_auth_manager.APIAuthorizationManager.FromYaml(
        """
router: "DummyAuthManagerTestConfigurableApiRouterProto"
router_params:
  foo: "Oh no!"
  bar: 42
  # This router uses `proto_params_type` so it needs to either specify
  # the raw value directly or use the !duration_seconds tag.
  duration_s: !duration_seconds '1h'
users:
- "u1"
""",
        DummyAuthManagerTestConfigurableApiRouterProto,
    )

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.params.foo, "Oh no!")
    self.assertEqual(router.params.bar, 42)
    self.assertEqual(router.params.duration_s, 3600)

  @api_test_lib.WithApiCallRouter(
      "DummyAuthManagerTestConfigurableApiRouterProto",
      DummyAuthManagerTestConfigurableApiRouterProto,
  )
  def testConfigurableRouterIsInitializedWithParametersProtoWithoutTag(self):
    auth_mgr = api_auth_manager.APIAuthorizationManager.FromYaml(
        """
router: "DummyAuthManagerTestConfigurableApiRouterProto"
router_params:
  foo: "Oh no!"
  bar: 42
  # This router uses `proto_params_type` so it needs to either specify
  # the raw value directly or use the !duration_seconds tag.
  duration_s: 3600
users:
- "u1"
""",
        DummyAuthManagerTestConfigurableApiRouterProto,
    )

    router = auth_mgr.GetRouterForUser("u1")
    self.assertEqual(router.params.foo, "Oh no!")
    self.assertEqual(router.params.bar, 42)
    self.assertEqual(router.params.duration_s, 3600)

  @api_test_lib.WithApiCallRouter(
      "DummyAuthManagerTestConfigurableApiRouterProto",
      DummyAuthManagerTestConfigurableApiRouterProto,
  )
  def testConfigurableRouterIsInitializedWithParametersProtoBadInput(self):
    with self.assertRaises(json_format.ParseError):
      api_auth_manager.APIAuthorizationManager.FromYaml(
          """
router: "DummyAuthManagerTestConfigurableApiRouterProto"
router_params:
  foo: "Oh no!"
  bar: 42
  # This should fail because it's not a valid number and there's no tag.
  duration_s: '1h'
users:
- "u1"
""",
          DummyAuthManagerTestConfigurableApiRouterProto,
      )


class DurationSecondsYamlTagTest(absltest.TestCase):

  def testDurationSecondsYamlTag(self):
    yaml_data = """
duration_str_no_tag: '1h'
duration_str_tag: !duration_seconds '1h'
duration_number_no_tag: 42
duration_number_tag: !duration_seconds 42
duration_str_tag_second: !duration_seconds '1s'
duration_str_tag_minute: !duration_seconds '2m'
duration_str_tag_hour: !duration_seconds '3h'
duration_str_tag_day: !duration_seconds '4d'
duration_str_tag_week: !duration_seconds '5w'
"""
    loader = yaml.SafeLoader
    loader.add_constructor(
        "!duration_seconds", api_auth_manager.DurationSecondsYamlConstructor
    )
    parsed_yaml = list(yaml.load_all(yaml_data, Loader=loader))[0]
    self.assertEqual(parsed_yaml["duration_str_no_tag"], "1h")
    self.assertEqual(parsed_yaml["duration_str_tag"], 3600)
    self.assertEqual(parsed_yaml["duration_number_no_tag"], 42)
    self.assertEqual(parsed_yaml["duration_number_tag"], 42)
    self.assertEqual(parsed_yaml["duration_str_tag_second"], 1)
    self.assertEqual(parsed_yaml["duration_str_tag_minute"], 2 * 60)
    self.assertEqual(parsed_yaml["duration_str_tag_hour"], 3 * 60 * 60)
    self.assertEqual(parsed_yaml["duration_str_tag_day"], 4 * 24 * 60 * 60)
    self.assertEqual(parsed_yaml["duration_str_tag_week"], 5 * 7 * 24 * 60 * 60)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
