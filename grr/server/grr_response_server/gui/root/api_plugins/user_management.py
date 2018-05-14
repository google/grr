#!/usr/bin/env python
"""Root-access-level API handlers for user management."""

from grr.lib.rdfvalues import events as rdf_events
from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api.root import user_management_pb2
from grr.server.grr_response_server import access_control
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import events
from grr.server.grr_response_server.aff4_objects import users
from grr.server.grr_response_server.gui import api_call_handler_base
from grr.server.grr_response_server.gui.api_plugins import user as api_user


class ApiCreateGrrUserArgs(rdf_structs.RDFProtoStruct):
  protobuf = user_management_pb2.ApiCreateGrrUserArgs


class ApiCreateGrrUserHandler(api_call_handler_base.ApiCallHandler):
  """Creates a new GRR user."""

  args_type = ApiCreateGrrUserArgs
  result_type = api_user.ApiGrrUser

  def Handle(self, args, token=None):
    if not args.username:
      raise ValueError("username can't be empty.")

    user_urn = aff4.ROOT_URN.Add("users").Add(args.username)

    events.Events.PublishEvent(
        "Audit",
        rdf_events.AuditEvent(
            user=token.username, action="USER_ADD", urn=user_urn),
        token=token)

    if aff4.FACTORY.ExistsWithType(
        user_urn, aff4_type=users.GRRUser, token=token):
      raise access_control.UnauthorizedAccess(
          "Cannot add user %s: User already exists." % args.username)

    with aff4.FACTORY.Create(
        user_urn, aff4_type=users.GRRUser, mode="rw", token=token) as fd:

      if args.HasField("password"):
        fd.SetPassword(args.password)

      if args.user_type == args.UserType.USER_TYPE_ADMIN:
        fd.AddLabels(["admin"], owner="GRR")

      return api_user.ApiGrrUser().InitFromAff4Object(fd)


class ApiDeleteGrrUserArgs(rdf_structs.RDFProtoStruct):
  protobuf = user_management_pb2.ApiDeleteGrrUserArgs


class ApiDeleteGrrUserHandler(api_call_handler_base.ApiCallHandler):
  """Deletes a GRR user."""

  args_type = ApiDeleteGrrUserArgs

  def Handle(self, args, token=None):
    if not args.username:
      raise ValueError("username can't be empty.")

    user_urn = aff4.ROOT_URN.Add("users").Add(args.username)

    events.Events.PublishEvent(
        "Audit",
        rdf_events.AuditEvent(
            user=token.username, action="USER_DELETE", urn=user_urn),
        token=token)

    if not aff4.FACTORY.ExistsWithType(
        user_urn, aff4_type=users.GRRUser, token=token):
      raise api_call_handler_base.ResourceNotFoundError(
          "GRR user with username '%s' could not be found." % args.username)

    aff4.FACTORY.Delete(user_urn, token=token)


class ApiModifyGrrUserArgs(rdf_structs.RDFProtoStruct):
  protobuf = user_management_pb2.ApiModifyGrrUserArgs


class ApiModifyGrrUserHandler(api_call_handler_base.ApiCallHandler):
  """Modifies a GRR user."""

  args_type = ApiModifyGrrUserArgs
  result_type = api_user.ApiGrrUser

  def Handle(self, args, token=None):
    if not args.username:
      raise ValueError("username can't be empty.")

    user_urn = aff4.ROOT_URN.Add("users").Add(args.username)

    events.Events.PublishEvent(
        "Audit",
        rdf_events.AuditEvent(
            user=token.username, action="USER_UPDATE", urn=user_urn),
        token=token)

    with aff4.FACTORY.Open(
        user_urn, aff4_type=users.GRRUser, mode="rw", token=token) as fd:

      if args.HasField("password"):
        fd.SetPassword(args.password)

      if args.user_type == args.UserType.USER_TYPE_ADMIN:
        fd.AddLabels(["admin"], owner="GRR")
      elif args.user_type == args.UserType.USER_TYPE_STANDARD:
        fd.RemoveLabels(["admin"], owner="GRR")

      return api_user.ApiGrrUser().InitFromAff4Object(fd)


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

  def Handle(self, args, token=None):
    users_root = aff4.FACTORY.Open(aff4.ROOT_URN.Add("users"), token=token)
    usernames = sorted(users_root.ListChildren())

    total_count = len(usernames)
    if args.count:
      usernames = usernames[args.offset:args.offset + args.count]
    else:
      usernames = usernames[args.offset:]

    items = []
    for aff4_obj in aff4.FACTORY.MultiOpen(
        usernames, aff4_type=users.GRRUser, token=token):
      items.append(api_user.ApiGrrUser().InitFromAff4Object(aff4_obj))

    return ApiListGrrUsersResult(total_count=total_count, items=items)


class ApiGetGrrUserArgs(rdf_structs.RDFProtoStruct):
  protobuf = user_management_pb2.ApiGetGrrUserArgs


class ApiGetGrrUserHandler(api_call_handler_base.ApiCallHandler):
  """Returns information about a user with a given name."""

  args_type = ApiGetGrrUserArgs
  result_type = api_user.ApiGrrUser

  def Handle(self, args, token=None):
    if not args.username:
      raise ValueError("username can't be empty.")

    user_urn = aff4.ROOT_URN.Add("users").Add(args.username)
    try:
      fd = aff4.FACTORY.Open(
          user_urn, aff4_type=users.GRRUser, mode="r", token=token)
      return api_user.ApiGrrUser().InitFromAff4Object(fd)
    except aff4.InstantiationError:
      raise api_call_handler_base.ResourceNotFoundError(
          "GRR user with username '%s' could not be found." % args.username)
