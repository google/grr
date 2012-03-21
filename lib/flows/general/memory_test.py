#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2012 Google Inc.
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

"""Tests for Memory."""

import os
import StringIO

from grr.client import conf as flags
import logging

from grr.lib import aff4
from grr.lib import maintenance_utils
from grr.lib import test_lib
from grr.proto import jobs_pb2


FLAGS = flags.FLAGS


class TestMemoryDriverDeployment(test_lib.FlowTestsBaseclass):
  """Test the memory driver deployment flow."""

  def testLoadDriverWindows(self):
    """Test the memory driver deployment flow."""

    class MockClient(object):
      """A mock of client state."""

      def InstallDriver(self, _):
        return []

      def UninstallDriver(self, _):
        return []

      def InitializeMemoryDriver(self, _):
        return [jobs_pb2.StatResponse(
            st_size=4294967296,
            pathspec=jobs_pb2.Path(pathtype=jobs_pb2.Path.OS,
                                   path="\\\\.\\gdd"))]

    # Make sure there is a signed driver for our client.
    signing_key = os.path.join(self.key_path, "ca-priv.pem")
    driver_path = AddSignedDriver("MZ Driveeerrrrrr", "mdd.64.signed.sys",
                                  signing_key, token=self.token)
    logging.info("Wrote signed driver to %s", driver_path)

    client = aff4.FACTORY.Create(aff4.ROOT_URN.Add(self.client_id),
                                 "VFSGRRClient", token=self.token)
    client.Set(client.Schema.OS_RELEASE("7"))
    client.Set(client.Schema.SYSTEM("Windows"))
    client.Close()

    # Run the flow in the simulated way
    for _ in test_lib.TestFlowHelper("LoadMemoryDriver", MockClient(),
                                     token=self.token, client_id=self.client_id):
      pass

    device_urn = aff4.ROOT_URN.Add(self.client_id).Add("devices/winmemory")
    fd = aff4.FACTORY.Open(device_urn, mode="r", token=self.token)
    self.assertTrue(fd.Get(fd.Schema.STAT).data.st_size > 100000)


def AddSignedDriver(binary_data, upload_name, signing_key, token):
  """Add a signed driver to the driver repo."""
  driver_binary = StringIO.StringIO(binary_data)

  out_path = maintenance_utils.UploadSignedConfigBlob(
      driver_binary, "/config/drivers", upload_name,
      signing_key=signing_key, token=token)
  return out_path
