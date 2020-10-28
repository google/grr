#!/usr/bin/env python
"""Root (i.e. administrative) actions support in GRR API client library."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import hashlib
from typing import Callable
from typing import IO
from typing import Optional

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa

from grr_api_client import context as api_context
from grr_api_client import utils
from grr_response_proto.api import config_pb2
from grr_response_proto.api import user_pb2
from grr_response_proto.api.root import binary_management_pb2
from grr_response_proto.api.root import client_management_pb2
from grr_response_proto.api.root import user_management_pb2


class GrrUserBase(object):
  """Base class for GrrUserRef and GrrUser."""

  USER_TYPE_STANDARD = user_pb2.ApiGrrUser.USER_TYPE_STANDARD
  USER_TYPE_ADMIN = user_pb2.ApiGrrUser.USER_TYPE_ADMIN

  def __init__(
      self,
      username: str,
      context: api_context.GrrApiContext,
  ):
    super(GrrUserBase, self).__init__()

    self.username = username  # type: str
    self._context = context  # type: api_context.GrrApiContext

  def Get(self) -> "GrrUser":
    """Fetches user's data and returns it wrapped in a Grruser object."""

    args = user_management_pb2.ApiGetGrrUserArgs(username=self.username)
    data = self._context.SendRequest("GetGrrUser", args)
    if not isinstance(data, user_pb2.ApiGrrUser):
      raise TypeError(f"Unexpected response type: '{type(data)}'")

    return GrrUser(data=data, context=self._context)

  def Delete(self):
    """Deletes the user."""

    args = user_management_pb2.ApiDeleteGrrUserArgs(username=self.username)
    self._context.SendRequest("DeleteGrrUser", args)

  # TODO(hanuszczak): Python's protobuf enums don't currently work with
  # `Optional`.
  def Modify(
      self,
      user_type: Optional[int] = None,
      password: Optional[str] = None,
      email: Optional[str] = None,
  ) -> "GrrUser":
    """Modifies user's type and/or password."""

    args = user_management_pb2.ApiModifyGrrUserArgs(username=self.username)

    if user_type is not None:
      args.user_type = user_type

    if password is not None:
      args.password = password

    if email is not None:
      args.email = email

    data = self._context.SendRequest("ModifyGrrUser", args)
    if not isinstance(data, user_pb2.ApiGrrUser):
      raise TypeError(f"Unexpected response type: '{type(data)}'")

    return GrrUser(data=data, context=self._context)

  def __repr__(self) -> str:
    return "<%s %s>" % (self.__class__.__name__, self.username)


class GrrUserRef(GrrUserBase):
  """Reference to a GRR user."""


class GrrUser(GrrUserBase):
  """A fetched GRR user object wrapper."""

  def __init__(
      self,
      data: user_pb2.ApiGrrUser,
      context: api_context.GrrApiContext,
  ):
    super(GrrUser, self).__init__(username=data.username, context=context)

    self.data = data  # type: user_pb2.ApiGrrUser


class GrrBinaryRef(object):
  """Reference class pointing at GrrBinary."""

  CHUNK_SIZE = 512 * 1024

  def __init__(
      self,
      binary_type: config_pb2.ApiGrrBinary.Type,
      path: str,
      context: api_context.GrrApiContext,
  ):
    super(GrrBinaryRef, self).__init__()

    self.binary_type = binary_type  # type: config_pb2.ApiGrrBinary.Type
    self.path = path  # type: str
    self._context = context  # type: api_context.GrrApiContext

  def _DefaultBlobSign(
      self,
      blob_bytes: bytes,
      private_key: rsa.RSAPrivateKey,
  ) -> bytes:
    padding_algorithm = padding.PKCS1v15()
    return private_key.sign(blob_bytes, padding_algorithm, hashes.SHA256())

  def DefaultUploadSigner(
      self,
      private_key: rsa.RSAPrivateKey,
  ) -> Callable[[bytes], bytes]:
    return lambda b: self._DefaultBlobSign(b, private_key=private_key)

  def Upload(self, fd: IO[bytes], sign_fn: Callable[[bytes], bytes]):
    """Uploads data from a given stream and signs them with a given key."""
    args = binary_management_pb2.ApiUploadGrrBinaryArgs(
        type=self.binary_type, path=self.path)

    while True:
      data = fd.read(self.__class__.CHUNK_SIZE)
      if not data:
        break

      blob = args.blobs.add()

      blob.signature = sign_fn(data)
      blob.signature_type = blob.RSA_PKCS1v15

      blob.digest = hashlib.sha256(data).digest()
      blob.digest_type = blob.SHA256

      blob.data = data

    self._context.SendRequest("UploadGrrBinary", args)

  def Delete(self):
    args = binary_management_pb2.ApiDeleteGrrBinaryArgs(
        type=self.binary_type, path=self.path)
    self._context.SendRequest("DeleteGrrBinary", args)


