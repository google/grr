#!/usr/bin/env python
from absl import app
from absl.testing import absltest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from grr_response_server import command_signer_test_mixin
from grr_response_server import private_key_file_command_signer
from grr.test_lib import test_lib


class PrivateKeyFileCommandSignerTest(
    command_signer_test_mixin.CommandSignerTestMixin,
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

    with test_lib.ConfigOverrider({
        "CommandSigning.ed25519_private_key_file": key_file.full_path,
    }):
      self.signer = (
          private_key_file_command_signer.PrivateKeyFileCommandSigner()
      )


if __name__ == "__main__":
  app.run(test_lib.main)
