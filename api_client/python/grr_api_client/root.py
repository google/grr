#!/usr/bin/env python
"""Root (i.e. administrative) actions support in GRR API client library."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import hashlib

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa

from grr_api_client import utils
from grr_response_proto.api import user_pb2
from grr_response_proto.api.root import binary_management_pb2
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

  def __repr__(self):
    return "<%s %s>" % (self.__class__.__name__, self.username)


class GrrUserRef(GrrUserBase):
  """Reference to a GRR user."""


class GrrUser(GrrUserBase):
  """A fetched GRR user object wrapper."""

  def __init__(self, data=None, context=None):
    super(GrrUser, self).__init__(username=data.username, context=context)

    self.data = data


class GrrBinaryRef(object):
  """Reference class pointing at GrrBinary."""

  CHUNK_SIZE = 512 * 1024

  def __init__(self, binary_type=None, path=None, context=None):
    super(GrrBinaryRef, self).__init__()

    self.binary_type = binary_type
    self.path = path
    self._context = context

  def _DefaultBlobSign(self, blob_bytes, private_key=None):
    if not private_key:
      raise ValueError("private_key can't be empty.")

    padding_algorithm = padding.PKCS1v15()
    return private_key.sign(blob_bytes, padding_algorithm, hashes.SHA256())

  def DefaultUploadSigner(self, private_key):
    if not private_key:
      raise ValueError("private_key can't be empty.")

    if not isinstance(private_key, rsa.RSAPrivateKey):
      raise ValueError("private_key has to be cryptography.io's RSAPrivateKey")

    return lambda b: self._DefaultBlobSign(b, private_key=private_key)

  def Upload(self, fd, sign_fn=None):
    """Uploads data from a given stream and signs them with a given key."""

    if not sign_fn:
      raise ValueError("sign_fn can't be empty. "
                       "See DefaultUploadSigner as a possible option.")

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

  def GrrBinary(self, binary_type, path):
    return GrrBinaryRef(
        binary_type=binary_type, path=path, context=self._context)
