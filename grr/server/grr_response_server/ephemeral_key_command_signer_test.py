#!/usr/bin/env python
from absl import app
from absl.testing import absltest

from grr_response_server import command_signer_test_mixin
from grr_response_server import ephemeral_key_command_signer
from grr.test_lib import test_lib


class EphemeralKeyCommandSignerTest(
    command_signer_test_mixin.CommandSignerTestMixin,
    absltest.TestCase,
):

  def setUp(self):
    super().setUp()
    self.signer = ephemeral_key_command_signer.EphemeralKeyCommandSigner()


if __name__ == "__main__":
  app.run(test_lib.main)
