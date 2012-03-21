#!/usr/bin/env python

# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Tests for flow utils classes."""


from grr.client import conf
from grr.lib import aff4
from grr.lib import aff4
from grr.lib import flow_utils
from grr.lib import test_lib
from grr.proto import jobs_pb2


class TestClientPathHelper(test_lib.GRRBaseTest):
  """Tests for ClientPathHelper class."""

  def testClientPathHelper(self):
    """Test ClientPathHelper."""
    client_id = "C.%016X" % 0

    # Set up a test client
    root_urn = aff4.ROOT_URN.Add(client_id)

    client = aff4.FACTORY.Create(root_urn, "VFSGRRClient", token=self.token)

    # Set up the operating system information
    client.Set(client.Schema.SYSTEM("Windows"))

    client.Set(client.Schema.OS_RELEASE("7"))

    client.Set(client.Schema.OS_VERSION("6.1.7600"))

    # Add a user account to the client
    users_list = client.Schema.USER()

    user_account = jobs_pb2.UserAccount(username="Administrator",
                                        comment="Built-in account for "
                                        "administering the computer/domain",
                                        last_logon=1296205801,
                                        domain="MYDOMAIN",
                                        homedir="C:\\Users\\Administrator")

    users_list.Append(user_account)

    client.AddAttribute(client.Schema.USER,
                        users_list)

    client.Close()

    # Run tests
    path_helper = flow_utils.ClientPathHelper(client_id, token=self.token)

    self.assertEqual(path_helper.GetPathSeparator(),
                     u"\\")

    self.assertEqual(path_helper.GetDefaultUsersPath(),
                     u"C:\\Users")

    self.assertEqual(path_helper.GetHomeDirectory("Administrator"),
                     u"C:\\Users\\Administrator")


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  conf.StartMain(main)
