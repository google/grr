#!/usr/bin/env python
"""Authentication for data servers and clients."""


import hashlib
import threading
import time
import uuid

from grr.lib import config_lib
from grr.lib import utils
from grr.lib.rdfvalues import data_server

from grr.server.data_server import errors

NONCE_SIZE = 36
HASH_SIZE = 64
TOKEN_SIZE = NONCE_SIZE + HASH_SIZE
INITVECTOR_SIZE = 32


class ClientCredentials(object):
  """Holds information about client usernames and passwords."""

  def __init__(self):
    self.client_users = {}

  def InitializeFromConfig(self):
    usernames = config_lib.CONFIG.Get("Dataserver.client_credentials")
    self.client_users = {}
    for user_spec in usernames:
      try:
        user, pwd, perm = user_spec.split(":", 2)
        self.client_users[user] = data_server.DataServerClientInformation(
            username=user, password=pwd,
            permissions=perm)
      except ValueError:
        raise errors.DataServerError(
            "User %s from Dataserver.client_credentials is not"
            " a valid specification" % user_spec)

  def Encrypt(self, username, password):
    """Encrypt the client credentials to other data servers.

    Args:
      username: This server's username.
      password: This server's password.

    Returns:
      A serialized DataServerEncryptedCreds proto that can be sent to other
      servers.
    """
    # We use the servers username and password to encrypt
    # the client credentials.
    creds = data_server.DataServerClientCredentials(
        users=self.client_users.values())

    result = data_server.DataServerEncryptedCreds()
    result.SetPayload(creds.SerializeToString(), username, password)

    return result.SerializeToString()

  def InitializeFromEncryption(self, string, username, password):
    """Initialize client credentials from encrypted string from the master.

    Args:
      string: The serialized DataServerEncryptedCreds proto to parse.
      username: This server's username.
      password: This server's password.

    Returns:
      self.
    """
    encrypted_creds = data_server.DataServerEncryptedCreds(string)

    creds = data_server.DataServerClientCredentials(encrypted_creds.GetPayload(
        username, password))

    # Create client credentials.
    self.client_users = {}
    for client in creds.users:
      self.client_users[client.username] = client

    return self

  def HasUser(self, username):
    return username in self.client_users

  def GetPassword(self, username):
    try:
      return self.client_users[username].password
    except KeyError:
      return None

  def GetPermissions(self, username):
    try:
      return self.client_users[username].permissions
    except KeyError:
      return None


class NonceStore(object):
  """Stores nonces requested by clients."""

  # We defined a limit of nonces that we can store
  # because we want to avoid denial of service.
  MAX_NONCES = 10000  # Maximum number of allowed nonces.
  NONCE_LEASE = 120  # Nonce lifetime if there are too many nonces.

  def __init__(self):
    # Stores all the registered nonces.
    self.nonces = {}
    self.lock = threading.Lock()
    # Data server credentials.
    self.server_username = config_lib.CONFIG.Get("Dataserver.server_username")
    self.server_password = config_lib.CONFIG.Get("Dataserver.server_password")
    if not self.server_username:
      raise errors.DataServerError("Dataserver.server_username not provided")
    if not self.server_password:
      raise errors.DataServerError("Dataserver.server_password not provided")
    # Client credentials.
    self.client_creds = None

  def SetClientCredentials(self, creds):
    self.client_creds = creds

  def EncryptClientCredentials(self):
    if self.client_creds:
      return self.client_creds.Encrypt(self.server_username,
                                       self.server_password)
    return None

  def GetServerCredentials(self):
    return self.server_username, self.server_password

  def _InvalidateAllNonces(self):
    self.nonces = {}

  def _InvalidateOldNonces(self, now):
    """Invalidate old nonces."""
    old = []
    for nonce, ts in self.nonces.iteritems():
      if now - ts > self.NONCE_LEASE:
        old.append(nonce)
    for item in old:
      del self.nonces[item]

  @utils.Synchronized
  def NewNonce(self):
    """Generates a new random, unique nonce to use for authentication."""
    now = time.time()
    if len(self.nonces) >= self.MAX_NONCES:
      self._InvalidateOldNonces(now)
      return None

    nonce = str(uuid.uuid4())
    if nonce in self.nonces:
      # This shouldn't really happen.
      return None

    if len(self.nonces) >= self.MAX_NONCES / 10:
      self._InvalidateOldNonces(now)
    self.nonces[nonce] = now

    return nonce

  @utils.Synchronized
  def GetNonce(self, nonce):
    """Return and remove nonce if in the store."""
    if self.nonces.pop(nonce, None):
      return nonce
    return None

  def ValidateAuthTokenServer(self, token):
    """Check if a given token has valid server credentials."""
    if not self.GetNonce(token.nonce):
      # Nonce was not generated before!
      return False
    if token.username != self.server_username:
      # Invalid username.
      return False
    generated_hash = self._GenerateAuthHash(token.nonce, self.server_username,
                                            self.server_password)
    return token.hash == generated_hash

  def ValidateAuthTokenClient(self, token):
    """Check if a given token has valid permissions and return them."""
    if not self.client_creds:
      return None
    if not self.GetNonce(token.nonce):
      # Nonce was not generated before!
      return None
    if not self.client_creds.HasUser(token.username):
      # No such user.
      return None
    password = self.client_creds.GetPassword(token.username)
    generated_hash = self._GenerateAuthHash(token.nonce, token.username,
                                            password)
    if token.hash != generated_hash:
      return None
    return self.client_creds.GetPermissions(token.username)

  def GenerateServerAuthToken(self, nonce):
    """Generate a new token based on the nonce and username/password."""
    return self.GenerateAuthToken(nonce, self.server_username,
                                  self.server_password)

  @classmethod
  def GenerateAuthToken(cls, nonce, username, password):
    hsh = cls._GenerateAuthHash(nonce, username, password)
    return data_server.DataStoreAuthToken(nonce=nonce,
                                          hash=hsh,
                                          username=username)

  @classmethod
  def _GenerateAuthHash(cls, nonce, username, password):
    full = nonce + username + password
    return hashlib.sha256(full).hexdigest()
