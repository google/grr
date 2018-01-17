#!/usr/bin/env python
"""Root (i.e. administrative) actions support in GRR API client library."""

from grr_api_client import utils
from grr_response_proto.api import user_pb2
from grr_response_proto.api.root import user_management_pb2


class GrrUserBase(object):
  """Base class for GrrUserRef and GrrUser."""

  USER_TYPE_STANDARD = user_pb2.ApiGrrUser.USER_TYPE_STANDARD
  USER_TYPE_ADMIN = user_pb2.ApiGrrUser.USER_TYPE_ADMIN

  def __init__(self, username=None, context=None):
    super(GrrUserBase, self).__init__()

    self.username = username
    self._context = context

  def Get(self):
    """Fetches user's data and returns it wrapped in a Grruser object."""

    args = user_management_pb2.ApiGetGrrUserArgs(username=self.username)
    data = self._context.SendRequest("GetGrrUser", args)
    return GrrUser(data=data, context=self._context)

  def Delete(self):
    """Deletes the user."""

    args = user_management_pb2.ApiDeleteGrrUserArgs(username=self.username)
    self._context.SendRequest("DeleteGrrUser", args)

  def Modify(self, user_type=None, password=None):
    """Modifies user's type and/or password."""

    args = user_management_pb2.ApiModifyGrrUserArgs(
        username=self.username, user_type=user_type)

    if user_type is not None:
      args.user_type = user_type

    if password is not None:
      args.password = password

    data = self._context.SendRequest("ModifyGrrUser", args)
    return GrrUser(data=data, context=self._context)


class GrrUserRef(GrrUserBase):
  """Reference to a GRR user."""


class GrrUser(GrrUserBase):
  """A fetched GRR user object wrapper."""

  def __init__(self, data=None, context=None):
    super(GrrUser, self).__init__(username=data.username, context=context)

    self.data = data


class RootGrrApi(object):
  """Object providing access to root-level access GRR methods."""

  def __init__(self, context=None):
    super(RootGrrApi, self).__init__()
    self._context = context

  def CreateGrrUser(self, username=None, user_type=None, password=None):
    """Creates a new GRR user of a given type with a given username/password."""

    if not username:
      raise ValueError("Username can't be empty.")

    args = user_management_pb2.ApiCreateGrrUserArgs(username=username)
    args.username = username

    if user_type is not None:
      args.user_type = user_type

    if password is not None:
      args.password = password

    data = self._context.SendRequest("CreateGrrUser", args)
    return GrrUser(data=data, context=self._context)

  def GrrUser(self, username):
    """Returns a reference to a GRR user."""

    return GrrUserRef(username=username, context=self._context)

  def ListGrrUsers(self):
    """Lists all registered GRR users."""

    args = user_management_pb2.ApiListGrrUsersArgs()

    items = self._context.SendIteratorRequest("ListGrrUsers", args)
    return utils.MapItemsIterator(
        lambda data: GrrUser(data=data, context=self._context), items)
