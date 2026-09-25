#!/usr/bin/env python
from absl import app
from absl.testing import absltest

from grr_response_server.command_signer import ephemeral_key
from grr_response_server.command_signer import test_mixin
from grr.test_lib import test_lib


class EphemeralKeyCommandSignerTest(
    test_mixin.CommandSignerTestMixin,
    absltest.TestCase,
):

  def setUp(self):
    super().setUp()
    self.signer = ephemeral_key.EphemeralKeyCommandSigner()


if __name__ == "__main__":
  app.run(test_lib.main)
