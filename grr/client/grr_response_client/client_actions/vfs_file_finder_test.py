#!/usr/bin/env python
"""Tests the client file finder action."""

import contextlib
import hashlib
import os
import platform
from typing import Optional
import unittest
from unittest import mock
import zlib

from absl.testing import absltest
from absl.testing import flagsaver

from grr_response_client import client_utils
from grr_response_client import vfs
from grr_response_client.client_actions import vfs_file_finder
from grr_response_client.client_actions.file_finder_utils import globbing
from grr_response_client.vfs_handlers import files
from grr_response_core import config
from grr_response_core.lib import config_lib
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import precondition
from grr_response_core.lib.util import temp
from grr.test_lib import client_test_lib

_LONG_KEY = "🚀a🚀b🚀" * 51  # 255 characters.
_LONG_STRING_VALUE = _LONG_KEY * 10  # 2550 characters.

_REG_VALUES = """
@="Default Value"
"foo"=hex:CA,FE,BA,BE,DE,AD,BE,EF
"aaa"="lolcat"
"aba"=dword:ffffffff
"{}"="{}"
""".format(_LONG_KEY, _LONG_STRING_VALUE).strip()

REG_SETUP = r"""
Windows Registry Editor Version 5.00

[HKEY_LOCAL_MACHINE\SOFTWARE\GRR_TEST]
{0}

[HKEY_LOCAL_MACHINE\SOFTWARE\GRR_TEST\1]
{0}

[HKEY_LOCAL_MACHINE\SOFTWARE\GRR_TEST\1\2]
{0}

[HKEY_LOCAL_MACHINE\SOFTWARE\GRR_TEST\1\2\3]
{0}

[HKEY_LOCAL_MACHINE\SOFTWARE\GRR_TEST\1\2\3\4]
{0}
""".format(_REG_VALUES).lstrip()

REG_TEARDOWN = r"""
Windows Registry Editor Version 5.00

[-HKEY_LOCAL_MACHINE\SOFTWARE\GRR_TEST]
""".lstrip()


def _DecodeDataBlob(datablob):
  precondition.AssertType(datablob, rdf_protodict.DataBlob)
  raw_value = zlib.decompress(datablob.GetValue())
  return raw_value.decode("utf-8")


def _GroupItemsByType(iterable):
  """Returns a dict, grouping items by the name of their type."""
  results = {}
  for item in iterable:
    results.setdefault(type(item).__name__, []).append(item)
  return results


def _RunFileFinder(
    args: rdf_file_finder.FileFinderArgs,
) -> list[rdf_file_finder.FileFinderResult]:
  results = []

  def SendReply(rdf_value, *args, **kwargs):
    del args, kwargs  # Unused.
    results.append(rdf_value)

  ff = vfs_file_finder.VfsFileFinder()
  ff.grr_worker = mock.MagicMock()
  ff.SendReply = SendReply
  ff.message = rdf_flows.GrrMessage(payload=args)
  ff.Run(args)

  return results


