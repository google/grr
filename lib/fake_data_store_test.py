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

"""Tests the fake data store - in memory implementation."""



from grr.client import conf
from grr.client import conf as flags

# pylint: disable=W0611
# Support bt storage
from grr.lib import data_store
# pylint: enable=W0611

from grr.lib import data_store_test
from grr.lib import registry
from grr.lib import test_lib

FLAGS = flags.FLAGS


class FakeDataStoreTest(data_store_test.DataStoreTest):
  """Test the fake data store."""


def main(args):
  FLAGS.storage = "FakeDataStore"
  registry.Init()
  test_lib.main(args)

if __name__ == "__main__":
  conf.StartMain(main)
