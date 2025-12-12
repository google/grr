#!/usr/bin/env python
import stat

from absl.testing import absltest

from grr_response_proto import jobs_pb2
from grr_response_server import rrg_winreg
from grr_response_proto.rrg import winreg_pb2 as rrg_winreg_pb2
from grr_response_proto.rrg.action import list_winreg_keys_pb2 as rrg_list_winreg_keys_pb2
from grr_response_proto.rrg.action import list_winreg_values_pb2 as rrg_list_winreg_values_pb2


class KeyGlobTest(absltest.TestCase):

  def testRoot_Empty(self):
    key_glob = rrg_winreg.KeyGlob("")
    self.assertEqual(key_glob.root, "")
    self.assertEqual(key_glob.root_level, 0)

  def testRoot_Literal(self):
    key_glob = rrg_winreg.KeyGlob(r"Foo\Bar\Baz")
    self.assertEqual(key_glob.root, r"Foo\Bar\Baz")
    self.assertEqual(key_glob.root_level, 0)

  def testRoot_Star_Leaf(self):
    key_glob = rrg_winreg.KeyGlob(r"Foo\Bar\*")
    self.assertEqual(key_glob.root, r"Foo\Bar")
    self.assertEqual(key_glob.root_level, 1)

  def testRoot_Star_NonLeaf(self):
    key_glob = rrg_winreg.KeyGlob(r"Foo\*\Baz")
    self.assertEqual(key_glob.root, "Foo")
    self.assertEqual(key_glob.root_level, 2)

  def testRoot_Star_Multiple(self):
    key_glob = rrg_winreg.KeyGlob(r"Foo\*\*")
    self.assertEqual(key_glob.root, "Foo")
    self.assertEqual(key_glob.root_level, 2)

  def testRoot_Recursive_Leaf(self):
    key_glob = rrg_winreg.KeyGlob(r"Foo\Bar\**2")
    self.assertEqual(key_glob.root, r"Foo\Bar")
    self.assertEqual(key_glob.root_level, 2)

  def testRoot_Recursive_NonLeaf(self):
    key_glob = rrg_winreg.KeyGlob(r"Foo\**2\Baz")
    self.assertEqual(key_glob.root, "Foo")
    self.assertEqual(key_glob.root_level, 3)

  def testRoot_Recursive_Default_Leaf(self):
    key_glob = rrg_winreg.KeyGlob(r"Foo\Bar\**")
    self.assertEqual(key_glob.root, r"Foo\Bar")
    self.assertEqual(key_glob.root_level, 3)

  def testRoot_Recursive_Default_NonLeaf(self):
    key_glob = rrg_winreg.KeyGlob(r"Foo\**\Baz")
    self.assertEqual(key_glob.root, r"Foo")
    self.assertEqual(key_glob.root_level, 4)

  def testRoot_Mixed(self):
    key_glob = rrg_winreg.KeyGlob(r"Foo\Bar\*\Baz\**2\Quux")
    self.assertEqual(key_glob.root, r"Foo\Bar")
    self.assertEqual(key_glob.root_level, 5)

  def testRegex_Literal(self):
    regex = rrg_winreg.KeyGlob(r"Foo\Bar\Baz").regex
    self.assertEqual(regex.pattern, r"^Foo\\Bar\\Baz$")
    self.assertRegex(r"Foo\Bar\Baz", regex)
    self.assertNotRegex(r"Foo\Bar\Quux", regex)
    self.assertNotRegex(r"Foo\Quux\Baz", regex)

  def testRegex_Star_Root_Leaf(self):
    regex = rrg_winreg.KeyGlob("*").regex
    self.assertEqual(regex.pattern, r"^[^\\]*$")
    self.assertRegex("Foo", regex)
    self.assertRegex("Bar", regex)
    self.assertNotRegex(r"Foo\Bar", regex)

  def testRegex_Star_Root_NonLeaf(self):
    regex = rrg_winreg.KeyGlob(r"*\Bar").regex
    self.assertEqual(regex.pattern, r"^[^\\]*\\Bar$")
    self.assertRegex(r"Foo\Bar", regex)
    self.assertRegex(r"Quux\Bar", regex)
    self.assertNotRegex(r"Foo\Baz", regex)

  def testRegex_Star_Leaf(self):
    regex = rrg_winreg.KeyGlob(r"Foo\Bar\*").regex
    self.assertEqual(regex.pattern, r"^Foo\\Bar\\[^\\]*$")
    self.assertRegex(r"Foo\Bar\Baz", regex)
    self.assertRegex(r"Foo\Bar\Quux", regex)
    self.assertRegex(r"Foo\Bar\Norf", regex)
    self.assertNotRegex(r"Foo\Baz\Quux", regex)
    self.assertNotRegex(r"Foo\Bar\Quux\Norf", regex)

  def testRegex_Star_NonLeaf(self):
    regex = rrg_winreg.KeyGlob(r"Foo\*\Baz").regex
    self.assertEqual(regex.pattern, r"^Foo\\[^\\]*\\Baz$")
    self.assertRegex(r"Foo\Bar\Baz", regex)
    self.assertRegex(r"Foo\Quux\Baz", regex)
    self.assertRegex(r"Foo\Norf\Baz", regex)
    self.assertNotRegex(r"Foo\Quux\Bar", regex)
    self.assertNotRegex(r"Foo\Bar\Baz\Norf", regex)

  def testRegex_Star_Multiple(self):
    regex = rrg_winreg.KeyGlob(r"Foo\*\*").regex
    self.assertEqual(regex.pattern, r"^Foo\\[^\\]*\\[^\\]*$")
    self.assertRegex(r"Foo\Bar\Baz", regex)
    self.assertRegex(r"Foo\Bar\Quux", regex)
    self.assertRegex(r"Foo\Quux\Baz", regex)
    self.assertRegex(r"Foo\Quux\Norf", regex)
    self.assertNotRegex(r"Foo\Bar\Baz\Quux", regex)

  def testRegex_Recursive_Leaf(self):
    regex = rrg_winreg.KeyGlob(r"Foo\**2").regex
    self.assertEqual(regex.pattern, r"^Foo(\\[^\\]*){0,2}$")
    self.assertRegex(r"Foo\Bar", regex)
    self.assertRegex(r"Foo\Baz", regex)
    self.assertRegex(r"Foo\Bar\Baz", regex)
    self.assertRegex(r"Foo\Bar\Quux", regex)
    self.assertNotRegex(r"Foo\Bar\Baz\Quux", regex)

  def testRegex_Recursive_NonLeaf(self):
    regex = rrg_winreg.KeyGlob(r"Foo\**2\Bar").regex
    self.assertEqual(regex.pattern, r"^Foo(\\[^\\]*){0,2}\\Bar$")
    self.assertRegex(r"Foo\Bar", regex)
    self.assertRegex(r"Foo\Baz\Bar", regex)
    self.assertRegex(r"Foo\Quux\Bar", regex)
    self.assertRegex(r"Foo\Baz\Quux\Bar", regex)
    self.assertNotRegex(r"Foo\Baz", regex)
    self.assertNotRegex(r"Foo\Quux\Baz", regex)
    self.assertNotRegex(r"Foo\Baz\Quux\Norf\Bar", regex)

  def testRegex_Recursive_Default_Leaf(self):
    regex = rrg_winreg.KeyGlob(r"Foo\**").regex
    self.assertEqual(regex.pattern, r"^Foo(\\[^\\]*){0,3}$")
    self.assertRegex(r"Foo\Bar", regex)
    self.assertRegex(r"Foo\Baz", regex)
    self.assertRegex(r"Foo\Bar\Baz", regex)
    self.assertRegex(r"Foo\Bar\Quux", regex)
    self.assertRegex(r"Foo\Bar\Baz\Quux", regex)
    self.assertNotRegex(r"Foo\Bar\Baz\Quux\Norf", regex)

  def testRegex_Recursive_Default_NonLeaf(self):
    regex = rrg_winreg.KeyGlob(r"Foo\**\Bar").regex
    self.assertEqual(regex.pattern, r"^Foo(\\[^\\]*){0,3}\\Bar$")
    self.assertRegex(r"Foo\Bar", regex)
    self.assertRegex(r"Foo\Baz\Bar", regex)
    self.assertRegex(r"Foo\Quux\Bar", regex)
    self.assertRegex(r"Foo\Baz\Quux\Bar", regex)
    self.assertRegex(r"Foo\Baz\Quux\Norf\Bar", regex)
    self.assertNotRegex(r"Foo\Baz", regex)
    self.assertNotRegex(r"Foo\Baz\Quux\Norf\Thud\Bar", regex)

  def testRecursive_Root_Leaf(self):
    regex = rrg_winreg.KeyGlob("**2").regex
    self.assertEqual(regex.pattern, r"^[^\\]*(\\[^\\]*){0,1}$")
    self.assertRegex("Foo", regex)
    self.assertRegex("Bar", regex)
    self.assertRegex(r"Foo\Bar", regex)
    self.assertRegex(r"Foo\Quux", regex)
    self.assertNotRegex(r"Foo\Bar\Quux", regex)

  def testRecursive_Root_NonLeaf(self):
    regex = rrg_winreg.KeyGlob(r"**2\Bar").regex
    self.assertEqual(regex.pattern, r"^[^\\]*(\\[^\\]*){0,1}\\Bar$")
    self.assertRegex(r"Foo\Bar", regex)
    self.assertRegex(r"Quux\Bar", regex)
    self.assertRegex(r"Foo\Quux\Bar", regex)
    self.assertNotRegex(r"Foo\Baz", regex)
    self.assertNotRegex(r"Foo\Quux\Baz", regex)
    self.assertNotRegex(r"Foo\Quux\Norf\Bar", regex)

  def testRecursive_Root_Default_Leaf(self):
    regex = rrg_winreg.KeyGlob("**").regex
    self.assertEqual(regex.pattern, r"^[^\\]*(\\[^\\]*){0,2}$")
    self.assertRegex("Foo", regex)
    self.assertRegex("Bar", regex)
    self.assertRegex(r"Foo\Bar", regex)
    self.assertRegex(r"Foo\Quux", regex)
    self.assertRegex(r"Foo\Bar\Quux", regex)
    self.assertNotRegex(r"Foo\Bar\Quux\Norf", regex)

  def testRecursive_Root_Default_NonLeaf(self):
    regex = rrg_winreg.KeyGlob(r"**\Bar").regex
    self.assertEqual(regex.pattern, r"^[^\\]*(\\[^\\]*){0,2}\\Bar$")
    self.assertRegex(r"Foo\Bar", regex)
    self.assertRegex(r"Quux\Bar", regex)
    self.assertRegex(r"Foo\Quux\Bar", regex)
    self.assertRegex(r"Foo\Quux\Norf\Bar", regex)
    self.assertNotRegex(r"Foo\Baz", regex)
    self.assertNotRegex(r"Foo\Quux\Baz", regex)
    self.assertNotRegex(r"Foo\Quux\Norf\Baz", regex)
    self.assertNotRegex(r"Foo\Quux\Norf\Thud\Bar", regex)


