#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Tests for the Windows Registry functions."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import platform
import unittest
from absl import app
from absl.testing import absltest

from grr_response_client import vfs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr.test_lib import client_test_lib
from grr.test_lib import test_lib

_LONG_KEY = "🚀a🚀b🚀" * 51  # 255 characters.
_LONG_STRING_VALUE = _LONG_KEY * 10  # 2550 characters.

_REG_VALUES = r"""
@="Default Value"
"foo"=hex:CA,FE,BA,BE,DE,AD,BE,EF
"aaa"="lolcat"
"aba"=dword:ffffffff
"mindword"=dword:0
"dword42"=dword:2a
"maxdword"=dword:ffffffff
"{}"="{}"
""".format(_LONG_KEY, _LONG_STRING_VALUE).strip()

REG_SETUP = r"""Windows Registry Editor Version 5.00
[HKEY_LOCAL_MACHINE\SOFTWARE\GRR_TEST]
{0}

[HKEY_LOCAL_MACHINE\SOFTWARE\GRR_TEST\listnametest]
"bar"="top level value"
"baz"="another value"

[HKEY_LOCAL_MACHINE\SOFTWARE\GRR_TEST\listnametest\bar]
@="default value in subkey"
""".format(_REG_VALUES)

REG_TEARDOWN = r"""Windows Registry Editor Version 5.00
[-HKEY_LOCAL_MACHINE\SOFTWARE\GRR_TEST]
"""


@unittest.skipIf(platform.system() != "Windows", "Registry is Windows-only.")
class RegistryFileTest(absltest.TestCase):

  @classmethod
  def setUpClass(cls):
    super(RegistryFileTest, cls).setUpClass()
    client_test_lib.import_to_registry(REG_TEARDOWN)
    client_test_lib.import_to_registry(REG_SETUP)

  @classmethod
  def tearDownClass(cls):
    super(RegistryFileTest, cls).tearDownClass()
    client_test_lib.import_to_registry(REG_TEARDOWN)

  def testFileStat(self):
    fd = vfs.VFSOpen(
        rdf_paths.PathSpec(
            path=r"/HKEY_LOCAL_MACHINE\SOFTWARE\GRR_TEST\aaa",
            pathtype="REGISTRY"))
    stat = fd.Stat()
    self.assertIn(stat.pathspec.path,
                  "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa")
    self.assertEqual(stat.pathspec.pathtype, "REGISTRY")
    self.assertEqual(stat.st_size, 6)

  def testFileRead(self):
    fd = vfs.VFSOpen(
        rdf_paths.PathSpec(
            path=r"/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa",
            pathtype="REGISTRY"))
    self.assertEqual(fd.Read(-1), b"lolcat")

  def testFileReadLongUnicodeValue(self):
    fd = vfs.VFSOpen(
        rdf_paths.PathSpec(
            path=r"/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/{}".format(_LONG_KEY),
            pathtype="REGISTRY"))
    self.assertEqual(fd.Read(-1).decode("utf-8"), _LONG_STRING_VALUE)

  def testReadMinDword(self):
    fd = vfs.VFSOpen(
        rdf_paths.PathSpec(
            path=r"/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/mindword",
            pathtype="REGISTRY"))
    self.assertEqual(fd.value, 0)

  def testReadMaxDword(self):
    fd = vfs.VFSOpen(
        rdf_paths.PathSpec(
            path=r"/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/maxdword",
            pathtype="REGISTRY"))
    self.assertEqual(fd.value, 0xFFFFFFFF)

  def testReadAnyDword(self):
    fd = vfs.VFSOpen(
        rdf_paths.PathSpec(
            path=r"/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/dword42",
            pathtype="REGISTRY"))
    self.assertEqual(fd.value, 42)

  def testReadMaxDwordAsString(self):
    fd = vfs.VFSOpen(
        rdf_paths.PathSpec(
            path=r"/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/maxdword",
            pathtype="REGISTRY"))
    self.assertEqual(fd.Read(-1), b"4294967295")

  def testListNamesDoesNotListKeyAndValueOfSameNameTwice(self):
    fd = vfs.VFSOpen(
        rdf_paths.PathSpec(
            path=r"/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/listnametest",
            pathtype="REGISTRY"))
    self.assertCountEqual(fd.ListNames(), ["bar", "baz"])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
