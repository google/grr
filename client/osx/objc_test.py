#!/usr/bin/env python
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


"""Tests for grr.client.lib.osx.objc."""



import ctypes
import mox

from grr.client import conf
from grr.client.osx import objc
from grr.lib import test_lib


class ObjcTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(ObjcTest, self).setUp()
    self.mox = mox.Mox()
    self.mox.StubOutWithMock(objc.ctypes.util, 'find_library')
    self.mox.StubOutWithMock(objc.ctypes.cdll, 'LoadLibrary')
    self.dll = self.mox.CreateMockAnything()
    self.function = self.mox.CreateMockAnything()
    self.dll.CFMockFunc = self.function
    self.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    self.restype = ctypes.c_void_p
    self.cftable = [
        ('CFMockFunc',
         self.argtypes,
         self.restype)
    ]

  def tearDown(self):
    self.mox.UnsetStubs()

  def testSetCTypesForLibraryLibNotFound(self):
    objc.ctypes.util.find_library('mock').AndReturn(None)
    self.mox.ReplayAll()
    self.assertRaises(objc.ErrorLibNotFound, objc.SetCTypesForLibrary,
                      'mock', self.cftable)
    self.mox.VerifyAll()

  def testSetCTypesForLibrary(self):
    objc.ctypes.util.find_library('mock').AndReturn('/mock/path')
    objc.ctypes.cdll.LoadLibrary('/mock/path').AndReturn(self.dll)
    self.mox.ReplayAll()
    dll = objc.SetCTypesForLibrary('mock', self.cftable)
    self.assertEqual(dll.CFMockFunc.argtypes, self.argtypes)
    self.assertEqual(dll.CFMockFunc.restype, self.restype)
    self.mox.VerifyAll()


def main(argv):
  test_lib.main(argv)

if __name__ == '__main__':
  conf.StartMain(main)
