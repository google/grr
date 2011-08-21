#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

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


"""OSX tests."""



import os


from grr.client import conf
from grr.client import conf as flags

# Populate the action registry
from grr.client import client_actions
from grr.client import conf
from grr.client import vfs
from grr.client.client_actions.osx import osx
from grr.lib import test_lib
from grr.lib import utils
from grr.proto import jobs_pb2

FLAGS = flags.FLAGS


class OsxClientTests(test_lib.EmptyActionTest):
  """Test reading osx file system."""

  def test64Bit(self):
    """Ensure we can enumerate file systems successfully."""
    path = os.path.join(self.base_path, "osx_fsdata")
    results = osx.ParseFileSystemsStruct(osx.StatFS64Struct, 7,
                                         open(path).read())
    self.assertEquals(len(results), 7)
    self.assertEquals(results[0].f_fstypename, "hfs")
    self.assertEquals(results[0].f_mntonname, "/")
    self.assertEquals(results[0].f_mntfromname, "/dev/disk0s2")
    self.assertEquals(results[2].f_fstypename, "autofs")
    self.assertEquals(results[2].f_mntonname, "/auto")
    self.assertEquals(results[2].f_mntfromname, "map auto.auto")


def main(argv):
  # Initialize the VFS system
  vfs.VFSInit()
  test_lib.main(argv)

if __name__ == "__main__":
  conf.StartMain(main)
