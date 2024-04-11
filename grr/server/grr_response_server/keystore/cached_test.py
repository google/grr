#!/usr/bin/env python
import datetime
from typing import Sequence

from absl.testing import absltest

from grr_response_server.keystore import abstract
from grr_response_server.keystore import abstract_test_lib
from grr_response_server.keystore import cached
from grr_response_server.keystore import mem


class CachedKeystoreTest(
    abstract_test_lib.KeystoreTestMixin,
    absltest.TestCase,
):

  def CreateKeystore(self, key_names: Sequence[str]) -> abstract.Keystore:
    return cached.CachedKeystore(mem.MemKeystore(key_names))

  def testCrypterCached(self):
    mem_ks = mem.MemKeystore(["foo"])

    # We create a keystore where all the keys expire after 128 weeks (so, enough
    # for the test to execute without expiring anything.
    cached_ks = cached.CachedKeystore(
        mem_ks, validity_duration=datetime.timedelta(weeks=128)
    )

    crypter_1 = cached_ks.Crypter("foo")
    crypter_2 = cached_ks.Crypter("foo")
    self.assertIs(crypter_1, crypter_2)

  def testCrypterExpired(self):
    mem_ks = mem.MemKeystore(["foo"])

    # We create a keystore where all the keys have no validity duration (meaning
    # the keystore should expire them all the time).
    cached_ks = cached.CachedKeystore(
        mem_ks, validity_duration=datetime.timedelta(0)
    )

    crypter_1 = cached_ks.Crypter("foo")
    crypter_2 = cached_ks.Crypter("foo")
    self.assertIsNot(crypter_1, crypter_2)


if __name__ == "__main__":
  absltest.main()
