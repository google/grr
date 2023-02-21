#!/usr/bin/env python
"""Register all available api calls."""

from grr_response_server.gui import api_call_robot_router
from grr_response_server.gui import api_call_router
from grr_response_server.gui import api_call_router_registry
from grr_response_server.gui import api_call_router_with_approval_checks
from grr_response_server.gui import api_call_router_without_checks
from grr_response_server.gui import api_labels_restricted_call_router
from grr_response_server.gui.root import api_root_router


def RegisterApiCallRouters():
  """Registers all API call routers."""

  # keep-sorted start block=yes
  api_call_router_registry.RegisterApiCallRouter(
      "ApiCallRobotRouter", api_call_robot_router.ApiCallRobotRouter)
  api_call_router_registry.RegisterApiCallRouter(
      "ApiCallRouterStub", api_call_router.ApiCallRouterStub)
  api_call_router_registry.RegisterApiCallRouter(
      "ApiCallRouterWithApprovalChecks",
      api_call_router_with_approval_checks.ApiCallRouterWithApprovalChecks)
  api_call_router_registry.RegisterApiCallRouter(
      "ApiCallRouterWithApprovalChecksWithRobotAccess",
      api_call_router_with_approval_checks
      .ApiCallRouterWithApprovalChecksWithRobotAccess)
  api_call_router_registry.RegisterApiCallRouter(
      "ApiCallRouterWithApprovalChecksWithoutRobotAccess",
      api_call_router_with_approval_checks
      .ApiCallRouterWithApprovalChecksWithoutRobotAccess)
  api_call_router_registry.RegisterApiCallRouter(
      "ApiCallRouterWithoutChecks",
      api_call_router_without_checks.ApiCallRouterWithoutChecks)
  api_call_router_registry.RegisterApiCallRouter(
      "ApiLabelsRestrictedCallRouter",
      api_labels_restricted_call_router.ApiLabelsRestrictedCallRouter)
  api_call_router_registry.RegisterApiCallRouter("ApiRootRouter",
                                                 api_root_router.ApiRootRouter)
  api_call_router_registry.RegisterApiCallRouter(
      "DisabledApiCallRouter", api_call_router.DisabledApiCallRouter)
  # keep-sorted end
