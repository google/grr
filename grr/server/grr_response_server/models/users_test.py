#!/usr/bin/env python
from absl import app
from absl.testing import absltest

from grr_response_proto import objects_pb2
from grr_response_server.models import users
from grr.test_lib import test_lib


class UsersTest(absltest.TestCase):

  def testGetEmail(self):
    with test_lib.ConfigOverrider({
        "Email.enable_custom_email_address": False,
        "Logging.domain": "localhost",
    }):
      u = objects_pb2.GRRUser(username="foo")
      self.assertEqual("foo@localhost", users.GetEmail(u))

  def testGetEmail_customEmailIgnored(self):
    with test_lib.ConfigOverrider({
        "Email.enable_custom_email_address": False,
        "Logging.domain": "localhost",
    }):
      u = objects_pb2.GRRUser(username="foo", email="bar@baz.org")
      self.assertEqual("foo@localhost", users.GetEmail(u))

  def testGetEmail_customEmailEnabled(self):
    with test_lib.ConfigOverrider({
        "Email.enable_custom_email_address": True,
    }):
      u = objects_pb2.GRRUser(username="foo", email="bar@baz.org")
      self.assertEqual("bar@baz.org", users.GetEmail(u))


def main(argv):
  # Initializes `config.CONFIG`.
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
