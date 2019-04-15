#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Tests the client file finder action."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import hashlib
import os
import platform
import unittest
import zlib
from absl import app
from absl.testing import absltest
import mock

from grr_response_client.client_actions import vfs_file_finder
from grr_response_client.client_actions.file_finder_utils import globbing

from grr_response_core import config
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util import precondition
from grr.test_lib import client_test_lib
from grr.test_lib import test_lib

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
    results.setdefault(compatibility.GetName(type(item)), []).append(item)
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

  def RunFileFinder(self, args):
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

  def testStatDoesNotFailForInaccessiblePath(self):
    results = self.RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SAM/SAM/FOOBAR"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT")))

    self.assertEmpty(results)

  def testCaseInsensitivitiy(self):
    results = self.RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/AaA"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT")))

    self.assertLen(results, 1)
    self.assertEqual(results[0].stat_entry.pathspec.path,
                     "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa")
    self.assertEqual(results[0].stat_entry.pathspec.pathtype, "REGISTRY")

  def testStatExactPath(self):
    results = self.RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT")))

    self.assertLen(results, 1)
    self.assertEqual(results[0].stat_entry.pathspec.path,
                     "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa")
    self.assertEqual(results[0].stat_entry.pathspec.pathtype, "REGISTRY")
    self.assertEqual(results[0].stat_entry.st_size, 6)

  def testStatExactPathInWindowsNativeFormat(self):
    results = self.RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=[r"HKEY_LOCAL_MACHINE\SOFTWARE\GRR_TEST\aaa"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT")))

    self.assertLen(results, 1)
    self.assertEqual(results[0].stat_entry.pathspec.path,
                     "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa")
    self.assertEqual(results[0].stat_entry.pathspec.pathtype, "REGISTRY")
    self.assertEqual(results[0].stat_entry.st_size, 6)

  def testStatLongUnicodeName(self):
    results = self.RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=[
                "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/{}".format(_LONG_KEY)
            ],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT")))

    self.assertLen(results, 1)
    self.assertEqual(
        results[0].stat_entry.pathspec.path,
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/{}".format(_LONG_KEY))
    self.assertEqual(results[0].stat_entry.pathspec.pathtype, "REGISTRY")

  def testStatKeyWithDefaultValue(self):
    results = self.RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT")))

    self.assertLen(results, 1)
    self.assertEqual(results[0].stat_entry.pathspec.path,
                     "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1")
    self.assertEqual(results[0].stat_entry.pathspec.pathtype, "REGISTRY")
    self.assertEqual(results[0].stat_entry.st_size, 13)

  def testDownloadExactPath(self):
    results = self.RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="DOWNLOAD")))

    self.assertLen(results, 2)
    self.assertEqual(_DecodeDataBlob(results[0]), "lolcat")
    self.assertEqual(results[1].stat_entry.pathspec.path,
                     "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa")

  def testDownloadUnicode(self):
    results = self.RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=[
                "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/{}".format(_LONG_KEY)
            ],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="DOWNLOAD")))

    self.assertLen(results, 2)
    res_by_type = _GroupItemsByType(results)

    self.assertEqual(
        _DecodeDataBlob(res_by_type["DataBlob"][0]), _LONG_STRING_VALUE)
    self.assertEqual(
        res_by_type["FileFinderResult"][0].stat_entry.pathspec.path,
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/{}".format(_LONG_KEY))

  def testDownloadDword(self):
    results = self.RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aba"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="DOWNLOAD")))

    self.assertLen(results, 2)
    res_by_type = _GroupItemsByType(results)

    self.assertEqual(_DecodeDataBlob(res_by_type["DataBlob"][0]), "4294967295")
    self.assertEqual(
        res_by_type["FileFinderResult"][0].stat_entry.pathspec.path,
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aba")

  def testDownloadGlob(self):
    results = self.RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/a*"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="DOWNLOAD")))

    self.assertLen(results, 4)
    self.assertEqual(results[1].stat_entry.pathspec.path,
                     "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa")
    self.assertEqual(_DecodeDataBlob(results[0]), "lolcat")
    self.assertEqual(results[3].stat_entry.pathspec.path,
                     "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aba")
    self.assertEqual(_DecodeDataBlob(results[2]), "4294967295")

  def testHashExactPath(self):
    results = self.RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction.Hash()))

    self.assertLen(results, 1)
    self.assertEqual(results[0].hash_entry.num_bytes, 6)
    self.assertEqual(results[0].hash_entry.md5.HexDigest(),
                     hashlib.md5("lolcat").hexdigest())
    self.assertEqual(results[0].hash_entry.sha1.HexDigest(),
                     hashlib.sha1("lolcat").hexdigest())
    self.assertEqual(results[0].hash_entry.sha256.HexDigest(),
                     hashlib.sha256("lolcat").hexdigest())

  def testHashSkipExactPath(self):
    results = self.RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction.Hash(
                max_size=5, oversized_file_policy="SKIP")))
    self.assertLen(results, 1)
    self.assertFalse(results[0].HasField("hash"))

  def testHashTruncateExactPath(self):
    results = self.RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction.Hash(
                max_size=5, oversized_file_policy="HASH_TRUNCATED")))

    self.assertLen(results, 1)
    self.assertEqual(results[0].hash_entry.md5.HexDigest(),
                     hashlib.md5("lolca").hexdigest())
    self.assertEqual(results[0].hash_entry.sha1.HexDigest(),
                     hashlib.sha1("lolca").hexdigest())
    self.assertEqual(results[0].hash_entry.sha256.HexDigest(),
                     hashlib.sha256("lolca").hexdigest())

  def testStatSingleGlob(self):
    results = self.RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/a*"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT")))

    self.assertCountEqual([res.stat_entry.pathspec.path for res in results], [
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa",
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aba",
    ])

    self.assertCountEqual([res.stat_entry.pathspec.path for res in results], [
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa",
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aba",
    ])
    self.assertEqual(results[0].stat_entry.pathspec.pathtype, "REGISTRY")
    self.assertEqual(results[1].stat_entry.pathspec.pathtype, "REGISTRY")

  def testQuestionMarkMatchesOneCharacterOnly(self):
    results = self.RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/a?"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT")))
    self.assertEmpty(results)

  def testQuestionMarkIsWildcard(self):
    results = self.RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/a?a"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT")))

    self.assertCountEqual([res.stat_entry.pathspec.path for res in results], [
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa",
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aba",
    ])

  def testStatEmptyGlob(self):
    results = self.RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/nonexistent*"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT")))
    self.assertEmpty(results)

  def testStatNonExistentPath(self):
    results = self.RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/nonexistent"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT")))
    self.assertEmpty(results)

  def testStatRecursiveGlobDefaultLevel(self):
    results = self.RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/**/aaa"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT")))
    self.assertCountEqual([res.stat_entry.pathspec.path for res in results], [
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/aaa",
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/2/aaa",
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/2/3/aaa",
    ])

  def testStatRecursiveGlobCustomLevel(self):
    results = self.RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/**4/aaa"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT")))
    self.assertCountEqual([res.stat_entry.pathspec.path for res in results], [
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/aaa",
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/2/aaa",
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/2/3/aaa",
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/2/3/4/aaa",
    ])

  def testStatRecursiveGlobAndRegularGlob(self):
    results = self.RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/**4/a*"],
            pathtype="REGISTRY",
            action=rdf_file_finder.FileFinderAction(action_type="STAT")))
    self.assertCountEqual([res.stat_entry.pathspec.path for res in results], [
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/aaa",
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/aba",
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/2/aaa",
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/2/aba",
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/2/3/aaa",
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/2/3/aba",
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/2/3/4/aaa",
        "/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/1/2/3/4/aba",
    ])

  def testMetadataConditionMatch(self):
    results = self.RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/*"],
            pathtype="REGISTRY",
            conditions=[
                rdf_file_finder.FileFinderCondition.Size(
                    min_file_size=6, max_file_size=6)
            ],
            action=rdf_file_finder.FileFinderAction(action_type="STAT")))
    self.assertCountEqual([res.stat_entry.pathspec.path for res in results],
                          ["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa"])

  def testSkipsIfMetadataConditionDoesNotMatch(self):
    results = self.RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/*"],
            pathtype="REGISTRY",
            conditions=[
                rdf_file_finder.FileFinderCondition.Size(
                    min_file_size=6, max_file_size=6),
                rdf_file_finder.FileFinderCondition.Size(
                    min_file_size=0, max_file_size=0),
            ],
            action=rdf_file_finder.FileFinderAction(action_type="STAT")))
    self.assertEmpty(results)

  def testContentConditionMatch(self):
    results = self.RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/*"],
            pathtype="REGISTRY",
            conditions=[
                rdf_file_finder.FileFinderCondition.ContentsLiteralMatch(
                    literal=b"lol")
            ],
            action=rdf_file_finder.FileFinderAction(action_type="STAT")))
    self.assertCountEqual([res.stat_entry.pathspec.path for res in results],
                          ["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/aaa"])
    self.assertCountEqual([match.data for match in results[0].matches],
                          [b"lol"])

  def testSkipsIfContentConditionDoesNotMatch(self):
    results = self.RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=["/HKEY_LOCAL_MACHINE/SOFTWARE/GRR_TEST/*"],
            pathtype="REGISTRY",
            conditions=[
                rdf_file_finder.FileFinderCondition.ContentsLiteralMatch(
                    literal=b"lol"),
                rdf_file_finder.FileFinderCondition.ContentsLiteralMatch(
                    literal=b"foo")
            ],
            action=rdf_file_finder.FileFinderAction(action_type="STAT")))
    self.assertEmpty(results)

  def testGlobbingKeyDoesNotYieldDuplicates(self):
    opts = globbing.PathOpts(pathtype="REGISTRY")
    results = globbing.ExpandGlobs(
        r"HKEY_LOCAL_MACHINE\SOFTWARE\GRR_TEST\*\aaa", opts)
    self.assertCountEqual(results, [
        r"HKEY_LOCAL_MACHINE\SOFTWARE\GRR_TEST\1\aaa",
    ])

  def testTSKFile(self):
    path = os.path.join(config.CONFIG["Test.data_dir"], "test_img.dd",
                        "Test Directory", "numbers.txt")
    results = self.RunFileFinder(
        rdf_file_finder.FileFinderArgs(
            paths=[path],
            pathtype="TSK",
            action=rdf_file_finder.FileFinderAction(action_type="STAT")))
    self.assertNotEmpty(results)

    last_path = results[0].stat_entry.pathspec
    while last_path.HasField("nested_path"):
      last_path = last_path.nested_path
    self.assertEndsWith(last_path.path, "numbers.txt")
    self.assertEqual(results[0].stat_entry.st_size, 3893)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
