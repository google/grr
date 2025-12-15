#!/usr/bin/env python
"""Tests for config_lib classes."""

import os
import platform
import stat
from typing import Any

from absl.testing import absltest

from grr_response_core.lib import config_parser
from grr_response_core.lib.util import temp


class IniConfigFileParserTest(absltest.TestCase):

  def testReadsRawDataCorrectly(self):
    with temp.AutoTempFilePath() as path:
      with open(path, "w") as fd:
        fd.write("""
[Section1]
test = val2
""")

      p = config_parser.IniConfigFileParser(path)
      self.assertEqual(p.ReadData(), {"Section1.test": "val2"})

  def testSavesRawDataCorrectly(self):
    with temp.AutoTempFilePath() as path:
      p = config_parser.IniConfigFileParser(path)
      p.SaveData({"Section1.test": "val2"})

      with open(path, "r") as fd:
        self.assertEqual(fd.read(), "[DEFAULT]\nSection1.test = val2\n\n")

  def testCopyPointsToTheSameConfigPath(self):
    p = config_parser.IniConfigFileParser("foo/bar")
    p_copy = p.Copy()
    self.assertNotEqual(p, p_copy)
    self.assertEqual(p_copy.config_path, "foo/bar")

  def testReturnsEmptyDictWhenFileIsMissing(self):
    with temp.AutoTempFilePath() as path:
      p = config_parser.IniConfigFileParser(path)
      self.assertEqual(p.ReadData(), {})

  # Windows permissions system is different from Unix and Windows clients use
  # registry-based parsers anyway. No practical need to make this
  # test Windows-compatible.
  @absltest.skipIf(platform.system() == "Windows", "Non-Windows only test")
  def testRaisesWhenFileIsNotAccessible(self):
    with temp.AutoTempFilePath() as path:
      with open(path, "w") as fd:
        fd.write("")
      os.chmod(path, stat.S_IWUSR)

      with self.assertRaises(config_parser.ReadDataPermissionError):
        p = config_parser.IniConfigFileParser(path)
        p.ReadData()

  def testRaisesWhenReadingAndConfigPathEmpty(self):
    p = config_parser.IniConfigFileParser("")
    with self.assertRaises(config_parser.ReadDataPathNotSpecifiedError):
      p.ReadData()

  def testRaisesWhenSavingAndConfigPathEmpty(self):
    p = config_parser.IniConfigFileParser("")
    with self.assertRaises(config_parser.SaveDataPathNotSpecifiedError):
      p.SaveData({})


class YamlConfigFileParserTest(absltest.TestCase):

  def testReadsRawDataCorrectly(self):
    with temp.AutoTempFilePath() as path:
      with open(path, "w") as fd:
        fd.write("""
Section1:
  test: val2
""")

      p = config_parser.YamlConfigFileParser(path)
      self.assertEqual(p.ReadData(), {"Section1": {"test": "val2"}})

  def testSavesRawDataCorrectly(self):
    with temp.AutoTempFilePath() as path:
      p = config_parser.YamlConfigFileParser(path)
      p.SaveData({"Section1": {"test": "val2"}})

      with open(path, "r") as fd:
        self.assertEqual(fd.read(), "Section1:\n  test: val2\n")

  def testCopyPointsToTheSameConfigPath(self):
    p = config_parser.YamlConfigFileParser("foo/bar")
    p_copy = p.Copy()
    self.assertNotEqual(p, p_copy)
    self.assertEqual(p_copy.config_path, "foo/bar")

  def testReturnsEmptyDictWhenFileIsMissing(self):
    with temp.AutoTempFilePath() as path:
      p = config_parser.YamlConfigFileParser(path)
      self.assertEqual(p.ReadData(), {})

  # Windows permissions system is different from Unix and Windows clients use
  # registry-based parsers anyway. No practical need to make this
  # test Windows-compatible.
  @absltest.skipIf(platform.system() == "Windows", "Non-Windows only test")
  def testRaisesWhenFileIsNotAccessible(self):
    with temp.AutoTempFilePath() as path:
      with open(path, "w") as fd:
        fd.write("")
      os.chmod(path, stat.S_IWUSR)

      with self.assertRaises(config_parser.ReadDataPermissionError):
        p = config_parser.YamlConfigFileParser(path)
        p.ReadData()

  def testRaisesWhenReadingAndConfigPathEmpty(self):
    p = config_parser.YamlConfigFileParser("")
    with self.assertRaises(config_parser.ReadDataPathNotSpecifiedError):
      p.ReadData()

  def testRaisesWhenSavingAndConfigPathEmpty(self):
    p = config_parser.YamlConfigFileParser("")
    with self.assertRaises(config_parser.SaveDataPathNotSpecifiedError):
      p.SaveData({})


class StubFileParser(config_parser.GRRConfigFileParser):

  def RawDataToBytes(self, raw_data: dict[Any, Any]) -> bytes:
    return b"to_bytes"

  def RawDataFromBytes(self, b: bytes) -> dict[Any, Any]:
    return {"from_bytes": b}


class FileParserDataWrapperTest(absltest.TestCase):

  def testRaisesOnSave(self):
    p = config_parser.FileParserDataWrapper(b"foo", StubFileParser(""))
    with self.assertRaises(config_parser.SaveDataError):
      p.SaveData({})

  def testForwardsDataToNestedParserOnRead(self):
    p = config_parser.FileParserDataWrapper(b"foo", StubFileParser(""))
    self.assertEqual(
        p.ReadData(),
        {
            "from_bytes": b"foo",
        },
    )


if __name__ == "__main__":
  absltest.main()
