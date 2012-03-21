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


"""Tests for administrative flows."""



from grr.client import conf as flags

from grr.client import conf
from grr.lib import aff4
from grr.lib import test_lib
from grr.proto import jobs_pb2


FLAGS = flags.FLAGS


class TestClientConfigHandling(test_lib.FlowTestsBaseclass):
  """Test the GetConfig flow."""

  def testUpdateConfig(self):
    """Ensure we can retrieve the config."""
    pass
    # # Only mock the pieces we care about.
    # client_mock = test_lib.ActionMock("GetConfig", "UpdateConfig")
    # # Fix up the client actions to not use /etc.
    # conf.FLAGS.config = FLAGS.test_tmpdir + "/config.ini"
    # loc = "http://www.example.com"
    # grr_config = jobs_pb2.GRRConfig(location=loc,
    #                                 foreman_check_frequency=3600,
    #                                 poll_min=1)
    # # Write the config.
    # for _ in test_lib.TestFlowHelper("UpdateConfig", client_mock,
    #                                  client_id=self.client_id,
    #                                  token=self.token,
    #                                  grr_config=grr_config):
    #   pass

    # # Now retrieve it again to see if it got written.
    # for _ in test_lib.TestFlowHelper("Interrogate", client_mock,
    #                                  token=self.token,
    #                                  client_id=self.client_id):
    #   pass

    # urn = aff4.ROOT_URN.Add(self.client_id)
    # fd = aff4.FACTORY.Open(urn, token=self.token)
    # config_dat = fd.Get(fd.Schema.GRR_CONFIG)
    # self.assertEqual(config_dat.data.location, loc)
    # self.assertEqual(config_dat.data.poll_min, 1)
