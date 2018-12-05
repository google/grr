#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_server import aff4
from grr_response_server.aff4_objects import users
from grr.test_lib import acl_test_lib
from grr.test_lib import aff4_test_lib
from grr.test_lib import test_lib


class UsersTest(aff4_test_lib.AFF4ObjectTest, acl_test_lib.AclTestMixin):

  def setUp(self):
    super(UsersTest, self).setUp()

    self.user = aff4.FACTORY.Create(
        "aff4:/users/foo", aff4_type=users.GRRUser, mode="rw", token=self.token)
    self.user.Flush()

  def testDescribe(self):
    self.user.AddLabels(["test1", "test2"])
    describe_str = self.user.Describe()
    self.assertIn("test1", describe_str)
    self.assertIn("test2", describe_str)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
