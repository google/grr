#!/usr/bin/env python
from collections.abc import Sequence

from absl.testing import absltest

from grr_response_server.keystore import abstract
from grr_response_server.keystore import abstract_test_lib
from grr_response_server.keystore import mem


class MemKeystoreTest(
    abstract_test_lib.KeystoreTestMixin,
    absltest.TestCase,
):

  def CreateKeystore(
      self, aead_key_names: Sequence[str], mac_key_names: Sequence[str]
  ) -> abstract.Keystore:
    combined = list(aead_key_names) + list(mac_key_names)
    return mem.MemKeystore(combined)


if __name__ == "__main__":
  absltest.main()
