#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.
"""Tests for grr_response_cleint.osx.objc.

These tests don't have OS X dependencies and will run on linux.
"""

import ctypes
from unittest import mock

from absl import app

from grr_response_client.osx import objc
from grr.test_lib import test_lib


class ObjcTest(test_lib.GRRBaseTest):

  def setUp(self):
    super().setUp()

    self.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    self.restype = ctypes.c_void_p
    self.cftable = [("CFMockFunc", self.argtypes, self.restype)]

  @mock.patch("ctypes.util.find_library")
  def testSetCTypesForLibraryLibNotFound(self, find_library_mock):
    find_library_mock.return_value = None

    with self.assertRaises(objc.ErrorLibNotFound):
      objc._SetCTypesForLibrary("mock", self.cftable)

      # Check that the first argument of the first find_library call is "mock".
      find_library_mock.assert_called_with("mock")

  @mock.patch("ctypes.util.find_library")
  @mock.patch("ctypes.cdll.LoadLibrary")
  def testLoadLibraryUsesWellKnownPathAsFallback(self, load_library_mock,
                                                 find_library_mock):
    mock_cdll = mock.Mock()
    find_library_mock.return_value = None
    load_library_mock.side_effect = [OSError("not found"), mock_cdll]

    result = objc.LoadLibrary("Foobazzle")

    self.assertGreaterEqual(load_library_mock.call_count, 1)
    load_library_mock.assert_called_with(
        "/System/Library/Frameworks/Foobazzle.framework/Foobazzle")
    self.assertIs(result, mock_cdll)

  @mock.patch("ctypes.util.find_library")
  @mock.patch("ctypes.cdll.LoadLibrary")
  def testLoadLibraryTriesLoadingSharedLoadedLibrary(self, load_library_mock,
                                                     find_library_mock):
    mock_cdll = mock.Mock()

    def _LoadLibrary(libpath):
      if libpath is None:
        return mock_cdll
      else:
        raise OSError("not found")

    find_library_mock.return_value = None
    load_library_mock.side_effect = _LoadLibrary

    loaded_lib_name = next(iter(objc._LOADED_SHARED_LIBRARIES))
    result = objc.LoadLibrary(loaded_lib_name)

    self.assertGreaterEqual(load_library_mock.call_count, 1)
    load_library_mock.assert_called_with(None)
    self.assertIs(result, mock_cdll)

  @mock.patch("ctypes.util.find_library")
  @mock.patch("ctypes.cdll.LoadLibrary")
  def testSetCTypesForLibrary(self, load_library_mock, find_library_mock):

    mock_dll = mock.MagicMock()

    find_library_mock.return_value = "/mock/path"
    load_library_mock.return_value = mock_dll

    dll = objc._SetCTypesForLibrary("mock", self.cftable)

    find_library_mock.assert_called_with("mock")
    self.assertEqual(dll.CFMockFunc.argtypes, self.argtypes)
    self.assertEqual(dll.CFMockFunc.restype, self.restype)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
