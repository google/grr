#!/usr/bin/env python
"""Authentication for data servers and clients."""


import hashlib
import threading
import time
import uuid

from M2Crypto import EVP

from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import crypto

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
    usernames = config_lib.CONFIG.Get("Dataserver.usernames")
    self.client_users = {}
    for user_spec in usernames:
      try:
        user, perm, pwd = user_spec.split(":", 2)
        self.client_users[user] = (perm, pwd)
      except ValueError:
        raise errors.DataServerError("User %s from Dataserver.usernames is not"
                                     " a valid specification" % user_spec)

  def _MakeEncryptKey(self, username, password):
    data = hashlib.md5(username + password).hexdigest()
    return crypto.AES128Key(data)

  def _MakeInitVector(self):
    init_vector = crypto.AES128Key()
    init_vector.Generate()
    return init_vector

  def Encrypt(self, username, password):
    """Encrypt the client credentials to other data servers."""
    # We use the servers username and password to encrypt
    # the client credentials.
    creds = rdfvalue.DataServerClientCredentials()
    for client_user, (perm, pwd) in self.client_users.iteritems():
      client = rdfvalue.DataServerClientInformation(username=client_user,
                                                    password=pwd,
                                                    permissions=perm)
      creds.users.Append(client)
    key = self._MakeEncryptKey(username, password)
    # We encrypt the credentials object.
    string = creds.SerializeToString()
    if len(string) % 16:
      string += " " * (16 - len(string) % 16)  # Must be in 16 byte blocks.
    init_vector = self._MakeInitVector()
    encryptor = crypto.AES128CBCCipher(key, init_vector,
                                       crypto.Cipher.OP_ENCRYPT)
    data = encryptor.Update(string)
    data += encryptor.Final()
    # Initialization vector is prepended to the encrypted credentials.
    return str(init_vector) + data

  def InitializeFromEncryption(self, string, username, password):
    """Initialize client credentials from encrypted string from the master."""
    # Use the same key used in Encrypt()
    key = self._MakeEncryptKey(username, password)
    # Initialization vector was prepended.
    init_vector_str = string[:INITVECTOR_SIZE]
    init_vector = crypto.AES128Key(init_vector_str)
    ciphertext = string[INITVECTOR_SIZE:]
    decryptor = crypto.AES128CBCCipher(key, init_vector,
                                       crypto.Cipher.OP_DECRYPT)
    # Decrypt credentials information and set the required fields.
    try:
      plain = decryptor.Update(ciphertext)
      plain += decryptor.Final()
      creds = rdfvalue.DataServerClientCredentials(plain)
      # Create client credentials.
      self.client_users = {}
      for client in list(creds.users):
        username = client.username
        self.client_users[username] = (client.permissions, client.password)
      return self
    except EVP.EVPError:
      return None

  def HasUser(self, username):
    try:
      unused_cred = self.client_users[username]
      return True
    except KeyError:
      return False

  def GetPassword(self, username):
    try:
      cred = self.client_users[username]
      return cred[1]
    except KeyError:
      return None

  def GetPermissions(self, username):
    try:
      cred = self.client_users[username]
      return cred[0]
    except KeyError:
      return None


class NonceStore(object):
  """Stores nonce's requested by clients."""

  # We defined a limit of nonces that we can store
  # because we want to avoid denial of service.
  MAX_NONCES = 10000  # Maximum number of allowed nonces.
  NONCE_LEASE = 120  # Nonce lifetime if there are too many nonces.

  def __init__(self):
    # Stores all the registered nonces.
    self.nonces = {}
    self.lock = threading.Lock()
    # Data server credentials.
    self.server_username = config_lib.CONFIG.Get("Dataserver.username")
    self.server_password = config_lib.CONFIG.Get("Dataserver.password")
    if not self.server_username:
      raise errors.DataServerError("Dataserver.username not provided")
    if not self.server_password:
      raise errors.DataServerError("Dataserver.password not provided")
    # Client credentials.
    self.client_creds = None

  def SetClientCredentials(self, creds):
    self.client_creds = creds

  def EncryptClientCredentials(self):
    if self.client_creds:
      return self.client_creds.Encrypt(self.server_username,
                                       self.server_password)
    else:
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

    if len(self.nonces) >= self.MAX_NONCES/10:
      self._InvalidateOldNonces(now)
    self.nonces[nonce] = now

    return nonce

  @utils.Synchronized
  def GetNonce(self, nonce):
    """Return and remove nonce if in the store."""
    if nonce in self.nonces:
      del self.nonces[nonce]
      return nonce
    else:
      return None

  def ValidateAuthTokenServer(self, token):
    """Check if a given token has valid server credentials."""
    nonce, hsh1, user = _SplitToken(token)
    if not self.GetNonce(nonce):
      # Nonce was not generated before!
      return False
    if user != self.server_username:
      # Invalid username.
      return False
    hsh2 = _GenerateAuthHash(nonce, self.server_username, self.server_password)
    return hsh1 == hsh2

  def ValidateAuthTokenClient(self, token):
    """Check if a given token has valid permissions and return them."""
    if not self.client_creds:
      return None
    nonce, hsh1, user = _SplitToken(token)
    if not self.GetNonce(nonce):
      # Nonce was not generated before!
      return None
    if not self.client_creds.HasUser(user):
      # No such user.
      return None
    password = self.client_creds.GetPassword(user)
    hsh2 = _GenerateAuthHash(nonce, user, password)
    if hsh1 != hsh2:
      return None
    return self.client_creds.GetPermissions(user)


def _GenerateAuthHash(nonce, username, password):
  full = nonce + username + password
  return hashlib.sha256(full).hexdigest()


def _SplitToken(token):
  nonce = token[:NONCE_SIZE]
  token = token[NONCE_SIZE:]
  hsh = token[:HASH_SIZE]
  token = token[HASH_SIZE:]
  username = token
  return nonce, hsh, username


def GenerateAuthToken(nonce, username, password):
  """Generate a new token based on the nonce and username/password."""
  hsh = _GenerateAuthHash(nonce, username, password)
  return nonce + hsh + username

