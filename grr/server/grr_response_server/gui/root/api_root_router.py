#!/usr/bin/env python
"""API root router definition and default implementation.

Root router provides root-level access to GRR. It is not externally accessible
and must be accessed from a machine that runs GRR services directly (it runs
on top of a server bound to "localhost").
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_server.gui import api_call_router

from grr_response_server.gui.api_plugins import reflection as api_reflection
from grr_response_server.gui.api_plugins import user as api_user
from grr_response_server.gui.root.api_plugins import binary_management as api_binary_management
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
  def CreateGrrUser(self, args, token=None):
    return api_user_management.ApiCreateGrrUserHandler()

  @api_call_router.Category("User management")
  @api_call_router.ArgsType(api_user_management.ApiDeleteGrrUserArgs)
  @api_call_router.Http("DELETE", "/api/root/grr-users/<username>")
  def DeleteGrrUser(self, args, token=None):
    return api_user_management.ApiDeleteGrrUserHandler()

  @api_call_router.Category("User management")
  @api_call_router.ArgsType(api_user_management.ApiModifyGrrUserArgs)
  @api_call_router.ResultType(api_user.ApiGrrUser)
  @api_call_router.Http(
      "PATCH", "/api/root/grr-users/<username>", strip_root_types=False)
  def ModifyGrrUser(self, args, token=None):
    return api_user_management.ApiModifyGrrUserHandler()

  @api_call_router.Category("User management")
  @api_call_router.ArgsType(api_user_management.ApiListGrrUsersArgs)
  @api_call_router.ResultType(api_user_management.ApiListGrrUsersResult)
  @api_call_router.Http("GET", "/api/root/grr-users")
  def ListGrrUsers(self, args, token=None):
    return api_user_management.ApiListGrrUsersHandler()

  @api_call_router.Category("User management")
  @api_call_router.ArgsType(api_user_management.ApiGetGrrUserArgs)
  @api_call_router.ResultType(api_user.ApiGrrUser)
  @api_call_router.Http("GET", "/api/root/grr-users/<username>")
  def GetGrrUser(self, args, token=None):
    return api_user_management.ApiGetGrrUserHandler()

  # Binary management.
  # ====================
  #
  @api_call_router.Category("Binary management")
  @api_call_router.ArgsType(api_binary_management.ApiUploadGrrBinaryArgs)
  @api_call_router.Http("POST", "/api/root/grr-binaries/<type>/<path:path>")
  def UploadGrrBinary(self, args, token=None):
    return api_binary_management.ApiUploadGrrBinaryHandler()

  @api_call_router.Category("Binary management")
  @api_call_router.ArgsType(api_binary_management.ApiDeleteGrrBinaryArgs)
  @api_call_router.Http("DELETE", "/api/root/grr-binaries/<type>/<path:path>")
  def DeleteGrrBinary(self, args, token=None):
    return api_binary_management.ApiDeleteGrrBinaryHandler()

  # Reflection methiods (needed for client libraries to work).
  # ===========================================================
  #
  @api_call_router.Category("Reflection")
  @api_call_router.ResultType(api_reflection.ApiListApiMethodsResult)
  @api_call_router.Http("GET", "/api/reflection/api-methods")
  @api_call_router.NoAuditLogRequired()
  def ListApiMethods(self, args, token=None):
    return api_reflection.ApiListApiMethodsHandler(self)