class ClientRef(object):
  """Reference class pointing to a GRR client."""

  def __init__(
      self,
      client_id: str,
      context: api_context.GrrApiContext,
  ) -> None:
    self.client_id = client_id  # type: str
    self._context = context  # type: api_context.GrrApiContext

  def KillFleetspeak(self, force: bool) -> None:
    """Kills fleetspeak on the given client."""
    args = client_management_pb2.ApiKillFleetspeakArgs()
    args.client_id = self.client_id
    args.force = force
    self._context.SendRequest("KillFleetspeak", args)

  def RestartFleetspeakGrrService(self) -> None:
    """Restarts the GRR fleetspeak service on the given client."""
    args = client_management_pb2.ApiRestartFleetspeakGrrServiceArgs()
    args.client_id = self.client_id
    self._context.SendRequest("RestartFleetspeakGrrService", args)

  def __repr__(self) -> str:
    return "<{} client_id={}>".format(self.__class__.__name__, self.client_id)


class RootGrrApi(object):
  """Object providing access to root-level access GRR methods."""

  def __init__(
      self,
      context: api_context.GrrApiContext,
  ):
    super(RootGrrApi, self).__init__()
    self._context = context  # type: api_context.GrrApiContext

  # TODO(hanuszczak): Python's protobuf enums don't currently work with
  # `Optional`.
  def CreateGrrUser(
      self,
      username: str,
      user_type: Optional[int] = None,
      password: Optional[str] = None,
      email: Optional[str] = None,
  ) -> GrrUser:
    """Creates a new GRR user of a given type with a given username/password."""

    if not username:
      raise ValueError("Username can't be empty.")

    args = user_management_pb2.ApiCreateGrrUserArgs(username=username)

    if user_type is not None:
      args.user_type = user_type

    if password is not None:
      args.password = password

    if email is not None:
      args.email = email

    data = self._context.SendRequest("CreateGrrUser", args)
    if not isinstance(data, user_pb2.ApiGrrUser):
      raise TypeError(f"Unexpected response type: '{type(data)}'")

    return GrrUser(data=data, context=self._context)

  def GrrUser(
      self,
      username: str,
  ) -> GrrUserRef:
    """Returns a reference to a GRR user."""

    return GrrUserRef(username=username, context=self._context)

  # TODO(hanuszczak): Investigate why `pytype` does not allow to specify the
  # type for the returned iterator more concretely.
  def ListGrrUsers(self) -> utils.ItemsIterator:
    """Lists all registered GRR users."""

    args = user_management_pb2.ApiListGrrUsersArgs()

    items = self._context.SendIteratorRequest("ListGrrUsers", args)
    return utils.MapItemsIterator(
        lambda data: GrrUser(data=data, context=self._context), items)

  def GrrBinary(
      self,
      binary_type: config_pb2.ApiGrrBinary.Type,
      path: str,
  ) -> GrrBinaryRef:
    return GrrBinaryRef(
        binary_type=binary_type, path=path, context=self._context)

  def Client(
      self,
      client_id: str,
  ) -> ClientRef:
    """Returns a reference to a GRR client."""
    return ClientRef(client_id, self._context)
