#!/usr/bin/env python
"""Root-access-level API handlers for user management."""

from typing import Optional

from grr_response_core import config
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_proto import jobs_pb2
from grr_response_proto.api import user_pb2 as api_user_pb2
from grr_response_proto.api.root import user_management_pb2
from grr_response_server import data_store
from grr_response_server.databases import db
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui.api_plugins import user as api_user


class ApiCreateGrrUserHandler(api_call_handler_base.ApiCallHandler):
  """Creates a new GRR user."""

  proto_args_type = user_management_pb2.ApiCreateGrrUserArgs
  proto_result_type = api_user_pb2.ApiGrrUser

  def Handle(
      self,
      args: user_management_pb2.ApiCreateGrrUserArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user_pb2.ApiGrrUser:
    if not args.username:
      raise ValueError("username can't be empty.")

    if args.user_type != api_user_pb2.ApiGrrUser.UserType.USER_TYPE_ADMIN:
      args.user_type = api_user_pb2.ApiGrrUser.UserType.USER_TYPE_STANDARD

    if args.email:
      if config.CONFIG["Email.enable_custom_email_address"]:
        email = args.email
      else:
        raise ValueError("email can't be set if the config option "
                         "Email.enable_custom_email_address is not enabled.")
    else:
      email = None

    password = None
    if args.HasField("password"):
      password = jobs_pb2.Password()
      rdf_crypto.SetPassword(password, args.password)

    data_store.REL_DB.WriteGRRUser(
        username=args.username,
        password=password,
        user_type=args.user_type,
        email=email,
    )
    # TODO: Use function to get API from proto user.
    user = data_store.REL_DB.ReadGRRUser(args.username)
    return api_user.InitApiGrrUserFromGrrUser(user)


class ApiDeleteGrrUserHandler(api_call_handler_base.ApiCallHandler):
  """Deletes a GRR user."""

  proto_args_type = user_management_pb2.ApiDeleteGrrUserArgs

  def Handle(
      self,
      args: user_management_pb2.ApiDeleteGrrUserArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> None:
    if not args.username:
      raise ValueError("Username is not set")

    try:
      data_store.REL_DB.DeleteGRRUser(args.username)
    except db.UnknownGRRUserError as e:
      raise api_call_handler_base.ResourceNotFoundError(e)


class ApiModifyGrrUserHandler(api_call_handler_base.ApiCallHandler):
  """Modifies a GRR user."""

  proto_args_type = user_management_pb2.ApiModifyGrrUserArgs
  proto_result_type = api_user_pb2.ApiGrrUser

  def Handle(
      self,
      args: user_management_pb2.ApiModifyGrrUserArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user_pb2.ApiGrrUser:
    if not args.username:
      raise ValueError("Username is empty")

    if (
        args.HasField("user_type")
        and args.user_type != api_user_pb2.ApiGrrUser.UserType.USER_TYPE_ADMIN
    ):
      args.user_type = api_user_pb2.ApiGrrUser.UserType.USER_TYPE_STANDARD

    # query user, to throw if a nonexistent user should be modified
    data_store.REL_DB.ReadGRRUser(args.username)

    password = None
    if args.HasField("password"):
      password = jobs_pb2.Password()
      rdf_crypto.SetPassword(password, args.password)

    user_type = None
    if args.HasField("user_type"):
      user_type = args.user_type

    if args.HasField("email"):
      if config.CONFIG["Email.enable_custom_email_address"]:
        email = args.email
      else:
        raise ValueError("email can't be set if the config option "
                         "Email.enable_custom_email_address is not enabled.")
    else:
      email = None

    data_store.REL_DB.WriteGRRUser(
        username=args.username,
        password=password,
        user_type=user_type,
        email=email,
    )

    # TODO: Use function to get API from proto user.
    user = data_store.REL_DB.ReadGRRUser(args.username)
    return api_user.InitApiGrrUserFromGrrUser(user)


class ApiListGrrUsersHandler(api_call_handler_base.ApiCallHandler):
  """Lists all users registered in the system."""

  proto_args_type = user_management_pb2.ApiListGrrUsersArgs
  proto_result_type = user_management_pb2.ApiListGrrUsersResult

  def Handle(
      self,
      args: user_management_pb2.ApiListGrrUsersArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> user_management_pb2.ApiListGrrUsersResult:
    total_count = data_store.REL_DB.CountGRRUsers()
    users = data_store.REL_DB.ReadGRRUsers(offset=args.offset, count=args.count)
    # TODO: Use function to get API from proto user.
    items = [api_user.InitApiGrrUserFromGrrUser(u) for u in users]
    return user_management_pb2.ApiListGrrUsersResult(
        total_count=total_count, items=items
    )


class ApiGetGrrUserHandler(api_call_handler_base.ApiCallHandler):
  """Returns information about a user with a given name."""

  result_type = api_user_pb2.ApiGrrUser
  proto_args_type = user_management_pb2.ApiGetGrrUserArgs
  proto_result_type = api_user_pb2.ApiGrrUser

  def Handle(
      self,
      args: user_management_pb2.ApiGetGrrUserArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user_pb2.ApiGrrUser:
    if not args.username:
      raise ValueError("Username is empty.")

    try:
      # TODO: Use function to get API from proto user.
      user = data_store.REL_DB.ReadGRRUser(args.username)
    except db.UnknownGRRUserError as e:
      raise api_call_handler_base.ResourceNotFoundError(e)

    return api_user.InitApiGrrUserFromGrrUser(user)
