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

"""Test client utility functions."""


import exceptions
import imp
import sys
from grr.client import conf
from grr.client import client_utils_linux
from grr.lib import test_lib
from grr.proto import jobs_pb2




def GetVolumePathName(_):
  return "C:\\"


def GetVolumeNameForVolumeMountPoint(_):
  return "\\\\?\\Volume{11111}\\"


class ClientUtilsTest(test_lib.GRRBaseTest):
  """Test the client utils."""

  def testLinuxSplitPathspec(self):
    """Test linux split pathspec functionality."""

    def MockGetMountpoints():
      return {"/dev/sda1": ["/"],
              "/dev/sdb1": ["/mnt/ext", "/home/test/ext"]}

    testdata = {"/home/test": ["/dev/sda1", "/", "home/test"],
                "/home/test/file": ["/dev/sda1", "/", "home/test/file"],
                "/home/test/ext/file": ["/dev/sdb1", "/home/test/ext", "/file"],
                "/dev/sda1/home": ["/dev/sda1", "/", "/home"],
                "/dev/sdb1/home": ["/dev/sdb1", "/mnt/ext", "/home"],
                "//././../.././/home///test/": ["/dev/sda1", "/", "home/test"],
               }

    for path, results in testdata.items():
      pb = jobs_pb2.Path(path=path, pathtype=0)
      res = client_utils_linux.LinSplitPathspec(pb, MockGetMountpoints)
      self.assertEqual(res.device, results[0])
      self.assertEqual(res.mountpoint, results[1])
      self.assertEqual(res.path, results[2])

  def setupWinEnvironment(self):
    """Mock windows includes."""

    winreg = imp.new_module("_winreg")
    winreg.error = exceptions.Exception
    sys.modules["_winreg"] = winreg

    pywintypes = imp.new_module("pywintypes")
    sys.modules["pywintypes"] = pywintypes

    winfile = imp.new_module("win32file")
    winfile.GetVolumeNameForVolumeMountPoint = GetVolumeNameForVolumeMountPoint
    winfile.GetVolumePathName = GetVolumePathName
    sys.modules["win32file"] = winfile

  def testWinSplitPathspec(self):
    """Test windows split pathspec functionality."""

    self.setupWinEnvironment()

    # We need to import after setupWinEnvironment or this will fail
    from grr.client import client_utils_windows

    testdata = {r"C:\Windows": ["\\\\.\\Volume{11111}\\", "C:\\", "Windows"],
                r"C:\\Windows\\": ["\\\\.\\Volume{11111}\\", "C:\\", "Windows"],
                r"C:\\": ["\\\\.\\Volume{11111}\\", "C:\\", ""],
                r"\\\\.\\Volume{11111}\\Windows\\":
                ["\\\\.\\Volume{11111}\\", "C:\\", "Windows"],
                r"Volume{11111}\\Windows\\":
                ["\\\\.\\Volume{11111}\\", "C:\\", "Windows"],
               }

    for path, results in testdata.items():
      pb = jobs_pb2.Path(path=path, pathtype=0)
      res = client_utils_windows.WinSplitPathspec(pb)
      self.assertEqual(res.device, results[0])
      self.assertEqual(res.mountpoint, results[1])
      self.assertEqual(res.path, results[2])

    sys.path.pop()


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  conf.StartMain(main)