class StatEntryOfKeyResultTest(absltest.TestCase):

  def testSimple(self):
    result = rrg_list_winreg_keys_pb2.Result()
    result.root = rrg_winreg_pb2.PredefinedKey.LOCAL_MACHINE
    result.key = r"SOFTWARE\Google"
    result.subkey = "Chrome"

    stat_entry = rrg_winreg.StatEntryOfKeyResult(result)
    self.assertEqual(
        stat_entry.pathspec.pathtype,
        jobs_pb2.PathSpec.PathType.REGISTRY,
    )
    self.assertEqual(
        stat_entry.pathspec.path,
        r"HKEY_LOCAL_MACHINE\SOFTWARE\Google\Chrome",
    )
    self.assertTrue(stat.S_ISDIR(stat_entry.st_mode))


class StatEntryOfValueResultTest(absltest.TestCase):

  def testString(self):
    result = rrg_list_winreg_values_pb2.Result()
    result.root = rrg_winreg_pb2.LOCAL_MACHINE
    result.key = r"SOFTWARE\Windows NT\CurrentVersion"
    result.value.name = "SystemRoot"
    result.value.string = "C:\\Windows"

    stat_entry = rrg_winreg.StatEntryOfValueResult(result)
    self.assertEqual(
        stat_entry.pathspec.pathtype,
        jobs_pb2.PathSpec.PathType.REGISTRY,
    )
    self.assertEqual(
        stat_entry.pathspec.path,
        r"HKEY_LOCAL_MACHINE\SOFTWARE\Windows NT\CurrentVersion\SystemRoot",
    )
    self.assertEqual(
        stat_entry.registry_type,
        jobs_pb2.StatEntry.REG_SZ,
    )
    self.assertEqual(
        stat_entry.registry_data.string,
        "C:\\Windows",
    )

  def testDefault(self):
    result = rrg_list_winreg_values_pb2.Result()
    result.root = rrg_winreg_pb2.CLASSES_ROOT
    result.key = r".txt"
    result.value.string = "txtfilelegacy"

    stat_entry = rrg_winreg.StatEntryOfValueResult(result)
    self.assertEqual(
        stat_entry.pathspec.pathtype,
        jobs_pb2.PathSpec.PathType.REGISTRY,
    )
    self.assertEqual(
        stat_entry.pathspec.path,
        r"HKEY_CLASSES_ROOT\.txt",
    )
    self.assertEqual(
        stat_entry.registry_type,
        jobs_pb2.StatEntry.REG_SZ,
    )
    self.assertEqual(
        stat_entry.registry_data.string,
        "txtfilelegacy",
    )


if __name__ == "__main__":
  absltest.main()
