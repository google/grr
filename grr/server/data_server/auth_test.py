#!/usr/bin/env python
"""Test the authentication facilities of the data servers."""



from grr.lib import config_lib
from grr.lib import flags
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.rdfvalues import crypto

from grr.server.data_server import auth


class AuthTest(test_lib.GRRBaseTest):
  """Tests the authentication package of the data server."""

  def setUp(self):
    super(AuthTest, self).setUp()
    self.config_overrider = test_lib.ConfigOverrider({
        "Dataserver.server_username": "rootuser1",
        "Dataserver.server_password": "somelongpasswordaabb",
        "Dataserver.client_credentials": ["rootuser1:somelongpasswordaabb:rw"]
    })
    self.config_overrider.Start()

  def tearDown(self):
    super(AuthTest, self).tearDown()
    self.config_overrider.Stop()

  def testNonceStoreSimple(self):
    # Test creation and deletion of nonces.
    store = auth.NonceStore()
    nonce1 = store.NewNonce()
    self.assertNotEqual(nonce1, None)
    self.assertEqual(nonce1, store.GetNonce(nonce1))
    self.assertEqual(None, store.GetNonce(nonce1))

    # Check if new nonce is not equal to the previous one.
    nonce2 = store.NewNonce()
    self.assertNotEqual(nonce2, None)
    self.assertNotEqual(nonce1, nonce2)
    self.assertEqual(nonce2, store.GetNonce(nonce2))
    self.assertEqual(None, store.GetNonce(nonce2))

  def testNonceStoreInvalidateOldNonces(self):
    with utils.MultiStubber(
        (auth.NonceStore, "NONCE_LEASE", 1),
        (auth.NonceStore, "MAX_NONCES", 5)):
      store = auth.NonceStore()

      now = 1000000
      with test_lib.FakeTime(now):
        # Add a few nonces first.
        nonces = []
        for _ in xrange(0, 5):
          nonces.append(store.NewNonce())

      with test_lib.FakeTime(now + 2):
        # Two seconds have passed, therefore old nonces will disappear.
        nonce = store.NewNonce()
        self.assertEqual(nonce, store.GetNonce(nonce))

        for nonce in nonces:
          self.assertEqual(store.GetNonce(nonce), None)

  def testNonceStoreTooMany(self):
    with utils.Stubber(auth.NonceStore, "MAX_NONCES", 5):
      # Attempt to get a lot of nonces at once.
      store = auth.NonceStore()

      old_nonce = None
      for _ in xrange(0, auth.NonceStore.MAX_NONCES):
        old_nonce = store.NewNonce()
        self.assertNotEqual(old_nonce, None)

      # We cannot get any nonce now!
      nonce1 = store.NewNonce()
      self.assertEqual(nonce1, None)

      # If we remove one nonce, then we should be able to get a new one.
      self.assertEqual(old_nonce, store.GetNonce(old_nonce))
      nonce1 = store.NewNonce()
      self.assertEqual(nonce1, store.GetNonce(nonce1))

  def testServerCredentials(self):
    user = config_lib.CONFIG["Dataserver.server_username"]
    pwd = config_lib.CONFIG["Dataserver.server_password"]

    # Use correct credentials.
    store = auth.NonceStore()
    nonce = store.NewNonce()
    token = auth.NonceStore.GenerateAuthToken(nonce, user, pwd)
    # Credentials must validate.
    self.assertTrue(store.ValidateAuthTokenServer(token))
    self.assertEqual(store.GetNonce(nonce), None)

    # Use bad password.
    nonce = store.NewNonce()
    token = auth.NonceStore.GenerateAuthToken(nonce, user, "badpassword")
    # Credentials must fail.
    self.assertFalse(store.ValidateAuthTokenServer(token))
    self.assertEqual(store.GetNonce(nonce), None)

    # Use bad nonce.
    token = auth.NonceStore.GenerateAuthToken("x" * auth.NONCE_SIZE, user, pwd)
    self.assertFalse(store.ValidateAuthTokenServer(token))

  def testClientCredentials(self):
    user = config_lib.CONFIG["Dataserver.server_username"]
    pwd = config_lib.CONFIG["Dataserver.server_password"]

    # Check credentials.
    creds = auth.ClientCredentials()
    creds.InitializeFromConfig()
    self.assertTrue(creds.HasUser(user))
    self.assertEqual(creds.GetPassword(user), "somelongpasswordaabb")
    self.assertEqual(creds.GetPermissions(user), "rw")

    self.assertFalse(creds.HasUser("user2"))
    self.assertEqual(creds.GetPassword("user2"), None)

    # Encrypt credentials.
    cipher = creds.Encrypt(user, pwd)
    self.assertNotEqual(cipher, "")

    creds2 = auth.ClientCredentials()
    creds2.InitializeFromEncryption(cipher, user, pwd)
    self.assertEqual(creds2.client_users, creds.client_users)

    # Must have same credentials.
    self.assertTrue(creds2.HasUser(user))
    self.assertEqual(creds2.GetPassword(user), "somelongpasswordaabb")
    self.assertEqual(creds2.GetPermissions(user), "rw")

    # Create new credentials with wrong password.
    creds3 = auth.ClientCredentials()
    self.assertRaises(crypto.CipherError, creds3.InitializeFromEncryption,
                      cipher, user, "badpassword")

    self.assertFalse(creds3.HasUser(user))


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
