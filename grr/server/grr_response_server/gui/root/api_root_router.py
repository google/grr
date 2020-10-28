#!/usr/bin/env python
# Lint as: python3
"""API root router definition and default implementation.

Root router provides root-level access to GRR. It is not externally accessible
and must be accessed from a machine that runs GRR services directly (it runs
on top of a server bound to "localhost").
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import Optional

from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_router

from grr_response_server.gui.api_plugins import metadata as api_metadata
from grr_response_server.gui.api_plugins import reflection as api_reflection
from grr_response_server.gui.api_plugins import user as api_user
from grr_response_server.gui.root.api_plugins import binary_management as api_binary_management
from grr_response_server.gui.root.api_plugins import client_management as api_client_management
from grr_response_server.gui.root.api_plugins import user_management as api_user_management


class ApiRootRouter(api_call_router.ApiCallRouter):
  """Root router definition."""

  # User management.
  # ================
  #
  @api_call_router.Category("User management")
  @api_call_router.ArgsType(api_user_management.ApiCreateGrrUserArgs)
  @api_call_router.ResultType(api_user.ApiGrrUser)
  @api_call_router.Http("POST", "/api/root/grr-users", strip_root_types=False)
  def CreateGrrUser(self, args, context=None):
    return api_user_management.ApiCreateGrrUserHandler()

  @api_call_router.Category("User management")
  @api_call_router.ArgsType(api_user_management.ApiDeleteGrrUserArgs)
  @api_call_router.Http("DELETE", "/api/root/grr-users/<username>")
  def DeleteGrrUser(self, args, context=None):
    return api_user_management.ApiDeleteGrrUserHandler()

  @api_call_router.Category("User management")
  @api_call_router.ArgsType(api_user_management.ApiModifyGrrUserArgs)
  @api_call_router.ResultType(api_user.ApiGrrUser)
  @api_call_router.Http(
      "PATCH", "/api/root/grr-users/<username>", strip_root_types=False)
  def ModifyGrrUser(self, args, context=None):
    return api_user_management.ApiModifyGrrUserHandler()

  @api_call_router.Category("User management")
  @api_call_router.ArgsType(api_user_management.ApiListGrrUsersArgs)
  @api_call_router.ResultType(api_user_management.ApiListGrrUsersResult)
  @api_call_router.Http("GET", "/api/root/grr-users")
  def ListGrrUsers(self, args, context=None):
    return api_user_management.ApiListGrrUsersHandler()

  @api_call_router.Category("User management")
  @api_call_router.ArgsType(api_user_management.ApiGetGrrUserArgs)
  @api_call_router.ResultType(api_user.ApiGrrUser)
  @api_call_router.Http("GET", "/api/root/grr-users/<username>")
  def GetGrrUser(self, args, context=None):
    return api_user_management.ApiGetGrrUserHandler()

  # Binary management.
  # ====================
  #
  @api_call_router.Category("Binary management")
  @api_call_router.ArgsType(api_binary_management.ApiUploadGrrBinaryArgs)
  @api_call_router.Http("POST", "/api/root/grr-binaries/<type>/<path:path>")
  def UploadGrrBinary(self, args, context=None):
    return api_binary_management.ApiUploadGrrBinaryHandler()

  @api_call_router.Category("Binary management")
  @api_call_router.ArgsType(api_binary_management.ApiDeleteGrrBinaryArgs)
  @api_call_router.Http("DELETE", "/api/root/grr-binaries/<type>/<path:path>")
  def DeleteGrrBinary(self, args, context=None):
    return api_binary_management.ApiDeleteGrrBinaryHandler()

  # Client management.
  # ====================
  #
  @api_call_router.Category("Client management")
  @api_call_router.ArgsType(api_client_management.ApiKillFleetspeakArgs)
  @api_call_router.Http("PATCH", "/api/root/client/<client_id>/fleetspeak/kill")
  def KillFleetspeak(self, args, context=None):
    return api_client_management.ApiKillFleetspeakHandler()

  @api_call_router.Category("Client management")
  @api_call_router.ArgsType(
      api_client_management.ApiRestartFleetspeakGrrServiceArgs)
  @api_call_router.Http("PATCH",
                        "/api/root/client/<client_id>/fleetspeak/grr/restart")
  def RestartFleetspeakGrrService(self, args, context=None):
    return api_client_management.ApiRestartFleetspeakGrrServiceHandler()

  # Reflection methiods (needed for client libraries to work).
  # ===========================================================
  #
  @api_call_router.Category("Reflection")
  @api_call_router.ResultType(api_reflection.ApiListApiMethodsResult)
  @api_call_router.Http("GET", "/api/reflection/api-methods")
  @api_call_router.NoAuditLogRequired()
  def ListApiMethods(self, args, context=None):
    return api_reflection.ApiListApiMethodsHandler(self)

  # Metadata methods.
  # ===========================================================
  #
  @api_call_router.Category("Metadata")
  @api_call_router.ResultType(api_metadata.ApiGetOpenApiDescriptionResult)
  @api_call_router.Http("GET", "/api/metadata/openapi")
  @api_call_router.NoAuditLogRequired()
  def GetOpenApiDescription(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_metadata.ApiGetOpenApiDescriptionHandler:
    return api_metadata.ApiGetOpenApiDescriptionHandler(self)
