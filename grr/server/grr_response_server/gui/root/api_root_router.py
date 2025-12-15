#!/usr/bin/env python
"""API root router definition and default implementation.

Root router provides root-level access to GRR. It is not externally accessible
and must be accessed from a machine that runs GRR services directly (it runs
on top of a server bound to "localhost").
"""

from typing import Optional

from grr_response_proto.api import metadata_pb2 as api_metadata_pb2
from grr_response_proto.api import reflection_pb2 as api_reflection_pb2
from grr_response_proto.api import signed_commands_pb2 as api_signed_commands_pb2
from grr_response_proto.api import user_pb2 as api_user_pb2
from grr_response_proto.api.root import binary_management_pb2
from grr_response_proto.api.root import user_management_pb2
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_router
from grr_response_server.gui.api_plugins import metadata as api_metadata
from grr_response_server.gui.api_plugins import reflection as api_reflection
from grr_response_server.gui.api_plugins import signed_commands as api_signed_commands
from grr_response_server.gui.root.api_plugins import binary_management as api_binary_management
from grr_response_server.gui.root.api_plugins import user_management as api_user_management


class ApiRootRouter(api_call_router.ApiCallRouter):
  """Root router definition."""

  # User management.
  # ================
  #
  @api_call_router.Category("User management")
  @api_call_router.ProtoArgsType(user_management_pb2.ApiCreateGrrUserArgs)
  @api_call_router.ProtoResultType(api_user_pb2.ApiGrrUser)
  @api_call_router.Http("POST", "/api/v2/root/grr-users")
  def CreateGrrUser(
      self,
      args: user_management_pb2.ApiCreateGrrUserArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user_management.ApiCreateGrrUserHandler:
    return api_user_management.ApiCreateGrrUserHandler()

  @api_call_router.Category("User management")
  @api_call_router.ProtoArgsType(user_management_pb2.ApiDeleteGrrUserArgs)
  @api_call_router.Http("DELETE", "/api/v2/root/grr-users/<username>")
  def DeleteGrrUser(
      self,
      args: user_management_pb2.ApiDeleteGrrUserArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user_management.ApiDeleteGrrUserHandler:
    return api_user_management.ApiDeleteGrrUserHandler()

  @api_call_router.Category("User management")
  @api_call_router.ProtoArgsType(user_management_pb2.ApiModifyGrrUserArgs)
  @api_call_router.ProtoResultType(api_user_pb2.ApiGrrUser)
  @api_call_router.Http("PATCH", "/api/v2/root/grr-users/<username>")
  def ModifyGrrUser(
      self,
      args: user_management_pb2.ApiModifyGrrUserArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user_management.ApiModifyGrrUserHandler:
    return api_user_management.ApiModifyGrrUserHandler()

  @api_call_router.Category("User management")
  @api_call_router.ProtoArgsType(user_management_pb2.ApiListGrrUsersArgs)
  @api_call_router.ProtoResultType(user_management_pb2.ApiListGrrUsersResult)
  @api_call_router.Http("GET", "/api/v2/root/grr-users")
  def ListGrrUsers(
      self,
      args: user_management_pb2.ApiListGrrUsersArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user_management.ApiListGrrUsersHandler:
    return api_user_management.ApiListGrrUsersHandler()

  @api_call_router.Category("User management")
  @api_call_router.ProtoArgsType(user_management_pb2.ApiGetGrrUserArgs)
  @api_call_router.ProtoResultType(api_user_pb2.ApiGrrUser)
  @api_call_router.Http("GET", "/api/v2/root/grr-users/<username>")
  def GetGrrUser(
      self,
      args: user_management_pb2.ApiGetGrrUserArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user_management.ApiGetGrrUserHandler:
    return api_user_management.ApiGetGrrUserHandler()

  # Binary management.
  # ====================
  #
  @api_call_router.Category("Binary management")
  @api_call_router.ProtoArgsType(binary_management_pb2.ApiUploadGrrBinaryArgs)
  @api_call_router.Http("POST", "/api/v2/root/grr-binaries/<type>/<path:path>")
  def UploadGrrBinary(
      self,
      args: binary_management_pb2.ApiUploadGrrBinaryArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_binary_management.ApiUploadGrrBinaryHandler:
    return api_binary_management.ApiUploadGrrBinaryHandler()

  @api_call_router.Category("Binary management")
  @api_call_router.ProtoArgsType(binary_management_pb2.ApiDeleteGrrBinaryArgs)
  @api_call_router.Http(
      "DELETE", "/api/v2/root/grr-binaries/<type>/<path:path>"
  )
  def DeleteGrrBinary(
      self,
      args: binary_management_pb2.ApiDeleteGrrBinaryArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_binary_management.ApiDeleteGrrBinaryHandler:
    return api_binary_management.ApiDeleteGrrBinaryHandler()

  # Signed commands methods.
  # ========================
  #
  @api_call_router.Category("SignedCommands")
  @api_call_router.ProtoArgsType(
      api_signed_commands_pb2.ApiCreateSignedCommandsArgs
  )
  @api_call_router.Http("POST", "/api/v2/signed-commands")
  def CreateSignedCommands(
      self,
      args: api_signed_commands_pb2.ApiCreateSignedCommandsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_signed_commands.ApiCreateSignedCommandsHandler:
    return api_signed_commands.ApiCreateSignedCommandsHandler()

  @api_call_router.Category("SignedCommands")
  @api_call_router.Http("DELETE", "/api/v2/signed-commands")
  def DeleteAllSignedCommands(
      self,
      args: Optional[None] = None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_signed_commands.ApiDeleteAllSignedCommandsHandler:
    return api_signed_commands.ApiDeleteAllSignedCommandsHandler()

  # Reflection methods (needed for client libraries to work).
  # ===========================================================
  #
  @api_call_router.Category("Reflection")
  @api_call_router.ProtoResultType(api_reflection_pb2.ApiListApiMethodsResult)
  @api_call_router.Http("GET", "/api/v2/reflection/api-methods")
  @api_call_router.NoAuditLogRequired()
  def ListApiMethods(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_reflection.ApiListApiMethodsHandler:
    return api_reflection.ApiListApiMethodsHandler(self)

  # Metadata methods.
  # ===========================================================
  #
  @api_call_router.Category("Metadata")
  @api_call_router.ProtoResultType(
      api_metadata_pb2.ApiGetOpenApiDescriptionResult
  )
  @api_call_router.Http("GET", "/api/v2/metadata/openapi")
  @api_call_router.NoAuditLogRequired()
  def GetOpenApiDescription(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_metadata.ApiGetOpenApiDescriptionHandler:
    return api_metadata.ApiGetOpenApiDescriptionHandler(self)
