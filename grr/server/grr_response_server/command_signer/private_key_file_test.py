#!/usr/bin/env python
from absl.testing import absltest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from grr_response_server.command_signer import private_key_file
from grr_response_server.command_signer import test_mixin


class PrivateKeyFileCommandSignerTest(
    test_mixin.CommandSignerTestMixin,
    absltest.TestCase,
):

  def setUp(self):
    super().setUp()
    key_file = self.create_tempfile(mode="wb")
    key_file.write_bytes(
        ed25519.Ed25519PrivateKey.generate().private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    self.signer = private_key_file.PrivateKeyFileCommandSigner.FromPath(
        key_file.full_path
    )


if __name__ == "__main__":
  absltest.main()