@unittest.skipIf(platform.system() != "Windows", "Skipping Windows-only test.")
class RegistryTest(absltest.TestCase):

  @classmethod
  def setUpClass(cls):
    super(RegistryTest, cls).setUpClass()
    client_test_lib.import_to_registry(REG_TEARDOWN)
    client_test_lib.import_to_registry(REG_SETUP)

  @classmethod
  def tearDownClass(cls):
    super(RegistryTest, cls).tearDownClass()
    client_test_lib.import_to_registry(REG_TEARDOWN)

  def testStatDoesNotFailForInaccessiblePath(self):
    results = _RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SAM/SAM/FOOBAR"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT"),
        )
    )

    self.assertEmpty(results)

  def testCaseInsensitivitiy(self):
    results = _RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/AaA"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT"),
        )
    )

    self.assertLen(results, 1)
    self.assertEqual(
        results[0].stat_entry.pathspec.path,
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa",
    )
    self.assertEqual(results[0].stat_entry.pathspec.pathtype, "REGISTRY")

  def testStatExactPath(self):
    results = _RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT"),
        )
    )

    self.assertLen(results, 1)
    self.assertEqual(
        results[0].stat_entry.pathspec.path,
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa",
    )
    self.assertEqual(results[0].stat_entry.pathspec.pathtype, "REGISTRY")
    self.assertEqual(results[0].stat_entry.st_size, 6)

  def testStatExactPathInWindowsNativeFormat(self):
    results = _RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=[r"HKEY_LOCAL_MACHINE\SOFTWARE\GRR_TEST\aaa"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT"),
        )
    )

    self.assertLen(results, 1)
    self.assertEqual(
        results[0].stat_entry.pathspec.path,
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa",
    )
    self.assertEqual(results[0].stat_entry.pathspec.pathtype, "REGISTRY")
    self.assertEqual(results[0].stat_entry.st_size, 6)

  def testStatLongUnicodeName(self):
    results = _RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=[
                "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/{}".format(_LONG_KEY)
            ],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT"),
        )
    )

    self.assertLen(results, 1)
    self.assertEqual(
        results[0].stat_entry.pathspec.path,
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/{}".format(_LONG_KEY),
    )
    self.assertEqual(results[0].stat_entry.pathspec.pathtype, "REGISTRY")

  def testStatKeyWithDefaultValue(self):
    results = _RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT"),
        )
    )

    self.assertLen(results, 1)
    self.assertEqual(
        results[0].stat_entry.pathspec.path,
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1",
    )
    self.assertEqual(results[0].stat_entry.pathspec.pathtype, "REGISTRY")
    self.assertEqual(results[0].stat_entry.st_size, 13)

  def testDownloadExactPath(self):
    results = _RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="DOWNLOAD"),
        )
    )

    self.assertLen(results, 2)
    self.assertEqual(_DecodeDataBlob(results[0]), "lolcat")
    self.assertEqual(
        results[1].stat_entry.pathspec.path,
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa",
    )

  def testDownloadUnicode(self):
    results = _RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=[
                "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/{}".format(_LONG_KEY)
            ],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="DOWNLOAD"),
        )
    )

    self.assertLen(results, 2)
    res_by_type = _GroupItemsByType(results)

    self.assertEqual(
        _DecodeDataBlob(res_by_type["DataBlob"][0]), _LONG_STRING_VALUE
    )
    self.assertEqual(
        res_by_type["FileFinderResult"][0].stat_entry.pathspec.path,
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/{}".format(_LONG_KEY),
    )

  def testDownloadDword(self):
    results = _RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aba"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="DOWNLOAD"),
        )
    )

    self.assertLen(results, 2)
    res_by_type = _GroupItemsByType(results)

    self.assertEqual(_DecodeDataBlob(res_by_type["DataBlob"][0]), "4294967295")
    self.assertEqual(
        res_by_type["FileFinderResult"][0].stat_entry.pathspec.path,
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aba",
    )

  def testDownloadGlob(self):
    results = _RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/a*"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="DOWNLOAD"),
        )
    )

    self.assertLen(results, 4)
    self.assertEqual(
        results[1].stat_entry.pathspec.path,
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa",
    )
    self.assertEqual(_DecodeDataBlob(results[0]), "lolcat")
    self.assertEqual(
        results[3].stat_entry.pathspec.path,
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aba",
    )
    self.assertEqual(_DecodeDataBlob(results[2]), "4294967295")

  def testHashExactPath(self):
    results = _RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction.Hash(),
        )
    )

    self.assertLen(results, 1)
    self.assertEqual(results[0].hash_entry.num_bytes, 6)
    self.assertEqual(
        results[0].hash_entry.md5.HexDigest(),
        hashlib.md5(b"lolcat").hexdigest(),
    )
    self.assertEqual(
        results[0].hash_entry.sha1.HexDigest(),
        hashlib.sha1(b"lolcat").hexdigest(),
    )
    self.assertEqual(
        results[0].hash_entry.sha256.HexDigest(),
        hashlib.sha256(b"lolcat").hexdigest(),
    )

  def testHashSkipExactPath(self):
    results = _RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction.Hash(
                max_size=5, oversized_file_policy="SKIP"
            ),
        )
    )
    self.assertLen(results, 1)
    self.assertFalse(results[0].HasField("hash"))

  def testHashTruncateExactPath(self):
    results = _RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction.Hash(
                max_size=5, oversized_file_policy="HASH_TRUNCATED"
            ),
        )
    )

    self.assertLen(results, 1)
    self.assertEqual(
        results[0].hash_entry.md5.HexDigest(), hashlib.md5(b"lolca").hexdigest()
    )
    self.assertEqual(
        results[0].hash_entry.sha1.HexDigest(),
        hashlib.sha1(b"lolca").hexdigest(),
    )
    self.assertEqual(
        results[0].hash_entry.sha256.HexDigest(),
        hashlib.sha256(b"lolca").hexdigest(),
    )

  def testStatSingleGlob(self):
    results = _RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/a*"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT"),
        )
    )

    self.assertCountEqual(
        [res.stat_entry.pathspec.path for res in results],
        [
            "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa",
            "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aba",
        ],
    )

    self.assertCountEqual(
        [res.stat_entry.pathspec.path for res in results],
        [
            "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa",
            "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aba",
        ],
    )
    self.assertEqual(results[0].stat_entry.pathspec.pathtype, "REGISTRY")
    self.assertEqual(results[1].stat_entry.pathspec.pathtype, "REGISTRY")

  def testQuestionMarkMatchesOneCharacterOnly(self):
    results = _RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/a?"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT"),
        )
    )
    self.assertEmpty(results)

  def testQuestionMarkIsWildcard(self):
    results = _RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/a?a"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT"),
        )
    )

    self.assertCountEqual(
        [res.stat_entry.pathspec.path for res in results],
        [
            "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa",
            "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aba",
        ],
    )

  def testStatEmptyGlob(self):
    results = _RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/nonexistent*"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT"),
        )
    )
    self.assertEmpty(results)

  def testStatNonExistentPath(self):
    results = _RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/nonexistent"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT"),
        )
    )
    self.assertEmpty(results)

  def testStatRecursiveGlobDefaultLevel(self):
    results = _RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/**/aaa"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT"),
        )
    )
    self.assertCountEqual(
        [res.stat_entry.pathspec.path for res in results],
        [
            "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/aaa",
            "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/2/aaa",
            "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/2/3/aaa",
        ],
    )

  def testStatRecursiveGlobCustomLevel(self):
    results = _RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/**4/aaa"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT"),
        )
    )
    self.assertCountEqual(
        [res.stat_entry.pathspec.path for res in results],
        [
            "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/aaa",
            "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/2/aaa",
            "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/2/3/aaa",
            "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/2/3/4/aaa",
        ],
    )

  def testStatRecursiveGlobAndRegularGlob(self):
    results = _RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/**4/a*"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT"),
        )
    )
    self.assertCountEqual(
        [res.stat_entry.pathspec.path for res in results],
        [
            "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/aaa",
            "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/aba",
            "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/2/aaa",
            "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/2/aba",
            "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/2/3/aaa",
            "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/2/3/aba",
            "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/2/3/4/aaa",
            "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/2/3/4/aba",
        ],
    )

  def testRecursiveGlobCallsProgressWithoutMatches(self):
    progress = mock.MagicMock()

    with mock.patch.object(vfs_file_finder.VfsFileFinder, "Progress", progress):
      results = _RunFileFinder(
          rdf_file_finder.FileFinderArgs(
              paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/**4/nonexistent"],
              pathtype="REGISTRY",
              action=rdf_file_finder.FileFinderAction(action_type="STAT"),
          )
      )
    self.assertEmpty(results)

    # progress.call_count should rise linearly to the number of keys and
    # values in the test registry data.
    self.assertGreater(progress.call_count, 10)

  def testMetadataConditionMatch(self):
    results = _RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/*"],
            pathtype="REGISTRY",
            conditions=[
                rdf_file_finder.FileFinderCondition.Size(
                    min_file_size=6, max_file_size=6
                )
            ],
            action=rdf_file_finder.FileFinderAction(action_type="STAT"),
        )
    )
    self.assertCountEqual(
        [res.stat_entry.pathspec.path for res in results],
        ["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa"],
    )

  def testSkipsIfMetadataConditionDoesNotMatch(self):
    results = _RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/*"],
            pathtype="REGISTRY",
            conditions=[
                rdf_file_finder.FileFinderCondition.Size(
                    min_file_size=6, max_file_size=6
                ),
                rdf_file_finder.FileFinderCondition.Size(
                    min_file_size=0, max_file_size=0
                ),
            ],
            action=rdf_file_finder.FileFinderAction(action_type="STAT"),
        )
    )
    self.assertEmpty(results)

  def testContentConditionMatch(self):
    results = _RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/*"],
            pathtype="REGISTRY",
            conditions=[
                rdf_file_finder.FileFinderCondition.ContentsLiteralMatch(
                    literal=b"lol"
                )
            ],
            action=rdf_file_finder.FileFinderAction(action_type="STAT"),
        )
    )
    self.assertCountEqual(
        [res.stat_entry.pathspec.path for res in results],
        ["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa"],
    )
    self.assertCountEqual(
        [match.data for match in results[0].matches], [b"lol"]
    )

  def testSkipsIfContentConditionDoesNotMatch(self):
    results = _RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/*"],
            pathtype="REGISTRY",
            conditions=[
                rdf_file_finder.FileFinderCondition.ContentsLiteralMatch(
                    literal=b"lol"
                ),
                rdf_file_finder.FileFinderCondition.ContentsLiteralMatch(
                    literal=b"foo"
                ),
            ],
            action=rdf_file_finder.FileFinderAction(action_type="STAT"),
        )
    )
    self.assertEmpty(results)

  def testGlobbingKeyDoesNotYieldDuplicates(self):
    opts = globbing.PathOpts(pathtype=rdf_paths.PathSpec.PathType.REGISTRY)
    results = globbing.ExpandGlobs(
        r"HKEY_LOCAL_MACHINE\SOFTWARE\GRR_TEST\*\aaa", opts
    )
    self.assertCountEqual(
        results,
        [
            r"HKEY_LOCAL_MACHINE\SOFTWARE\GRR_TEST\1\aaa",
        ],
    )


class OsTest(absltest.TestCase):

  def testRecursiveRegexMatch(self) -> None:
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dir:
      nested_dir = os.path.join(temp_dir, "a", "b", "c")
      os.makedirs(nested_dir)
      with open(os.path.join(nested_dir, "foo.txt"), "w") as f:
        f.write("bar123")
      results = _RunFileFinder(
          rdf_file_finder.FileFinderArgs(
              paths=[os.path.join(temp_dir, "**", "*")],
              pathtype=rdf_paths.PathSpec.PathType.OS,
              conditions=[
                  rdf_file_finder.FileFinderCondition.ContentsRegexMatch(
                      regex=b"bar[0-9]+"
                  ),
              ],
              action=rdf_file_finder.FileFinderAction.Stat(),
          )
      )
      self.assertLen(results, 1)
      self.assertEqual(results[0].matches[0].data, b"bar123")
      files.FlushHandleCache()


class NtfsImageTestBase(absltest.TestCase):

  pathtype: Optional[rdf_structs.EnumNamedValue] = None

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    if platform.system() == "Windows":
      self._root = "C:"
      self._paths_expr = "C:/*"
    else:
      self._root = "/"
      self._paths_expr = "/*"

  def _MockGetRawDevice(self, path: str) -> tuple[rdf_paths.PathSpec, str]:
    ntfs_img_path = os.path.join(config.CONFIG["Test.data_dir"], "ntfs.img")

    pathspec = rdf_paths.PathSpec(
        path=ntfs_img_path,
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path_options=rdf_paths.PathSpec.Options.CASE_LITERAL,
    )

    if platform.system() == "Windows":
      return (pathspec, path[len(self._root) :])
    else:
      return (pathspec, path)

  def testListRootDirectory(self):
    with mock.patch.object(
        client_utils, "GetRawDevice", new=self._MockGetRawDevice
    ):
      results = _RunFileFinder(
          rdf_file_finder.FileFinderArgs(
              paths=[self._paths_expr],
              pathtype=self.pathtype,
              action=rdf_file_finder.FileFinderAction.Stat(),
          )
      )
      names = [
          result.stat_entry.pathspec.nested_path.path for result in results
      ]
      self.assertIn("/numbers.txt", names)
      files.FlushHandleCache()

  def testImplementationType(self) -> None:
    orig_vfs_open = vfs.VFSOpen

    def MockVfsOpen(pathspec, *args, **kwargs):
      self.assertEqual(
          pathspec.implementation_type,
          rdf_paths.PathSpec.ImplementationType.DIRECT,
      )
      return orig_vfs_open(pathspec, *args, **kwargs)

    with contextlib.ExitStack() as stack:
      stack.enter_context(mock.patch.object(vfs, "VFSOpen", new=MockVfsOpen))
      stack.enter_context(
          mock.patch.object(
              client_utils, "GetRawDevice", new=self._MockGetRawDevice
          )
      )
      _RunFileFinder(
          rdf_file_finder.FileFinderArgs(
              paths=[self._paths_expr],
              pathtype=self.pathtype,
              implementation_type=rdf_paths.PathSpec.ImplementationType.DIRECT,
              action=rdf_file_finder.FileFinderAction.Stat(),
          )
      )

    files.FlushHandleCache()


class NtfsTest(NtfsImageTestBase):
  pathtype = rdf_paths.PathSpec.PathType.NTFS


class TskTest(NtfsImageTestBase):
  pathtype = rdf_paths.PathSpec.PathType.TSK


# Abstract test case
del NtfsImageTestBase


def setUpModule() -> None:
  with temp.AutoTempFilePath(suffix=".yaml") as dummy_config_path:
    with flagsaver.flagsaver(config=dummy_config_path):
      config_lib.ParseConfigCommandLine()


if __name__ == "__main__":
  absltest.main()
