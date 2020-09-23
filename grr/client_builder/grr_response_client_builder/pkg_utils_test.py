#!/usr/bin/env python
import contextlib
import os
import platform
import subprocess
import unittest

from absl.testing import absltest

from grr_response_client_builder import pkg_utils
from grr_response_core.lib import utils


class PkgSplitJoinTest(absltest.TestCase):

  def setUp(self):
    super(PkgSplitJoinTest, self).setUp()
    stack = contextlib.ExitStack()
    self.tmp_dir = stack.enter_context(utils.TempDirectory())
    self.addCleanup(stack.close)

  @unittest.skipIf(platform.system() != "Darwin", "requires OSX")
  def testSplitJoin(self):

    def TmpPath(*components):
      result = os.path.join(self.tmp_dir, *components)
      utils.EnsureDirExists(os.path.dirname(result))
      return result

    def TmpDir(*components):
      result = TmpPath(*components)
      utils.EnsureDirExists(result)
      return result

    def WriteFile(path, contents):
      with open(path, "w") as f:
        f.write(contents)

    WriteFile(TmpPath("root_dir", "a", "b", "file1"), "data1")
    WriteFile(TmpPath("root_dir", "a", "b", "file2"), "data2")
    WriteFile(
        TmpPath("scripts", "preinstall"), """#!/bin/sh
      echo the preinstall
      """)
    WriteFile(
        TmpPath("scripts", "postinstall"), """#!/bin/sh
      echo the postinstall
      """)

    subprocess.check_call([
        "pkgbuild",
        "--root",
        TmpPath("root_dir"),
        "--identifier",
        "foo",
        "--scripts",
        TmpPath("scripts"),
        "--version",
        "1.0.0",
        TmpPath("foo.pkg"),
    ])

    WriteFile(
        TmpPath("distribution.xml"), """<?xml version="1.0" encoding="utf-8"?>
       <installer-gui-script minSpecVersion="1">
           <title>foo</title>
           <organization>bar</organization>
           <pkg-ref id="id">
               <bundle-version/>
           </pkg-ref>
           <options customize="never" require-scripts="false"/>
           <choices-outline>
               <line choice="default">
                   <line choice="id"/>
               </line>
           </choices-outline>
           <choice id="default"/>
           <choice id="id" visible="false">
               <pkg-ref id="id"/>
           </choice>
           <pkg-ref id="id" version="1.0.0" onConclusion="none" packageIdentifier="foo">foo.pkg</pkg-ref>
       </installer-gui-script>
       """)

    subprocess.check_call([
        "productbuild",
        "--distribution",
        TmpPath("distribution.xml"),
        "--package-path",
        TmpPath(),
        TmpPath("product.pkg"),
    ])

    pkg_utils.SplitPkg(
        TmpPath("product.pkg"), TmpPath("split"), TmpPath("blocks"))
    pkg_utils.JoinPkg(
        TmpPath("split"), TmpPath("blocks"), TmpPath("joined.pkg"))

    def ExtractCpio(path):
      with open(path) as f:
        subprocess.check_call(["cpio", "-id"],
                              cwd=os.path.dirname(path),
                              stdin=f)
      os.unlink(path)

    def ExtractPackage(package_path, dst_dir):
      subprocess.check_call(["xar", "-x", "-f", package_path], cwd=dst_dir)
      ExtractCpio(os.path.join(dst_dir, "foo.pkg", "Payload"))
      ExtractCpio(os.path.join(dst_dir, "foo.pkg", "Scripts"))

    ExtractPackage(TmpPath("product.pkg"), TmpDir("original"))
    ExtractPackage(TmpPath("joined.pkg"), TmpDir("joined"))

    subprocess.check_call(["diff", "-r", TmpDir("original"), TmpDir("joined")])


if __name__ == "__main__":
  absltest.main()
