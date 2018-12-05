#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.
"""Tests for grr_response_cleint.osx.objc.

These tests don't have OS X dependencies and will run on linux.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import ctypes
import mock

from grr_response_client.osx import objc
from grr_response_core.lib import flags
from grr.test_lib import test_lib


class ObjcTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(ObjcTest, self).setUp()

    self.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    self.restype = ctypes.c_void_p
    self.cftable = [("CFMockFunc", self.argtypes, self.restype)]

  @mock.patch(
      "grr_response_client.osx.objc.ctypes.util"
      ".find_library")
  def testSetCTypesForLibraryLibNotFound(self, find_library_mock):
    find_library_mock.return_value = None

    with self.assertRaises(objc.ErrorLibNotFound):
      objc.SetCTypesForLibrary("mock", self.cftable)

      # Check that hte first argument of the first find_library call is "mock".
      find_library_mock.assert_called_with("mock")

  @mock.patch(
      "grr_response_client.osx.objc.ctypes.util"
      ".find_library")
  @mock.patch(
      "grr_response_client.osx.objc.ctypes.cdll"
      ".LoadLibrary")
  def testSetCTypesForLibrary(self, load_library_mock, find_library_mock):

    mock_dll = mock.MagicMock()

    find_library_mock.return_value = "/mock/path"
    load_library_mock.return_value = mock_dll

    dll = objc.SetCTypesForLibrary("mock", self.cftable)

    find_library_mock.assert_called_with("mock")
    self.assertEqual(dll.CFMockFunc.argtypes, self.argtypes)
    self.assertEqual(dll.CFMockFunc.restype, self.restype)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
