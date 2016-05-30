#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.
"""Tests for grr.client.lib.osx.objc.

These tests don't have OS X dependencies and will run on linux.
"""



import ctypes
import mox

from grr.client.osx import objc
from grr.lib import flags
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
    self.cftable = [('CFMockFunc', self.argtypes, self.restype)]

  def tearDown(self):
    self.mox.UnsetStubs()

  def testSetCTypesForLibraryLibNotFound(self):
    objc.ctypes.util.find_library('mock').AndReturn(None)
    self.mox.ReplayAll()
    self.assertRaises(objc.ErrorLibNotFound, objc.SetCTypesForLibrary, 'mock',
                      self.cftable)
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
  flags.StartMain(main)
