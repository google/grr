#!/usr/bin/env python
import contextlib
import os
import platform
import subprocess
from absl.testing import absltest

from grr_response_client_builder.repackers import cab_utils
from grr_response_core.lib import utils


@absltest.skipIf(platform.system() != "Windows", "Windows only test")
class CabUtilsTest(absltest.TestCase):
  _FILES = [
      ("a", 123456),
      ("b", 67345),
      ("c", 1),
      ("d", 123),
      ("e", 12345),
      ("f", 3000000),
  ]

  def setUp(self):
    super().setUp()

    stack = contextlib.ExitStack()
    self.addCleanup(stack.close)

    self._tmp_dir = stack.enter_context(utils.TempDirectory())

  def _TempPath(self, *components: str) -> str:
    return os.path.join(self._tmp_dir, *components)

  def _CreateFiles(self) -> str:
    directory = self._TempPath("files")
    for name, size in self._FILES:
      path = os.path.join(directory, name)
      dirname = os.path.dirname(path)
      utils.EnsureDirExists(dirname)
      data = os.urandom(size)
      with open(path, "wb") as f:
        f.write(data)
    return directory

  def _MakeCab(self, directory: str, out_file: str) -> None:

    file_list = self._TempPath("file_list")
    with open(file_list, "w") as f:
      for name, _ in self._FILES:
        print(name, file=f)

    subprocess.check_call([
        "c:\\Windows\\System32\\makecab.exe",
        "/f",
        file_list,
        "/d",
        "CabinetName1=" + os.path.basename(out_file),
        "/D",
        "DiskDirectoryTemplate=" + os.path.dirname(out_file),
        "/D",
        f"MaxCabinetSize={10 * 1024 * 1024}",
        "/D",
        f"MaxDiskSize={10 * 1024 * 1024}",
    ],
                          cwd=directory)

  def _Expand(self, cab_path: str, dst_dir: str) -> None:
    utils.EnsureDirExists(dst_dir)
    subprocess.check_call([
        "c:\\Windows\\System32\\expand.exe",
        "-F:*",
        cab_path,
        ".",
    ],
                          cwd=dst_dir)

  def _AssertFileEquals(self, path1: str, path2: str) -> None:
    with open(path1, "rb") as f:
      data1 = f.read()
    with open(path2, "rb") as f:
      data2 = f.read()
    self.assertEqual(data1, data2)

  def testExtractFiles(self):
    files_dir = self._CreateFiles()
    cab_path = self._TempPath("foo.cab")

    self._MakeCab(files_dir, cab_path)

    cab_tmp_dir = self._TempPath("cab_tmp_dir")
    cab = cab_utils.Cab(cab_path, cab_tmp_dir)
    cab.ExtractFiles()

    for name, _ in self._FILES:
      self._AssertFileEquals(
          os.path.join(cab.file_path_base, name), os.path.join(files_dir, name))

  def testPack(self):
    files_dir = self._CreateFiles()
    cab_path = self._TempPath("foo.cab")

    self._MakeCab(files_dir, cab_path)

    cab = cab_utils.Cab(cab_path, self._TempPath("cab_tmp_dir"))
    cab.ExtractFiles()

    a_new_data = os.urandom(256367)
    cab.WriteFile("d", a_new_data)

    cab_repacked_path = self._TempPath("foo_repacked.cab")
    cab.Pack(cab_repacked_path)

    extracted_dir = self._TempPath("foo_repacked_extracted")
    self._Expand(cab_repacked_path, extracted_dir)

    with open(os.path.join(extracted_dir, "d"), "rb") as f:
      self.assertEqual(f.read(), a_new_data)

    for name, _ in self._FILES:
      if name in ("d",):
        continue
      self._AssertFileEquals(
          os.path.join(files_dir, name), os.path.join(extracted_dir, name))

  def testPadCabFile(self):
    files_dir = self._CreateFiles()
    cab_path = self._TempPath("foo.cab")
    self._MakeCab(files_dir, cab_path)
    padded_cab_path = self._TempPath("foo_paded.cab")
    new_size = os.path.getsize(cab_path) + 123435
    cab_utils.PadCabFile(cab_path, padded_cab_path, new_size)
    self.assertEqual(os.path.getsize(padded_cab_path), new_size)
    extracted_dir = self._TempPath("extracted")
    self._Expand(padded_cab_path, extracted_dir)
    for name, _ in self._FILES:
      # Test that the file extracted from the padded CAB file hasn't changed.
      # (That it is still the same as the original file.)
      self._AssertFileEquals(
          os.path.join(files_dir, name), os.path.join(extracted_dir, name))


if __name__ == "__main__":
  absltest.main()
