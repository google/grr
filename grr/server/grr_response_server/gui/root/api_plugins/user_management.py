#!/usr/bin/env python
# Lint as: python3
"""Root-access-level API handlers for user management."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core import config
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api.root import user_management_pb2
from grr_response_server import data_store
from grr_response_server.databases import db
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui.api_plugins import user as api_user


class ApiCreateGrrUserArgs(rdf_structs.RDFProtoStruct):
  protobuf = user_management_pb2.ApiCreateGrrUserArgs


class ApiCreateGrrUserHandler(api_call_handler_base.ApiCallHandler):
  """Creates a new GRR user."""

  args_type = ApiCreateGrrUserArgs
  result_type = api_user.ApiGrrUser

  def Handle(self, args, context=None):
    if not args.username:
      raise ValueError("username can't be empty.")

    if args.user_type != args.UserType.USER_TYPE_ADMIN:
      args.user_type = args.UserType.USER_TYPE_STANDARD

    if args.email:
      if config.CONFIG["Email.enable_custom_email_address"]:
        email = args.email
      else:
        raise ValueError("email can't be set if the config option "
                         "Email.enable_custom_email_address is not enabled.")
    else:
      email = None

    data_store.REL_DB.WriteGRRUser(
        username=args.username,
        password=args.password if args.HasField("password") else None,
        user_type=args.user_type,
        email=email,
    )
    user = data_store.REL_DB.ReadGRRUser(args.username)
    return api_user.ApiGrrUser().InitFromDatabaseObject(user)


class ApiDeleteGrrUserArgs(rdf_structs.RDFProtoStruct):
  protobuf = user_management_pb2.ApiDeleteGrrUserArgs


class ApiDeleteGrrUserHandler(api_call_handler_base.ApiCallHandler):
  """Deletes a GRR user."""

  args_type = ApiDeleteGrrUserArgs

  def Handle(self, args, context=None):
    if not args.username:
      raise ValueError("username can't be empty.")

    try:
      data_store.REL_DB.DeleteGRRUser(args.username)
    except db.UnknownGRRUserError as e:
      raise api_call_handler_base.ResourceNotFoundError(e)


class ApiModifyGrrUserArgs(rdf_structs.RDFProtoStruct):
  protobuf = user_management_pb2.ApiModifyGrrUserArgs


class ApiModifyGrrUserHandler(api_call_handler_base.ApiCallHandler):
  """Modifies a GRR user."""

  args_type = ApiModifyGrrUserArgs
  result_type = api_user.ApiGrrUser

  def Handle(self, args, context=None):
    if not args.username:
      raise ValueError("username can't be empty.")

    if args.HasField(
        "user_type") and args.user_type != args.UserType.USER_TYPE_ADMIN:
      args.user_type = args.UserType.USER_TYPE_STANDARD

    # query user, to throw if a nonexistent user should be modified
    data_store.REL_DB.ReadGRRUser(args.username)

    if args.HasField("password"):
      password = args.password
    else:
      password = None

    if args.HasField("user_type"):
      user_type = args.user_type
    else:
      user_type = None

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
        email=email)

    user = data_store.REL_DB.ReadGRRUser(args.username)
    return api_user.ApiGrrUser().InitFromDatabaseObject(user)


class ApiListGrrUsersArgs(rdf_structs.RDFProtoStruct):
  protobuf = user_management_pb2.ApiListGrrUsersArgs


class ApiListGrrUsersResult(rdf_structs.RDFProtoStruct):
  protobuf = user_management_pb2.ApiListGrrUsersResult
  rdf_deps = [
      api_user.ApiGrrUser,
  ]


class ApiListGrrUsersHandler(api_call_handler_base.ApiCallHandler):
  """Lists all users registered in the system."""

  args_type = ApiListGrrUsersArgs
  result_type = ApiListGrrUsersResult

  def Handle(self, args, context=None):
    total_count = data_store.REL_DB.CountGRRUsers()
    db_users = data_store.REL_DB.ReadGRRUsers(
        offset=args.offset, count=args.count)
    items = [api_user.ApiGrrUser().InitFromDatabaseObject(u) for u in db_users]
    return ApiListGrrUsersResult(total_count=total_count, items=items)


class ApiGetGrrUserArgs(rdf_structs.RDFProtoStruct):
  protobuf = user_management_pb2.ApiGetGrrUserArgs


class ApiGetGrrUserHandler(api_call_handler_base.ApiCallHandler):
  """Returns information about a user with a given name."""

  args_type = ApiGetGrrUserArgs
  result_type = api_user.ApiGrrUser

  def Handle(self, args, context=None):
    if not args.username:
      raise ValueError("username can't be empty.")

    try:
      user = data_store.REL_DB.ReadGRRUser(args.username)
      return api_user.ApiGrrUser().InitFromDatabaseObject(user)
    except db.UnknownGRRUserError as e:
      raise api_call_handler_base.ResourceNotFoundError(e)
